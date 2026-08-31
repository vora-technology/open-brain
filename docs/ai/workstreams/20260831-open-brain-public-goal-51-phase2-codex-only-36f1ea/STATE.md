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

- Milestone: P2-W2 surface convergence on engine tasks
- Status: verified; evidence commit pending
- Allowed scope: engine task extraction, one-root application capability injection, four-family HTTP capture, scoped read-only MCP, exact public-job sink migration, representation-test relocation, source-safe results, and exact architecture classification/debt
- Stop condition: P2-W3 starts before P2-W2 has a clean verified checkpoint and independent READY re-review
- Code checkpoints: `d3acb64` engine foundation and `a5c2cf1` surface convergence
- Result: CLI, authenticated HTTP, local UI, MCP, and exactly JOB-005/JOB-027/JOB-028/JOB-029 use one local application task set; HTTP accepts all common capture families; MCP query/fetch apply an explicit space allow-list before projection; public results expose bounded provenance only; 198/198 runtime files are classified with 275 exact temporary-debt entries

## Last verification

- Command: P2-W2 exact focused Pytest; affected production/process Pytest; repository Ruff; strict MyPy; `make verify`; `git diff --check`; owner-approved `make audit`; fresh independent Codex re-review
- Result: passed 138 focused tests, 82 affected tests, Ruff, strict MyPy on 421 source files, 2,883 total tests, wheel/sdist builds, artifact policy, diff integrity, release audit, and independent READY review with no findings

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
- Chosen: extract engine contracts, normalization, storage, capture, spaces, review, and retrieval behind `open_local_engine() -> EngineTaskSet`, retaining the old engine class only as compatibility composition. Rejected: surface-specific task wrappers or a Phase 4 package split. Reason: every P2-W2 surface must receive the same task objects without changing distribution layout.
- Chosen: make `SingleUserLocalApplication` own one root and inject only bounded task capabilities into CLI, HTTP, UI, MCP, and public jobs. Rejected: translating the legacy multi-root `AppConfig` into a second engine path. Reason: process startup now has one authoritative task graph while legacy config supplies only bounded service metadata.
- Chosen: require MCP retrieval to scope both search and fetch at the SQL lookup before reading canonical content, with an empty default and identical unknown/disallowed fetch results. Rejected: filtering projected results after retrieval. Reason: callers outside the allow-list must never expose the underlying capability.
- Chosen: grant capture-only contexts to exactly JOB-005, JOB-027, JOB-028, and JOB-029, and advance connector checkpoints only after durable acceptance. Rejected: queue fallback or route/canonicalize authority. Reason: public ingress can submit idempotently but cannot acquire owner actions.
- Chosen: advance JOB-005 past policy-rejected rows while saving no cursor if an eligible sink submission fails. Rejected: advancing the whole batch before persistence or leaving a full rejected page at the old cursor. Reason: preserve durable ordering without starving later authorized messages.

## Dispatch ledger

- Codex coordinator: current Codex session; P2-W0 through P2-W2 grounding, diagnosis, verification, review reconciliation, and git integration; active
- P2-W0: `W0-LOCK-01`, `W0-ARCH-01`, and `W0-ARCH-IMPL-01`; 3 Codex children complete and coordinator-verified
- P2-W1 mapping: `W1-MAP-COMPOSITION-01` and `W1-MAP-VALUES-01`; 2 Codex children complete
- P2-W1 implementation: `W1-IMPLEMENT-01` ended on model capacity; `W1-RESUME-01` completed the preserved patch and focused gates
- P2-W1 review: `W1-REVIEW-01` returned NOT_READY; `W1-REVIEW-FIX-01` resolved all findings; `W1-REREVIEW-01` returned READY with no findings
- P2-W1 children: 7 total, 0 active. No Claude-family or other non-Codex agent was dispatched.
- P2-W2 mapping/reconciliation: four independent Codex mappers plus `W2-RECONCILE-01`; complete
- P2-W2 implementation: engine foundation and semantic repair completed; the surface worker exited incomplete; its resume patch was recovered and coordinator-verified
- P2-W2 review: `W2-INDEPENDENT-REVIEW-01` found JOB-005 rejected-page starvation; coordinator reproduced and fixed it; `W2-INDEPENDENT-REREVIEW-01` returned READY with no findings
- P2-W2 children: 11 total, 0 active. No Claude-family or other non-Codex agent was dispatched.

## Next action

Commit this P2-W2 evidence, verify a clean checkpoint, push the goal branch, then execute P2-W3 with Codex-only bounded workers.
