from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import DomainName


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_fixture_path() -> Path:
    return repository_root() / "data" / "fixtures" / "benign_records.json"


@dataclass(frozen=True)
class FixtureRecord:
    record_id: str
    text: str
    origin: str
    importance: float
    critical: bool
    created_step: int
    tags: tuple[str, ...]


@dataclass(frozen=True)
class FixtureScenario:
    domain: DomainName
    target_record_id: str
    canary_query: str
    expected_terms: tuple[str, ...]
    records: tuple[FixtureRecord, ...]

    @property
    def target(self) -> FixtureRecord:
        return next(record for record in self.records if record.record_id == self.target_record_id)

    @property
    def background(self) -> tuple[FixtureRecord, ...]:
        return tuple(record for record in self.records if not record.critical)


@dataclass(frozen=True)
class FixtureCatalog:
    fixture_id: str
    digest: str
    scenarios: tuple[FixtureScenario, ...]

    def scenario(self, domain: DomainName) -> FixtureScenario:
        return next(item for item in self.scenarios if item.domain == domain)


def _parse_record(raw: dict[str, Any]) -> FixtureRecord:
    return FixtureRecord(
        record_id=str(raw["record_id"]),
        text=str(raw["text"]),
        origin=str(raw["origin"]),
        importance=float(raw["importance"]),
        critical=bool(raw["critical"]),
        created_step=int(raw["created_step"]),
        tags=tuple(str(tag) for tag in raw.get("tags", [])),
    )


def load_fixtures(path: str | Path | None = None) -> FixtureCatalog:
    source = Path(path) if path is not None else default_fixture_path()
    payload = source.read_bytes()
    raw = json.loads(payload)
    if raw.get("schema_version") != "1.0":
        raise ValueError("unsupported fixture schema version")
    scenarios: list[FixtureScenario] = []
    for raw_scenario in raw["scenarios"]:
        records = tuple(_parse_record(item) for item in raw_scenario["records"])
        target_id = str(raw_scenario["target_record_id"])
        matches = [record for record in records if record.record_id == target_id]
        if len(matches) != 1 or not matches[0].critical:
            raise ValueError("each fixture scenario must have one declared critical target")
        if any(record.critical for record in records if record.record_id != target_id):
            raise ValueError("undeclared critical fixture record")
        scenarios.append(
            FixtureScenario(
                domain=DomainName(str(raw_scenario["domain"])),
                target_record_id=target_id,
                canary_query=str(raw_scenario["canary_query"]),
                expected_terms=tuple(str(term) for term in raw_scenario["expected_terms"]),
                records=records,
            )
        )
    return FixtureCatalog(
        fixture_id=str(raw["fixture_id"]),
        digest=hashlib.sha256(payload).hexdigest(),
        scenarios=tuple(scenarios),
    )
