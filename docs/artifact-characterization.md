# v0 artifact characterization

Status: Phase 0 explicit boundary. Machine policy:
[`release/v0-artifact-policy.json`](../release/v0-artifact-policy.json).

This records the Python artifacts produced from the current monolith. It does not claim that the
native v0 release exists or that mixed and legacy packages are ready to ship.

## Wheel

Hatch builds the wheel from `src/open_brain`. The current wheel therefore contains the complete
existing package graph, including paths classified as mixed, legacy, connector-specific, or
workspace tooling. Phase 0 characterizes that fact instead of silently excluding files that the
current CLI still imports.

Two public compatibility resources are force-included:

- `schemas/portable-brain/v1` at `open_brain/portable/schemas/v1`;
- `tests/fixtures/portable-brain/v1` at
  `open_brain/portable/conformance/v1`.

The machine policy derives required members from every file in both resource trees, rather than
sampling one representative schema or fixture. Missing files or new unaccounted-for files are
therefore visible in artifact verification. The wheel status is
`explicit-current-not-release-ready`.

## Source distribution

The sdist has an explicit Hatch include list. It contains the current source package, root project
metadata, the selected public architecture and contract documents, artifact policy, Portable
Brain schemas, current-record characterization, contract tests, and synthetic conformance
fixtures. It does not include nested workstream state under `docs/ai`.

`open_brain.dev.artifact_policy` strips the sdist root directory and compares actual archive
members with the machine policy. Missing schemas or conformance evidence, duplicate members,
unsafe member paths, operational state, credential paths, or database files fail verification.

## Target release exclusions

The current artifact and the target public artifact are different boundaries. Before release,
package separation must remove workspace tooling, predecessor migration/parity and cutover code,
optional cloud code, and source-specific connector bridges from the default app artifact. The
complete target list is machine-readable. Optional connectors can be built and tested separately
after their own Phase 2 contracts exist.

## Approved host matrix

The only supported v0 targets are macOS 14 or newer on Apple Silicon and Linux x86_64 on Ubuntu
24.04 LTS, Ubuntu 26.04 LTS, and Debian 13. Intel macOS, Linux arm64, and Windows are outside the
v0 support promise.

## Native artifact status

Phase 4 pending: PyInstaller 6 onedir is the first candidate, with Nuitka standalone as the
accepted fallback if that spike fails. The policy has an empty `published` list and does not
assert that a native artifact exists. No bundler spike or clean-host run is Phase 0 evidence.

## Private-history audit

`open_brain.dev.public_history_audit` scans each reachable Git blob once, applies bounded batch
reads and command timeouts, fails closed when scan limits are exceeded, and emits only commit ID,
redacted path, and rule ID. The owner declared no additional project-specific private terms for
the clean public repository. Generic credential, private-IP, absolute-home, forbidden-path, and
scan-limit rules run with a synthetic denylist in CI.

Reviewed historical false positives may be recorded in
`release/public-history-allowlist.json`. Each entry binds one SHA-256 blob digest, one normalized
repository path, and one rule. Only `absolute-home-path` and `private-ip-address` are eligible;
credential, denylist, forbidden-path, and scan-limit findings cannot be suppressed.

The Phase 0 real-history result is recorded in
[`docs/audits/2026-08-30-phase0-public-history-audit.md`](audits/2026-08-30-phase0-public-history-audit.md).
