from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from chaffmem.api import create_app
from chaffmem.artifacts import ArtifactStore, replay_manifest, verify_snapshot
from chaffmem.cli import main
from chaffmem.experiment import run_experiment
from chaffmem.schemas import ExperimentConfig, MemoryRecord


def test_artifact_write_verify_replay_and_tamper(tmp_path: Path) -> None:
    result = run_experiment(ExperimentConfig(capacity=5, background_records=2, budget=4, top_k=2))
    store = ArtifactStore(tmp_path / "runs")
    directory = store.write(result)
    assert set(path.name for path in directory.iterdir()) >= {
        "manifest.json",
        "result.json",
        "trace.jsonl",
        "metrics.csv",
        "snapshot.json",
        "report.html",
        "figure.svg",
    }
    valid, errors = store.verify(result.run_id)
    assert valid
    assert not errors
    replayed = replay_manifest(directory / "manifest.json")
    assert replayed.digest == result.digest
    assert verify_snapshot(directory / "snapshot.json")

    trace_path = directory / "trace.jsonl"
    trace_path.write_text(trace_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    valid, errors = store.verify(result.run_id)
    assert not valid
    assert any("hash mismatch" in error for error in errors)


def test_api_experiment_catalog_and_memory(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "api-runs"))
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").status_code == 200
    assert client.get("/api/v1/policies").status_code == 200
    assert client.get("/api/v1/attacks").status_code == 200
    assert client.get("/api/v1/defenses").status_code == 200

    config = ExperimentConfig(
        experiment_id="api-test",
        capacity=5,
        background_records=2,
        budget=3,
    )
    response = client.post(
        "/api/v1/experiments",
        headers={"Idempotency-Key": "stable-key"},
        json={"config": config.model_dump(mode="json")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    assert client.get("/api/v1/experiments/api-test").status_code == 200
    run = client.post("/api/v1/experiments/api-test/run")
    assert run.json()["status"] == "completed"
    assert client.get("/api/v1/experiments/api-test/metrics").status_code == 200
    assert client.get("/api/v1/experiments/api-test/trace?limit=2").status_code == 200
    assert client.get("/api/v1/experiments/api-test/artifacts").status_code == 200
    assert client.post("/api/v1/experiments/api-test/replay").json()["verified"]

    record = MemoryRecord(record_id="api-record", content="local ordinary note")
    write = client.post(
        "/api/v1/memories/write",
        json={"store_id": "test", "record": record.model_dump(mode="json")},
    )
    assert write.json()["accepted"]
    query = client.post(
        "/api/v1/memories/query",
        json={"store_id": "test", "query": {"text": "ordinary note", "top_k": 2}},
    )
    assert query.json()["items"][0]["record"]["record_id"] == "api-record"
    assert client.get("/api/v1/memories/snapshot?store_id=test").status_code == 200
    canary = client.post(
        "/api/v1/canaries/evaluate",
        json={
            "store_id": "test",
            "target_record_id": "api-record",
            "query": {"text": "ordinary note", "top_k": 2},
        },
    )
    assert canary.json()["retrieval_available"]


def test_api_pause_resume_and_idempotency_conflict(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "api-runs"))
    config = ExperimentConfig(experiment_id="paused", budget=0)
    payload = {"config": config.model_dump(mode="json")}
    assert client.post("/api/v1/experiments", json=payload).status_code == 200
    assert client.post("/api/v1/experiments/paused/pause").json()["status"] == "paused"
    assert client.post("/api/v1/experiments/paused/resume").json()["status"] == "created"
    client.post(
        "/api/v1/experiments",
        headers={"Idempotency-Key": "same"},
        json={"config": ExperimentConfig(experiment_id="one").model_dump(mode="json")},
    )
    conflict = client.post(
        "/api/v1/experiments",
        headers={"Idempotency-Key": "same"},
        json={"config": ExperimentConfig(experiment_id="two").model_dump(mode="json")},
    )
    assert conflict.status_code == 409
    assert client.get("/api/v1/experiments/missing").status_code == 404


def test_cli_validate_run_audit_export_and_catalog(tmp_path: Path, capsys) -> None:
    starter = tmp_path / "starter.yaml"
    assert main(["init", str(starter)]) == 0
    assert starter.is_file()
    assert main(["validate-config", "configs/benchmark/smoke.yaml"]) == 0
    output = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                "configs/benchmark/smoke.yaml",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    run_directory = next(path for path in output.iterdir() if path.is_dir())
    assert main(["audit-store", str(run_directory)]) == 0
    assert main(["replay", str(run_directory / "manifest.json")]) == 0
    assert main(["compare", str(run_directory), str(run_directory)]) == 0
    destination = tmp_path / "metrics.json"
    assert (
        main(
            [
                "export",
                str(run_directory),
                "--format",
                "json",
                "--output",
                str(destination),
            ]
        )
        == 0
    )
    assert json.loads(destination.read_text(encoding="utf-8"))
    assert main(["report", str(run_directory)]) == 0
    assert main(["catalog"]) == 0
    assert "policies" in capsys.readouterr().out
    assert main(["validate-config", "missing.yaml"]) == 2
