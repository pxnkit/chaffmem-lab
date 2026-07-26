# Reproducibility

## Reference command

```bash
python scripts/reproduce_reference.py
```

The command creates a fresh artifact directory, executes the frozen smoke configuration, verifies the trace chain, and regenerates the reference JSON, CSV, SVG, HTML, and Markdown outputs.

## Verification

```bash
chaffmem replay artifacts/runs/RUN_ID/manifest.json
chaffmem audit-store artifacts/runs/RUN_ID/snapshot.json
```

A successful artifact verification checks:

- Stored artifact file hashes
- Trace chain and final digest
- Snapshot hash
- Snapshot checkpoint linkage

The manifest also records the normalized configuration, fixture hash, and source-tree hash used when the run was created.

## Deterministic boundary

The reference feature-hash backend, policies, traffic generators, and tie-breaking are deterministic under the stored seed. Wall-clock metadata is excluded from the semantic trace digest.

## Environment capture

Every run manifest records:

- Source-tree hash
- Python version
- Operating system and architecture
- Installed dependency versions
- Complete normalized configuration
- Random seed
- Fixture identifier and hash
- Embedding, policy, attack, and defense identifiers
- Artifact generation timestamp
- Hashes for every emitted run file

## Releasing artifacts

Do not commit a local artifact that contains an absolute path, username, credential, hostname, or private dependency URL. Run the anonymous release checklist before sharing a bundle.

## Non-deterministic extensions

A learned model or parallel approximate index must declare its nondeterminism, device, library settings, and tolerance. It may not replace the deterministic reference path.
