# Workstream State

- ID: `20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b`
- Repo root: <repo-root>
- Remote identity SHA-256 fingerprint: `cb5e9cd7ac71c16e5109717b4bc07f01aed1bbda2b18a99bfbc76f7bd98245bc`
- Worktree: <repo-root>
- Branch: goal/open-brain-phase4
- Objective: Execute Goal 63 through Phase 4 P4A, P4B, and P4C with independently reviewed package isolation, unpublished native artifacts, full-stop cutover, and day-0 evidence
- Created date: 2026-09-01

## Current milestone

- Milestone: Gate 0 immutable launch baseline
- Status: Gate 0 complete; P4-W0 implementation candidate locally green;
  checkpoint commit, push, draft PR, and required CI pending
- Allowed scope: Gate 0 inventories and evidence, P4-W0 manifest/harness/toolchain
  implementation, verified commits, branch push, draft PR creation, and sanitized
  Goal #63 status updates
- Stop condition: any runtime source move before P4-W0 is green, any P4A/P4B
  acceptance review before applicable CI is green, or any production access
  before P4A, P4B, P4-W8, recovery, and receipt review all pass unchanged
- Base: freshly fetched `origin/main` at
  `3b89a4ba4787a378e6040ff042bd117da881918d`
- Launch commit: reviewed planning commit cherry-picked as
  `68c34d723e8f0bbdc7a51d5c5070e63e994b335d`
- Branch: `goal/open-brain-phase4`
- Plan SHA-256:
  `7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`
- Runtime goal thread: `01a05f1b-de55-7a41-bc01-673d277a1995`

## Launch constraints

- Goal #24's earlier approved production apply is complete and must never be
  rerun. Phase 4 will create a new, separately bound full-stop transaction only
  after its source, artifact, recovery, and rehearsal gates pass.
- The public repository stores bounded result classes and opaque identities
  only. Private topology, recovery material, and operational output remain in
  the private governed state repository.
- Public package publication, tags, releases, predecessor deletion, and
  irreversible cleanup remain forbidden.
- No implementation child has been dispatched. One coordinator owns shared
  package metadata, the move manifest, imports, lockfile, and integration.

## Gate 0 observations

- Public `origin/main` matches the reviewed baseline and its latest CI,
  release-audit, and CodeQL runs are green.
- Protected `main` requires linear history plus `verify (3.12)`, `verify
  (3.13)`, `verify (3.14)`, and `public-artifacts`; force pushes and deletions
  are disabled.
- Goals #24, #39, #41, and #63 are open. Goal #63 had no comments at launch.
- Local host: ARM64 macOS, Python 3.12 available, `uv` available,
  `notarytool` available, and one valid Developer ID Application identity.
- Successful CI logs directly identify the current builders as macOS 14 ARM64
  and Ubuntu 24.04 x86_64.
- Notarization credentials were not ready on either checked authorized host.
  This is a P4B prerequisite, not permission to weaken or skip signing.
- Durable context lookup: no Phase 4-specific work-brain page was found;
  project gotchas and the Phase 3 decision/evidence logs were used.
- Latest private Goal #24 handoff is complete and safe to read. It reports the
  old production apply complete, the remote stage absent, transaction
  namespaces inactive, and immutable historical/recovery artifacts retained.
- Fresh private read-only checks proved exact scoped-helper authority and
  recorded current service, writer, synchronization, executable-reference,
  and recovery-readiness result classes. Recovery access needs remediation and
  re-proof before P4-W8. No private topology or raw output entered this repo.
- Private companion workstream:
  `20260901-open-brain-private-retain-private-goal-63-recovery-service-writer-synchronization-notarization-rehe-70e37e`.
- Baseline `make verify` passed Ruff, strict MyPy on 474 source files, all
  3,114 tests, wheel/sdist builds, and artifact policy.
- The explicit ownership suite passed 53 tests. Source/artifact release audit,
  reachable-history audit, artifact policy, and diff integrity passed.
- Current inventory: 224 runtime files (46 engine, 34 app, 5 connector, 135
  legacy, 4 workspace), 250 tracked Python files under `tests/`, 36 tracked
  schema/fixture files, and zero temporary live architecture debt.
- Launch notices are recorded on child Goal #63 and parent Goals #41 and #24.

## Next action

Commit the exact P4-W0 candidate, push `goal/open-brain-phase4`, open the
required draft PR, make `phase4-contracts` a required check after its first
run, and require all applicable CI plus artifact safety to pass before P4-W1.

## P4-W0 candidate

- Canonical manifest schema 3 covers 555 subjects: all 224 runtime files and
  331 non-runtime subjects. The latter include all 253 current Python files
  under `tests/`, all 36 schema/fixture files, three entry points, package and
  test resources, release resources/tools, and three generated reports.
- Runtime ownership remains engine 46, app 34, connector 5, legacy 135, and
  workspace 4. No file below `src/open_brain` moved or changed.
- The validator emits stable `P4M001` through `P4M011` findings and rejects
  incomplete/stale subjects, duplicate/out-of-bound destinations, unresolved
  rewrites, forbidden dependency edges, unresolved old paths, shipping leaks,
  and release/schema mismatches.
- The reusable harness defines all six P4A/P4B acceptance contracts, isolated
  no-sources/no-index commands, source-path masking checks, and stable artifact
  finding codes. Synthetic missing, leaked, mismatched, unsafe, duplicate, and
  source-masked cases pass.
- The current monolith check is intentionally outside the default green gate.
  It exits 1 with exactly 11 bounded `P4E001` through `P4E005` findings matching
  the committed expected-red report.
- Toolchain records pin `uv 0.12.8`, Hatchling `1.32.0`, PyInstaller `6.22.2`,
  hooks `2026.7`, and fallback Nuitka `4.2`. Workspace activation remains
  correctly assigned to P4-W1.
- Dedicated real-subject `phase4-contracts` CI and widened public-artifact
  triggers are present. No future artifact has a placeholder-green job.
- Local verification: 68 focused tests, Ruff, strict MyPy on 481 files,
  manifest validation, all 3,129 repository tests, isolated wheel/sdist build,
  artifact policy, source/artifact and reachable-history audits, Gitleaks,
  lock check, diff integrity, and zero runtime-source movement all passed.
