from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .schemas import AttackName, DefenseName, ExperimentConfig, KnowledgeLevel, PolicyName

ATTACK_ALIASES = {
    "matched_benign": AttackName.NONE.value,
    "semantic": AttackName.SEMANTIC_NEAREST.value,
    "multi_origin": AttackName.SYBIL.value,
}
DEFENSE_ALIASES = {
    "canary_guided": DefenseName.ADAPTIVE.value,
}
POLICY_ALIASES = {
    "diversity": PolicyName.MMR.value,
}
KNOWLEDGE_ALIASES = {
    "target_domain": KnowledgeLevel.CONCEPT.value,
    "domain_only": KnowledgeLevel.CONCEPT.value,
    "query_known": KnowledgeLevel.QUERY.value,
}


def _first(value: Any, default: Any = None) -> Any:
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return slug[:80] or "experiment"


def normalize_config_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a flat config or the human-oriented nested study format."""
    section_names = ("experiment", "embedding", "memory", "retrieval", "traffic", "defense")
    if not any(isinstance(raw.get(key), dict) for key in section_names):
        return dict(raw)

    experiment = raw.get("experiment") or {}
    embedding = raw.get("embedding") or {}
    memory = raw.get("memory") or {}
    retrieval = raw.get("retrieval") or {}
    traffic = raw.get("traffic") or {}
    defense = raw.get("defense") or {}
    canary = raw.get("canary") or {}

    attack = str(_first(traffic.get("strategy", traffic.get("strategies")), "none"))
    policy = str(_first(memory.get("policy", memory.get("policies")), "lru"))
    defense_name = str(_first(defense.get("strategy", defense.get("strategies")), "none"))
    knowledge = str(
        _first(traffic.get("knowledge", traffic.get("knowledge_conditions")), "concept")
    )
    domain = str(_first(experiment.get("domain", experiment.get("domains")), "travel"))
    seed = _first(experiment.get("seed", experiment.get("seeds")), 17)
    capacity = _first(memory.get("capacity", memory.get("capacities")), 24)
    top_k = _first(retrieval.get("top_k", retrieval.get("top_k_values")), 5)
    budget = _first(traffic.get("write_budget", traffic.get("write_budgets")), 36)
    embedding_dim = _first(embedding.get("dimensions"), 128)

    if memory.get("pin_target"):
        defense_name = DefenseName.ORACLE_PIN.value

    return {
        "schema_version": str(raw.get("schema_version", "1.0")),
        "experiment_id": _slug(str(experiment.get("name", "experiment"))),
        "policy": POLICY_ALIASES.get(policy, policy),
        "attack": ATTACK_ALIASES.get(attack, attack),
        "defense": DEFENSE_ALIASES.get(defense_name, defense_name),
        "knowledge": KNOWLEDGE_ALIASES.get(knowledge, knowledge),
        "domain": domain,
        "capacity": int(capacity),
        "top_k": int(top_k),
        "budget": int(budget),
        "seed": int(seed),
        "embedding_dim": int(embedding_dim),
        "background_records": min(10, max(0, int(capacity) - 1)),
        "origin_quota": int(defense.get("per_origin_quota", 6)),
        "semantic_cell_quota": 4,
        "canary_threshold": float(canary.get("alert_threshold", 0.58)),
        "criticality_threshold": float(defense.get("criticality_floor", 0.82)),
        "quick": int(budget) <= 128,
    }


def load_config(path: str | Path) -> ExperimentConfig:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"configuration not found: {source}")
    if source.suffix.casefold() in {".yaml", ".yml"}:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    else:
        raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("configuration root must be an object")
    return ExperimentConfig.model_validate(normalize_config_dict(raw))
