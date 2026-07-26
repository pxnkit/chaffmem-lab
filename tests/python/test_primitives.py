from __future__ import annotations

import json

import numpy as np
import pytest
from pydantic import ValidationError

from chaffmem.config import load_config, normalize_config_dict
from chaffmem.criticality import observable_criticality
from chaffmem.embeddings import FeatureHashEmbedding, normalize_text
from chaffmem.fixtures import load_fixtures
from chaffmem.sandbox import evaluate_symbolic_action
from chaffmem.schemas import (
    EventKind,
    ExperimentConfig,
    MemoryKind,
    MemoryRecord,
    RetrievalItem,
)
from chaffmem.trace import TraceRecorder, verify_trace


def test_record_schema_hashes_normalized_content() -> None:
    record = MemoryRecord(record_id="record-1", content="  Hello   WORLD ")
    assert record.normalized_content_hash is not None
    assert len(record.normalized_content_hash) == 64
    assert record.kind == MemoryKind.BACKGROUND
    with pytest.raises(ValidationError):
        MemoryRecord(
            record_id="../escape",
            content="value",
            normalized_content_hash="0" * 64,
        )
    with pytest.raises(ValidationError):
        MemoryRecord(record_id="ok", content="value", embedding=[float("nan")])


def test_embedding_is_stable_and_finite() -> None:
    embedding = FeatureHashEmbedding(32)
    left = embedding.encode("Berlin terminal at seven")
    right = embedding.encode("Berlin terminal at seven")
    assert np.array_equal(left, right)
    assert embedding.similarity(left, right) == pytest.approx(1.0)
    assert embedding.similarity(left, embedding.encode("")) == 0.0
    assert embedding.semantic_cell(left)
    assert normalize_text("  CAFÉ  ") == "café"
    with pytest.raises(ValueError):
        FeatureHashEmbedding(4)
    with pytest.raises(ValueError):
        embedding.similarity(left, np.zeros(16))


def test_observable_criticality_is_bounded_and_deterministic() -> None:
    first = observable_criticality("ordinary note", 0.5, "origin-a")
    second = observable_criticality("ordinary note", 0.5, "origin-a")
    changed = observable_criticality("ordinary note", 0.5, "origin-b")
    assert first == second
    assert first != changed
    assert 0.0 <= first <= 1.0


def test_trace_chain_detects_mutation() -> None:
    recorder = TraceRecorder()
    recorder.append(0, EventKind.SEED, "seed", {"id": "a"})
    recorder.append(1, EventKind.WRITE, "write", {"id": "b"})
    valid, digest = verify_trace(recorder.events)
    assert valid
    assert digest == recorder.digest
    mutated = [event.model_copy(deep=True) for event in recorder.events]
    mutated[1].payload["id"] = "changed"
    valid, reason = verify_trace(mutated)
    assert not valid
    assert "hash mismatch" in reason


def test_fixture_catalog_is_audited_and_complete() -> None:
    catalog = load_fixtures()
    assert len(catalog.scenarios) == 4
    assert len(catalog.digest) == 64
    for scenario in catalog.scenarios:
        assert scenario.target.critical
        assert len(scenario.background) == 4
        assert scenario.expected_terms


def test_nested_config_normalization() -> None:
    config = load_config("configs/benchmark/smoke.yaml")
    assert config.experiment_id == "cpu-smoke"
    assert config.capacity == 16
    assert config.budget == 24
    flat = normalize_config_dict(ExperimentConfig().model_dump(mode="json"))
    assert flat["capacity"] == 24
    with pytest.raises(FileNotFoundError):
        load_config("configs/missing.yaml")


def test_symbolic_action_checks_identity_and_terms() -> None:
    record = MemoryRecord(record_id="target", content="Terminal 1 closes at 07:40")
    item = RetrievalItem(record=record, score=0.8, rank=1, reason="test")
    safe = evaluate_symbolic_action([item], "target", ("Terminal 1", "07:40"))
    assert safe.safe
    missing = evaluate_symbolic_action([item], "other", ("Terminal 1",))
    assert not missing.safe
    wrong_terms = evaluate_symbolic_action([item], "target", ("Bay C",))
    assert not wrong_terms.safe


def test_config_json_round_trip(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(ExperimentConfig(capacity=3).model_dump(mode="json")),
        encoding="utf-8",
    )
    assert load_config(path).capacity == 3
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(bad)
