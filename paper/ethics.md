# Ethics and responsible use

## Purpose

ChaffMem Lab supports defensive measurement of availability in local agent-memory research. The intended outcome is better evaluation, safer retention policy design, and clearer evidence about utility and capacity tradeoffs.

## Data

Default fixtures are synthetic and contain no personal information. Every generated record has provenance, an origin identifier, and a deterministic content hash.

## Harm controls

- Attack records contain no malicious instruction
- Experiments run against disposable local stores
- Write budgets are explicit and enforced
- External service connectors are excluded
- Secret access and arbitrary code execution are rejected
- Oracle conditions are labeled as upper bounds

## Dual-use risk

Knowledge about bounded-memory failure could be misapplied to degrade a system. The repository reduces this risk by excluding hosted targets, provider-specific integrations, stealth, credential access, persistence, and harmful content. Examples stay small, local, and auditable.

## Reporting

Report negative and null results. Do not remove a strong baseline because it weakens a preferred method. Do not generalize from the deterministic reference store to another system without lawful and explicit evaluation.

## Human impact

Memory availability can affect accessibility needs, medical constraints, security rules, and user preferences. Synthetic scenarios should avoid implying that the benchmark is a substitute for clinical, legal, or safety review.

## Attribution

Future additions must preserve code licenses, dataset terms, model licenses, and scholarly attribution. A clean repository does not remove the duty to cite a method or result that materially informs a study.
