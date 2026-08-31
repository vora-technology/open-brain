# Workstream State

- ID: `20260831-open-brain-public-goal-51-phase2-codex-only-36f1ea`
- Repo root: <repo-root>
- Remote identity SHA-256 fingerprint: `cb5e9cd7ac71c16e5109717b4bc07f01aed1bbda2b18a99bfbc76f7bd98245bc`
- Worktree: <repo-root>
- Branch: goal/open-brain-phase2
- Objective: Execute goal 51 through P2-W5 with Codex-only workers, verification, review, PR, and merge
- Created date: 2026-08-31
- Public-repo redaction: local absolute paths are represented as `<repo-root>`; the remote fingerprint, branch, and workstream ID retain identity.

## Current milestone

- Milestone: P2-W1 application composition inversion
- Status: verified; evidence commit pending
- Allowed scope: app-owned construction and startup, producer-owned result/config values, public engine profile imports, default predecessor-route removal, exact architecture classification and debt
- Stop condition: P2-W2 starts before P2-W1 has a clean verified checkpoint and independent READY review
- Code checkpoint: `9cbacbd`
- Result: one app-owned composition facade with a one-way startup graph; production is a compatibility shim; forbidden production-to-CLI, operations-to-CLI, config-to-ledger, and storage-to-operations edges are absent; default migrate, parity, shadow, and cutover routes are unavailable; 190/190 runtime files are classified with 280 exact temporary-debt entries

## Last verification

- Command: P2-W1 focused Pytest; repository Ruff; strict MyPy; `make verify`; factory-identity/import-graph smoke; `git diff --check`; owner-approved `make audit`; fresh independent Codex re-review
- Result: passed 117 focused tests, Ruff, strict MyPy on 411 source files, 2,861 total tests, wheel/sdist builds, artifact policy, factory identity, diff integrity, release audit, and independent READY review with no findings

## Decision log

- Chosen: one canonical comment marker represents an explicitly approved empty owner denylist. Rejected: treating “no additional terms” as a scan term, accepting arbitrary comments, or skipping the audit. Reason: preserve fail-closed behavior while representing the owner's actual decision.
- Chosen: redact local absolute paths as `<repo-root>` in public workstream state. Rejected: publishing laptop paths or excluding workstream evidence from the release audit. Reason: project privacy rules outrank the generic workflow-state path format.
- Chosen: define `LockScope` once in `core/locks.py`, export it through `open_brain.engine`, and preserve operations compatibility by re-exporting the same type. Rejected: a second operations-owned enum or storage importing operations. Reason: one engine-owned vocabulary closes the storage-to-operations edge without breaking callers.
- Chosen: treat the live filesystem inventory of 188 runtime files as authoritative. Rejected: carrying the mapper's provisional count forward. Reason: the classification checker discovers and compares the current tree on every run.
- Chosen: retain every current violation as one exact sorted temporary-debt edge instead of weakening rules around the monolith. Rejected: package-level exemptions or vacuous absent-namespace tests. Reason: later waves must remove observable debt while the rules remain enforced now.
- Chosen: make `services.application` the authoritative application facade, move shared HTTP/MCP/config helpers to `services.runtime`, and point the production compatibility module back to the app facade. Rejected: a deferred entrypoint/application cycle or startup through a production re-export. Reason: startup and construction now form one one-way dependency graph.
- Chosen: return scheduler records from operations, retention records from production, and ledger config values from app config, converting only at the CLI/composition edges. Rejected: producer modules importing CLI representation or config importing ledger internals. Reason: ownership must follow the capability that creates the value.
- Chosen: keep predecessor modules for compatibility tests while removing their default application routes. Rejected: deleting historical modules in P2-W1 or leaving migrate/cutover reachable by default. Reason: the pre-alpha compatibility change is explicit without broadening into P2-W2 convergence.
- Chosen: expose profile dependencies through the public engine package and keep profile-local confined file handling. Rejected: profile imports from engine, provider, core, or storage internals. Reason: the profile boundary now depends only on the supported engine facade.

## Dispatch ledger

- Codex coordinator: current Codex session; P2-W0 and P2-W1 grounding, diagnosis, verification, review reconciliation, and git integration; active
- P2-W0: `W0-LOCK-01`, `W0-ARCH-01`, and `W0-ARCH-IMPL-01`; 3 Codex children complete and coordinator-verified
- P2-W1 mapping: `W1-MAP-COMPOSITION-01` and `W1-MAP-VALUES-01`; 2 Codex children complete
- P2-W1 implementation: `W1-IMPLEMENT-01` ended on model capacity; `W1-RESUME-01` completed the preserved patch and focused gates
- P2-W1 review: `W1-REVIEW-01` returned NOT_READY; `W1-REVIEW-FIX-01` resolved all findings; `W1-REREVIEW-01` returned READY with no findings
- P2-W1 children: 7 total, 0 active. No Claude-family or other non-Codex agent was dispatched.

## Next action

Commit this P2-W1 evidence, verify a clean checkpoint, push the goal branch, then execute P2-W2 with Codex-only bounded workers.
