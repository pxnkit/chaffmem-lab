from __future__ import annotations

import pytest

from chaffmem.attacks import build_traffic
from chaffmem.embeddings import FeatureHashEmbedding
from chaffmem.experiment import run_experiment
from chaffmem.fixtures import load_fixtures
from chaffmem.schemas import (
    AttackName,
    DefenseName,
    DomainName,
    ExperimentConfig,
    KnowledgeLevel,
    PolicyName,
)
from chaffmem.trace import verify_trace


def test_experiment_is_deterministic_and_trace_verifies() -> None:
    config = ExperimentConfig(
        capacity=8,
        background_records=4,
        budget=12,
        top_k=3,
        attack=AttackName.SEMANTIC_NEAREST,
        defense=DefenseName.NONE,
        seed=41,
    )
    first = run_experiment(config)
    second = run_experiment(config)
    assert first == second
    valid, digest = verify_trace(first.trace)
    assert valid
    assert digest == first.digest
    assert len(first.trajectory) == config.budget + 1
    assert first.summary.accepted_writes == config.budget


def test_physical_and_retrieval_availability_are_separate() -> None:
    result = run_experiment(
        ExperimentConfig(
            capacity=6,
            background_records=2,
            budget=0,
            top_k=0,
        )
    )
    assert result.trajectory[0].physical_available
    assert not result.trajectory[0].retrieval_available
    assert not result.trajectory[0].behavioral_available


def test_oracle_pin_is_explicit_upper_bound() -> None:
    result = run_experiment(
        ExperimentConfig(
            capacity=4,
            background_records=3,
            budget=20,
            defense=DefenseName.ORACLE_PIN,
            policy=PolicyName.FIFO,
        )
    )
    assert result.trajectory[-1].physical_available


@pytest.mark.parametrize("domain", list(DomainName))
def test_all_domains_execute(domain: DomainName) -> None:
    result = run_experiment(
        ExperimentConfig(
            domain=domain,
            capacity=5,
            background_records=2,
            budget=3,
        )
    )
    assert result.target_record_id.startswith(domain.value)


@pytest.mark.parametrize("attack", list(AttackName))
def test_all_traffic_strategies_are_bounded(attack: AttackName) -> None:
    config = ExperimentConfig(attack=attack, budget=3, capacity=6)
    catalog = load_fixtures()
    scenario = catalog.scenario(config.domain)
    traffic = build_traffic(
        config,
        catalog,
        scenario,
        FeatureHashEmbedding(config.embedding_dim),
    )
    assert len(traffic) == 3
    assert len({record.record_id for record in traffic}) == 3
    assert all(record.provenance["generator"] == "bounded-synthetic-v1" for record in traffic)


def test_knowledge_condition_changes_generated_stream() -> None:
    catalog = load_fixtures()
    base = ExperimentConfig(
        attack=AttackName.SEMANTIC_NEAREST,
        budget=5,
        seed=2,
    )
    embedding = FeatureHashEmbedding(base.embedding_dim)
    scenario = catalog.scenario(base.domain)
    zero = build_traffic(
        base.model_copy(update={"knowledge": KnowledgeLevel.ZERO}),
        catalog,
        scenario,
        embedding,
    )
    query = build_traffic(
        base.model_copy(update={"knowledge": KnowledgeLevel.QUERY}),
        catalog,
        scenario,
        embedding,
    )
    assert [item.content for item in zero] != [item.content for item in query]
