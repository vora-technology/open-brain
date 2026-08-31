# Workstream State

- ID: `20260830-open-brain-phase0-release-boundary-c09140`
- Repo root: repository containing this workstream state
- Remote identity SHA-256 fingerprint: `4b4cbb45d166074eb60801a9180acb4f849a57c15adf3440552a6ef8dd10867f`
- Worktree: same as repository root
- Branch: main
- Objective: Complete approved Option C Phase 0 release boundary and satisfy its five exit gates
- Created date: 2026-08-30

## Milestone contract

- Milestone: `phase-0-freeze-release-boundary`
- Objective: Complete the six approved Phase 0 work items and satisfy all five exit gates without entering Phase 1.
- Allowed scope: contract change control and expansion backlog; current-namespace import-rule enforcement; characterization evidence for the public CLI, typed data, and source/wheel/sdist artifacts; Brain-root layout version 1 schemas and synthetic conformance fixtures; common envelope and stable tenant/actor/role/space identity contracts; four payload-family contracts; safe tracked-source and history audit for private-only material.
- Excluded scope: physical package movement, provider `none`, new CLI/UI product journeys, connector SDK work, hosted implementation, and the PyInstaller/Nuitka spike.
- Stop condition: all Phase 0 work items are implemented, every exit gate has reproducible evidence, and `make lint typecheck test build` plus the bounded public-tree/release audit pass.
- Output contract: changed paths, exact checks and results, one evidence record per exit gate, unresolved blocker if any, and no commits or pushes unless explicitly requested.
- Shared child budget: 0 active of 6; all 12 child slots used across mapping, implementation, remediation, and adversarial review.
- Scratch ledger: `/tmp/open-brain-phase0-c09140/ledger.json`; session-local and intentionally excluded from repository state.

## Baseline

- Command: `make lint typecheck test build`
- Result: passed on 2026-08-30; Ruff clean, mypy clean across 387 source files, 2,683 tests passed, and `open_brain-0.1.0` wheel/sdist built successfully.

## Completed milestone

- Status: complete on 2026-08-30; all six Phase 0 work items and all five exit gates have reproducible evidence.
- Contract boundary: accepted v0 change control, concrete expansion backlog, and explicit classification for every current top-level package and root module.
- Characterization: machine-readable public CLI and current-record inventories, plus explicit current and target artifact policy.
- Portable Brain v1: 14 local-URN schemas, strict serializer, four payload families, stable identity and role-claim bindings, complete checked-in Brain root, two JSONL correction batches, blob fixture, manifest, and fail-closed proposal-to-publication/action chains.
- Release hygiene: bounded metadata-only history audit, source/archive release audit, exact artifact-member verification, and explicit target exclusions.

## Final verification

- Command: `make verify`
- Result: passed; Ruff clean, mypy clean across 398 source files, 2,754 tests passed, wheel and sdist built, and artifact-member policy passed.
- Release audit: passed against the source tree and both artifacts with `/tmp/open-brain-phase0-c09140/synthetic-private-denylist.txt`.
- Artifact evidence: wheel and sdist each contain all 14 schemas and all 18 conformance-fixture files.
- Hygiene: `uv lock --check` and `git diff --check` passed; all 18 Portable fixture files are visible to Git.

## Remaining work outside Phase 0

- Repository publication remains owner-gated until 101 generic history findings across 25 commits and eight paths are dispositioned and a project-specific private denylist is supplied.
- The PyInstaller 6 clean-host spike, Nuitka fallback, native artifacts, and host verification remain Phase 1 work.
- No commit or push was made.
