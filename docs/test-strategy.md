# Test strategy

The test suite follows failure boundaries rather than file count.

## Unit tests

Unit tests cover:

- Schema normalization and rejection
- Stable feature hashing
- Similarity and tie-breaking
- Capacity enforcement
- Every policy decision
- Attack budget accounting
- Defense admission and retention
- Canary warning-score bounds
- Availability metrics
- Event serialization and hashing

## Invariant tests

Deterministic invariant cases check:

- Store size never exceeds capacity
- The same configuration and seed produce the same digest
- Snapshot and restore preserve the stored state hash
- No-attack traffic emits no attack records
- Retrieval never returns more than top-k
- Metric values remain bounded
- Mutated events fail integrity verification
- Browser comparison arms preserve coordinates for shared traffic records
- Browser playback snapshots never exceed the declared capacity

## Integration tests

Small matrix tests connect each major policy family with traffic and defense families. They verify that non-oracle defenses do not receive gold target identity.

## Regression tests

Frozen regression cases cover:

- Reservoir determinism
- Correction replacement
- Origin quota boundaries
- Snapshot recovery
- Canary warning-score bounds
- Adaptive budget accounting
- Metric aggregation

## Adversarial tests

Tests include zero capacity, zero top-k, empty text, Unicode normalization, duplicates, zero vectors, corrupted snapshots, and legitimate repeated traffic.

## End-to-end tests

The CLI path validates, runs, replays, compares, exports, audits, and reports an episode. The web suite builds the production worker, executes simulator invariants, and verifies the server-rendered product shell.

## Coverage

Core policy, attack, defense, trace, and evaluation modules are included in branch-aware coverage. The current suite passes 40 Python tests at 90.49% total coverage and seven web tests.
