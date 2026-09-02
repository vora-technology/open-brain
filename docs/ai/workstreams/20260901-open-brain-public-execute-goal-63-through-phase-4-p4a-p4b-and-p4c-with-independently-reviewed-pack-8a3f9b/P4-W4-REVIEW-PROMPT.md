# P4-W4 and P4A rereview task

Objective: Independently rereview the exact repair candidate supplied in the
child-resume message. Decide whether both prior findings are closed and P4-W4
and the full P4A gate are `READY` with P0/P1/P2 `0/0/0`.

Source of truth and precedence: Runtime authority; the immutable Git object and
exact-head CI, Release audit, and CodeQL runs supplied in the resume message;
`origin/main` at `3b89a4ba4787a378e6040ff042bd117da881918d`;
`CLAUDE.md`; the checked-in Phase 4 goal contract;
`docs/plans/phase-4-physical-split-native-artifacts-and-cutover.md` at SHA-256
`7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`;
the P4-W4 phase prompt; `docs/v0-package-classification.json`; and the release
policy records. Review the exact committed source, not later or uncommitted
work.

Allowed write scope: None. This is read-only. Do not edit files, create commits,
push, deploy, publish, access private state, or perform production actions.

Verification: Reproduce closure of `P4A-001`. The canonical graph, validator,
legacy metadata, lockfile, source imports, and private wheel metadata must agree
on `legacy -> engine` only. No legacy runtime file may import or dynamically
load the app or connector distributions. The private `_compat` namespace must
remain legacy-only, consume only engine/stdlib/legacy code, and stay absent from
all shipping artifacts. Reproduce the clean-room contract that installs only
engine and legacy wheels, imports every packaged legacy module, and proves app
and connectors unavailable. Reproduce closure of `P4A-002` by checking the
artifact-policy path in `CLAUDE.md`.

Also inspect all P4A completion criteria: canonical movement and destinations,
absence of `src/open_brain`, deterministic import rewriting, one
`tools.open_brain_dev` identity, zero manifest findings, source-free isolated
engine/app/connector artifacts, artifact policy, full tests, and exact-head
checks. Review the reusable readiness preflight for the owner-added requirement:
signing, notarization, macOS ARM64, Linux x86_64, disk capacity, and recovery
access; read-only injected probes; booleans and opaque receipts only; one
validated snapshot reusable from P4-W5 through P4-W9 without another probe call.

Stop condition: Return `NOT_READY` or a bounded blocker if the exact SHA is
unavailable, source identity cannot be proved, required exact-head checks are
not green, verification would require private data, either prior finding
survives, or any new P0/P1/P2 finding remains. Do not weaken a gate or review a
different revision.

Sensitive-data policy: Public-repository data only. Never access or persist
private Brain state, customer data, credentials, secret values, private
topology, raw operational output, or credential-bearing URLs. Report bounded
metadata and repository paths only.

Output contract: Return `VERDICT: READY` or `NOT_READY`; exact reviewed source
SHA; P0, P1, and P2 counts; findings ordered by severity with stable IDs, path
and line, concrete evidence, reproduction, impact, and bounded fix guidance;
checks performed; and verification limits. `READY` is valid only with P0/P1/P2
`0/0/0`. State explicitly when there are no findings. Do not modify the
repository.
