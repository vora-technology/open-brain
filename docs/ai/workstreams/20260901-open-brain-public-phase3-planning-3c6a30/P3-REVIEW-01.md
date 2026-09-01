# Independent plan review 1

- Reviewer: fresh read-only Codex `gpt-5.4` high session.
- Verdict: `NEEDS_FIX`.
- Counts: P0/P1/P2/P3 `1/4/0/0`.
- Files changed by reviewer: none.

## Actionable findings

1. P0: the proposed daemon-lifetime writer lease would self-conflict with every existing per-operation writer lease because same-process nested acquisition is rejected.
2. P1: the plan claimed artifact-defined `V0-GATE-08` passed from source checkout.
3. P1: the plan did not require `pyproject.toml`, `open_brain.__main__`, and current entrypoint tests to cut installed/module CLI paths over from `phase1_entrypoints`.
4. P1: the plan omitted the real HTTP router, which sends every POST to share intake and makes UI mutation handlers unreachable through composition.
5. P1: the plan relied on backup behavior that exists only in legacy-classified modules without planning a non-legacy engine extraction and verification path.

## Reconciliation

- Added a distinct daemon-authority lock scope and engine-issued active authority capability; per-operation shared-writer locks remain separate and non-nested.
- Reclassified `V0-GATE-08` as Phase 3 source-checkout behavior with artifact proof deferred to Phase 4.
- Added exact installed/module/MCP entrypoint cutover paths and tests.
- Added `http_server.py`, composed-listener routing tests, and exact `/api` versus `/share` capability separation.
- Added engine-owned backup contracts, ports, SQLite snapshot adapter, restore verifier, exact backup contents/exclusions, and non-legacy tests.
- Also clarified the non-mutating read view, scheduler inventory, purpose-bound credentials, SSH-tunnel remote path, owner gates, and Phase 3 artifact-lifecycle port.

The revised file passed requirement-presence checks, seven-wave structure checks, existing-test-path checks, and `git diff --check`. A fresh exact-file rereview is required before the plan is ready.
