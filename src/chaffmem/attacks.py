from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from .criticality import observable_criticality
from .embeddings import FeatureHashEmbedding
from .fixtures import FixtureCatalog, FixtureRecord, FixtureScenario
from .schemas import AttackName, ExperimentConfig, KnowledgeLevel, MemoryKind, MemoryRecord

LOGICAL_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _logical_time(step: int) -> datetime:
    return LOGICAL_EPOCH + timedelta(seconds=step)


def _candidate_records(
    config: ExperimentConfig,
    catalog: FixtureCatalog,
    scenario: FixtureScenario,
) -> list[FixtureRecord]:
    all_background = [record for item in catalog.scenarios for record in item.background]
    if config.knowledge == KnowledgeLevel.ZERO:
        return all_background
    if config.knowledge in {KnowledgeLevel.CONCEPT, KnowledgeLevel.TRANSFER}:
        return list(scenario.background)
    return all_background + list(scenario.background)


def build_traffic(
    config: ExperimentConfig,
    catalog: FixtureCatalog,
    scenario: FixtureScenario,
    embedding: FeatureHashEmbedding,
) -> list[MemoryRecord]:
    """Pre-generate a bounded stream so comparison defenses see identical writes."""
    rng = random.Random(f"{config.seed}:traffic:{config.attack.value}:{config.knowledge.value}")
    candidates = _candidate_records(config, catalog, scenario)
    query_vector = embedding.encode(scenario.canary_query)
    ranked = sorted(
        candidates,
        key=lambda item: (
            -embedding.similarity(query_vector, embedding.encode(item.text)),
            item.record_id,
        ),
    )

    records: list[MemoryRecord] = []
    for index in range(1, config.budget + 1):
        strategy = config.attack
        if strategy == AttackName.NONE:
            base = candidates[(index - 1) % len(candidates)]
        elif strategy == AttackName.RANDOM:
            base = candidates[rng.randrange(len(candidates))]
        elif strategy in {
            AttackName.SAME_DOMAIN,
            AttackName.BURST,
            AttackName.SLOW_DRIP,
        }:
            base = scenario.background[(index - 1) % len(scenario.background)]
        elif strategy in {
            AttackName.SEMANTIC_NEAREST,
            AttackName.ADAPTIVE,
        }:
            window = max(1, min(len(ranked), 1 + index // 6))
            base = ranked[(index - 1) % window]
        elif strategy == AttackName.DIVERSE:
            base = candidates[(index * 3 + rng.randrange(len(candidates))) % len(candidates)]
        elif strategy == AttackName.TRANSFER:
            scenario_ids = {record.record_id for record in scenario.records}
            other = [item for item in candidates if item.record_id not in scenario_ids]
            base = (other or candidates)[(index - 1) % len(other or candidates)]
        else:
            base = ranked[(index - 1) % max(1, min(3, len(ranked)))]

        domain_context = ""
        query_informed = config.knowledge in {
            KnowledgeLevel.QUERY,
            KnowledgeLevel.BLACK_BOX,
            KnowledgeLevel.WHITE_BOX,
            KnowledgeLevel.POLICY,
        }
        if (
            strategy
            in {
                AttackName.SAME_DOMAIN,
                AttackName.SEMANTIC_NEAREST,
                AttackName.ADAPTIVE,
                AttackName.MIXED,
            }
            and query_informed
        ):
            domain_context = (
                f" Search catalog label: {scenario.canary_query}. "
                "This synthetic label contains no itinerary or scheduling claim."
            )
        elif (
            strategy
            in {
                AttackName.SAME_DOMAIN,
                AttackName.SEMANTIC_NEAREST,
                AttackName.ADAPTIVE,
                AttackName.MIXED,
            }
            and config.knowledge != KnowledgeLevel.ZERO
        ):
            tags = " ".join(scenario.target.tags[:2])
            domain_context = f" Related index terms: {tags}."
        content = (
            f"{base.text}{domain_context} "
            f"Synthetic observation {index:04d} for bounded local testing."
        )
        if strategy == AttackName.SYBIL:
            origin = f"synthetic-origin-{index % max(2, config.origin_quota + 1):02d}"
        else:
            origin = base.origin
        kind = MemoryKind.BACKGROUND if strategy == AttackName.NONE else MemoryKind.CHAFF
        predicted_criticality = observable_criticality(content, min(0.45, base.importance), origin)
        records.append(
            MemoryRecord(
                record_id=f"traffic-{strategy.value}-{index:05d}",
                content=content,
                created_at=_logical_time(index),
                event_time=index,
                ingest_time=index,
                origin_id=origin,
                session_id="reference",
                kind=kind,
                importance=min(0.45, base.importance),
                predicted_criticality=predicted_criticality,
                is_gold_critical=False,
                provenance={
                    "fixture_record_id": base.record_id,
                    "generator": "bounded-synthetic-v1",
                    "attack_label_for_evaluation_only": strategy.value,
                },
            )
        )
    return records
