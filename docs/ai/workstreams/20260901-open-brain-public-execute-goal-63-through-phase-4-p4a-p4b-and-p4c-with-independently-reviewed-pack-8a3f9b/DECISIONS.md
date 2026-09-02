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

## D-012: bind installed app scripts only after P4-W2 acceptance

- Chosen: keep all app entry-point subjects `planned`, remove console scripts
  from the nonbuildable P4-W1 app skeleton, and retain source-checkout coverage
  through the app-owned callables and module entry point.
- Rejected: leave dormant `[project.scripts]` declarations in the app skeleton
  and mark them moved before an isolated app wheel exists.
- Why: P4-W2 owns installed entry points. Moving their manifest state during
  P4-W1 would contradict D-009 and claim artifact behavior that has not passed
  acceptance.

## D-013: derive exact artifact membership from the canonical manifest

- Chosen: make `docs/v0-package-classification.json` select every required
  engine wheel and sdist member, with only bounded archive-layout rewrites for
  PEP 639 license destinations. Reject every non-generated member that the
  manifest does not declare.
- Rejected: maintain a second exhaustive allowlist in the artifact policy or
  rely only on required and forbidden patterns.
- Why: the first P4-W1 rereview proved that pattern checks could miss absent
  license files and an undeclared `.gitignore`. One canonical selection plus
  exact archive comparison prevents that drift.

## D-014: keep engine product and test-runner environments separate

- Chosen: install only the engine wheel in one disposable Python 3.12
  environment, install locked pytest/jsonschema tooling in another, copy the
  moved engine tests and bounded shared fixtures into a temporary test root,
  and expose only the installed engine site-packages to the runner.
- Rejected: execute the moved tests through the editable root environment or
  install test tooling into the engine product environment.
- Why: P4-W1 must prove the full engine test subset with repository source,
  app, connectors, legacy, and workspace package sources unavailable.

## D-015: keep one canonical move manifest

- Chosen: correct every review packet and coordination reference to
  `docs/v0-package-classification.json`.
- Rejected: create the nonexistent `release/phase4-move-manifest.json` named in
  one temporary review packet.
- Why: the approved plan and validator already designate the documentation
  manifest as the sole ownership and movement authority.

## D-016: copy isolated product installs out of uv's cache

- Chosen: pass `--link-mode copy` when installing built product wheels into
  disposable isolation environments.
- Rejected: uv's default Linux hardlink mode, because installed Portable
  fixtures then share inodes with uv's cache and violate the product's
  unique-regular-file safety invariant.
- Why: exact-head Linux CI exposed the filesystem-dependent behavior. A clean
  Linux container passes the complete focused contract with copied installs,
  without weakening validation or adding repository sources to the product
  environment.

## D-017: test the app wheel through separate product and test environments

- Chosen: install only app and engine wheels in the product environment. Keep
  pytest and locked development requirements in a separate runner environment,
  copy app test inputs, and expose only product site-packages to those tests.
- Rejected: run app tests through the editable workspace or install test tools
  into the product environment.
- Why: P4-W2 must prove app behavior and entry points without connector,
  legacy, workspace source, or undeclared dependencies. The split environment
  keeps test tooling from becoming product evidence.

## D-018: key Python artifact policy by distribution and kind

- Chosen: use one versioned policy with four coordinates: app wheel, app sdist,
  engine wheel, and engine sdist. Derive exact members for each coordinate from
  the canonical manifest.
- Rejected: run two unrelated policy files or keep global wheel/sdist
  uniqueness, which would reject the expected second wheel and sdist.
- Why: one release identity owns both distributions. Coordinate-level
  uniqueness detects real duplicates while preserving one auditable command
  and one membership authority.

## D-019: keep phased namespace coexistence in the root test harness only

- Chosen: while unmoved modules remain under `src/open_brain`, extend the
  `cli`, `integrations`, and `services` search paths only from root
  `tests/conftest.py`. The isolated app test copy has no source tree, so the
  extension is a no-op there.
- Rejected: add `pkgutil.extend_path` or checkout paths to shipping app code,
  and rejected moving P4-W3/P4-W4 files early merely to satisfy collection.
- Why: regular moved subpackages hide unmoved peer modules during the phased
  root suite. A test-only bridge keeps every wave green without giving the app
  artifact an undeclared workspace dependency. P4-W4 removes the bridge.

## D-020: derive app-to-engine import authority from the canonical manifest

- Chosen: parse app wheel sources and allow only engine modules whose manifest
  records are public.
- Rejected: maintain another hard-coded module allowlist or widen the engine
  facade solely to satisfy existing app imports.
- Why: API status already belongs to the canonical manifest. Reusing it makes
  private imports fail at the artifact boundary and prevents policy drift.

## D-021: validate source layout before rendering checkout supervisor paths

- Chosen: derive a checkout root only when the running module resolves to the
  exact declared `src/open_brain/services/appliance_lifecycle.py` layout.
- Rejected: infer source mode from a fixed number of `__file__` parents.
- Why: an installed wheel has the same module depth under `site-packages`.
  Parent counting fabricated a nonexistent `src` directory and made the
  packaged installed mode unreachable.

## D-022: bind artifact isolation to the active matrix interpreter

- Chosen: create product and test environments with the major/minor version of
  the interpreter running each acceptance job. Keep an explicit version
  parameter for deterministic focused tests.
- Rejected: hard-code Python 3.12 inside the harness while labeling outer CI
  jobs as Python 3.13 and 3.14.
- Why: each matrix leg must execute the installed artifacts on its own
  interpreter, not merely run workspace tests before delegating isolation back
  to Python 3.12.

## D-023: enforce the app import boundary from artifact metadata and the manifest

- Chosen: derive declared external roots from app wheel metadata, derive all
  public and private engine modules from the canonical manifest, resolve
  imported submodule aliases, reject forbidden/undeclared roots, and permit one
  exact reviewed dynamic-import signature.
- Rejected: inspect only `ImportFrom.module`, trust lazy imports to runtime
  coverage, or maintain another engine API list.
- Why: a public parent can expose a private child syntactically, and a lazy
  workspace dependency may never execute during a passing journey. The wheel
  itself must prove both boundaries.

## D-024: keep isolation failure evidence bounded but stage-specific

- Chosen: report the allow-listed harness stage when an installed-app
  subprocess fails, without including commands, paths, stdout, or stderr.
- Rejected: collapse every failure into generic `P4H007` or expose raw
  subprocess output.
- Why: the first exact-head Python 3.12 run failed transiently inside the
  installed-app harness. A bounded stage distinguishes setup, install, tests,
  CLI, and product-contract failures without leaking local details.

## D-025: treat dynamic importer capabilities as reviewed artifact events

- Chosen: track `importlib`, `builtins`, their importer functions, assignment
  aliases, and reflective lookups by lexical provenance. Record both capability
  bindings and calls, then allow only the exact path and function signature of
  the existing optional-provider seam.
- Rejected: match callable spellings globally, allow unresolved aliases, or
  classify every local object named `importlib` as the standard-library module.
- Why: name-only scanning both missed real import paths and rejected unrelated
  code. Capability events fail closed when an importer escapes while preserving
  one narrow, reviewable exception.

## D-026: fail closed on runtime namespace importer acquisition

- Chosen: recognize `sys.modules` and built-in namespace mappings as importer
  provenance, and reject `globals`, `locals`, `vars`, `eval`, and `exec` as
  unreviewed artifact capabilities.
- Rejected: enumerate only direct imports or attempt to interpret dynamic code
  strings inside the acceptance harness.
- Why: Python exposes the same importer through runtime registries and dynamic
  evaluation. The app has no authorized use for those capabilities, so a
  bounded fail-closed policy is simpler and safer than partial interpretation.

## D-027: join provenance across control flow and lexical binding scopes

- Chosen: represent each binding as a set of possible capabilities, merge
  branch and loop outcomes, predeclare function-local names, and model compound
  targets plus nested scope visibility.
- Rejected: let AST traversal order overwrite provenance or treat every shared
  identifier as the module it once referenced.
- Why: a dead or alternate branch must not erase a possible importer path, but
  a loop, context-manager, or exception target must shadow that path inside its
  own body. Conservative joins enforce both halves of the boundary.

## D-028: derive imported members and comprehension bindings from Python semantics

- Chosen: resolve `ImportFrom` aliases through the same module-member model as
  attribute access, and bind comprehension assignment expressions in the
  nearest enclosing non-comprehension scope.
- Rejected: maintain separate per-syntax alias lists or discard all names when
  a comprehension scope exits.
- Why: equivalent member access must carry equivalent provenance regardless of
  syntax. PEP 572 deliberately gives walrus targets different scope from
  comprehension iteration targets, so the analyzer must preserve that split.
