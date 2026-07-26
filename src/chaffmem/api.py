from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Query

from .artifacts import ArtifactStore, replay_manifest
from .defenses import canary_alert_score
from .experiment import run_experiment
from .memory import BoundedMemoryStore
from .schemas import (
    AttackName,
    CanaryRequest,
    CatalogItem,
    DefenseName,
    ExperimentCreateRequest,
    ExperimentState,
    ExperimentStatus,
    MemoryQueryRequest,
    MemoryWriteRequest,
    PolicyName,
)
from .trace import canonical_json


class ServiceState:
    def __init__(self, artifact_root: str | Path) -> None:
        self.artifacts = ArtifactStore(artifact_root)
        self.experiments: dict[str, ExperimentState] = {}
        self.results: dict[str, Any] = {}
        self.stores: dict[str, BoundedMemoryStore] = {}
        self.idempotency: dict[str, tuple[str, str]] = {}
        self.lock = threading.RLock()


POLICY_DESCRIPTIONS = {
    PolicyName.FIFO: "Evict the oldest inserted record",
    PolicyName.LRU: "Evict the least recently retrieved record",
    PolicyName.RESERVOIR: "Maintain a seeded uniform sample of admitted writes",
    PolicyName.IMPORTANCE: "Retain records with higher declared or predicted importance",
    PolicyName.SIMILARITY: "Retain records most relevant to the declared canary query",
    PolicyName.MMR: "Reduce local semantic crowding",
    PolicyName.HYBRID: "Combine importance, recency, and semantic coverage",
}


def _catalog(enum_type: type[Any], descriptions: dict[Any, str] | None = None) -> list[CatalogItem]:
    return [
        CatalogItem(
            id=item.value,
            name=item.value.replace("_", " ").title(),
            description=(descriptions or {}).get(item, f"Bounded {item.value} strategy"),
            oracle=item.value == "oracle_pin",
        )
        for item in enum_type
    ]


def create_app(artifact_root: str | Path | None = None) -> FastAPI:
    app = FastAPI(
        title="ChaffMem Lab API",
        version="0.2.1",
        description="Local deterministic memory availability research service",
    )
    resolved_artifact_root: str | Path
    if artifact_root is None:
        resolved_artifact_root = os.environ.get(
            "CHAFFMEM_ARTIFACT_DIR",
            "artifacts/runs",
        )
    else:
        resolved_artifact_root = artifact_root
    state = ServiceState(resolved_artifact_root)
    app.state.chaffmem = state

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        state.artifacts.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ready", "artifact_root": str(state.artifacts.root)}

    @app.get("/api/v1/policies", response_model=list[CatalogItem])
    def policies() -> list[CatalogItem]:
        return _catalog(PolicyName, POLICY_DESCRIPTIONS)

    @app.get("/api/v1/attacks", response_model=list[CatalogItem])
    def attacks() -> list[CatalogItem]:
        return _catalog(AttackName)

    @app.get("/api/v1/defenses", response_model=list[CatalogItem])
    def defenses() -> list[CatalogItem]:
        return _catalog(DefenseName)

    @app.post("/api/v1/experiments", response_model=ExperimentState)
    def create_experiment(
        request: ExperimentCreateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ExperimentState:
        request_hash = hashlib.sha256(
            canonical_json(request.model_dump(mode="json")).encode("utf-8")
        ).hexdigest()
        generated = request.config.experiment_id or f"experiment-{request_hash[:12]}"
        with state.lock:
            if idempotency_key is not None and idempotency_key in state.idempotency:
                previous_hash, experiment_id = state.idempotency[idempotency_key]
                if previous_hash != request_hash:
                    raise HTTPException(
                        status_code=409,
                        detail="idempotency key was used with a different request",
                    )
                return state.experiments[experiment_id]
            if generated in state.experiments:
                existing = state.experiments[generated]
                if existing.config != request.config:
                    raise HTTPException(status_code=409, detail="experiment id already exists")
                return existing
            created = ExperimentState(
                experiment_id=generated,
                status=ExperimentStatus.CREATED,
                config=request.config,
            )
            state.experiments[generated] = created
            if idempotency_key is not None:
                state.idempotency[idempotency_key] = (request_hash, generated)
            return created

    def _experiment(experiment_id: str) -> ExperimentState:
        if experiment_id not in state.experiments:
            raise HTTPException(status_code=404, detail="experiment not found")
        return state.experiments[experiment_id]

    @app.get("/api/v1/experiments/{experiment_id}", response_model=ExperimentState)
    def get_experiment(experiment_id: str) -> ExperimentState:
        return _experiment(experiment_id)

    @app.post("/api/v1/experiments/{experiment_id}/run", response_model=ExperimentState)
    def execute_experiment(experiment_id: str) -> ExperimentState:
        current = _experiment(experiment_id)
        if current.status == ExperimentStatus.COMPLETED:
            return current
        if current.status == ExperimentStatus.PAUSED:
            raise HTTPException(status_code=409, detail="resume the experiment before running")
        current.status = ExperimentStatus.RUNNING
        try:
            result = run_experiment(current.config)
            state.artifacts.write(result)
            state.results[experiment_id] = result
            current.run_id = result.run_id
            current.status = ExperimentStatus.COMPLETED
            return current
        except Exception as exc:
            current.status = ExperimentStatus.FAILED
            current.error = str(exc)
            raise HTTPException(status_code=500, detail="experiment execution failed") from exc

    @app.post("/api/v1/experiments/{experiment_id}/pause", response_model=ExperimentState)
    def pause_experiment(experiment_id: str) -> ExperimentState:
        current = _experiment(experiment_id)
        if current.status != ExperimentStatus.CREATED:
            raise HTTPException(
                status_code=409,
                detail="only a not-yet-run experiment can be paused",
            )
        current.status = ExperimentStatus.PAUSED
        return current

    @app.post("/api/v1/experiments/{experiment_id}/resume", response_model=ExperimentState)
    def resume_experiment(experiment_id: str) -> ExperimentState:
        current = _experiment(experiment_id)
        if current.status != ExperimentStatus.PAUSED:
            raise HTTPException(status_code=409, detail="experiment is not paused")
        current.status = ExperimentStatus.CREATED
        return current

    def _result(experiment_id: str) -> Any:
        _experiment(experiment_id)
        if experiment_id not in state.results:
            raise HTTPException(status_code=409, detail="experiment has not completed")
        return state.results[experiment_id]

    @app.post("/api/v1/experiments/{experiment_id}/replay")
    def replay_experiment(experiment_id: str) -> dict[str, Any]:
        current = _experiment(experiment_id)
        if current.run_id is None:
            raise HTTPException(status_code=409, detail="experiment has not completed")
        result = replay_manifest(state.artifacts.run_directory(current.run_id) / "manifest.json")
        return {"verified": True, "run_id": result.run_id, "digest": result.digest}

    @app.get("/api/v1/experiments/{experiment_id}/trace")
    def trace(
        experiment_id: str,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        events = _result(experiment_id).trace
        return {
            "offset": offset,
            "limit": limit,
            "total": len(events),
            "items": [item.model_dump(mode="json") for item in events[offset : offset + limit]],
        }

    @app.get("/api/v1/experiments/{experiment_id}/metrics")
    def metrics(experiment_id: str) -> dict[str, Any]:
        result = _result(experiment_id)
        return {
            "summary": result.summary.model_dump(mode="json"),
            "trajectory": [item.model_dump(mode="json") for item in result.trajectory],
        }

    @app.get("/api/v1/experiments/{experiment_id}/artifacts")
    def artifacts(experiment_id: str) -> dict[str, Any]:
        current = _experiment(experiment_id)
        if current.run_id is None:
            raise HTTPException(status_code=409, detail="experiment has not completed")
        directory = state.artifacts.run_directory(current.run_id)
        return {
            "run_id": current.run_id,
            "files": sorted(path.name for path in directory.iterdir() if path.is_file()),
        }

    def _store(store_id: str) -> BoundedMemoryStore:
        if store_id not in state.stores:
            from .schemas import ExperimentConfig

            state.stores[store_id] = BoundedMemoryStore(
                ExperimentConfig(
                    experiment_id=f"api-{store_id}",
                    capacity=64,
                    policy=PolicyName.LRU,
                )
            )
        return state.stores[store_id]

    @app.post("/api/v1/memories/write")
    def memory_write(request: MemoryWriteRequest) -> dict[str, Any]:
        store = _store(request.store_id)
        query_vector = store.embedding.encode(request.record.content)
        outcome = store.write(request.record, request.record.event_time, query_vector)
        return {
            "accepted": outcome.accepted,
            "reason": outcome.reason,
            "record_id": outcome.record_id,
            "evicted_record_id": (
                outcome.evicted.record_id if outcome.evicted is not None else None
            ),
        }

    @app.post("/api/v1/memories/query")
    def memory_query(request: MemoryQueryRequest) -> dict[str, Any]:
        items = _store(request.store_id).query(request.query)
        return {"items": [item.model_dump(mode="json") for item in items]}

    @app.get("/api/v1/memories/snapshot")
    def memory_snapshot(store_id: str = "default") -> dict[str, Any]:
        return _store(store_id).snapshot()

    @app.post("/api/v1/canaries/evaluate")
    def canary(request: CanaryRequest) -> dict[str, Any]:
        store = _store(request.store_id)
        rank = store.rank_of(request.target_record_id, request.query)
        items = store.query(request.query)
        scores = {item.record.record_id: item.score for item in items}
        target_score = scores.get(request.target_record_id)
        runner_up = max(
            (item.score for item in items if item.record.record_id != request.target_record_id),
            default=None,
        )
        margin = (
            target_score - runner_up if target_score is not None and runner_up is not None else None
        )
        return {
            "target_rank": rank,
            "retrieval_available": target_score is not None,
            "margin": margin,
            "alert_score": canary_alert_score(rank, request.query.top_k),
            "score_note": "Deterministic heuristic, not a calibrated probability",
        }

    return app


app = create_app()
