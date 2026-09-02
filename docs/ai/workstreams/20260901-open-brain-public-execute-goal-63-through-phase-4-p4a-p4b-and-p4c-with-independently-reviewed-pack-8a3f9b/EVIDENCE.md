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
- Exact-head CI at `974631e21e0a71a97b7269c69757e268687a5a63` failed only
  the installed-engine contract in `phase4-contracts` and Python 3.12, 3.13,
  and 3.14 verification. A clean Linux reproduction showed uv's default wheel
  install had hardlinked packaged Portable fixtures to its cache, so their
  link count correctly violated the unique-regular-file invariant.
- Commit `181f9ae3438955d23dd39a155b7f23e9b93aa2f6` makes the
  isolated product install use uv's copy mode. All 11 focused harness and
  engine-distribution tests passed in a metadata-free Linux Python 3.12
  container; no validator invariant was weakened.
- Candidate `7266e494f431ac84d9635b1a044bd15ce303c731` is pushed and
  clean. Exact-head CI run `33584116919`, public-artifacts run `33584116923`,
  and CodeQL run `33584115528` passed, including Phase 4 contracts and Python
  3.12, 3.13, and 3.14 verification.
- Fresh read-only child 4 reviewed all nine P4-W1 commits and 371 changed paths
  at `7266e494`. It returned `NOT_READY`, P0/P1/P2 `0/0/1`. Exact artifact
  membership, execution of all moved tests under wheel isolation, and the sole
  canonical manifest path are independently resolved. The only finding was
  stale completion evidence in STATE, EVIDENCE, HANDOFF, and the dispatch
  ledger; this bounded evidence-only update repairs that finding.
- Local Python 3.12 and uv 0.12.8 verification passed: 76 Phase 4 contracts,
  Ruff, strict MyPy on 485 files, manifest validation, 3,139 total tests,
  wheel/sdist build, exact artifact policy, source plus artifact release audit,
  reachable-history audit, Gitleaks over 59 commits, `uv lock --check`, and
  `git diff --check`.
- Artifact SHA-256 digests:
  wheel `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`;
  sdist `d62df80976117ff76ccbbb3a753b8765e7cb9f3c2404b273ef27e3a18e418c26`.
- Evidence successor `aab6f1e0891d551a87a2968ef9fb0dae1a8e62e2` passed all
  exact-head checks. Its fresh rereview returned `READY`, P0/P1/P2 `0/0/0`;
  P4-W1 is complete.
- No publication, deployment, production, private-state, or cutover action
  occurred.

## P4-W2 repaired source checkpoint

- Behavior repair `2f08a48aefe51eb755885d9f9ae01cf9c5fa5769` packages the
  launchd/systemd templates and adds an installed supervisor mode. Its red
  regression failed exactly for absent resources and rejected installed mode;
  the repaired supervisor suite passed before movement.
- Implementation checkpoint `2ed82c05ad2f5508a9a04b3c7eadeb86ed676cdf`
  moves all 34 app runtime files, 28 existing app test modules, and app
  resources to `packages/app`; adds one explicit two-test wheel gate module;
  and binds the installed CLI/MCP scripts.
- Canonical inventory is 224 runtime plus 348 non-runtime subjects. It includes
  257 test subjects, 34 moved app runtime records, and 38 moved app subjects.
- App metadata requires exactly `open-brain-engine==0.1.0`; wheel metadata,
  module origins, console scripts, supervisor resources, and connector/legacy
  absence are asserted from an installed product environment.
- A static wheel scan derives the allowed public engine modules from the
  canonical manifest and rejects app imports of private engine modules.
- The isolated app contract builds with `--no-sources`, installs only copied
  app/engine wheels into Python 3.12, and exposes that site-packages directory
  to a separate locked test runner. All 400 app tests pass without checkout
  fixtures, connector, legacy, or workspace source.
- Named wheel-only contracts pass `V0-GATE-07` with six sibling proposals and
  independent CLI/UI approve, reject, and safe edit. They pass `V0-GATE-13`
  with space create/rename, later route without capture-identity change, and
  scoped/all-space retrieval through CLI and UI.
- Artifact policy version 2 owns app and engine distribution/kind coordinates.
  The real app/engine wheels and sdists contain exactly canonical members and
  no forbidden or undeclared members.
- Candidate `85428b125ddd370cfa6a6c2be20f2aab4669bf7e` passed exact-head CI after
  one same-SHA retry. CI attempt 1 failed only the Python 3.12 app-isolation
  wrapper with generic `P4H007`; the concurrent dedicated Ubuntu/Python 3.12
  contract and a local isolated Python 3.12 full suite passed. Attempt 2
  passed every job.
- Child 6 reviewed `85428b1` and returned `NOT_READY`, P0/P1/P2 `0/3/1`.
  The P1 findings were installed supervisor source leakage, false-positive
  3.13/3.14 wheel coverage, and incomplete private/undeclared import checks.
  The P2 was this stale evidence packet.
- Three focused regressions reproduced all P1 findings before repair:
  installed factory rendering leaked `PYTHONPATH`; environment creation
  selected 3.12 while the active interpreter was 3.14; and the artifact scan
  missed private-child, undeclared, and unreviewed dynamic imports.
- Repair checkpoint `7d87c3968e15de5d98f7e509c8c8a31c4c5b500c` validates a
  source-checkout layout before adding supervisor paths, selects the active
  matrix interpreter, derives the complete engine module policy and declared
  app dependencies, allow-lists one exact dynamic import seam, and reports
  bounded app-isolation failure stages.
- Local verification passed: `make verify` (Ruff, strict MyPy on 488 files,
  3,148 tests, and all four artifact builds/policy); a separate uncached Ruff
  run; `make phase4-contracts` (79 tests, Ruff, MyPy, manifest); app-wheel
  journeys under isolated Python 3.12, 3.13, and 3.14; source+artifact release audit;
  reachable-history audit; Gitleaks 8.30.1 over 66 commits; `uv lock --check`;
  and `git diff --check`.
- Exact-head CI run `33591952670`, public-artifacts run `33591952648`, and
  CodeQL run `33591951436` passed at `7d87c39`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Artifact SHA-256 digests:
  app wheel `9b0f06e03e2bdfcfc690e011faa15773eb4efbf26844fff5c446bfc0d11ad84d`;
  app sdist `d6afc82e2cc3ec4d9bf53215129c39a64542a60cbe7831b95505b2660208917a`;
  engine wheel `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`;
  engine sdist `a52e659e44d4dcfc882f76d998540a41d2abffa7886a83db365cb688c914084a`.
- Evidence checkpoint `579b45bc12247d34ed612798fc2a6021ccc1d30a`
  passed all exact-head checks before the second P4-W2 review.
- Child 7 reviewed `579b45b` and returned `NOT_READY`, P0/P1/P2 `0/1/0`.
  The sole P1 found dynamic-import bypasses through `builtins`, assignment
  aliases, and reflective access, plus a false positive for a local object
  named `importlib`.
- A focused artifact regression failed before repair on every reported case.
  Self-review extended it with an importer-capability escape inside the sole
  reviewed dynamic-import file.
- Repair checkpoint `e27ac3c3ad7daa4748b094490fdadab6e66a3773`
  follows lexical provenance for dynamic importer capabilities, records
  constant targets for private and undeclared dependency checks, rejects
  unresolved uses, and binds the only exception to its exact artifact path
  and function signature.
- Final local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,149 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (80 tests, Ruff, MyPy, manifest); isolated
  app-wheel journeys on Python 3.12, 3.13, and 3.14; source+artifact release
  audit; reachable-history audit; Gitleaks 8.30.1 over 69 commits; `uv lock
  --check`; and `git diff --check`.
- Exact-head CI run `33594652359`, public-artifacts run `33594652371`, and
  CodeQL run `33594650509` passed at `e27ac3c`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Rebuilt artifact SHA-256 digests were unchanged from the preceding repair.
- Evidence checkpoint `0a67a26210b79d0c91fa8953846560db34903034`
  passed all exact-head checks before the third P4-W2 review.
- Child 8 reviewed `0a67a26` and returned `NOT_READY`, P0/P1/P2 `0/1/1`.
  The P1 reproduced a private engine import through
  `sys.modules["builtins"]` and identified the same fail-open class through
  runtime namespace helpers. The P2 found that the isolated app evidence said
  402 tests although the exact package scope collects 400.
- A focused artifact regression failed before repair for `sys.modules`,
  `globals`, `locals`, `vars`, `eval`, `exec`, and an assigned alias. Its
  negative case proved a shadowed local `globals` callable remains clean.
- Repair checkpoint `d8e2cb20f0268e16ebdd5b46053d5081dab7ac7c`
  carries provenance through `sys.modules` and built-in namespace mappings,
  fails closed on dynamic evaluation capabilities, records constant private
  and forbidden targets, and corrects both app-suite claims to 400.
- Latest local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,150 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (81 tests, Ruff, MyPy, manifest); exact collection
  of 400 app tests; isolated app-wheel journeys on Python 3.12, 3.13, and
  3.14; source+artifact release audit; reachable-history audit; Gitleaks
  8.30.1 over 71 commits; `uv lock --check`; and `git diff --check`.
- Exact-head CI run `33596668616`, public-artifacts run `33596668630`, and
  CodeQL run `33596666546` passed at `d8e2cb2`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Rebuilt artifact SHA-256 digests remained unchanged.
- No package publication, tag, release, native build, deployment, production
  access, private-state access, or cutover action occurred. This evidence
  successor, exact-head CI, and a fresh read-only review remain required before
  P4-W2 closes.
