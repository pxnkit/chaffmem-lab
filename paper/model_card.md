# Model card

## Default representation

The default backend is deterministic signed feature hashing over normalized lexical features. It produces a fixed-size vector without a model download.

## Intended use

- Reproducible CPU smoke tests
- Policy and defense conformance
- Trace replay
- Controlled sensitivity studies
- Browser reference simulations

## Not intended for

- Semantic quality claims about learned embeddings
- Production search
- Multilingual benchmark conclusions
- User profiling
- Classification of malicious intent

## Inputs

UTF-8 text records and queries. Normalization is versioned and rejects invalid non-text payloads.

## Outputs

Finite normalized vectors and cosine similarity scores. Exact ties use stable record identifiers.

## Determinism

Feature indices and signs derive from stable hashes. The backend does not depend on process-randomized Python hashing.

## Failure handling

Empty text produces a valid zero vector with an explicit trace field. Non-finite values, dimension mismatch, and unknown backend identifiers are rejected.

## Optional backends

A future learned backend must be disabled by default and record:

- Package and model identifier
- Model revision
- Download and license terms
- Vector dimension
- Normalization
- Content or artifact hash

The system must never silently replace a requested backend.

## Symbolic decision component

The downstream sandbox maps retrieved facts to a small declared action set. It has no network, file, shell, or tool access. Its role is to test causal use of a memory, not to emulate general language reasoning.
