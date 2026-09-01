# Workstream State

- ID: `20260901-open-brain-public-goal-62-phase3-codex-only-4c70c8`
- Repo root: /Users/calebbolden/Projects/oss/open-brain-public
- Remote identity SHA-256 fingerprint: `cb5e9cd7ac71c16e5109717b4bc07f01aed1bbda2b18a99bfbc76f7bd98245bc`
- Worktree: /Users/calebbolden/Projects/oss/open-brain-public
- Branch: goal/open-brain-phase3
- Objective: Execute goal 62 Open Brain Phase 3 P3-W0 through P3-W6 with Codex-only workers and gated merge
- Created date: 2026-09-01

## Milestone

- Status: in progress; Gate 0 and `P3-W0` through `P3-W5` clean checkpoints complete.
- Goal: `cbolden15/agent-config#62`; parent `cbolden15/agent-config#41` remains open.
- Baseline: freshly fetched `origin/main` at `d93c6dae2a22ef028390f30c990b27968229178e`.
- Planning commit: `e8a4ec2` contains the reviewed plan and review evidence only.
- Plan: `docs/plans/phase-3-appliance-control-plane.md`, SHA-256 `e842eac8a5a933d20405bc84bde0ecf87474c7d4317018f32ac6ef95ef0263b7`.
- Baseline verification: `make verify` passed Ruff, strict MyPy on 439 source files, all 2,981 tests, wheel/sdist builds, and artifact policy.
- GitHub baseline: unrelated Dependabot PR `vora-technology/open-brain#1` is open and untouched; protected `main` requires Python 3.12/3.13/3.14 CI and `public-artifacts`.
- Scope: Codex-only source-checkout implementation. No Phase 4, publishing, release, deployment, production, private predecessor, real supervisor, credential, or live Brain action.
- P3-W0 verification: 92 focused tests, focused Ruff, strict MyPy on 439 source files, full `make verify` with 2,984 tests, wheel/sdist builds, artifact policy, and diff integrity passed.
- P3-W0 behavior gate: future appliance application/entrypoint names and the owner-only Unix-domain daemon mutation path are reserved; current Phase 2 scripts and behavior remain unchanged.
- P3-W0 failure gate: no shipping import reaches legacy operations/release code, no Phase 4 packaging is required, and no control/writer/auth architecture fork remains.
- P3-W1 verification: 32 focused tests, focused Ruff, strict MyPy on 447 source files, full `make verify` with 2,999 tests, wheel/sdist builds, artifact policy, architecture ownership/debt, and diff integrity passed.
- P3-W1 behavior gate: init is preflighted and idempotent over identity, spaces, content, credential, schema, and index; maintenance evidence is bounded; absent/newer read views make no mutation or writer acquisition.
- P3-W1 failure gate: unsafe credentials are preserved and rejected, newer schemas are rejected before writer acquisition, legacy schema migration preserves content, nested writable roots initialize, and installed scripts remain on Phase 1.
- P3-W2 status: clean checkpoint complete across authority, control, scheduler, supervisors, entrypoints, and restart recovery.
- P3-W2 authority evidence: daemon lifetime lease is process-exclusive and distinct from shared writer; engine capability is issuer-created, root-bound, stale after exit, required by appliance mutation composition, and revalidated on every writer acquisition.
- P3-W2 control evidence: owner-only confined Unix socket, bounded canonical envelopes and accepted-client timeouts, root-bound authority-gated stale cleanup, replacement detection, second-daemon exclusion, fail-closed clients, and lost-receipt replay without duplicate capture passed 130 focused tests, Ruff, strict MyPy on 452 source files, and diff hygiene.
- P3-W2 runtime evidence: the profile-bound scheduler uses root-confined bounded atomic state and immutable receipts; daemon shutdown closes operation admission before releasing authority; restart replay preserves one capture and one publication; packaged and compatibility entrypoints cannot open a direct writer; launchd/systemd behavior is deterministic and fake-injected only.
- P3-W2 verification: 178 focused tests, full Ruff, strict MyPy on 457 source files, full `make verify` with 3,050 tests, wheel/sdist builds, artifact policy, architecture ownership with no temporary debt, and diff integrity passed in a sanitized environment.
- P3-W3 status: clean checkpoint complete across owner UI parity, browser auth, HTTP route security, status/doctor parity, and bounded metadata-only run history.
- P3-W3 behavior evidence: the daemon owns the one HTTP listener; host-only sessions, exact origins, CSRF, and route-capability separation fail closed; CLI and UI share app state; page reads, status, doctor, and bounded run history pass through the composed service.
- P3-W3 failure evidence: credentials stay out of URLs, HTML, logs, and result envelopes; private binding requires an exact HTTPS external origin and explicit encryption termination; unknown and cross-capability POST routes are rejected before body read.
- P3-W3 verification: 99 focused and architecture tests, 45 post-fix daemon/scheduler/history/UI/auth/log/storage tests, full Ruff, strict MyPy on 464 source files, full sanitized `make verify` with 3,070 tests, wheel/sdist builds, artifact policy, and diff integrity passed.
- P3-W4 status: clean checkpoint complete across direct-Markdown reconciliation, engine-owned backup creation and verification, atomic disposable restore, replacement preflight, and distinct Portable export/import jobs.
- P3-W4 behavior evidence: backup manifests bind exact Portable bytes, SQLite backup-API snapshots, and schema-validated immutable app receipts; mutable scheduler state and credentials remain excluded. Restore regenerates credentials, initializes scheduler state, rebuilds retrieval, and checks appliance health only on disposable roots.
- P3-W4 failure evidence: bounded no-follow scans reject missing, changed, symlinked, malformed, over-budget, or identity-shifted Markdown and app state. Backup/restore containment, invalid SQLite, forbidden inventory, credential-shaped app state, pre-promotion interruption, post-promotion replay, effect-before-receipt replay, and timestamp inversion all fail closed or replay safely.
- P3-W4 verification: 96 focused tests, full Ruff, strict MyPy on 472 source files, full sanitized `make verify` with 3,091 tests, wheel/sdist builds, artifact policy, and diff integrity passed.
- P3-W5 status: clean checkpoint complete across typed artifact lifecycle ports, explicit owner upgrade/uninstall requests, durable lifecycle journals, crash/concurrency-safe rollback, data-preserving removal, source-checkout CLI injection, and macOS/Linux CI evidence.
- P3-W5 behavior evidence: upgrade binds compatible candidate, verified backup, matching disposable preflight, exact engine/app migrations, activation, active restart, and healthy doctor receipts. Uninstall orders stop, one supervisor removal, and artifact removal while preserving the root and exposing no purge surface.
- P3-W5 failure evidence: missing owner confirmation, request conflicts, mismatched recovery evidence, incomplete migrations, forward-stage errors, rollback failure, effect-before-receipt interruption, concurrent lifecycle requests, path residue, and absent artifact composition all fail closed with bounded receipts.
- P3-W5 verification: 47 focused tests, 88 architecture/lock tests, full Ruff, strict MyPy on 474 source files, full sanitized `make verify` with 3,111 tests, wheel/sdist builds, artifact policy, and diff integrity passed.
- Current subphase: `P3-W6` ready after the W5 checkpoint gates.
- Next action: commit and push the W5 checkpoint, then run exact-candidate audits, gotcha capture, and the reserved fresh read-only Codex review.
