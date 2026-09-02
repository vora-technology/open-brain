# v0 artifact characterization

Status: Phase 4 app/engine isolation boundary. Machine policy:
[`release/v0-artifact-policy.json`](../release/v0-artifact-policy.json).

This records the isolated, unpublished engine and app Python artifacts. It does not claim that a
native v0 release exists or that the connector and legacy distributions are ready to ship.

## Wheel

Hatch builds two wheels with workspace sources disabled:

- `open-brain-engine` contains the public engine facade, engine implementation, and Portable
  schemas/conformance data. It contains no app, connector, legacy, test, or workspace module.
- `open-brain` contains app composition, daemon/HTTP/UI behavior, installed CLI/MCP entry points,
  and packaged launchd/systemd templates. It has an exact `open-brain-engine==0.1.0` dependency
  and contains no engine copy, connector, legacy, test, or workspace module.

The app scanner rejects imports of engine modules not marked public in
`docs/v0-package-classification.json`. Installed acceptance creates a fresh product environment
from only the app and engine wheels and runs the app tests from a separate test environment.

The machine policy derives required members from every classified artifact member. Missing files,
new unaccounted-for files, private resources, and duplicate distribution/kind coordinates fail
verification. The wheel statuses are `engine-isolated-unpublished` and
`app-isolated-unpublished`.

## Source distribution

Each sdist has an explicit Hatch include list. The engine sdist contains engine source, Portable
resources, and release policy metadata. The app sdist contains app source, public documentation,
synthetic examples, and release policy metadata. Neither includes tests, nested workstream state
under `docs/ai`, connector source, or legacy source.

`open_brain.dev.artifact_policy` strips the sdist root directory and compares actual archive
members with the machine policy. Missing schemas or conformance evidence, duplicate members,
unsafe member paths, operational state, credential paths, or database files fail verification.

## Target release exclusions

The default app and engine artifacts already exclude workspace tooling, predecessor migration and
cutover code, optional cloud code, and source-specific connector bridges. Connector and legacy
distributions remain separate gated work. The complete exclusion list is machine-readable.

## Approved host matrix

The only supported v0 targets are macOS 14 or newer on Apple Silicon and Linux x86_64 on Ubuntu
24.04 LTS, Ubuntu 26.04 LTS, and Debian 13. Intel macOS, Linux arm64, and Windows are outside the
v0 support promise.

## Native artifact status

Native artifacts remain pending. PyInstaller 6 onedir is the first candidate, with Nuitka
standalone as the accepted fallback if that spike fails. The policy has an empty `published` list
and does not assert that a native artifact exists. No bundler spike or clean-host run is current
release evidence.

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
