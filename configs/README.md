# Configuration profiles

`benchmark/smoke.yaml` is the bounded CPU validation profile used by local development and CI.

`studies/paper.yaml` declares the larger matched study matrix. It is intentionally a study
specification rather than bundled evidence. Run it explicitly and inspect every generated
artifact before reporting results.

All paths are resolved from the repository root. Catalog identifiers use lowercase snake case
and are stable within schema version `1.0`.
