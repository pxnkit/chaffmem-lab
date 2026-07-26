from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RECORD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalized_hash(content: str) -> str:
    normalized = " ".join(content.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class MemoryKind(StrEnum):
    CRITICAL = "critical"
    BACKGROUND = "background"
    CHAFF = "chaff"
    CORRECTION = "correction"


class PolicyName(StrEnum):
    FIFO = "fifo"
    LRU = "lru"
    RESERVOIR = "reservoir"
    IMPORTANCE = "importance"
    SIMILARITY = "similarity"
    MMR = "mmr"
    HYBRID = "hybrid"


class AttackName(StrEnum):
    NONE = "none"
    RANDOM = "random"
    SAME_DOMAIN = "same_domain"
    SEMANTIC_NEAREST = "semantic_nearest"
    DIVERSE = "diverse"
    BURST = "burst"
    SLOW_DRIP = "slow_drip"
    SYBIL = "sybil"
    ADAPTIVE = "adaptive"
    TRANSFER = "transfer"
    MIXED = "mixed"


class DefenseName(StrEnum):
    NONE = "none"
    DUPLICATE_CONTROL = "duplicate_control"
    ORIGIN_QUOTA = "origin_quota"
    SEMANTIC_COVERAGE = "semantic_coverage"
    CRITICALITY_RETENTION = "criticality_retention"
    PROTECTED_COVERAGE = "protected_coverage"
    CANARY_MONITOR = "canary_monitor"
    ADAPTIVE = "adaptive"
    ORACLE_PIN = "oracle_pin"


class KnowledgeLevel(StrEnum):
    ZERO = "zero"
    QUERY = "query"
    CONCEPT = "concept"
    BLACK_BOX = "black_box"
    WHITE_BOX = "white_box"
    POLICY = "policy"
    TRANSFER = "transfer"


class DomainName(StrEnum):
    TRAVEL = "travel"
    HEALTHCARE = "healthcare"
    OPERATIONS = "operations"
    FINANCE = "finance"


class EventKind(StrEnum):
    SEED = "seed"
    WRITE = "write"
    DEFENSE = "defense"
    EVICTION = "eviction"
    RETRIEVAL = "retrieval"
    BEHAVIOR = "behavior"
    CHECKPOINT = "checkpoint"


class MemoryRecord(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    record_id: str = Field(min_length=1, max_length=128)
    content: str = Field(max_length=4096)
    normalized_content_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    created_at: datetime = Field(default_factory=utc_now)
    event_time: int = 0
    ingest_time: int = 0
    origin_id: str = Field(default="local", min_length=1, max_length=128)
    session_id: str = Field(default="default", min_length=1, max_length=128)
    kind: MemoryKind = MemoryKind.BACKGROUND
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    predicted_criticality: float = Field(default=0.0, ge=0.0, le=1.0)
    is_gold_critical: bool = False
    expires_at: int | None = None
    supersedes: str | None = None
    embedding: list[float] | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_record(self) -> MemoryRecord:
        if not RECORD_ID_PATTERN.fullmatch(self.record_id):
            raise ValueError("record_id contains unsupported characters")
        expected = normalized_hash(self.content)
        if self.normalized_content_hash is None:
            object.__setattr__(self, "normalized_content_hash", expected)
        elif self.normalized_content_hash != expected:
            raise ValueError("normalized_content_hash does not match content")
        if self.embedding is not None and not all(math.isfinite(value) for value in self.embedding):
            raise ValueError("embedding values must be finite")
        if self.expires_at is not None and self.expires_at < self.event_time:
            raise ValueError("expires_at cannot precede event_time")
        if self.supersedes is not None and not RECORD_ID_PATTERN.fullmatch(self.supersedes):
            raise ValueError("supersedes contains unsupported characters")
        return self


class Query(StrictModel):
    text: str = Field(max_length=4096)
    top_k: int = Field(default=5, ge=0, le=100)
    event_time: int = Field(default=0, ge=0)
    include_expired: bool = False


class RetrievalItem(StrictModel):
    record: MemoryRecord
    score: float
    rank: int = Field(ge=1)
    reason: str

    @model_validator(mode="after")
    def finite_score(self) -> RetrievalItem:
        if not math.isfinite(self.score):
            raise ValueError("retrieval score must be finite")
        return self


class TraceEvent(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    event_id: str
    step: int = Field(ge=0)
    kind: EventKind
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    event_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ExperimentConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    experiment_id: str | None = Field(default=None, max_length=80)
    policy: PolicyName = PolicyName.LRU
    attack: AttackName = AttackName.SEMANTIC_NEAREST
    defense: DefenseName = DefenseName.ADAPTIVE
    knowledge: KnowledgeLevel = KnowledgeLevel.CONCEPT
    domain: DomainName = DomainName.TRAVEL
    capacity: int = Field(default=24, ge=0, le=100_000)
    top_k: int = Field(default=5, ge=0, le=100)
    budget: int = Field(default=36, ge=0, le=100_000)
    seed: int = Field(default=17, ge=0, le=2**32 - 1)
    embedding_dim: int = Field(default=128, ge=8, le=4096)
    background_records: int = Field(default=10, ge=0, le=10_000)
    origin_quota: int = Field(default=6, ge=1, le=10_000)
    semantic_cell_quota: int = Field(default=4, ge=1, le=10_000)
    canary_threshold: float = Field(default=0.58, ge=0.0, le=1.0)
    criticality_threshold: float = Field(default=0.82, ge=0.0, le=1.0)
    quick: bool = True

    @model_validator(mode="after")
    def normalize_limits(self) -> ExperimentConfig:
        valid_experiment_id = self.experiment_id is None or (
            re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}",
                self.experiment_id,
            )
            is not None
        )
        if not valid_experiment_id:
            raise ValueError("experiment_id contains unsupported characters")
        return self


class TrajectoryMetric(StrictModel):
    step: int = Field(ge=0)
    physical_available: bool
    retrieval_available: bool
    behavioral_available: bool
    target_rank: int | None = Field(default=None, ge=1)
    occupancy: int = Field(ge=0)
    capacity: int = Field(ge=0)
    accepted_writes: int = Field(ge=0)
    rejected_writes: int = Field(ge=0)
    alert_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic warning score. It is not a calibrated probability.",
    )
    benign_utility: float = Field(ge=0.0, le=1.0)


class SummaryMetrics(StrictModel):
    critical_recall: float = Field(ge=0.0, le=1.0)
    physical_availability: float = Field(ge=0.0, le=1.0)
    behavioral_availability: float = Field(ge=0.0, le=1.0)
    benign_utility: float = Field(ge=0.0, le=1.0)
    final_target_rank: int | None = Field(default=None, ge=1)
    writes_to_failure: int | None = Field(default=None, ge=0)
    accepted_writes: int = Field(ge=0)
    rejected_writes: int = Field(ge=0)
    peak_alert_score: float = Field(ge=0.0, le=1.0)


class ExperimentResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    config: ExperimentConfig
    target_record_id: str
    final_records: list[MemoryRecord]
    trajectory: list[TrajectoryMetric]
    trace: list[TraceEvent]
    snapshot: dict[str, Any]
    summary: SummaryMetrics
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class ExperimentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentState(StrictModel):
    experiment_id: str
    status: ExperimentStatus
    config: ExperimentConfig
    run_id: str | None = None
    error: str | None = None


class CatalogItem(StrictModel):
    id: str
    name: str
    description: str
    oracle: bool = False


class MemoryWriteRequest(StrictModel):
    store_id: str = Field(default="default", pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    record: MemoryRecord


class MemoryQueryRequest(StrictModel):
    store_id: str = Field(default="default", pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    query: Query


class CanaryRequest(StrictModel):
    store_id: str = Field(default="default", pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    target_record_id: str
    query: Query


class ExperimentCreateRequest(StrictModel):
    config: ExperimentConfig
