from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .embeddings import FeatureHashEmbedding
from .schemas import PolicyName


class StoredLike(Protocol):
    @property
    def record_id(self) -> str: ...

    @property
    def importance(self) -> float: ...

    @property
    def predicted_criticality(self) -> float: ...

    @property
    def sequence(self) -> int: ...

    @property
    def last_access(self) -> int: ...

    @property
    def vector(self) -> NDArray[np.float64]: ...


@dataclass(frozen=True)
class EvictionDecision:
    record_id: str
    reason: str
    score: float
    protected_overflow: bool = False


def _crowding(
    candidate: StoredLike,
    records: list[StoredLike],
    embedding: FeatureHashEmbedding,
) -> float:
    others = [record for record in records if record.record_id != candidate.record_id]
    if not others:
        return 0.0
    return max(embedding.similarity(candidate.vector, other.vector) for other in others)


def select_eviction(
    records: Mapping[str, StoredLike],
    policy: PolicyName,
    random_source: random.Random,
    embedding: FeatureHashEmbedding,
    query_vector: NDArray[np.float64],
    step: int,
    protected_ids: set[str] | None = None,
) -> EvictionDecision:
    if not records:
        raise ValueError("cannot evict from an empty store")
    protected = protected_ids or set()
    all_records = sorted(records.values(), key=lambda item: item.record_id)
    candidates = [record for record in all_records if record.record_id not in protected]
    protected_overflow = False
    if not candidates:
        candidates = all_records
        protected_overflow = True

    if policy == PolicyName.FIFO:
        chosen = min(candidates, key=lambda item: (item.sequence, item.record_id))
        return EvictionDecision(
            chosen.record_id,
            "oldest insertion sequence",
            float(chosen.sequence),
            protected_overflow,
        )

    if policy == PolicyName.LRU:
        chosen = min(candidates, key=lambda item: (item.last_access, item.sequence, item.record_id))
        return EvictionDecision(
            chosen.record_id,
            "least recent access",
            float(chosen.last_access),
            protected_overflow,
        )

    if policy == PolicyName.RESERVOIR:
        chosen = candidates[random_source.randrange(len(candidates))]
        return EvictionDecision(
            chosen.record_id,
            "seeded reservoir draw",
            float(candidates.index(chosen)),
            protected_overflow,
        )

    if policy == PolicyName.IMPORTANCE:
        chosen = min(
            candidates,
            key=lambda item: (
                max(item.importance, item.predicted_criticality),
                item.sequence,
                item.record_id,
            ),
        )
        score = max(chosen.importance, chosen.predicted_criticality)
        return EvictionDecision(
            chosen.record_id,
            "lowest retention importance",
            score,
            protected_overflow,
        )

    if policy == PolicyName.SIMILARITY:
        scored = [
            (embedding.similarity(record.vector, query_vector), record) for record in candidates
        ]
        score, chosen = min(
            scored,
            key=lambda item: (item[0], item[1].sequence, item[1].record_id),
        )
        return EvictionDecision(
            chosen.record_id,
            "lowest target-query similarity",
            score,
            protected_overflow,
        )

    if policy == PolicyName.MMR:
        scored = [(_crowding(record, candidates, embedding), record) for record in candidates]
        score, chosen = max(
            scored,
            key=lambda item: (item[0], -item[1].sequence, item[1].record_id),
        )
        return EvictionDecision(
            chosen.record_id,
            "highest semantic crowding",
            score,
            protected_overflow,
        )

    scored_hybrid: list[tuple[float, StoredLike]] = []
    denominator = max(1, step)
    for record in candidates:
        crowding = _crowding(record, candidates, embedding)
        recency = max(0.0, min(1.0, record.last_access / denominator))
        retention = (
            0.45 * max(record.importance, record.predicted_criticality)
            + 0.25 * recency
            + 0.30 * (1.0 - max(0.0, crowding))
        )
        scored_hybrid.append((retention, record))
    score, chosen = min(
        scored_hybrid,
        key=lambda item: (item[0], item[1].sequence, item[1].record_id),
    )
    return EvictionDecision(
        chosen.record_id,
        "lowest hybrid retention score",
        score,
        protected_overflow,
    )
