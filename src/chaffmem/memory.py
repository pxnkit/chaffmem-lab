from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .defenses import protected_record_ids
from .embeddings import FeatureHashEmbedding
from .policies import EvictionDecision, select_eviction
from .schemas import ExperimentConfig, MemoryRecord, Query, RetrievalItem


@dataclass
class StoredMemory:
    record: MemoryRecord
    vector: NDArray[np.float64]
    sequence: int
    last_access: int
    retrieval_count: int = 0

    @property
    def record_id(self) -> str:
        return self.record.record_id

    @property
    def origin_id(self) -> str:
        return self.record.origin_id

    @property
    def normalized_content_hash(self) -> str:
        assert self.record.normalized_content_hash is not None
        return self.record.normalized_content_hash

    @property
    def importance(self) -> float:
        return self.record.importance

    @property
    def predicted_criticality(self) -> float:
        return self.record.predicted_criticality

    @property
    def is_gold_critical(self) -> bool:
        return self.record.is_gold_critical


@dataclass(frozen=True)
class WriteOutcome:
    accepted: bool
    reason: str
    record_id: str
    evicted: EvictionDecision | None = None
    superseded_record_id: str | None = None


class BoundedMemoryStore:
    def __init__(
        self,
        config: ExperimentConfig,
        embedding: FeatureHashEmbedding | None = None,
        random_source: random.Random | None = None,
    ) -> None:
        self.config = config
        self.embedding = embedding or FeatureHashEmbedding(config.embedding_dim)
        self.random = random_source or random.Random(config.seed)
        self.records: dict[str, StoredMemory] = {}
        self.sequence = 0
        self.accepted_stream_count = 0

    def __len__(self) -> int:
        return len(self.records)

    def values(self) -> list[StoredMemory]:
        return list(self.records.values())

    def contains(self, record_id: str) -> bool:
        return record_id in self.records

    def get(self, record_id: str) -> StoredMemory | None:
        return self.records.get(record_id)

    def _vector_for(self, record: MemoryRecord) -> NDArray[np.float64]:
        if record.embedding is None:
            vector = self.embedding.encode(record.content)
            record.embedding = vector.tolist()
            return vector
        vector = np.asarray(record.embedding, dtype=np.float64)
        if vector.shape != (self.embedding.dimension,):
            raise ValueError("record embedding dimension mismatch")
        if not np.isfinite(vector).all():
            raise ValueError("record embedding contains non-finite values")
        return vector

    def write(
        self,
        record: MemoryRecord,
        step: int,
        query_vector: NDArray[np.float64],
    ) -> WriteOutcome:
        if record.record_id in self.records:
            existing = self.records[record.record_id].record
            if existing.normalized_content_hash == record.normalized_content_hash:
                return WriteOutcome(True, "idempotent duplicate delivery", record.record_id)
            return WriteOutcome(
                False,
                "record_id already exists with different content",
                record.record_id,
            )

        superseded_record_id: str | None = None
        if record.supersedes is not None and record.supersedes in self.records:
            superseded_record_id = record.supersedes
            del self.records[record.supersedes]

        if self.config.capacity == 0:
            self.accepted_stream_count += 1
            return WriteOutcome(
                True,
                "accepted then immediately discarded because capacity is zero",
                record.record_id,
                EvictionDecision(record.record_id, "zero-capacity store", 0.0),
                superseded_record_id,
            )

        vector = self._vector_for(record)
        self.accepted_stream_count += 1
        if self.config.policy.value == "reservoir" and len(self.records) >= self.config.capacity:
            draw = self.random.randrange(self.accepted_stream_count)
            if draw >= self.config.capacity:
                return WriteOutcome(
                    True,
                    "accepted by admission control but not selected by reservoir",
                    record.record_id,
                    EvictionDecision(
                        record.record_id,
                        "reservoir stream draw retained the existing sample",
                        float(draw),
                    ),
                    superseded_record_id,
                )
            retained_records = sorted(
                self.records.values(),
                key=lambda item: item.record_id,
            )
            proposed = retained_records[draw]
            protected = protected_record_ids(self.records.values(), self.config)
            if proposed.record_id in protected:
                return WriteOutcome(
                    True,
                    "accepted by admission control but reservoir draw hit a protected record",
                    record.record_id,
                    EvictionDecision(
                        record.record_id,
                        "protected reservoir proposal retained the existing sample",
                        float(draw),
                    ),
                    superseded_record_id,
                )
            del self.records[proposed.record_id]
            self.sequence += 1
            self.records[record.record_id] = StoredMemory(
                record=record,
                vector=vector,
                sequence=self.sequence,
                last_access=step,
            )
            return WriteOutcome(
                True,
                "record selected by reservoir stream draw",
                record.record_id,
                EvictionDecision(
                    proposed.record_id,
                    "reservoir stream replacement",
                    float(draw),
                ),
                superseded_record_id,
            )

        self.sequence += 1
        self.records[record.record_id] = StoredMemory(
            record=record,
            vector=vector,
            sequence=self.sequence,
            last_access=step,
        )
        eviction: EvictionDecision | None = None
        if len(self.records) > self.config.capacity:
            protected = protected_record_ids(self.records.values(), self.config)
            eviction = select_eviction(
                self.records,
                self.config.policy,
                self.random,
                self.embedding,
                query_vector,
                step,
                protected,
            )
            del self.records[eviction.record_id]
        return WriteOutcome(
            True,
            "record stored",
            record.record_id,
            eviction,
            superseded_record_id,
        )

    def _ranked(
        self,
        query: Query,
        touch: bool,
        limit: int | None,
    ) -> list[RetrievalItem]:
        query_vector = self.embedding.encode(query.text)
        scored: list[tuple[float, StoredMemory]] = []
        for stored in self.records.values():
            expired = (
                stored.record.expires_at is not None
                and stored.record.expires_at <= query.event_time
            )
            if expired and not query.include_expired:
                continue
            score = self.embedding.similarity(query_vector, stored.vector)
            scored.append((score, stored))
        scored.sort(key=lambda item: (-item[0], item[1].record_id))
        ranked = [
            RetrievalItem(
                record=stored.record,
                score=score,
                rank=index,
                reason=f"cosine similarity {score:.6f} with stable record-id tie-breaking",
            )
            for index, (score, stored) in enumerate(scored, start=1)
        ]
        selected = ranked if limit is None else ranked[:limit]
        if touch:
            for item in selected:
                stored = self.records[item.record.record_id]
                stored.last_access = max(stored.last_access, query.event_time)
                stored.retrieval_count += 1
        return selected

    def query(self, query: Query) -> list[RetrievalItem]:
        if query.top_k == 0:
            return []
        return self._ranked(query, touch=True, limit=query.top_k)

    def rank_of(self, record_id: str, query: Query) -> int | None:
        ranked = self._ranked(query, touch=False, limit=None)
        for item in ranked:
            if item.record.record_id == record_id:
                return item.rank
        return None

    def snapshot(self) -> dict[str, Any]:
        records = []
        for stored in sorted(self.records.values(), key=lambda item: item.record_id):
            records.append(
                {
                    "record": stored.record.model_dump(mode="json"),
                    "sequence": stored.sequence,
                    "last_access": stored.last_access,
                    "retrieval_count": stored.retrieval_count,
                }
            )
        body = {
            "schema_version": "1.0",
            "config": self.config.model_dump(mode="json"),
            "sequence": self.sequence,
            "accepted_stream_count": self.accepted_stream_count,
            "records": records,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {**body, "snapshot_hash": digest}

    @classmethod
    def restore(cls, snapshot: dict[str, Any]) -> BoundedMemoryStore:
        body = {key: value for key, value in snapshot.items() if key != "snapshot_hash"}
        expected = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if snapshot.get("snapshot_hash") != expected:
            raise ValueError("snapshot hash mismatch")
        config = ExperimentConfig.model_validate(snapshot["config"])
        store = cls(config)
        store.sequence = int(snapshot["sequence"])
        store.accepted_stream_count = int(
            snapshot.get("accepted_stream_count", snapshot["sequence"])
        )
        for item in snapshot["records"]:
            record = MemoryRecord.model_validate(item["record"])
            vector = store._vector_for(record)
            store.records[record.record_id] = StoredMemory(
                record=record,
                vector=vector,
                sequence=int(item["sequence"]),
                last_access=int(item["last_access"]),
                retrieval_count=int(item["retrieval_count"]),
            )
        if len(store) > config.capacity:
            raise ValueError("snapshot exceeds configured capacity")
        return store

    def record_models(self) -> list[MemoryRecord]:
        return [
            stored.record
            for stored in sorted(self.records.values(), key=lambda item: item.record_id)
        ]

    def content_hashes(self) -> set[str]:
        return {stored.normalized_content_hash for stored in self.records.values()}

    def origin_count(self, origin_id: str) -> int:
        return sum(stored.origin_id == origin_id for stored in self.records.values())

    def iter_records(self) -> Iterable[StoredMemory]:
        return iter(self.records.values())
