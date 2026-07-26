from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .api import create_app
from .artifacts import ArtifactStore, replay_manifest, verify_snapshot
from .config import load_config
from .experiment import run_experiment
from .schemas import AttackName, DefenseName, PolicyName


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chaffmem",
        description="Deterministic bounded-memory availability research tools",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="write a starter experiment configuration")
    init.add_argument("path", nargs="?", default="chaffmem.yaml")
    init.add_argument("--force", action="store_true")

    validate = subparsers.add_parser("validate-config", help="validate and normalize a config")
    validate.add_argument("config")

    run = subparsers.add_parser("run", help="execute a bounded experiment")
    run.add_argument("config")
    run.add_argument("--output", default="artifacts/runs")

    replay = subparsers.add_parser("replay", help="reproduce a stored manifest")
    replay.add_argument("manifest")

    compare = subparsers.add_parser("compare", help="compare two artifact directories")
    compare.add_argument("left")
    compare.add_argument("right")

    report = subparsers.add_parser("report", help="show the generated run summary")
    report.add_argument("run")

    export = subparsers.add_parser("export", help="copy trajectory metrics")
    export.add_argument("run")
    export.add_argument("--format", choices=("csv", "json"), default="csv")
    export.add_argument("--output")

    audit = subparsers.add_parser(
        "audit-store",
        aliases=["verify"],
        help="verify a run artifact directory or snapshot",
    )
    audit.add_argument("path")

    subparsers.add_parser("catalog", help="list implemented strategies")

    serve = subparsers.add_parser("serve", help="start the local FastAPI service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    return parser


def _load_summary(directory: Path) -> dict[str, Any]:
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    return dict(result["summary"])


def _run_directory(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_file() and candidate.name == "manifest.json":
        return candidate.parent
    if not candidate.is_dir():
        raise FileNotFoundError(f"run directory not found: {candidate}")
    return candidate


def _execute(args: argparse.Namespace) -> int:
    if args.command == "init":
        destination = Path(args.path)
        if destination.exists() and not args.force:
            raise FileExistsError(f"{destination} already exists, pass --force to replace it")
        source = Path(__file__).resolve().parents[2] / "configs" / "benchmark" / "smoke.yaml"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        print(destination)
        return 0

    if args.command == "validate-config":
        config = load_config(args.config)
        print(json.dumps(config.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0

    if args.command == "run":
        config = load_config(args.config)
        result = run_experiment(config)
        directory = ArtifactStore(args.output).write(result)
        print(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "digest": result.digest,
                    "artifacts": str(directory),
                    "summary": result.summary.model_dump(mode="json"),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "replay":
        result = replay_manifest(args.manifest)
        print(json.dumps({"verified": True, "run_id": result.run_id, "digest": result.digest}))
        return 0

    if args.command == "compare":
        left = _load_summary(_run_directory(args.left))
        right = _load_summary(_run_directory(args.right))
        numeric_keys = sorted(
            key
            for key in left.keys() & right.keys()
            if isinstance(left[key], int | float) and isinstance(right[key], int | float)
        )
        print(
            json.dumps(
                {
                    "left": left,
                    "right": right,
                    "right_minus_left": {
                        key: float(right[key]) - float(left[key]) for key in numeric_keys
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "report":
        print((_run_directory(args.run) / "summary.md").read_text(encoding="utf-8"))
        return 0

    if args.command == "export":
        directory = _run_directory(args.run)
        destination = Path(args.output) if args.output else Path(f"metrics.{args.format}")
        if args.format == "csv":
            shutil.copyfile(directory / "metrics.csv", destination)
        else:
            with (directory / "metrics.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            destination.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(destination)
        return 0

    if args.command in {"audit-store", "verify"}:
        path = Path(args.path)
        if path.is_file() and path.name == "snapshot.json":
            verify_snapshot(path)
            print(json.dumps({"verified": True, "snapshot": str(path)}))
            return 0
        directory = _run_directory(args.path)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        store = ArtifactStore(directory.parent)
        valid, errors = store.verify(str(manifest["run_id"]))
        print(json.dumps({"verified": valid, "errors": errors}, indent=2))
        return 0 if valid else 1

    if args.command == "catalog":
        print(
            json.dumps(
                {
                    "policies": [item.value for item in PolicyName],
                    "attacks": [item.value for item in AttackName],
                    "defenses": [item.value for item in DefenseName],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0

    raise RuntimeError("unknown command")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        return _execute(parser.parse_args(argv))
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
