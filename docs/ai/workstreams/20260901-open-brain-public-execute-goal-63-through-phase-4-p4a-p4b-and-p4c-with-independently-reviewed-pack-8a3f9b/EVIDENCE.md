# Phase 4 execution evidence

## Gate 0 launch

- Explicit user launch received on 2026-09-01.
- Runtime goal registered for Goal #63.
- Fresh fetch confirmed `origin/main` at
  `3b89a4ba4787a378e6040ff042bd117da881918d`.
- Exact reviewed plan SHA-256 confirmed as
  `7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`.
- New branch `goal/open-brain-phase4` created from that base; reviewed planning
  commit cherry-picked as `68c34d723e8f0bbdc7a51d5c5070e63e994b335d`.
- New implementation workstream created; planning task IDs and state were not
  reused.
- Public required checks, current workflow hosts, open parent goals, local
  ARM64/Python/uv/signing tools, project gotchas, and latest private Goal #24
  handoff were inspected.
- No runtime source moved, no native artifact built, and no production or live
  Brain state was accessed during launch.

## Gate 0 baseline verification

- `make verify`: passed Ruff, strict MyPy on 474 source files, all 3,114 tests,
  isolated wheel/sdist builds, and artifact policy.
- Current source-ownership validator: 53 tests passed.
- Source plus wheel/sdist release audit: passed with one untracked synthetic
  denylist.
- Reachable-history audit: passed with the same denylist.
- Explicit artifact-policy rerun and `git diff --check`: passed.
- Inventory equality: all 224 tracked runtime Python files exactly match the
  canonical classification; owner counts are engine 46, app 34, connector 5,
  legacy 135, and workspace 4; temporary live debt is zero.
- Additional manifest subjects observed: 250 tracked Python files under
  `tests/` and 36 tracked schema/fixture files.
- Required public checks: strict linear `main`, `verify (3.12)`, `verify
  (3.13)`, `verify (3.14)`, and `public-artifacts`; force pushes and branch
  deletion disabled.
- Successful CI logs directly identify macOS 14 ARM64 and Ubuntu 24.04 x86_64
  builders.
- Local build host: ARM64, Python 3.12, `uv`, `notarytool`, and one valid
  Developer ID Application identity. A ready notary credential profile was not
  found on either checked authorized host.
- Private read-only preflight: exact scoped helper and host identity checks
  passed; arbitrary sudo and root SSH remained denied; service, writer,
  synchronization, executable-reference, and recovery-readiness inventories
  completed with zero mutations and no private output in this repository.
- Private recovery access is not currently ready and must be remediated and
  re-proved before P4-W8. The prior Goal #24 apply remains historical and will
  not be rerun.
- Launch status comments:
  `cbolden15/agent-config#63` comment `5502133708`, parent `#41` comment
  `5502134010`, and parent `#24` comment `5502134267`.

## P4-W0 local candidate

- Canonical schema: version 3 with Phase 4 schema version 1.
- Subject closure: 224 runtime plus 331 non-runtime equals 555 exact current
  subjects. Non-runtime kinds: 253 tests, 21 package resources, 21 fixtures,
  15 schemas, 10 release tools, 4 release resources, 3 generated reports, 3
  entry points, and 1 test resource.
- Generated evidence: exact move report, exact import-rewrite report, and one
  11-finding current-monolith expected-red report.
- Expected-red execution: exited 1 and exactly matched the committed bounded
  finding set (`P4E001` through `P4E005`). It is not a required green test.
- `make phase4-contracts`: 68 tests passed; Ruff passed; strict MyPy passed on
  481 source files; canonical validator returned zero findings.
- `make verify`: 3,129 tests passed; Ruff and strict MyPy passed; isolated
  wheel/sdist builds used Hatchling 1.32.0; artifact policy passed.
- Source plus built-artifact release audit, reachable-history audit, explicit
  artifact-policy rerun, Gitleaks over 51 commits, `uv lock --check`, and
  `git diff --check`: passed.
- Runtime movement assertion: no path below `src/open_brain` changed relative
  to the reviewed launch commit.
- Read-only child 1 implementation map: `READY`, P0/P1/P2 `0/2/2`. Both P1s
  were implemented: Phase 4 tools are under strict MyPy and public-artifact
  triggers cover the new manifest/tools/tests.
- Checkpoint commit: `ae144db9e461f9e369976c04b75467eb5c69a144`.
- Draft PR: `vora-technology/open-brain#6`.
- Exact-commit PR checks passed: protected `phase4-contracts`, `verify (3.12)`,
  `verify (3.13)`, `verify (3.14)`, `public-artifacts`, macOS ARM64 appliance
  lifecycle, CodeQL Actions analysis, and CodeQL Python analysis.
- Branch protection now requires `phase4-contracts` in addition to the prior
  four required checks.
- Sanitized Goal #63 checkpoint comment: `5502376856`.
- P4-W0 is complete. P4-W1 may begin; later gates remain blocked by their own
  source, artifact, review, recovery, and production preconditions.

## P4-W1 source checkpoint

- Workspace and engine movement completed in commits `c884d88`, `5f127c1`, and
  `2174dc2`. The four-member workspace is active, all 46 engine runtime files
  and Portable resources are moved, and the app/connector/legacy skeletons
  remain nonbuildable for their later waves.
- Remote Python 3.12, 3.13, and 3.14 jobs failed only because the source-checkout
  restart test waited for a changed Unix socket inode. Linux immediately reused
  that inode. Commit `4ab916d27dacdccefdf1619120d3b323da5dc707` now waits for
  a bounded status control-protocol response. Twenty consecutive local restart
  cycles passed, followed by all exact-head PR checks.
- Fresh read-only review of `4ab916d27dacdccefdf1619120d3b323da5dc707`
  returned `NOT_READY`, P0/P1/P2 `0/0/4`. The valid repository findings were:
  incomplete manifest-declared artifact membership, no execution of the moved
  engine tests from the installed wheel, and stale P4-W1 evidence. The fourth
  finding corrected the review packet from a nonexistent manifest path to
  `docs/v0-package-classification.json`; no second manifest was created.
- Red regressions proved the gaps: the acceptance test could not import an
  installed engine-test command, and artifact tests failed for absent manifest
  binding, accepted unclassified members, and incomplete derived membership.
- Source checkpoint `a82485dd699ca7cd56c86d1904da7487fa1f87c1` fixes all
  three repository findings. Exact artifact membership is derived from the
  canonical manifest. PEP 639 license files and declared release resources are
  packaged, and a bounded Hatch hook removes forced VCS exclusion-file residue
  from the sdist.
- The isolated engine gate now installs only the engine wheel into its product
  environment and executes all 20 moved engine test modules through a separate
  locked test-runner environment. Tests run from copied inputs with repository
  source and the app, connector, and legacy distributions unavailable.
- Local Python 3.12 and uv 0.12.8 verification passed: 76 Phase 4 contracts,
  Ruff, strict MyPy on 485 files, manifest validation, 3,139 total tests,
  wheel/sdist build, exact artifact policy, source plus artifact release audit,
  `uv lock --check`, and `git diff --check`.
- Artifact SHA-256 digests:
  wheel `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`;
  sdist `d62df80976117ff76ccbbb3a753b8765e7cb9f3c2404b273ef27e3a18e418c26`.
- P4-W1 is not closed yet. The evidence commit must be pushed, all exact-head CI
  checks must pass, and a corrected fresh review must return `READY` with
  P0/P1/P2 `0/0/0` before P4-W2.
- No publication, deployment, production, private-state, or cutover action
  occurred.
