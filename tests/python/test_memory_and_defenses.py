from __future__ import annotations

import random

import pytest

from chaffmem.defenses import (
    admission_decision,
    canary_alert_score,
    protected_record_ids,
)
from chaffmem.embeddings import FeatureHashEmbedding
from chaffmem.memory import BoundedMemoryStore
from chaffmem.schemas import (
    DefenseName,
    ExperimentConfig,
    MemoryRecord,
    PolicyName,
    Query,
)


def _record(index: int, **updates: object) -> MemoryRecord:
    values: dict[str, object] = {
        "record_id": f"record-{index}",
        "content": f"ordinary note number {index}",
        "event_time": index,
        "ingest_time": index,
        "origin_id": "origin-a",
    }
    values.update(updates)
    return MemoryRecord.model_validate(values)


def test_fifo_query_duplicate_and_snapshot() -> None:
    config = ExperimentConfig(capacity=2, policy=PolicyName.FIFO, top_k=2)
    store = BoundedMemoryStore(config)
    query_vector = store.embedding.encode("ordinary note")
    first = _record(1)
    assert store.write(first, 1, query_vector).accepted
    duplicate = store.write(first.model_copy(deep=True), 1, query_vector)
    assert duplicate.accepted
    conflict = _record(1, content="different")
    assert not store.write(conflict, 1, query_vector).accepted
    store.write(_record(2), 2, query_vector)
    outcome = store.write(_record(3), 3, query_vector)
    assert outcome.evicted is not None
    assert outcome.evicted.record_id == first.record_id
    items = store.query(Query(text="ordinary note number 3", top_k=1, event_time=4))
    assert items[0].record.record_id == "record-3"
    snapshot = store.snapshot()
    restored = BoundedMemoryStore.restore(snapshot)
    assert restored.snapshot()["snapshot_hash"] == snapshot["snapshot_hash"]
    snapshot["snapshot_hash"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot hash"):
        BoundedMemoryStore.restore(snapshot)


def test_zero_capacity_and_supersession() -> None:
    zero = BoundedMemoryStore(ExperimentConfig(capacity=0))
    vector = zero.embedding.encode("")
    outcome = zero.write(_record(1), 1, vector)
    assert outcome.accepted
    assert outcome.evicted is not None
    assert len(zero) == 0

    store = BoundedMemoryStore(ExperimentConfig(capacity=2))
    store.write(_record(1), 1, vector)
    replacement = _record(2, supersedes="record-1")
    outcome = store.write(replacement, 2, vector)
    assert outcome.superseded_record_id == "record-1"
    assert not store.contains("record-1")


@pytest.mark.parametrize(
    "policy",
    [
        PolicyName.LRU,
        PolicyName.RESERVOIR,
        PolicyName.IMPORTANCE,
        PolicyName.SIMILARITY,
        PolicyName.MMR,
        PolicyName.HYBRID,
    ],
)
def test_every_policy_is_bounded_and_deterministic(policy: PolicyName) -> None:
    config = ExperimentConfig(capacity=3, policy=policy, seed=9)

    def run_once() -> list[str]:
        store = BoundedMemoryStore(config, random_source=random.Random(9))
        vector = store.embedding.encode("ordinary")
        for index in range(1, 11):
            store.write(
                _record(index, importance=index / 20),
                index,
                vector,
            )
        return sorted(record.record_id for record in store.values())

    assert run_once() == run_once()
    assert len(run_once()) == 3


def test_admission_controls_and_protection() -> None:
    embedding = FeatureHashEmbedding(32)
    existing = _record(
        1,
        embedding=embedding.encode_list("same note"),
        predicted_criticality=0.95,
        is_gold_critical=True,
    )
    store = BoundedMemoryStore(ExperimentConfig(embedding_dim=32))
    store.write(existing, 0, embedding.encode("query"))
    incoming = _record(2, content="same note", origin_id="origin-a")
    vector = embedding.encode(incoming.content)

    duplicate_config = ExperimentConfig(
        embedding_dim=32,
        defense=DefenseName.DUPLICATE_CONTROL,
    )
    assert not admission_decision(
        incoming,
        vector,
        store.values(),
        duplicate_config,
        embedding,
        0.0,
    ).accepted

    quota_config = ExperimentConfig(
        embedding_dim=32,
        defense=DefenseName.ORIGIN_QUOTA,
        origin_quota=1,
    )
    assert not admission_decision(
        incoming,
        vector,
        store.values(),
        quota_config,
        embedding,
        0.0,
    ).accepted

    adaptive = ExperimentConfig(
        embedding_dim=32,
        defense=DefenseName.ADAPTIVE,
        semantic_cell_quota=1,
        canary_threshold=0.5,
    )
    assert not admission_decision(
        incoming,
        vector,
        store.values(),
        adaptive,
        embedding,
        0.9,
    ).accepted
    protected = protected_record_ids(store.values(), adaptive)
    assert existing.record_id in protected
    assert canary_alert_score(None, 4) == 0.99
    assert canary_alert_score(1, 4) < canary_alert_score(4, 4)
