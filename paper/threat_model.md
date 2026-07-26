# Threat model

## Protected property

The protected property is selective memory availability. An important record should remain stored, retrievable inside a fixed query budget, and useful to a downstream decision without preserving every record indefinitely.

## Target system

The target is a disposable local research store with:

- Fixed capacity
- Explicit write and query interfaces
- Deterministic embedding and ranking
- Declared eviction policy
- Bounded top-k retrieval
- Append-only audit events

The model does not represent a specific hosted assistant.

## Attacker goal

Reduce the target record's physical, retrieval, behavioral, or temporal availability by adding individually harmless records.

## Allowed capabilities

The configured attacker may:

- Select candidates from the audited benign fixture set
- Choose write ordering and timing
- Use one origin or several synthetic origins
- Operate under a fixed write budget
- Use the declared query or target knowledge
- Observe only the outputs allowed by the knowledge condition
- Adapt candidate selection inside the local simulator

## Prohibited capabilities

The attacker may not:

- Delete or edit the target directly
- Modify database files, scores, or event logs
- Insert executable code or tool instructions
- Add prompt injection text
- Claim that a false record supersedes the target
- Access a credential or private record
- Escape the local store
- Target a third-party service
- Generate unaudited harmful or personal content

## Knowledge conditions

- Zero knowledge selects random benign records from the broad domain
- Query knowledge knows the future query type but not target content
- Concept knowledge knows the target topic
- Black-box knowledge observes allowed retrieval outcomes
- White-box knowledge knows the deterministic embedding
- Policy knowledge knows eviction behavior
- Transfer knowledge optimizes against a source condition and evaluates a distinct target condition

Results from these conditions must not be pooled without a declared analysis.

## Defender knowledge

Non-oracle defenses may use only record content, metadata, origin counters, semantic-cell occupancy, retrieval history, and canary outcomes available in the declared configuration.

Gold target labels are restricted to evaluation and the explicitly labeled gold-pin storage control.

## Success conditions

Attack success is reported separately for:

- Physical removal
- Target rank outside top-k
- Symbolic downstream failure
- First write at failure
- Fraction of the trajectory with availability

## Exclusions

System compromise, confidentiality, model extraction, data poisoning, direct misinformation, and prompt injection are outside this threat model.
