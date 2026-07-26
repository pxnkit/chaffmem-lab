# Contributing to ChaffMem Lab

Thank you for improving the research artifact. Contributions should make experiments easier to audit, reproduce, or falsify.

## Development setup

```bash
python -m venv .venv
```

Activate the environment, then install the project:

```bash
pip install -e ".[dev]"
npm ci
```

Run the checks before opening a pull request:

```bash
ruff check src tests
mypy src
pytest
npm run lint
npm test
```

## Design rules

- Keep the default path deterministic and CPU only
- Keep all attack records benign and auditable
- Separate non-oracle methods from gold-label upper bounds
- Record provenance, normalized configuration, seed, and artifact hashes
- Reject invalid input explicitly instead of silently changing a requested method
- Preserve fixed capacity in non-oracle defense comparisons
- Add a matched simple baseline when adding a complex method
- Mark unsupported claims as untested

## Add a memory policy

Implement the policy contract in `src/chaffmem/policies.py`. A policy must expose a stable identifier, deterministic tie-breaking, an eviction decision, and a machine-readable reason.

Add tests for:

- Capacity zero and one
- Determinism under a fixed seed
- Exact score ties
- Snapshot and restore
- Target inserted first, middle, and last
- Conformance with the common store interface

## Add a traffic strategy

Implement candidate selection in `src/chaffmem/attacks.py`. Every output record must originate from the audited benign fixture set or a deterministic transformation with stored provenance.

Document:

- Attacker knowledge
- Allowed observations
- Write budget
- Identity and timing behavior
- Candidate audit rule

Do not add instructions, executable strings, false corrections, private data, or harmful content.

## Add a defense

Implement the defense contract in `src/chaffmem/defenses.py`. The intervention must use only information available in the declared condition.

Add tests for:

- Legitimate repeated traffic
- False criticality predictions
- Correction and supersession
- Fixed capacity
- Intervention trace reasons
- Utility impact on unrelated queries

## Add a benchmark domain

Add typed domain metadata, a critical record, canary queries, ordinary background records, and a symbolic downstream decision. Keep the fixture small enough for a CPU smoke run.

Do not introduce a private dataset or mandatory model download.

## Add an embedding backend

Register the backend explicitly. Record its package version, model identifier, configuration, and content hash. If the dependency is optional, return an unavailable result with installation instructions. Never silently fall back to another embedding.

## Pull request checklist

- Tests cover the new behavior and failure cases
- The smoke run remains reproducible
- Documentation describes the public contract
- No generated artifact contains a secret or local absolute path
- No third-party code or data was added without a license
- Claims remain tied to executable evidence
