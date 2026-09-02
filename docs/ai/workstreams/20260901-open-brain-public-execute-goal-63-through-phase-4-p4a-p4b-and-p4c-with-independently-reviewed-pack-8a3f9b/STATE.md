# Workstream State

- ID: `20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b`
- Repo root: <repo-root>
- Remote identity SHA-256 fingerprint: `cb5e9cd7ac71c16e5109717b4bc07f01aed1bbda2b18a99bfbc76f7bd98245bc`
- Worktree: <repo-root>
- Branch: goal/open-brain-phase4
- Objective: Execute Goal 63 through Phase 4 P4A, P4B, and P4C with independently reviewed package isolation, unpublished native artifacts, full-stop cutover, and day-0 evidence
- Created date: 2026-09-01

## Current milestone

- Milestone: P4-W3 connector distribution, provisional interface, and isolated
  worker
- Status: locally verified source candidate from clean checkpoint
  `c3480be28fa36b9dae2256ff6aee610044b86847`. Source checkpoint, exact-head CI,
  and independent review remain pending; the P4-W3 reviewer ledger is still
  zero
- Allowed scope: the five manifest-owned connector runtime files and authorized
  tests/resources; `open-brain-connectors` build metadata and artifacts;
  already-demonstrated provisional extension values and conformance rules;
  isolated host/worker protocol and closed explicit discovery; applicable app,
  acceptance, artifact-policy, CI, manifest, release, and bounded evidence work
- Stop condition: any unmanifested move, behavior repair without a red
  regression and separate verified commit, stable-SDK claim, implicit connector
  enablement, default app dependency on connectors, unbounded capability,
  P4-W4 work, acceptance review before applicable CI is green, or any
  publication, deployment, production, or private-state access
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

Create the bounded P4-W3 source checkpoint, push the explicit plan-authorized
branch update, and require exact-head CI to pass. Only then dispatch one fresh
source-SHA-bound read-only reviewer before milestone closure.

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
- Evidence successor `aab6f1e0891d551a87a2968ef9fb0dae1a8e62e2` passed every
  exact-head required check. A fresh read-only rereview returned `READY`,
  P0/P1/P2 `0/0/0`; P4-W1 is complete.
- No package publication, tag, release, deployment, production access, private
  state access, or cutover action occurred.

## P4-W2 complete

- All 34 app runtime files, 28 existing app test modules, two supervisor
  resources, and one explicit wheel-gate test module are at their manifest
  destinations under `packages/app`.
- `open-brain` depends on exactly `open-brain-engine==0.1.0`. Installed scripts
  bind `open-brain` and `open-brain-mcp` to app-owned appliance entry points;
  HTTP remains an app-owned callable rather than a third installed script.
- Installed supervisor rendering loads package resources and emits no checkout
  `PYTHONPATH` or working directory. Source-checkout rendering remains explicit.
- The app isolation harness builds app and engine with workspace sources
  disabled, installs only those two wheels into the product environment, and
  runs 400 app tests through a separate locked test environment. Connector,
  legacy, workspace source, and private engine imports remain unavailable.
- Named wheel-only tests prove `V0-GATE-07` through independent CLI/UI sibling
  approve, reject, and safe edit, and `V0-GATE-13` through create, rename,
  later route with stable capture identity, and scoped/all-space retrieval.
- One policy verifies four Python artifact coordinates: app/engine crossed
  with wheel/sdist. Exact members derive from the canonical manifest; all four
  real archives pass.
- The phased root suite uses a test-only namespace overlay for unmoved
  `cli`, `integrations`, and `services` modules. Installed-wheel acceptance
  proves the overlay is absent from the app product; P4-W4 removes it.
- First-repair local gates passed: `make verify` with strict MyPy on 488 files, 3,148
  tests, and four artifact builds; uncached Ruff; `make phase4-contracts`
  with 79 tests;
  isolated app-wheel journeys on Python 3.12, 3.13, and 3.14; source/artifact
  and reachable-history audits; Gitleaks over 66 commits; lockfile and diff
  integrity.
- Child 6 reviewed exact candidate
  `85428b125ddd370cfa6a6c2be20f2aab4669bf7e` and returned `NOT_READY`,
  P0/P1/P2 `0/3/1`. It found unreachable installed supervisor mode, a
  hard-coded Python 3.12 isolation interpreter, incomplete app import
  enforcement, and stale completion evidence.
- Three focused regressions failed before repair. Source checkpoint
  `7d87c3968e15de5d98f7e509c8c8a31c4c5b500c` validates source-checkout
  detection, runs wheel isolation on the active matrix interpreter, rejects
  private/undeclared/unreviewed imports, and reports bounded failure stages.
- Exact-head CI run `33591952670`, public-artifacts run `33591952648`,
  and CodeQL run `33591951436` passed at `7d87c39`. PR head, remote branch,
  and local head matched; the draft PR was mergeable.
- Evidence checkpoint `579b45bc12247d34ed612798fc2a6021ccc1d30a`
  recorded the first review and repair. Child 7 reviewed that exact candidate
  and returned `NOT_READY`, P0/P1/P2 `0/1/0`. The sole P1 found that dynamic
  import checks could be bypassed through `builtins`, assignment aliases, and
  reflective access, while a shadowed local `importlib` object was falsely
  flagged.
- Focused regressions reproduced those bypasses and the false positive. A
  self-review added the related unresolved-capability escape inside the one
  reviewed dynamic-import file before the final repair.
- Source repair `e27ac3c3ad7daa4748b094490fdadab6e66a3773`
  tracks lexical import provenance, binds the one reviewed variable import to
  its exact artifact path and function, rejects all other capability uses,
  and leaves unrelated local objects clean.
- Final local gates passed: `make verify` with strict MyPy on 488 files, 3,149
  tests, and four artifact builds; uncached Ruff; `make phase4-contracts`
  with 80 tests; isolated app-wheel journeys on Python 3.12, 3.13, and 3.14;
  source/artifact and reachable-history audits; Gitleaks over 69 commits;
  lockfile and diff integrity.
- Exact-head CI run `33594652359`, public-artifacts run `33594652371`, and
  CodeQL run `33594650509` passed at `e27ac3c`. PR head, remote branch, and
  local head matched; the draft PR was mergeable.
- Evidence checkpoint `0a67a26210b79d0c91fa8953846560db34903034`
  recorded the second review and repair. Child 8 reviewed that exact candidate
  and returned `NOT_READY`, P0/P1/P2 `0/1/1`. The P1 found an importer escape
  through `sys.modules` and related runtime namespace access. The P2 corrected
  the installed app-suite evidence from 402 tests to its exact 400-test scope.
- One focused artifact regression failed before repair across `sys.modules`,
  `globals`, `locals`, `vars`, `eval`, `exec`, and an assigned alias. It also
  proved a shadowed local `globals` callable remains unrelated.
- Source repair `d8e2cb20f0268e16ebdd5b46053d5081dab7ac7c`
  rejects those reflective importer paths, preserves ordinary `sys` and
  `getattr` use, records the private engine target reached through
  `sys.modules`, and corrects the app-suite count to 400.
- Latest local gates passed: `make verify` with strict MyPy on 488 files,
  3,150 tests, and four artifact builds; uncached Ruff;
  `make phase4-contracts` with 81 tests; exact collection of 400 app tests;
  isolated app-wheel journeys on Python 3.12, 3.13, and 3.14; source/artifact
  and reachable-history audits; Gitleaks over 71 commits; lockfile and diff
  integrity.
- Exact-head CI run `33596668616`, public-artifacts run `33596668630`, and
  CodeQL run `33596666546` passed at `d8e2cb2`. PR head, remote branch, and
  local head matched; the draft PR was mergeable.
- Evidence checkpoint `e483973e7f8153b97aa5a44b049d787d08fd884f`
  recorded the third review and repair. Child 9 reviewed that exact candidate
  and returned `NOT_READY`, P0/P1/P2 `0/1/0`. The sole P1 found bounded
  reflection paths through `sys.__dict__`, `sys.__getattribute__`, and
  function `__globals__`, plus path-insensitive rebinding and false positives
  for loop, `with`, and exception targets.
- A focused artifact regression failed before repair on every positive and
  negative case. Self-review added bound function and `object.__getattribute__`
  paths before broad verification.
- Source repair `bd994a0288f8711f216e130c25c45f7a654eb90f`
  tracks provenance sets, joins branch outcomes, models lexical and compound
  bindings, recognizes namespace and function reflection, and keeps shadowed
  targets clean.
- Current local gates passed: `make verify` with strict MyPy on 488 files,
  3,151 tests, and four artifact builds; uncached Ruff;
  `make phase4-contracts` with 82 tests; the complete analyzer test file with
  11 tests on each of Python 3.12, 3.13, and 3.14; isolated app-wheel journeys
  on all three versions; source/artifact and reachable-history audits;
  Gitleaks over 73 commits; lockfile and diff integrity.
- Exact-head CI run `33600292963`, public-artifacts run `33600292877`, and
  CodeQL run `33600287985` passed at `bd994a0`. PR head, remote branch, and
  local head matched; the draft PR was mergeable.
- Evidence checkpoint `0cff2ea6077b2450febd07f456310aff1f6ffd25`
  recorded the fourth review and repair. Child 10 reviewed that exact
  candidate and returned `NOT_READY`, P0/P1/P2 `0/2/0`. The P1 findings were
  missing `ImportFrom` provenance for modeled module members and incorrect
  PEP 572 scope for assignment expressions inside comprehensions.
- Focused wheel regressions failed before repair for aliases of
  `sys.__dict__`, `sys.__getattribute__`, and `builtins.object`, plus an
  enclosing-scope comprehension assignment and its shadow-negative case.
  Self-review added symmetric `importlib` and `builtins` aliases and normal
  walrus overwrite behavior.
- Source repair `e103255b2ab03c3312206383b71ce38fcde67b8e`
  derives `ImportFrom` provenance uniformly from modeled module members and
  binds comprehension assignment expressions to the nearest enclosing scope
  without changing ordinary assignment-expression semantics.
- Latest local gates passed: `make verify` with strict MyPy on 488 files,
  3,151 tests, and four artifact builds; uncached Ruff;
  `make phase4-contracts` with 82 tests; all 14 analyzer and app-wheel tests on
  each of Python 3.12, 3.13, and 3.14; source/artifact and reachable-history
  audits; Gitleaks over 75 commits; lockfile and diff integrity.
- Exact-head CI run `33602946392`, public-artifacts run `33602946514`, and
  CodeQL run `33602944303` passed at `e103255`. PR head, remote branch, and
  local head matched; the draft PR was mergeable.
- Evidence checkpoint `995bd781869901e772eee0c7fdfd0ab8132065d5`
  recorded the fifth review and repair. Child 11 reviewed that exact candidate
  and returned `NOT_READY`, P0/P1/P2 `0/2/0`. The P1 findings were equivalent
  loader and reflection spellings with lost authority, and an allow-listed
  dynamic-import argument whose name survived unsafe reassignment.
- Two focused artifact regressions failed before repair with zero findings.
  They cover `importlib.__init__`, `pkgutil.resolve_name`, aliased
  `importlib.util`, frame namespaces, function-type reflection, direct and
  branch parameter replacement, and a second-parameter substitution.
- Source repair `559690e14b9a1dd935566b54e97ec8f2b73f8d06`
  models those authorities by semantics, distinguishes pristine parameters
  from unknown values through control-flow joins, preserves safe
  `importlib.metadata` and `importlib.resources` use, and rejects internal
  package roots at the optional-provider runtime boundary.
- Latest local gates passed: `make verify` with strict MyPy on 488 files,
  3,157 tests, and four artifact builds; uncached Ruff;
  `make phase4-contracts` with 84 tests; exact collection of 404 app tests;
  all 16 analyzer and app-wheel tests on each of Python 3.12, 3.13, and 3.14;
  source/artifact and reachable-history audits; Gitleaks over 77 commits;
  lockfile and diff integrity.
- Exact-head CI run `33608085686`, public-artifacts run `33608085774`, and
  CodeQL run `33608082590` passed at `559690e`. PR head, remote branch, and
  local head matched; the draft PR was mergeable.
- Evidence checkpoint `ce909a525dbc66ec5d893892984f2814f7bb9e71`
  passed CI run `33609157287`, public-artifacts run `33609157406`, and CodeQL
  run `33609152877`. Child 12 began reviewing that candidate, then stopped
  without a verdict when the source architecture was superseded.
- Source repair `9ca31ba36c44e4e4a269e5c932fae27fa174831e`
  replaces arbitrary module strings with a closed `OptionalProvider` enum and
  immutable lazy-loader registry containing the one declared `openai` extra.
  Internal roots are unrepresentable through the typed API and rejected again
  at runtime. P4H009 now has no dynamic-import exception and is explicitly a
  finite architecture regression corpus rather than a Python sandbox.
- Latest local gates passed: `make verify` with strict MyPy on 488 files,
  3,157 tests, and four artifact builds; uncached Ruff;
  `make phase4-contracts` with 84 tests; exact collection of 404 app tests;
  all 16 analyzer and app-wheel tests on each of Python 3.12, 3.13, and 3.14;
  source/artifact and reachable-history audits; Gitleaks over 79 commits;
  lockfile and diff integrity.
- Exact-head CI run `33611279850`, public-artifacts run `33611279794`, and
  CodeQL run `33611274401` passed at `9ca31ba`. PR head, remote branch, and
  local head matched; the draft PR was mergeable.
- Evidence checkpoint `ee2f8c22ac1bd00fd6a3d2924071b8ff23a32238`
  passed CI run `33611917553`, public-artifacts run `33611917534`, and CodeQL
  run `33611914545`. Child 12 resumed against source `9ca31ba` and this
  docs-only evidence successor, then returned `NOT_READY`, P0/P1/P2 `0/0/1`.
  The P2 was a stale dynamic-import review in the canonical manifest that the
  normal architecture gate hid by filtering moved source records first.
- Source repair `30d49d31d35f86e26be3c0ac99b884a47d76b5f6`
  removes the stale generic-loader review, validates the canonical review
  inventory against every current `open_brain` source location, and adds a
  moved-source regression. The legacy source projection no longer rewrites
  review evidence.
- Latest local gates passed: `make verify` with strict MyPy on 488 files,
  3,158 tests, and four artifact builds; uncached Ruff;
  `make phase4-contracts` with 85 tests; exact collection of 404 app tests;
  all 16 analyzer and app-wheel tests on each of Python 3.12, 3.13, and 3.14;
  source/artifact and reachable-history audits; Gitleaks 8.30.1 over 81
  commits; lockfile and diff integrity.
- Exact-head CI run `33614647926`, public-artifacts run `33614647755`, and
  CodeQL run `33614643945` passed at `30d49d3`. PR head, remote branch, and
  local head matched; the draft PR remained open.
- Docs-only evidence checkpoint
  `e20be9debc6cd68cd443a3df00f6c2cd76041cb3` passed CI run `33615635189`,
  public-artifacts run `33615635198`, and CodeQL run `33615631031`.
- Child 12's same-lineage rereview was bound to source `30d49d3` and evidence
  `e20be9d`. It returned `READY`, P0/P1/P2 `0/0/0`, explicitly closed the
  prior P2, and declared P4-W2 ready for milestone closure.
- P4-W2 is complete. No P4-W3 implementation or review child was started; its
  reviewer budget resets at the next milestone boundary.
- Independent review is bound to the source SHA. A docs-only evidence
  successor does not invalidate an unchanged source review. Child budgets are
  scoped to and reset at each milestone.
- Rebuilt SHA-256 digests are app wheel
  `cfee79bfe16adc1dc09ffd930db3a49763028b44bd0eb8c85d3403ea6e17b43e`,
  app sdist
  `fc6b43252d5842fdd470236c07a4bbd9a96d1c55450e81c77e922d0d4e20f68d`,
  engine wheel
  `83e534799359e8ccb7ac8e90dfd5114564c0638428c5f50ca897a26f495cc682`,
  and engine sdist
  `a52e659e44d4dcfc882f76d998540a41d2abffa7886a83db365cb688c914084a`.
- No publication, tag, release, native build, deployment, private-state access,
  production access, or cutover action occurred.

## P4-W3 local source candidate

- All five connector-owned runtime files and their three owned tests are in the
  buildable `open-brain-connectors` package. Nine connector runtime records are
  moved; the workspace inventory is 232 runtime files and 355 Phase 4 subjects,
  including 260 tests.
- Published app extension values remain provisional v1. The connector package
  depends on exact app and engine versions; the app has no connector dependency
  and defaults to an empty connector profile.
- The bounded worker loads the explicitly enabled entry point only in its child,
  applies capability, budget, process, memory, time, output, network, receipt,
  and replay checks, and runs real YouTube reference conformance without
  production/private state.
- Latest local gates passed: `make phase4-contracts` with 87 tests; `make
  verify` with Ruff, strict MyPy on 500 files, 3,170 tests, and six artifact
  builds/policy; connector wheel acceptance with 3 tests on each of Python
  3.12, 3.13, and 3.14; source/artifact and reachable-history audits; Gitleaks
  8.30.1 over 83 commits; actionlint; lockfile and diff integrity.
- Three new durable gotchas record canonical child bootstrap identity, singular
  artifact coordinates, and parent-bound receipt budgets. No package
  publication, tag, release, native build, deployment, private-state access,
  production access, cutover, or P4-W4 work occurred.
- Exact-head CI and a fresh independent READY P0/P1/P2 `0/0/0` verdict remain
  required. Reviewer budget remains 0 active and 0 total until CI is green.
