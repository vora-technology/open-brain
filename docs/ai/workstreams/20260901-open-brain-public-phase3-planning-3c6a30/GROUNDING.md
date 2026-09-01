# Phase 3 planning grounding

## Verified repository state

- Repository: `/Users/calebbolden/Projects/oss/open-brain-public`.
- Planning branch: `phase3-planning`, created from clean `main`.
- Baseline: `d93c6dae2a22ef028390f30c990b27968229178e`; freshly fetched `origin/main` is identical (`0` ahead, `0` behind).
- Parent program: `cbolden15/agent-config#41`.
- Completed predecessor child: `cbolden15/agent-config#51`, Open Brain Phase 2 through P2-W5.
- Baseline verification on 2026-09-01: `make verify` exited `0`; Ruff passed; strict MyPy passed on 439 source files; 2,981 tests passed; wheel and sdist built; artifact policy passed.

## Authority order

1. `CLAUDE.md` and the current repository state.
2. `docs/v0-product-contract.md`, approved contract version 0.3.
3. `docs/plans/option-c-architecture.md`, especially Phase 3 and its traceability/verification sections.
4. `docs/architecture/proposed-v0-system-architecture.md` for the target runtime, authority gates, and lifecycle flow.
5. `docs/architecture.md` for the implemented Phase 2 boundary.
6. `docs/plans/phase-2-deepen-modules-in-place.md` and the completed Phase 2 handoff.

## Required Phase 3 outcomes

- Pass `V0-INSTALL-02` through `V0-INSTALL-06`.
- Pass `V0-OPS-01` through `V0-OPS-09` at the public application boundary.
- Run one supervised daemon with one canonical writer and durable internal schedules.
- Complete the owner UI and expose actionable health, doctor, and bounded run history through the same application state as the CLI.
- Exercise verified backup, empty disposable restore, Portable export/import, upgrade, and data-preserving uninstall through the app interface.
- Pass `V0-GATE-14` through the public app interface.
- Preserve all Phase 2 engine, privacy, portability, connector-absence, and import-direction gates.

## Observed current state and gaps

- `pyproject.toml` still points the supported CLI, HTTP, and MCP scripts at `services/phase1_entrypoints.py`; no `init`, daemon, lifecycle, backup, restore, upgrade, or uninstall command exists.
- `profile.compile_single_user_local()` safely and idempotently creates the version-1 root and stable identities, but it does not generate the local credential or return an application initialization receipt.
- `EngineTaskSet` exposes capture, inbox/spaces, review, retrieval, and portability only. It has no public health, reconciliation, backup, restore-validation, or schema-migration task.
- The engine has strong per-operation writer leases and crash recovery. The default CLI still opens full mutating engine tasks directly; there is no daemon-owned lifetime writer authority or local control client boundary.
- The current Phase 1 UI covers health, inbox, spaces, proposals, capture, decisions, and search. It lacks canonical page viewing, run history, browser-session authentication, origin enforcement, and CSRF protection. The HTTP router sends POST requests to share intake instead of UI mutation routes.
- All existing `operations/*` scheduler, run-log, doctor, status, backup, and recovery files and all `release/*` installation files are classified `legacy` in `docs/v0-package-classification.json`. Shipping app/engine code may not import them. They are characterization evidence only.
- The legacy scheduler is hard-bound to `JOB-001` through `JOB-030`; it cannot be promoted into the one-daemon v0 profile.
- Portable export/import is implemented and heavily fault-tested at the engine boundary, but no public app orchestration exists for backup, restore, upgrade, or uninstall.
- The local engine SQLite schema is created and patched in place without one versioned application migration contract. Upgrade orchestration therefore needs an explicit engine-owned compatibility/migration surface.
- Current GitHub CI runs the full suite on Ubuntu for Python 3.12, 3.13, and 3.14. No macOS lifecycle job exists.
- Direct Markdown edits can affect retrieval reads, but the approved bounded validation/remediation reconciliation task is absent.

## Planning constraints

- Prefer the do-it-properly architecture: new app-owned Phase 3 lifecycle, daemon, scheduler, health, and recovery modules with explicit engine maintenance contracts. Make `phase1_*` entry points compatibility-only after the new path is proven.
- Do not import or reclassify the legacy 30-job application as the public appliance. Port only demonstrated generic behavior behind new owner-correct contracts and tests.
- Keep the retained monolith and existing namespace. Phase 4 owns the four-distribution split, `packages/`, isolated connector workers, PyInstaller/Nuitka work, native release artifacts, signing, and publishing.
- Separate Phase 3 orchestration evidence from Phase 4 artifact evidence. Upgrade/uninstall may use injected artifact lifecycle ports in Phase 3; native artifact adapters and clean-host artifact gates remain Phase 4.
- Use only disposable roots and ephemeral test-service identities. No live Brain data, production, private predecessor source, deployment, package publication, tag, or release is allowed.
- Keep MCP read-only and space scoped. The default profile stays provider `none`, egress off, and connector empty.
- Every implementation wave must start from and end at a clean verified checkpoint, with focused Pytest, Ruff, strict MyPy, and full `make verify` evidence.

## Codex mapper result

- `P3-MAP-01` completed read-only with no repository-authority conflict and no required new product decision.
- It recommended dependency order: appliance bootstrap; daemon/supervisor control plane; owner-surface parity; recovery lifecycle; final reconciliation.
- It identified the proper-architecture fork as a dedicated app-owned control plane and rejected promoting `services/entrypoints.py` plus the 30-job scheduler.
- Its sandbox could not run `git status`; the coordinator independently verified the branch, SHA, remote equality, and worktree state.
