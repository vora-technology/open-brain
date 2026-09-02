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

## P4-W2 complete

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
- Evidence checkpoint `e483973e7f8153b97aa5a44b049d787d08fd884f`
  passed all exact-head checks before the fourth P4-W2 review.
- Child 9 reviewed `e483973` and returned `NOT_READY`, P0/P1/P2 `0/1/0`.
  The P1 reproduced import escapes through `sys.__dict__`,
  `sys.__getattribute__`, and function or lambda `__globals__`. It also found
  path-insensitive rebinding and false positives where loop, `with`, or
  exception targets shadowed the standard-library `sys` module.
- One focused artifact regression failed before repair on every positive and
  negative case, including a hidden `__globals__` import in the otherwise
  reviewed optional-provider file. Self-review added bound function and
  `object.__getattribute__` variants before broad verification.
- Repair checkpoint `bd994a0288f8711f216e130c25c45f7a654eb90f`
  uses conservative provenance sets, joins branch states, models function,
  class, loop, `with`, exception, match, and comprehension bindings, and
  recognizes namespace and bound `__getattribute__` reflection.
- Current local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,151 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (82 tests, Ruff, MyPy, manifest); all 11 analyzer
  tests independently on Python 3.12, 3.13, and 3.14; isolated app-wheel
  journeys on all three versions; source+artifact release audit;
  reachable-history audit; Gitleaks 8.30.1 over 73 commits; `uv lock --check`;
  and `git diff --check`.
- Exact-head CI run `33600292963`, public-artifacts run `33600292877`, and
  CodeQL run `33600287985` passed at `bd994a0`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Rebuilt artifact SHA-256 digests remained unchanged.
- Evidence checkpoint `0cff2ea6077b2450febd07f456310aff1f6ffd25`
  passed all exact-head checks before the fifth P4-W2 review.
- Child 10 reviewed `0cff2ea` and returned `NOT_READY`, P0/P1/P2 `0/2/0`.
  One P1 reproduced forbidden imports through aliases of `sys.__dict__`,
  `sys.__getattribute__`, and `builtins.object`. The other reproduced a PEP
  572 comprehension assignment that lost its enclosing-scope provenance.
- Focused wheel regressions failed before repair for each positive path and
  for the related shadow-negative case. Self-review added symmetric
  `importlib` and `builtins` aliases plus normal walrus overwrite behavior.
- Repair checkpoint `e103255b2ab03c3312206383b71ce38fcde67b8e`
  derives `ImportFrom` bindings from the same modeled module-member authority
  used for attribute access. Comprehension assignment expressions now update
  their nearest enclosing scope and are predeclared as function locals.
- Latest local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,151 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (82 tests, Ruff, MyPy, manifest); all 14 analyzer and
  app-wheel tests on Python 3.12, 3.13, and 3.14; source+artifact release
  audit; reachable-history audit; Gitleaks 8.30.1 over 75 commits; `uv lock
  --check`; and `git diff --check`.
- Exact-head CI run `33602946392`, public-artifacts run `33602946514`, and
  CodeQL run `33602944303` passed at `e103255`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Rebuilt artifact SHA-256 digests remained unchanged.
- Evidence checkpoint `995bd781869901e772eee0c7fdfd0ab8132065d5`
  passed CI run `33603709388`, public-artifacts run `33603709475`, and CodeQL
  run `33603706129` before the sixth P4-W2 review.
- Child 11 reviewed `995bd78` and returned `NOT_READY`, P0/P1/P2 `0/2/0`.
  One P1 reproduced unreviewed imports through `importlib.__init__`,
  `pkgutil.resolve_name`, aliased `importlib.util`, `sys._getframe`, and
  function-type reflection. The other showed that the reviewed helper could
  reassign `import_path` while retaining its approved call spelling.
- Both focused artifact regressions failed with zero findings before repair.
  Self-review added `from` aliases, colon-qualified resolver targets,
  `function.__class__`, direct and conditional replacement, and
  second-parameter substitution. Four app tests prove internal roots are
  rejected by metadata construction and the runtime loader.
- Repair checkpoint `559690e14b9a1dd935566b54e97ec8f2b73f8d06`
  normalizes equivalent module authorities, tracks frame and type reflection,
  separates pristine parameters from unknown values through control flow,
  preserves the app's safe importlib resource/metadata APIs, and blocks
  internal package roots at the optional-provider boundary.
- Latest local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,157 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (84 tests, Ruff, MyPy, manifest); exact collection
  of 404 app tests; all 16 analyzer and app-wheel tests on Python 3.12, 3.13,
  and 3.14; source+artifact release audit; reachable-history audit; Gitleaks
  8.30.1 over 77 commits; `uv lock --check`; and `git diff --check`.
- Exact-head CI run `33608085686`, public-artifacts run `33608085774`, and
  CodeQL run `33608082590` passed at `559690e`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Rebuilt SHA-256 digests are app wheel
  `812b0a64bbecb2f19b1713411f31bab69a5d52027dc7c3c871bc493ffc65f272`,
  app sdist
  `48a7c763b9b46c5832d11ddd20a3f6975bfd57f0f5db6a96e870aaea3543d080`,
  engine wheel
  `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`,
  and engine sdist
  `a52e659e44d4dcfc882f76d998540a41d2abffa7886a83db365cb688c914084a`.
- Evidence checkpoint `ce909a525dbc66ec5d893892984f2814f7bb9e71`
  passed CI run `33609157287`, public-artifacts run `33609157406`, and CodeQL
  run `33609152877`. Child 12 started a final review and was stopped without a
  verdict after the candidate architecture was superseded.
- Repair checkpoint `9ca31ba36c44e4e4a269e5c932fae27fa174831e`
  removes the generic string-based loader and its sole P4H009 exception. A
  closed `OptionalProvider` enum selects an immutable lazy-loader registry
  containing only the declared `openai` extra. Typed construction makes
  internal roots unrepresentable, while the runtime loader rejects non-enum
  internal identifiers. P4H009 remains a finite adversarial architecture
  corpus rather than a malicious-code sandbox.
- Latest local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,157 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (84 tests, Ruff, MyPy, manifest); exact collection
  of 404 app tests; all 16 analyzer and app-wheel tests on Python 3.12, 3.13,
  and 3.14; source+artifact release audit; reachable-history audit; Gitleaks
  8.30.1 over 79 commits; `uv lock --check`; and `git diff --check`.
- Exact-head CI run `33611279850`, public-artifacts run `33611279794`, and
  CodeQL run `33611274401` passed at `9ca31ba`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14.
- Rebuilt SHA-256 digests are app wheel
  `cfee79bfe16adc1dc09ffd930db3a49763028b44bd0eb8c85d3403ea6e17b43e`,
  app sdist
  `fc6b43252d5842fdd470236c07a4bbd9a96d1c55450e81c77e922d0d4e20f68d`,
  engine wheel
  `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`,
  and engine sdist
  `a52e659e44d4dcfc882f76d998540a41d2abffa7886a83db365cb688c914084a`.
- Evidence checkpoint `ee2f8c22ac1bd00fd6a3d2924071b8ff23a32238`
  passed CI run `33611917553`, public-artifacts run `33611917534`, and CodeQL
  run `33611914545`. Its six changed files were docs-only, so child 12 resumed
  against unchanged source `9ca31ba` with `ee2f8c2` as the evidence scope.
- Child 12 returned `NOT_READY`, P0/P1/P2 `0/0/1`. The canonical manifest
  retained the removed optional-loader review at `integrations/ports.py:917`.
  A direct full-inventory reproduction reported the stale review, while the
  normal architecture test passed because `_planned_source_classification`
  removed reviews for moved source records before stale validation.
- Repair checkpoint `30d49d31d35f86e26be3c0ac99b884a47d76b5f6`
  removes the stale review and makes the normal architecture gate compare the
  canonical review inventory with all current `open_brain` source locations.
  A moved-source regression proves stale and unreviewed records remain visible;
  the legacy source projection no longer filters review evidence.
- Latest local verification passed: `make verify` (Ruff, strict MyPy on 488
  files, 3,158 tests, and all four artifact builds/policy); uncached Ruff;
  `make phase4-contracts` (85 tests, Ruff, MyPy, manifest); exact collection
  of 404 app tests; all 16 analyzer and app-wheel tests on Python 3.12, 3.13,
  and 3.14; source+artifact release audit; reachable-history audit; Gitleaks
  8.30.1 over 81 commits; `uv lock --check`; and `git diff --check`.
- Exact-head CI run `33614647926`, public-artifacts run `33614647755`, and
  CodeQL run `33614643945` passed at `30d49d3`, including interpreter-specific
  wheel execution on Python 3.12, 3.13, and 3.14. Rebuilt artifact SHA-256
  digests remained unchanged.
- Docs-only evidence checkpoint
  `e20be9debc6cd68cd443a3df00f6c2cd76041cb3` passed CI run `33615635189`,
  public-artifacts run `33615635198`, and CodeQL run `33615631031`.
- Child 12's same-lineage rereview was bound to source `30d49d3` and evidence
  `e20be9d`. It returned `READY`, P0/P1/P2 `0/0/0`, confirmed the prior P2 is
  closed, and declared P4-W2 ready for milestone closure.
- P4-W2 is complete. P4-W3 has not started, and its reviewer budget resets at
  the milestone boundary.
- Independent review is source-SHA-bound. A docs-only evidence successor does
  not invalidate unchanged source review, and the child budget resets at each
  milestone boundary.
- No package publication, tag, release, native build, deployment, production
  access, private-state access, cutover action, or P4-W3 work occurred.

## P4-W3 local source candidate

- Starting from verified P4-W2 closure
  `c3480be28fa36b9dae2256ff6aee610044b86847`, all five canonical
  connector-owned runtime files and three connector-owned tests moved to the
  buildable `open-brain-connectors` distribution. The canonical inventory now
  contains 232 runtime files and 355 Phase 4 subjects, including 260 tests; all
  nine connector runtime records are moved.
- The connector wheel depends on exact app and engine versions and imports app
  values only from the published provisional extension modules. The app wheel
  has no connector dependency, its default profile discovers none, and an
  installed connector remains unloaded in the parent before and after child
  execution.
- The worker request binds protocol version, invocation, entry-point metadata,
  manifest, budget, and network mode. The child runs with an empty environment,
  direct socket APIs disabled, bounded process/time/memory/output resources,
  metadata-only responses, and process-group termination. Parent validation
  binds receipts to identity, manifest, budget, capture count, and replay.
- Actual reference conformance runs the YouTube connector twice against
  synthetic host-mediated media and a durable temporary checkpoint. The first
  run creates one capture; replay creates none.
- Local verification passed: `make phase4-contracts` with 87 tests, Ruff,
  strict MyPy on 500 files, and manifest validation; `make verify` with 3,170
  tests and all six artifact builds/policy; connector wheel-only acceptance on
  Python 3.12, 3.13, and 3.14 with 3 tests per version; and `actionlint`.
- Source plus built-artifact release audit, reachable-history audit, Gitleaks
  8.30.1 over 83 commits, `uv lock --check`, and `git diff --check` passed.
- Rebuilt SHA-256 digests are app wheel
  `e2ecef1d7a283f6af485fbb9a5a8f666a69935c68c96466a5a644807b2d256a1`,
  app sdist
  `1e10a663dabfde9015a6ffedeb319465213fc19d052f8b6b9d455c0eabbcd9f9`,
  connector wheel
  `0a43a8b80423a5b03168f9ae2e9d13ff037f683503f9ba716280bf911c0ad31b`,
  connector sdist
  `5fc3c220849544ac35d24d7caefb678d3da313bd57d2a62a3bbc79f1bc3d0473`,
  engine wheel
  `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`,
  and engine sdist
  `199e0fc2adb264b0a0f9db50fd291e906b4d0a61cdb90e4eb55784716d000eca`.
- The branch-finish gotcha audit added canonical module-identity,
  artifact-coordinate, and parent-budget receipt entries. No other
  non-duplicate finding survived the evidence and registry checks.
- Exact-head CI and the independent source-SHA-bound review are still pending.
  No publication, tag, release, native build, deployment, production/private
  access, cutover action, or P4-W4 work occurred.
