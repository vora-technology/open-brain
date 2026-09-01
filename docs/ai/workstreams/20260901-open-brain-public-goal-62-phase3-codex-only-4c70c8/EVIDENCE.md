# Phase 3 execution evidence

## Gate 0: implementation baseline

- `git fetch --prune origin`: passed.
- `main`, `origin/main`, and launch HEAD:
  `d93c6dae2a22ef028390f30c990b27968229178e`; ahead/behind `0/0`.
- Reviewed plan SHA-256:
  `e842eac8a5a933d20405bc84bde0ecf87474c7d4317018f32ac6ef95ef0263b7`.
- Goal `cbolden15/agent-config#62`: open with `goal` label; parent `#41` open;
  completed Phase 2 child `#51` closed.
- Open product PRs: only unrelated Dependabot PR `#1`; untouched.
- Protected-branch checks: `verify (3.12)`, `verify (3.13)`, `verify (3.14)`,
  and `public-artifacts` required with strict branch freshness.
- Baseline `make verify`: passed Ruff, strict MyPy on 439 source files, 2,981
  tests, wheel/sdist builds, and artifact policy.
- Planning-only commit: `e8a4ec2`.
- Forbidden-scope evidence: no source/test implementation preceded the
  planning commit; no production, live Brain, private predecessor, package
  publication, deployment, service install, or unrelated PR action occurred.

## P3-W0: frozen appliance seams

- Worker: `P3-W0-IMPLEMENT-01`, Codex `gpt-5.4` high, exclusive W0 scope.
- Red evidence: focused collection failed because the new
  `DaemonMutationPathUnavailableError` contract did not yet exist.
- Green focused Pytest: 92 passed.
- Focused Ruff: passed.
- Strict MyPy: passed on 439 source files.
- Full `make verify`: passed Ruff, MyPy, 2,984 tests, wheel/sdist builds, and
  artifact policy.
- `git diff --check`: passed.
- Behavior: `open_brain.services.appliance_application` and
  `open_brain.services.appliance_entrypoints` are reserved without repointing
  current scripts; `.open-brain/run/control.sock` is daemon-owned and fails
  closed until lifecycle implementation.
- Failure gate: no `open_brain.operations` or release import in shipping W0
  surfaces, no Phase 4 package work, and no current service behavior change.
- Worker environment note: default uv cache access was sandbox-denied before
  tests started; the worker changed strategy to a disposable cache and then
  produced the required red/green evidence. Coordinator checks used the
  normal project environment and passed.

## P3-W1: init and maintenance read seams

- Worker: `P3-W1-IMPLEMENT-01`, Codex `gpt-5.4` high, exclusive W1 scope.
- Worker red evidence: new appliance modules, read-view error, and existing
  profile opener were absent; later Ruff and MyPy red checks found concrete
  implementation defects.
- Worker green evidence: 26 focused tests, focused Ruff, and strict MyPy on
  447 source files passed.
- Coordinator hardening red evidence: four new regressions demonstrated
  nested-root preflight rejection, unsafe credential replacement,
  newer-schema acceptance, and profile descriptor double-close.
- Coordinator repairs: nearest-existing-ancestor permission check, real
  supervisor executable detection, owner-file fail-closed handling, bounded
  schema errors, direct pre-writer newer-schema rejection, legacy schema
  migration, and single-close profile cleanup.
- First full `make verify`: failed only three architecture tests because the
  five new runtime files were unclassified and app code imported engine
  internals. No product test failed.
- Architecture repair: classified all new files, exported maintenance/read
  contracts through `open_brain.engine`, removed app-to-engine-internal
  imports, and removed the legacy capture-queue dependency.
- Final focused Pytest: 32 passed. Focused Ruff and strict MyPy passed.
- Final full `make verify`: passed Ruff, MyPy, 2,999 tests, wheel/sdist builds,
  and artifact policy. `git diff --check` passed.
- Commit hygiene: `9c147d2` contained two extra EOF blank lines because the
  staged check did not stop its compound shell. A non-rewriting follow-up
  removes both; all later compound gates use fail-fast shell settings.
- Queue evidence is explicitly `unavailable` in W1 instead of falsely empty;
  W2 must supply the new scheduler-owned evidence without legacy imports.
- No real credential, service, network, production, live Brain, private
  predecessor, package publication, deployment, or unrelated PR was used.

## P3-W2 authority subphase

- `P3-W2-IMPLEMENT-01` stopped early after adding only the distinct
  `DAEMON_AUTHORITY` lock scope/discriminator and one lock test. It explicitly
  reported every remaining W2 gate incomplete; no partial result was accepted
  as the wave checkpoint.
- Changed strategy: split W2 into serial authority, control, and runtime
  subphases with one writer at a time.
- `P3-W2-AUTHORITY-02` added an issuer-created, root-bound active capability
  held inside the daemon authority context. A second authority fails, and the
  capability becomes stale on context exit.
- Appliance mutating composition rejects missing, stale, and wrong-root
  capabilities. Its constructor cannot accept a caller-supplied mutating task
  set.
- Authorized engine tasks revalidate the capability on every shared-writer
  acquisition; a valid capture succeeds while lifetime authority is held,
  proving the lock scopes do not self-conflict.
- Focused authority/lock/architecture Pytest: 91 passed. Ruff, strict MyPy on
  449 source files, and `git diff --check` passed.
- No control socket, listener, scheduler, supervisor command, installed
  entrypoint, real service, production, or live data action occurred.

## P3-W2 control subphase

- Worker `P3-W2-CONTROL-03` added the app-owned daemon, lifecycle client,
  owner-only `.open-brain/run/control.sock`, and bounded canonical capture
  request/receipt envelopes.
- Coordinator review found that the worker's separate stale-cleanup witness
  was active but not root-bound. Cleanup now validates the engine-issued
  daemon capability against the exact profile root; a cross-root regression
  proves rejection.
- The accepted connection has a bounded I/O timeout, and the serve loop
  survives a stalled client. Control failures never fall back to direct
  mutation.
- Restart evidence covers both ordinary request replay and the harder case
  where capture committed but the receipt could not be delivered. Replaying
  the same delivery identity returns the same capture with one durable row.
- Stale cleanup requires active daemon authority, rejects symlinks and
  non-sockets, and detects an identity replacement before unlink. The run
  directory is `0700`; the control socket is `0600`.
- Focused control/authority/entrypoint/architecture/storage Pytest: 130
  passed. Ruff, strict MyPy on 452 source files, and `git diff --check`
  passed.
- Scheduler, supervisor adapters, installed entrypoint cutover, real host
  service commands, network listeners, production, private predecessor, and
  live Brain data remained untouched.

## P3-W2 runtime and repair subphases

- `P3-W2-RUNTIME-04` implemented the first scheduler, supervisor, entrypoint,
  and control-dispatch candidate. Its reported focused gate passed 148 tests,
  Ruff, and strict MyPy on 456 files.
- Coordinator review rejected that candidate as a checkpoint: scheduler state
  used raw path writes without confinement or crash durability; shutdown could
  release authority during an operation; legacy phase1 and auxiliary package
  entrypoints still bypassed the daemon; and supervisor/CLI failures were not
  fully bounded.
- The first coordinator `make verify` confirmed two additional integration
  failures: stale package characterization and a cross-process test that still
  assumed direct installed-CLI writes. The suite result was 3,032 passed and
  two failed.
- `P3-W2-REPAIR-05` added 16 concrete red regressions, then passed 119 repair
  tests and 158 plan-focused tests. It introduced bounded confined reads,
  atomic scheduler state, immutable run receipts, receipt-before-state crash
  replay, compatibility delegation, package-script cleanup, supervisor input
  escaping, and disposable daemon restart evidence.
- Coordinator hardening then bound the scheduler to `LocalEngineContext`,
  capped connector/state size, moved its storage dependency behind a narrow
  public operational-storage facade, removed temporary architecture debt,
  closed operation admission before shutdown waits, bounded adapter/query and
  supervisor failures, sanitized subprocess environments, and corrected stale
  architecture/CLI documentation.
- Restart evidence now covers a lost capture receipt and a lost review receipt:
  repeated delivery identities preserve stable IDs with one capture, decision,
  publication, and page. A concurrent stop keeps daemon authority until the
  active operation exits and rejects any later operation admission.
- Package metadata exposes only `open-brain` and read-only `open-brain-mcp`,
  both on appliance entrypoints. The old phase1 entrypoints delegate to those
  paths; standalone HTTP and legacy bridge scripts are not packaged.
- Final focused Pytest: 178 passed. Full Ruff, strict MyPy on 457 source files,
  and `git diff --check` passed.
- Final sanitized `make verify`: 3,050 tests passed; wheel and sdist built; the
  public artifact policy passed.
- No launchctl/systemctl command, real user unit, persistent daemon, TCP
  listener, production system, private predecessor, package publication,
  deployment, live Brain data, or unrelated PR was touched.

## P3-W3: owner UI, browser security, and bounded history

- Workers `P3-W3-IMPLEMENT-01` and `P3-W3-REPAIR-02` used Codex `gpt-5.4`
  high with one exclusive writer at a time.
- The first architecture run failed four tests because two new service files
  were unclassified, internal imports were unresolved, and app composition
  imported storage directly. The repair worker fixed those boundaries.
- Coordinator review then added six red regressions for proposal-decision
  routing, private HTTPS origin reporting, inconsistent listener
  configuration, startup traceback leakage, and untrusted history job names.
  The repaired regression block passed seven tests.
- Final behavior evidence covers the daemon-owned listener, purpose-bound
  host-only sessions, exact browser origins, CSRF, strict `/api` versus
  `/share` route capabilities, page reads, shared CLI/UI status and doctor,
  and bounded metadata-only history.
- Final focused and architecture Pytest passed 99 tests. A separate post-fix
  daemon, scheduler, history, UI, auth, log, and storage block passed 45 tests.
- Full Ruff, strict MyPy on 464 source files, and `git diff --check` passed.
  Sanitized `make verify` passed 3,070 tests, wheel/sdist builds, and artifact
  policy.
- Clean checkpoint commit `3691d04dc97f926b5a9aa0d1609d817e860b6d12`
  is pushed to `origin/goal/open-brain-phase3`.
- No persistent listener, real credential, production, private predecessor,
  package publication, deployment, live Brain data, or unrelated PR was
  touched.

## P3-W4: recovery, reconciliation, backup, and Portable orchestration

- Worker `P3-W4-IMPLEMENT-01` used Codex `gpt-5.4` high and reported 83
  focused plus 58 architecture tests passing. It also reported four missing
  proofs: replacement preflight, effect-before-receipt backup replay, SQLite
  integrity validation, and explicit TOCTOU/overlap coverage.
- Coordinator review added eight red regressions for invalid SQLite with a
  matching digest, forbidden app-state inventory, backup/root containment,
  unbounded scheduler receipts, explicit replacement preflight,
  effect-before-receipt replay, deleted pages, and owner identity continuity.
  All eight passed after repair.
- A later checkpoint review added two more red regressions. One proved an
  allow-listed app-state path could carry arbitrary credential-shaped JSON;
  the other proved a long-lived recovery handler could record completion
  before request time. Exact metadata schemas and monotonic completion time
  now close both cases.
- Backup creation uses descriptor-confined bounded scans, exact typed
  manifests, SQLite backup-API snapshots plus `quick_check`, schema-validated
  immutable app receipts, same-filesystem staging, and no-replace promotion.
  Mutable scheduler state, credentials, indexes, sockets, locks, supervisor
  files, staging data, and SQLite sidecars are excluded.
- Reconciliation scans canonical owner Markdown through bounded no-follow
  descriptors, preserves tenant/actor/role/space/page/provenance identity,
  detects deletion and replacement, and updates only derived retrieval state.
- App recovery verifies before restore, writes only to a proven empty
  disposable root, acquires target authority, generates a fresh credential,
  initializes fresh scheduler state, rebuilds the index, and runs doctor.
  Replacement remains preflight-only; no live replacement API exists.
- The daemon control socket accepts bounded owner requests for distinct
  `backup-create`, `portable-export`, and `portable-import` jobs and routes
  them to the scheduler attached to its existing application. Recovery
  request and scheduler receipts remain path-free and replay safe.
- Final focused Pytest passed 96 tests. Full Ruff, strict MyPy on 472 source
  files, and `git diff --check` passed. Final sanitized `make verify` passed
  3,091 tests, wheel/sdist builds, and artifact policy.
- No real credential, persistent service, production system, private
  predecessor, package publication, deployment, live Brain data, or unrelated
  PR was touched.

## P3-W5: upgrade, uninstall, host-family CI, and Phase 4 lock

- Worker `P3-W5-IMPLEMENT-01` used Codex `gpt-5.4` high and passed 40 focused
  plus 58 architecture tests. It reported two clean-exit gaps: replay existed
  only in memory, and no owner CLI/daemon path could reach lifecycle
  orchestration.
- Coordinator review added four initial red regressions proving that process
  restart reran upgrade/uninstall effects, mismatched recovery evidence was
  accepted, incomplete migrations could succeed, and CLI injection was
  absent. All four passed after repair.
- Additional regressions prove activation effect-before-receipt recovery and
  concurrent-process exclusion. A canonical root-confined journal records
  request identity, stage, and terminal receipt; a distinct kernel-backed
  lifecycle lease prevents an active request from being mistaken for a crash.
  Interrupted forward work rolls back once, persists a bounded failure, and
  does not repeat on later replay.
- Upgrade now requires candidate/compatibility continuity, exact backup and
  disposable-preflight identity/digest continuity, engine then app migration
  receipts over the same version edge, candidate activation, active
  supervisor status, and healthy doctor evidence. Every failed forward stage
  records rollback disposition and cannot declare success.
- Uninstall requires a separate confirmed owner request and orders daemon
  stop, one supervisor-unit removal, then artifact-port removal. Root identity
  and canonical/Portable bytes are preserved by default; no purge argument or
  method exists.
- The source-checkout CLI exposes typed upgrade/uninstall commands only
  through an injected lifecycle port. Its default remains unavailable, so
  Phase 3 has no native artifact effect. Linux full verification remains in
  CI; a pinned macOS job runs lifecycle and launchd/systemd adapter evidence.
- Final focused Pytest passed 47 tests. Architecture/lock Pytest passed 88
  tests. Full Ruff, strict MyPy on 474 source files, and `git diff --check`
  passed. Sanitized `make verify` passed 3,111 tests, wheel/sdist builds, and
  artifact policy.
- No launchctl/systemctl command, real supervisor unit, native artifact,
  package publication, deployment, production system, private predecessor,
  real credential, or live Brain data was touched.
