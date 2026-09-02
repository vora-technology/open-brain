# Workstream State

- ID: `20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b`
- Repo root: <repo-root>
- Remote identity SHA-256 fingerprint: `cb5e9cd7ac71c16e5109717b4bc07f01aed1bbda2b18a99bfbc76f7bd98245bc`
- Worktree: <repo-root>
- Branch: goal/open-brain-phase4
- Objective: Execute Goal 63 through Phase 4 P4A, P4B, and P4C with independently reviewed package isolation, unpublished native artifacts, full-stop cutover, and day-0 evidence
- Created date: 2026-09-01

## Current milestone

- Milestone: P4-W1 workspace and engine distribution
- Status: P4-W1 candidate `7266e494f431ac84d9635b1a044bd15ce303c731`
  is pushed and exact-head CI is green. Its fresh review returned `NOT_READY`
  P0/P1/P2 `0/0/1` only because completion evidence lagged; this bounded
  evidence repair, exact-head CI, and fresh rereview remain before P4-W2
- Allowed scope: manifest-driven P4-W1 workspace/member skeletons, mechanical
  engine moves and import rewrites, engine API/package metadata, isolated
  engine build/install checks, verified commits, draft PR updates, and bounded
  evidence
- Stop condition: any move not authorized by the manifest, behavior repair
  without a red regression and separate commit, P4-W2 before P4-W1 is green,
  any acceptance review before applicable CI is green, or any production access
  before P4A, P4B, P4-W8, recovery, and receipt review all pass unchanged
- Base: freshly fetched `origin/main` at
  `3b89a4ba4787a378e6040ff042bd117da881918d`
- Launch commit: reviewed planning commit cherry-picked as
  `68c34d723e8f0bbdc7a51d5c5070e63e994b335d`
- Branch: `goal/open-brain-phase4`
- Plan SHA-256:
  `7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`
- Launch runtime goal thread: `01a05f1b-de55-7a41-bc01-673d277a1995`
- Resumed runtime goal thread: `01a05fc4-2219-7251-8798-a74a1a200911`

## Launch constraints

- Goal #24's earlier approved production apply is complete and must never be
  rerun. Phase 4 will create a new, separately bound full-stop transaction only
  after its source, artifact, recovery, and rehearsal gates pass.
- The public repository stores bounded result classes and opaque identities
  only. Private topology, recovery material, and operational output remain in
  the private governed state repository.
- Public package publication, tags, releases, predecessor deletion, and
  irreversible cleanup remain forbidden.
- No implementation writer child has been dispatched. One coordinator owns
  shared package metadata, the canonical manifest, imports, lockfile, and
  integration; review children remain read-only.

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

Commit and push this bounded evidence-only successor of the green
`7266e494f431ac84d9635b1a044bd15ce303c731` checkpoint, require every
exact-head PR check to pass, then dispatch a fresh read-only review. P4-W2
remains blocked until the verdict is `READY` with P0/P1/P2 `0/0/0`.

## P4-W0 complete

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
- Checkpoint commit:
  `ae144db9e461f9e369976c04b75467eb5c69a144`.
- Draft PR: `vora-technology/open-brain#6`.
- Required `phase4-contracts`, Python 3.12/3.13/3.14, public artifacts,
  macOS ARM64 lifecycle, and both CodeQL analyses passed on the exact commit.
- `phase4-contracts` was added to protected `main` as a required check.
- Sanitized Goal #63 checkpoint comment: `5502376856`.

## P4-W1 source checkpoint

- The root uv workspace has all four declared members. The engine distribution
  owns its distinct `open_brain_engine` namespace; app, connector, and legacy
  skeletons remain nonbuildable until their waves.
- All 46 engine runtime files and Portable resources are at their canonical
  manifest destinations. The engine has an explicit public API and no app,
  connector, legacy, third-party, or hidden workspace import edge.
- The manifest now covers 565 subjects: 224 runtime and 341 non-runtime.
  Package-local PEP 639 license files and the bounded Hatch sdist hook are
  classified, and generated movement evidence was refreshed.
- Exact artifact policy derives required membership from
  `docs/v0-package-classification.json`. The engine wheel contains the declared
  PEP 639 `LICENSE` and `NOTICE`; the sdist contains those files plus declared
  release resources and no `.gitignore` or undeclared member.
- The isolated engine contract installs only the engine wheel into one Python
  3.12 environment. A separate disposable test-runner environment executes all
  20 moved engine test modules from copied test inputs while repository source,
  app, connectors, and legacy remain unavailable.
- Remote CI at `2174dc2cfbc0e942c0842991650427b8a75ef91f` exposed Linux socket inode
  reuse in the restart readiness test. Commit
  `4ab916d27dacdccefdf1619120d3b323da5dc707` replaced inode observation with a
  bounded real status-protocol probe; 20 consecutive local restart cycles and
  all exact-head PR checks passed.
- A fresh review of `4ab916d27dacdccefdf1619120d3b323da5dc707` returned
  `NOT_READY`, P0/P1/P2 `0/0/4`. It found incomplete artifact membership,
  missing installed-wheel engine tests, stale wave evidence, and one incorrect
  manifest path in the review packet. The three repository findings are fixed
  at source checkpoint `a82485dd699ca7cd56c86d1904da7487fa1f87c1`; the next
  review packet names the sole canonical manifest correctly.
- Exact-head CI at evidence commit
  `974631e21e0a71a97b7269c69757e268687a5a63` then exposed uv's default Linux
  hardlink install mode: packaged Portable fixtures shared an inode with uv's
  cache and correctly failed the unique-regular-file invariant. Commit
  `181f9ae3438955d23dd39a155b7f23e9b93aa2f6` forces copied product installs.
  The 11 focused contracts passed in a metadata-free Linux Python 3.12
  container before the full local gate.
- Repaired candidate `7266e494f431ac84d9635b1a044bd15ce303c731` is pushed.
  CI run `33584116919`, public-artifacts run `33584116923`, and CodeQL run
  `33584115528` passed at that exact SHA, including Phase 4 contracts and
  Python 3.12, 3.13, and 3.14 verification.
- Fresh read-only child 4 reviewed the full P4-W1 range at `7266e494` and
  returned `NOT_READY`, P0/P1/P2 `0/0/1`. It independently resolved artifact
  membership, all moved engine tests under wheel isolation, and the canonical
  manifest path. Its sole P2 was that STATE, EVIDENCE, HANDOFF, and the
  dispatch ledger did not yet record the completed push, CI, and verdict; this
  evidence-only update is the bounded repair.
- Pinned local verification passed: 76 Phase 4 contracts, Ruff, strict MyPy on
  485 source files, canonical manifest validation, all 3,139 repository tests,
  isolated wheel/sdist build, exact artifact policy, source/artifact and
  reachable-history audits, Gitleaks over 59 commits, lock check, and diff
  integrity.
- Rebuilt artifact SHA-256 digests are
  `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`
  for the wheel and
  `d62df80976117ff76ccbbb3a753b8765e7cb9f3c2404b273ef27e3a18e418c26`
  for the sdist.
- No package publication, tag, release, deployment, production access, private
  state access, or cutover action occurred. P4-W2 remains blocked on final
  exact-head CI and rereview of this evidence-only successor.
