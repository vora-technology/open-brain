# Phase 4 execution decisions

## D-001: carry the reviewed planning commit onto a fresh implementation branch

- Chosen: create `goal/open-brain-phase4` directly from freshly fetched
  `origin/main`, then cherry-pick the exact reviewed planning commit.
- Rejected: implement on `phase4-planning`, because the goal requires a new
  implementation branch from the fresh public base.
- Rejected: merge a separate planning PR first, because one Phase 4 draft PR
  can carry the reviewed plan and implementation without changing the base
  requirement or adding an unnecessary review cycle.
- Why: this preserves the exact reviewed plan, starts implementation from the
  required base, and keeps one coordinator-owned writer surface.

## D-002: treat Goal #24's earlier apply as immutable history

- Chosen: retain and reference the prior Goal #24 receipts, but build a new,
  separately bound Phase 4 rehearsal and full-stop transaction.
- Rejected: rerun or repurpose the old production apply.
- Why: the latest private handoff explicitly says the earlier apply and stage
  cleanup are complete and must never be rerun. Goal #63 authorizes a later
  transaction only after new P4A, P4B, recovery, and P4-W8 gates pass.

## D-003: use project-local durable context when context-mode is unavailable

- Chosen: search the project gotcha registry, Phase 3 decisions/evidence, and
  the work-brain filesystem for relevant Phase 4 context.
- Rejected: infer prior decisions without a durable-context search.
- Why: no `ctx_search` capability is installed in this runtime, and no Phase
  4-specific work-brain page was found. Project-local verified records remain
  available and authoritative for implementation behavior.

## D-004: classify all 250 tracked Python files under tests

- Chosen: treat all 250 currently tracked Python files under `tests/` as
  manifest subjects, including root `tests/__init__.py` and
  `tests/conftest.py`.
- Rejected: preserve the planning snapshot's count of 248 by omitting the two
  root files.
- Why: the goal says every test must have one owner and disposition, and every
  creation-time count must be reverified. The broader current inventory is the
  stronger and mechanically complete boundary.

## D-005: continue P4A preparation while preserving the notarization blocker

- Chosen: record unavailable notarization credentials as a mandatory P4B
  prerequisite while continuing reversible source-only P4-W0/P4A work.
- Rejected: weaken the signed/notarized macOS requirement or claim readiness
  from the presence of `notarytool` and a local Developer ID identity alone.
- Why: neither checked authorized host has a ready standard notary credential
  profile. No current source milestone consumes that credential, and the goal
  remains able to make meaningful progress before P4B signing.

## D-006: record the exact workspace in P4-W0 and activate it in P4-W1

- Chosen: bind the four members, shared lockfile, backend, and no-sources build
  command in the P4-W0 toolchain record and validator; keep the current root
  project active until P4-W1 creates the four member skeletons atomically.
- Rejected: create empty member projects in P4-W0, which would pull P4-W1 work
  across the reviewed checkpoint.
- Rejected: add workspace members that do not exist, which would make the root
  toolchain unusable and the green P4-W0 gate dishonest.
- Why: P4-W0 records and tests the exact decision; P4-W1 owns physical
  activation. The expected-red report explicitly records inactive membership.

## D-007: one runtime map plus one non-runtime subject map

- Chosen: enrich each existing runtime `files` record in place and add one
  `phase4.subjects` map for every non-runtime subject.
- Rejected: a second runtime ownership list, which could drift from the
  architecture validator.
- Rejected: separate hand-maintained maps for tests, fixtures, schemas,
  resources, entry points, and release tools, which would fragment destination
  uniqueness and make whole-repository closure harder to prove.
- Why: all 555 current subjects share one validator and one destination index,
  while existing runtime import policy keeps its canonical owner fields.

## D-008: pin current verified bundlers without installing them in P4-W0

- Chosen: bind current primary-index versions in the Phase 4 toolchain record
  and install them only when P4-W5 creates real native build subjects.
- Rejected: add native bundlers to the root development environment now,
  before any native adapter/spec exists.
- Why: P4-W0 must make the decision reproducible, while P4-W5 owns build/smoke
  execution. This avoids a placeholder toolchain and unnecessary root weight.

## D-009: keep stable source identities and track movement separately

- Chosen: retain each manifest key as the stable source identity, add an
  explicit `movement_state`, and change `current_path` to the target only after
  that distribution's isolated artifact contract passes.
- Rejected: re-key every record to its destination during each wave, which
  would erase the stable source-to-target identity and create large unrelated
  rewrites in later waves.
- Why: the plan requires the engine contract to pass before manifest state is
  changed to moved. A stable identity plus current and target paths represents
  that order directly and lets the validator reject copied, stale, or
  prematurely claimed files.

## D-010: keep the Phase 7 capture parity scenario with legacy parity

- Chosen: correct `test_capture_scenarios.py` from engine to legacy ownership
  and leave it at its source path until P4-W4.
- Rejected: make the engine test tree import app parity and consume a
  legacy-owned scenario resource.
- Why: collection after the mechanical move proved the test exercises the
  Phase 7 parity harness and its paired legacy fixture, not an isolated engine
  contract. Keeping both in the same later wave preserves the dependency graph
  and prevents a false engine-isolation claim.

## D-011: retain shared test factories in the workspace

- Chosen: keep `tests/unit/storage/_factories.py` as a workspace-owned shared
  test helper and keep `tests/integration/migrate/_synthetic.py` with the
  legacy migration wave.
- Rejected: place either helper in the engine test tree while app, operations,
  parity, or migration tests still import it from the shared test namespace.
- Why: full-suite collection proved the storage factory has cross-distribution
  consumers and the synthetic note helper serves migration tests. Their
  original engine assignments would make unrelated test suites depend on the
  engine test package and misstate ownership.
