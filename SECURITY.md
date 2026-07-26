# Security policy

ChaffMem Lab is a defensive research simulator for local memory implementations. It is not a scanner, exploit framework, or production security control.

## Supported versions

Security fixes are applied to the latest release on the `main` branch.

## Report a vulnerability

Do not open a public issue for a vulnerability that exposes secrets, permits arbitrary code execution, escapes the local artifact directory, or affects a dependency with an unpublished advisory.

Use GitHub private vulnerability reporting for the repository. Include:

- A concise description of the affected component
- The smallest safe reproduction
- Expected and observed behavior
- Environment and version details
- Suggested remediation if known

Avoid including live credentials, personal data, third-party production targets, or destructive payloads.

## Research safety boundary

The repository must not be extended to:

- Attack a hosted assistant or third-party memory service
- Harvest credentials or private records
- Deliver prompt injection or executable content
- Add persistence, evasion, or system compromise
- Bypass provider limits or authorization

All default traffic fixtures are benign and run inside disposable local stores. A pull request that expands the threat model needs a documented safety review before merge.

## Dependency reporting

Report vulnerable dependencies with the package name, installed version, advisory identifier, and the reachable ChaffMem Lab path. A dependency advisory is not automatically a reachable product vulnerability.
