from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .embeddings import FeatureHashEmbedding
from .schemas import DefenseName, ExperimentConfig, MemoryRecord


class StoredLike(Protocol):
    @property
    def record_id(self) -> str: ...

    @property
    def origin_id(self) -> str: ...

    @property
    def normalized_content_hash(self) -> str: ...

    @property
    def predicted_criticality(self) -> float: ...

    @property
    def is_gold_critical(self) -> bool: ...

    @property
    def vector(self) -> NDArray[np.float64]: ...


@dataclass(frozen=True)
class AdmissionDecision:
    accepted: bool
    reason: str
    observed_value: float | int | str | None = None


def canary_alert_score(rank: int | None, top_k: int) -> float:
    """Return a bounded heuristic warning score, not a calibrated probability."""
    if rank is None or top_k == 0:
        return 0.99
    ratio = rank / max(1, top_k)
    return max(0.04, min(0.99, 0.06 + 0.62 * ratio * ratio))


def admission_decision(
    incoming: MemoryRecord,
    incoming_vector: NDArray[np.float64],
    records: Iterable[StoredLike],
    config: ExperimentConfig,
    embedding: FeatureHashEmbedding,
    alert_score: float,
) -> AdmissionDecision:
    retained = list(records)
    if config.defense == DefenseName.NONE:
        return AdmissionDecision(True, "no write-time defense")

    if config.defense == DefenseName.DUPLICATE_CONTROL:
        for record in retained:
            if record.normalized_content_hash == incoming.normalized_content_hash:
                return AdmissionDecision(False, "exact duplicate content hash", 1.0)
            similarity = embedding.similarity(record.vector, incoming_vector)
            if similarity >= 0.965:
                return AdmissionDecision(False, "near-duplicate semantic record", similarity)
        return AdmissionDecision(True, "duplicate checks passed")

    if config.defense == DefenseName.ORIGIN_QUOTA:
        count = sum(record.origin_id == incoming.origin_id for record in retained)
        if count >= config.origin_quota:
            return AdmissionDecision(False, "per-origin quota reached", count)
        return AdmissionDecision(True, "origin remains below quota", count)

    if config.defense in {DefenseName.SEMANTIC_COVERAGE, DefenseName.PROTECTED_COVERAGE}:
        incoming_cell = embedding.semantic_cell(incoming_vector)
        count = sum(embedding.semantic_cell(record.vector) == incoming_cell for record in retained)
        if count >= config.semantic_cell_quota:
            return AdmissionDecision(False, "semantic-cell quota reached", incoming_cell)
        return AdmissionDecision(True, "semantic cell has available coverage", count)

    if config.defense == DefenseName.ADAPTIVE and alert_score >= config.canary_threshold:
        local_count = sum(
            embedding.similarity(record.vector, incoming_vector) >= 0.70 for record in retained
        )
        adaptive_quota = max(1, min(config.semantic_cell_quota, config.top_k or 1))
        if local_count >= adaptive_quota:
            return AdmissionDecision(
                False,
                "canary-guided local admission limit reached",
                local_count,
            )
        return AdmissionDecision(True, "adaptive local pressure remains below limit", local_count)

    return AdmissionDecision(True, "defense observes the write without blocking")


def protected_record_ids(
    records: Iterable[StoredLike],
    config: ExperimentConfig,
) -> set[str]:
    protected: set[str] = set()
    for record in records:
        oracle = config.defense == DefenseName.ORACLE_PIN and record.is_gold_critical
        predicted = (
            config.defense
            in {
                DefenseName.CRITICALITY_RETENTION,
                DefenseName.PROTECTED_COVERAGE,
                DefenseName.CANARY_MONITOR,
                DefenseName.ADAPTIVE,
            }
            and record.predicted_criticality >= config.criticality_threshold
        )
        if oracle or predicted:
            protected.add(record.record_id)
    return protected
