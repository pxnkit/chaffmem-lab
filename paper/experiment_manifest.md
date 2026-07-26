# Experiment manifest

## Primary question

At fixed capacity and retrieval budget, does targeted benign traffic reduce critical memory availability more than matched ordinary traffic?

## Primary metric

Critical Recall@k averaged across the post-seed trajectory.

## Secondary metrics

- Physical availability
- Behavioral availability
- Writes to first failure
- Final target rank
- Ordinary benign retrieval utility
- Canary warning score
- Accepted and rejected writes
- Runtime and peak memory

## Primary traffic conditions

- Matched benign traffic
- Random benign flooding
- Same-domain flooding
- Semantic-nearest benign chaff

## Primary policies

- FIFO
- LRU
- Reservoir
- Importance retention
- Diversity retention
- Hybrid retention

## Primary defense

Canary-guided adaptive admission compared with no defense, duplicate control, origin quota, semantic coverage, and criticality-aware retention.

## Storage controls

- Unlimited capacity
- Gold target pinning

These non-deployable controls bound physical retention. They do not guarantee top-k retrieval and are never described as proposed defenses.

## Smoke profile

- Four domains
- Small fixed capacities
- Small write budgets
- Deterministic feature hashing
- A limited seed set for pipeline verification

## Full profile

The full profile expands policies, capacities, top-k values, timing, knowledge, origins, criticality noise, transfer, and seeds. It remains pending until the smoke pipeline and frozen analysis pass.

## Frozen test rule

The final test manifest must not be overwritten. A configuration change requires a new experiment identifier and a new manifest digest.

## Kill criteria

The analysis reports whether:

1. At least two nontrivial policies lose at least 20 absolute points of critical recall under bounded targeted traffic
2. The selected defense recovers a meaningful fraction of that loss
3. Ordinary utility falls by no more than the declared tolerance
4. Targeted traffic outperforms random and same-domain traffic at equal writes
5. The effect appears across multiple domains and representation or policy families

Failure is reported as a negative result. Thresholds and baselines remain fixed after the test manifest is frozen.
