from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .attacks import build_traffic
from .criticality import observable_criticality
from .defenses import admission_decision, canary_alert_score
from .embeddings import FeatureHashEmbedding
from .fixtures import FixtureCatalog, FixtureRecord, FixtureScenario, load_fixtures
from .memory import BoundedMemoryStore
from .sandbox import evaluate_symbolic_action
from .schemas import (
    EventKind,
    ExperimentConfig,
    ExperimentResult,
    MemoryKind,
    MemoryRecord,
    Query,
    SummaryMetrics,
    TrajectoryMetric,
)
from .trace import TraceRecorder, canonical_json

LOGICAL_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _logical_time(step: int) -> datetime:
    return LOGICAL_EPOCH + timedelta(seconds=step)


def _fixture_memory(
    record: FixtureRecord,
    *,
    session_id: str,
    event_time: int,
) -> MemoryRecord:
    return MemoryRecord(
        record_id=record.record_id,
        content=record.text,
        created_at=_logical_time(event_time),
        event_time=event_time,
        ingest_time=event_time,
        origin_id=record.origin,
        session_id=session_id,
        kind=MemoryKind.CRITICAL if record.critical else MemoryKind.BACKGROUND,
        importance=record.importance,
        predicted_criticality=observable_criticality(
            record.text,
            record.importance,
            record.origin,
        ),
        is_gold_critical=record.critical,
        provenance={
            "fixture_record_id": record.record_id,
            "synthetic": True,
        },
    )


def _run_id(config: ExperimentConfig, catalog: FixtureCatalog) -> str:
    body = canonical_json(
        {
            "engine": "chaffmem-python-v1",
            "config": config.model_dump(mode="json"),
            "fixture_digest": catalog.digest,
        }
    )
    return f"run-{hashlib.sha256(body.encode('utf-8')).hexdigest()[:20]}"


def _benign_utility(
    store: BoundedMemoryStore,
    record: FixtureRecord | None,
    step: int,
    top_k: int,
) -> float:
    if record is None or top_k == 0:
        return 0.0
    items = store.query(Query(text=record.text, top_k=top_k, event_time=step))
    return float(any(item.record.record_id == record.record_id for item in items))


def _observe(
    *,
    store: BoundedMemoryStore,
    scenario: FixtureScenario,
    step: int,
    config: ExperimentConfig,
    accepted: int,
    rejected: int,
    benign_probe: FixtureRecord | None,
    trace: TraceRecorder,
) -> TrajectoryMetric:
    query = Query(text=scenario.canary_query, top_k=config.top_k, event_time=step)
    rank = store.rank_of(scenario.target_record_id, query)
    retrieved = store.query(query)
    physical = store.contains(scenario.target_record_id)
    retrieval_available = any(
        item.record.record_id == scenario.target_record_id for item in retrieved
    )
    behavior = evaluate_symbolic_action(
        retrieved,
        scenario.target_record_id,
        scenario.expected_terms,
    )
    alert_score = canary_alert_score(rank, config.top_k)
    benign_utility = _benign_utility(store, benign_probe, step, config.top_k)
    trace.append(
        step,
        EventKind.RETRIEVAL,
        "evaluate_canary",
        {
            "query": scenario.canary_query,
            "top_k": config.top_k,
            "target_rank": rank,
            "target_retrieved": retrieval_available,
            "retrieved_record_ids": [item.record.record_id for item in retrieved],
            "alert_score": alert_score,
        },
    )
    trace.append(
        step,
        EventKind.BEHAVIOR,
        "grade_symbolic_action",
        {
            "safe": behavior.safe,
            "selected_record_id": behavior.selected_record_id,
            "reason": behavior.reason,
        },
    )
    return TrajectoryMetric(
        step=step,
        physical_available=physical,
        retrieval_available=retrieval_available,
        behavioral_available=behavior.safe,
        target_rank=rank,
        occupancy=len(store),
        capacity=config.capacity,
        accepted_writes=accepted,
        rejected_writes=rejected,
        alert_score=alert_score,
        benign_utility=benign_utility,
    )


def run_experiment(
    config: ExperimentConfig,
    *,
    fixture_path: str | Path | None = None,
) -> ExperimentResult:
    catalog = load_fixtures(fixture_path)
    scenario = catalog.scenario(config.domain)
    embedding = FeatureHashEmbedding(config.embedding_dim)
    eviction_rng = random.Random(f"{config.seed}:eviction:{config.policy.value}")
    store = BoundedMemoryStore(config, embedding, eviction_rng)
    trace = TraceRecorder()
    run_id = _run_id(config, catalog)
    query_vector = embedding.encode(scenario.canary_query)

    target = _fixture_memory(scenario.target, session_id=run_id, event_time=0)
    target_outcome = store.write(target, 0, query_vector)
    trace.append(
        0,
        EventKind.SEED,
        "seed_target",
        {
            "record_id": target.record_id,
            "accepted": target_outcome.accepted,
            "reason": target_outcome.reason,
        },
    )

    background_count = min(config.background_records, len(scenario.background))
    for fixture_record in scenario.background[:background_count]:
        record = _fixture_memory(
            fixture_record,
            session_id=run_id,
            event_time=0,
        )
        outcome = store.write(record, 0, query_vector)
        trace.append(
            0,
            EventKind.SEED,
            "seed_background",
            {
                "record_id": record.record_id,
                "accepted": outcome.accepted,
                "evicted_record_id": (
                    outcome.evicted.record_id if outcome.evicted is not None else None
                ),
            },
        )

    accepted = 0
    rejected = 0
    trajectory: list[TrajectoryMetric] = []
    benign_probe = scenario.background[0] if background_count else None
    trajectory.append(
        _observe(
            store=store,
            scenario=scenario,
            step=0,
            config=config,
            accepted=accepted,
            rejected=rejected,
            benign_probe=benign_probe,
            trace=trace,
        )
    )

    traffic = build_traffic(config, catalog, scenario, embedding)
    for step, incoming in enumerate(traffic, start=1):
        incoming.session_id = run_id
        incoming_vector = embedding.encode(incoming.content)
        previous_rank = trajectory[-1].target_rank
        previous_alert = canary_alert_score(previous_rank, config.top_k)
        decision = admission_decision(
            incoming,
            incoming_vector,
            store.values(),
            config,
            embedding,
            previous_alert,
        )
        trace.append(
            step,
            EventKind.DEFENSE,
            "admission_decision",
            {
                "record_id": incoming.record_id,
                "accepted": decision.accepted,
                "reason": decision.reason,
                "observed_value": decision.observed_value,
            },
        )
        if decision.accepted:
            accepted += 1
            outcome = store.write(incoming, step, query_vector)
            trace.append(
                step,
                EventKind.WRITE,
                "write_record",
                {
                    "record_id": incoming.record_id,
                    "reason": outcome.reason,
                    "retained_after_write": store.contains(incoming.record_id),
                },
            )
            if outcome.evicted is not None:
                trace.append(
                    step,
                    EventKind.EVICTION,
                    "evict_record",
                    {
                        "record_id": outcome.evicted.record_id,
                        "reason": outcome.evicted.reason,
                        "score": outcome.evicted.score,
                        "protected_overflow": outcome.evicted.protected_overflow,
                    },
                )
        else:
            rejected += 1
        trajectory.append(
            _observe(
                store=store,
                scenario=scenario,
                step=step,
                config=config,
                accepted=accepted,
                rejected=rejected,
                benign_probe=benign_probe,
                trace=trace,
            )
        )

    final_snapshot = store.snapshot()
    trace.append(
        config.budget,
        EventKind.CHECKPOINT,
        "final_snapshot",
        {
            "snapshot_hash": final_snapshot["snapshot_hash"],
            "occupancy": len(store),
        },
    )
    observations = max(1, len(trajectory))
    first_failure = next(
        (item.step for item in trajectory if not item.retrieval_available),
        None,
    )
    summary = SummaryMetrics(
        critical_recall=sum(item.retrieval_available for item in trajectory) / observations,
        physical_availability=sum(item.physical_available for item in trajectory) / observations,
        behavioral_availability=sum(item.behavioral_available for item in trajectory)
        / observations,
        benign_utility=sum(item.benign_utility for item in trajectory) / observations,
        final_target_rank=trajectory[-1].target_rank,
        writes_to_failure=first_failure,
        accepted_writes=accepted,
        rejected_writes=rejected,
        peak_alert_score=max(item.alert_score for item in trajectory),
    )
    final_records = [
        item.record for item in sorted(store.values(), key=lambda stored: stored.record_id)
    ]
    return ExperimentResult(
        run_id=run_id,
        config=config,
        target_record_id=scenario.target_record_id,
        final_records=final_records,
        trajectory=trajectory,
        trace=trace.events,
        snapshot=final_snapshot,
        summary=summary,
        digest=trace.digest,
    )
