# Dataset card

## Name

ChaffMem Lab deterministic fixtures

## Purpose

The fixtures provide small, auditable records for testing bounded memory, retrieval ranking, benign traffic pressure, canary queries, and symbolic downstream decisions.

## Composition

Each domain includes:

- One verified critical memory
- Ordinary background records
- Canary queries
- Expected terms for the symbolic action rule

The runner derives matched, same-domain, and semantically targeted traffic from the ordinary records. It uses an ordinary record as the utility probe.

Included reference domains cover travel operations, clinic scheduling, incident response, and expense controls.

## Generation

Records are authored as synthetic factual statements. Deterministic transformations may vary origin, ordering, timing, and lexical form. The pipeline stores the parent fixture identifier and transformation parameters.

## Exclusions

The fixtures contain no:

- Personal data
- Secrets or credentials
- Harmful or illegal content
- Prompt injection
- Tool instructions
- False supersession of the target
- Third-party production data

## Labels

Gold criticality and target identity are used for evaluation and the explicitly labeled gold-pin storage control. Non-oracle defenses receive only observable record fields and an intentionally noisy deterministic criticality score. That score is not calibrated.

## Limitations

The fixture vocabulary and domain diversity are narrow. Results may depend on synthetic wording and deterministic representation. External datasets require a separate card, license review, and frozen acquisition manifest.

## Versioning

The corpus version and SHA-256 digest are stored in every run manifest. A content change requires a new fixture version.
