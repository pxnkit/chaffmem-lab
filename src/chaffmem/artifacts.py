from __future__ import annotations

import csv
import hashlib
import html
import importlib.metadata
import json
import os
import platform
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .experiment import run_experiment
from .fixtures import default_fixture_path, load_fixtures, repository_root
from .memory import BoundedMemoryStore
from .schemas import ExperimentConfig, ExperimentResult, TraceEvent
from .trace import verify_trace

RUN_ID_PATTERN = re.compile(r"^run-[a-f0-9]{20}$")
ARTIFACT_NAMES = {
    "figure.svg",
    "manifest.json",
    "metrics.csv",
    "report.html",
    "result.json",
    "snapshot.json",
    "summary.md",
    "trace.jsonl",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_digest(root: Path | None = None) -> str:
    base = root or repository_root()
    digest = hashlib.sha256()
    includes = [
        base / "src",
        base / "configs",
        base / "data" / "fixtures",
        base / "scripts",
        base / "pyproject.toml",
        base / "requirements.lock",
    ]
    files: list[Path] = []
    for item in includes:
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(path for path in item.rglob("*") if path.is_file())
    for path in sorted(files):
        relative = path.relative_to(base).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in ("fastapi", "numpy", "pydantic", "PyYAML", "uvicorn"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = "not-installed"
    return versions


def _figure_svg(result: ExperimentResult) -> str:
    width = 840
    height = 320
    margin = 46
    plot_width = width - 2 * margin
    plot_height = height - 2 * margin
    points = result.trajectory
    maximum_step = max(1, points[-1].step if points else 1)

    def x(step: int) -> float:
        return margin + plot_width * step / maximum_step

    def y(value: float) -> float:
        return margin + plot_height * (1.0 - value)

    series = {
        "physical": (
            "#0f766e",
            [float(item.physical_available) for item in points],
        ),
        "retrieval": (
            "#dc6b2f",
            [float(item.retrieval_available) for item in points],
        ),
        "behavioral": (
            "#5b5bd6",
            [float(item.behavioral_available) for item in points],
        ),
    }
    paths: list[str] = []
    legend: list[str] = []
    for offset, (name, (color, values)) in enumerate(series.items()):
        coordinates = " ".join(
            f"{x(item.step):.2f},{y(value):.2f}" for item, value in zip(points, values, strict=True)
        )
        paths.append(
            f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
            'stroke-width="3" stroke-linejoin="round" />'
        )
        legend_y = 22 + offset * 18
        legend.append(
            f'<line x1="620" y1="{legend_y}" x2="644" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="3" />'
            f'<text x="650" y="{legend_y + 4}" font-size="12">{name}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Availability trajectory">'
        '<rect width="100%" height="100%" fill="#fbfaf6" />'
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" '
        'stroke="#333" />'
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" '
        f'y2="{height - margin}" stroke="#333" />'
        f'<text x="{margin}" y="24" font-size="15" font-weight="600">'
        "Availability trajectory</text>"
        f'<text x="{width / 2 - 20}" y="{height - 8}" font-size="12">write step</text>'
        f'<text x="8" y="{height / 2}" font-size="12" transform="rotate(-90 8 '
        f'{height / 2})">available</text>' + "".join(paths) + "".join(legend) + "</svg>"
    )


def _summary_markdown(result: ExperimentResult) -> str:
    summary = result.summary
    rows = [
        ("Run", result.run_id),
        ("Trace digest", result.digest),
        ("Critical Recall@k", f"{summary.critical_recall:.3f}"),
        ("Physical availability", f"{summary.physical_availability:.3f}"),
        ("Behavioral availability", f"{summary.behavioral_availability:.3f}"),
        ("Benign utility", f"{summary.benign_utility:.3f}"),
        ("Writes to first failure", str(summary.writes_to_failure)),
        ("Accepted writes", str(summary.accepted_writes)),
        ("Rejected writes", str(summary.rejected_writes)),
        ("Peak canary warning score", f"{summary.peak_alert_score:.3f}"),
    ]
    body = "\n".join(f"| {label} | {value} |" for label, value in rows)
    return (
        "# Run summary\n\n"
        "| Measure | Value |\n"
        "| --- | --- |\n"
        f"{body}\n\n"
        "The canary score is a deterministic heuristic and is not a calibrated probability.\n"
    )


def _report_html(result: ExperimentResult) -> str:
    summary = result.summary
    config = html.escape(
        json.dumps(result.config.model_dump(mode="json"), indent=2, sort_keys=True)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ChaffMem Lab report {html.escape(result.run_id)}</title>
  <style>
    body {{ max-width: 900px; margin: 40px auto; padding: 0 20px;
      font: 16px/1.55 system-ui; color: #18201d; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d8ddd9; padding: 10px; text-align: left; }}
    pre {{ overflow: auto; background: #f2f3ef; padding: 16px; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>ChaffMem Lab run report</h1>
  <p><strong>Run:</strong> {html.escape(result.run_id)}</p>
  <p><strong>Trace digest:</strong> <code>{html.escape(result.digest)}</code></p>
  <h2>Summary</h2>
  <table>
    <tr><th>Critical Recall@k</th><td>{summary.critical_recall:.3f}</td></tr>
    <tr><th>Physical availability</th><td>{summary.physical_availability:.3f}</td></tr>
    <tr><th>Behavioral availability</th><td>{summary.behavioral_availability:.3f}</td></tr>
    <tr><th>Benign utility</th><td>{summary.benign_utility:.3f}</td></tr>
    <tr><th>Writes to first failure</th><td>{summary.writes_to_failure}</td></tr>
    <tr><th>Accepted writes</th><td>{summary.accepted_writes}</td></tr>
    <tr><th>Rejected writes</th><td>{summary.rejected_writes}</td></tr>
  </table>
  <p>The canary warning score is deterministic and is not a calibrated probability.</p>
  <h2>Trajectory</h2>
  <img src="figure.svg" alt="Availability trajectory">
  <h2>Normalized configuration</h2>
  <pre>{config}</pre>
</body>
</html>
"""


class ArtifactStore:
    def __init__(self, root: str | Path = "artifacts/runs") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def run_directory(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("invalid run identifier")
        candidate = (self.root / run_id).resolve()
        if candidate.parent != self.root:
            raise ValueError("run path escapes artifact root")
        return candidate

    def write(self, result: ExperimentResult) -> Path:
        directory = self.run_directory(result.run_id)
        manifest_path = directory / "manifest.json"
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("result_digest") != result.digest:
                raise FileExistsError("immutable run identifier already has different content")
            return directory
        directory.mkdir(parents=False, exist_ok=False)

        result_path = directory / "result.json"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        trace_path = directory / "trace.jsonl"
        trace_path.write_text(
            "\n".join(event.model_dump_json() for event in result.trace) + "\n",
            encoding="utf-8",
        )
        metrics_path = directory / "metrics.csv"
        with metrics_path.open("w", encoding="utf-8", newline="") as handle:
            rows = [item.model_dump(mode="json") for item in result.trajectory]
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

        snapshot_path = directory / "snapshot.json"
        snapshot_path.write_text(
            json.dumps(result.snapshot, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (directory / "figure.svg").write_text(_figure_svg(result), encoding="utf-8")
        (directory / "summary.md").write_text(_summary_markdown(result), encoding="utf-8")
        (directory / "report.html").write_text(_report_html(result), encoding="utf-8")

        fixture = load_fixtures()
        files = {
            path.name: sha256_file(path)
            for path in sorted(directory.iterdir())
            if path.is_file() and path.name != "manifest.json"
        }
        manifest = {
            "schema_version": "1.0",
            "run_id": result.run_id,
            "result_digest": result.digest,
            "generated_at": datetime.now(UTC).isoformat(),
            "config": result.config.model_dump(mode="json"),
            "fixture": {
                "id": fixture.fixture_id,
                "path": os.fspath(default_fixture_path().relative_to(repository_root())),
                "sha256": fixture.digest,
            },
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "architecture": platform.machine(),
                "dependencies": _dependency_versions(),
                "source_tree_sha256": source_tree_digest(),
            },
            "files": files,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return directory

    def verify(self, run_id: str) -> tuple[bool, list[str]]:
        directory = self.run_directory(run_id)
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            return False, ["manifest.json is missing"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        errors: list[str] = []
        for name, expected in manifest.get("files", {}).items():
            if name not in ARTIFACT_NAMES:
                errors.append(f"unexpected manifest artifact: {name}")
                continue
            path = directory / name
            if not path.is_file():
                errors.append(f"missing artifact: {name}")
            elif sha256_file(path) != expected:
                errors.append(f"hash mismatch: {name}")
        trace_events = [
            TraceEvent.model_validate_json(line)
            for line in (directory / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        valid_trace, trace_digest = verify_trace(trace_events)
        if not valid_trace:
            errors.append(trace_digest)
        elif trace_digest != manifest.get("result_digest"):
            errors.append("trace digest does not match manifest")
        snapshot_path = directory / "snapshot.json"
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            BoundedMemoryStore.restore(snapshot)
            checkpoint_hashes = [
                event.payload.get("snapshot_hash")
                for event in trace_events
                if event.action == "final_snapshot"
            ]
            if checkpoint_hashes != [snapshot.get("snapshot_hash")]:
                errors.append("snapshot hash does not match final trace checkpoint")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"snapshot verification failed: {exc}")
        return not errors, errors


def replay_manifest(path: str | Path) -> ExperimentResult:
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = ExperimentConfig.model_validate(manifest["config"])
    reproduced = run_experiment(config)
    if reproduced.digest != manifest["result_digest"]:
        raise ValueError("replay digest mismatch")
    return reproduced


def verify_snapshot(path: str | Path) -> bool:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    BoundedMemoryStore.restore(payload)
    return True
