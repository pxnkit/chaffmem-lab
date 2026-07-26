# Claim registry

Status vocabulary:

- `IMPLEMENTED` means the mechanism exists and has direct tests
- `SMOKE_SUPPORTED` means an executed smoke artifact supports the narrow statement
- `NOT_SUPPORTED` means current evidence contradicts the statement
- `UNTESTED` means the declared study has not produced sufficient evidence

## C1. The system can measure distinct forms of memory availability

Status: `IMPLEMENTED`

Evidence:

- Typed physical, retrieval, behavioral, and temporal metrics
- Unit tests for each metric
- Hash-chained trajectory export

Scope:

This states only that the instrument computes the declared quantities. It does not establish external validity.

## C2. Bounded benign traffic can reduce critical retrieval in at least one reference condition

Status: `SMOKE_SUPPORTED`

Evidence:

- `artifacts/reference/reference_summary.json`
- Hash-verified raw manifests, trajectories, traces, and snapshots under `artifacts/reference/runs`
- One deterministic FIFO travel condition with seed 17
- Query-nearest traffic reached first retrieval failure at write 4 and 0.16 trajectory Recall@4
- Matched and random traffic reached first retrieval failure at write 12 and 0.48 trajectory Recall@4

Scope:

This supports only the frozen synthetic smoke condition. It does not establish an effect across seeds, domains, representations, policies, or external systems.

## C3. Targeted selection is more efficient than random traffic at equal write budget

Status: `UNTESTED`

Required evidence:

- Paired random, same-domain, and targeted runs
- Writes-to-failure confidence interval
- Effect size across declared policies and domains

## C4. Canary-guided admission recovers availability without excessive benign utility loss

Status: `UNTESTED`

Required evidence:

- Matched undefended and defended episodes
- Critical Recall@k recovery
- Ordinary benign retrieval utility loss
- Legitimate topic growth false-alert rate

## C5. Retrieval loss can change a downstream symbolic action

Status: `IMPLEMENTED`

Evidence:

- Paired target-present and target-unavailable sandbox paths
- Automatic behavior grading
- Integration tests connecting retrieval output to the action

Scope:

The symbolic task establishes executable causality inside the benchmark. It does not model every behavior of a language model.

## C6. Results transfer across embedding or policy families

Status: `UNTESTED`

Required evidence:

- Attack generated under one policy or embedding
- Evaluation under a distinct declared target
- No tuning on the frozen target configuration

## C7. A named commercial product is vulnerable

Status: `NOT_SUPPORTED`

No named commercial product is connected, tested, or represented by the default simulator.
