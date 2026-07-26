# Architecture

ChaffMem Lab separates experiment control, memory behavior, traffic generation, defenses, evaluation, and presentation. Each boundary is typed and traceable.

## Runtime surfaces

### Python research engine

The Python package is authoritative for benchmark execution and artifacts. It owns:

- Typed configuration and domain records
- Deterministic embeddings
- Fixed-capacity memory policies
- Benign traffic and attack selection
- Defense decisions
- Canary evaluation
- Symbolic downstream actions
- Metrics and report generation
- Snapshot, replay, and audit
- FastAPI and CLI adapters

### Browser reference engine

The live application contains a compact deterministic implementation for interactive exploration. It has no external dependency and stores no server-side data. Browser output illustrates the method but is not used as publication evidence.

### Deployment worker

The web build targets a Cloudflare-compatible worker. It serves the React application and static assets. No research database, identity flow, or secret is required for the public demo.

## Experiment lifecycle

1. Validate and normalize a versioned configuration
2. Create a deterministic run identifier
3. Seed the critical and ordinary records
4. Select a benign candidate under the declared knowledge condition
5. Apply write-time defense admission
6. Write the record and enforce fixed capacity
7. Query the target and ordinary utility tasks
8. Execute the symbolic downstream action
9. Append hash-chained decisions and metrics
10. Repeat until the write budget is exhausted
11. Write the immutable manifest, verify artifacts, and generate reports

## Deterministic boundary

The engine avoids process-randomized hashing. Seeds are explicit. Exact ties use stable record identifiers. Wall-clock values do not enter the semantic trace digest.

## Persistence

Runs write into an experiment-scoped directory. The service resolves artifact identifiers through a controlled store and does not accept arbitrary filesystem paths. Snapshots include content and integrity hashes.

## Extension contracts

Policies, traffic strategies, defenses, domains, and embedding backends expose registries with stable identifiers. Unknown identifiers are rejected. Optional components return a typed unavailable result instead of silently falling back.

## Trust boundaries

- Configuration is untrusted input and is validated before execution
- Fixture content is audited but still serialized safely
- Browser export is user-triggered and contains the current local run only
- Artifact reads are restricted to known run identifiers
- The symbolic sandbox has no shell, network, file, or tool capability
