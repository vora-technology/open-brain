# v0 artifact characterization

Status: Phase 4 P4-W5 unpublished native build subject. Machine policy:
[`release/v0-artifact-policy.json`](../release/v0-artifact-policy.json).

This records the isolated, unpublished Python artifacts and the native P4-W5 build subject. It
does not claim that a native v0 release exists, that a clean-host candidate has passed P4-W6, or
that any artifact is ready to publish.

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

Native build subjects are present for PyInstaller 6.22.2 onedir with
`pyinstaller-hooks-contrib` 2026.7 and Python 3.12. The same checked-in spec runs on native macOS
ARM64 and Ubuntu 24.04 x86_64 CI. Its bounded audit records exact source identity, member and tree
digests, packaged supervisor resources, confined symlinks, frozen child routing, daemon restart,
native lifecycle activation, uninstall, and clean managed residue.

These are P4-W5 spike inputs and checks, not published release artifacts. Nuitka standalone 4.2
remains the accepted fallback only if the documented PyInstaller failure gate is exhausted. The
policy keeps `published` empty. Signing, notarization, checksummed release candidates, and
clean-host lifecycle proof remain P4-W6 gates.

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

Gitleaks has a separate exact-fingerprint ignore file for reviewed synthetic or opaque public
values that match a generic detector. Each exception binds the introducing commit, path, rule, and
line. The immutable P4 readiness snapshot uses one such entry for an opaque receipt; its strict
schema and fixed file SHA-256 remain independently enforced. Changing `.gitleaksignore` triggers
the full Release audit workflow.

The Phase 0 real-history result is recorded in
[`docs/audits/2026-08-30-phase0-public-history-audit.md`](audits/2026-08-30-phase0-public-history-audit.md).
