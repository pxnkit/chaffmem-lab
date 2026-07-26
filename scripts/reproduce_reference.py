from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from chaffmem.artifacts import ArtifactStore  # noqa: E402
from chaffmem.config import load_config  # noqa: E402
from chaffmem.experiment import run_experiment  # noqa: E402
from chaffmem.schemas import AttackName, DefenseName, KnowledgeLevel  # noqa: E402


def reproduce(output: Path) -> list[dict[str, object]]:
    base = load_config(REPOSITORY_ROOT / "configs" / "benchmark" / "smoke.yaml")
    arms = [
        ("matched-benign", {"attack": AttackName.NONE, "defense": DefenseName.NONE}),
        ("random", {"attack": AttackName.RANDOM, "defense": DefenseName.NONE}),
        (
            "semantic-nearest",
            {
                "attack": AttackName.SEMANTIC_NEAREST,
                "defense": DefenseName.NONE,
                "knowledge": KnowledgeLevel.QUERY,
            },
        ),
        (
            "adaptive-admission",
            {
                "attack": AttackName.SEMANTIC_NEAREST,
                "defense": DefenseName.ADAPTIVE,
                "knowledge": KnowledgeLevel.QUERY,
                "canary_threshold": 0.10,
                "semantic_cell_quota": 1,
            },
        ),
        (
            "pinned-storage-oracle-control",
            {
                "attack": AttackName.SEMANTIC_NEAREST,
                "defense": DefenseName.ORACLE_PIN,
                "knowledge": KnowledgeLevel.QUERY,
            },
        ),
    ]
    store = ArtifactStore(output / "runs")
    rows: list[dict[str, object]] = []
    for name, updates in arms:
        config = base.model_copy(
            update={
                **updates,
                "experiment_id": f"reference-{name}",
            }
        )
        result = run_experiment(config)
        store.write(result)
        valid, errors = store.verify(result.run_id)
        if not valid:
            raise RuntimeError(f"artifact verification failed for {result.run_id}: {errors}")
        rows.append(
            {
                "arm": name,
                "run_id": result.run_id,
                "trace_digest": result.digest,
                **result.summary.model_dump(mode="json"),
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "reference_summary.json"
    json_path.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    csv_path = output / "reference_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / "README.md").write_text(
        "# Reference smoke output\n\n"
        "These deterministic single-seed runs validate the pipeline. They are not a "
        "statistical study and do not support claims about external systems.\n",
        encoding="utf-8",
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "artifacts" / "reference",
    )
    args = parser.parse_args()
    rows = reproduce(args.output)
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
