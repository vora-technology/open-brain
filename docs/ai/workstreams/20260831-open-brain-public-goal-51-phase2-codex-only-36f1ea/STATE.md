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

- Milestone: P2-W5 complete Phase 2 boundary reconciliation
- Status: the first recorded-override exact review passed the dry-run fix and found two P2 capability/loading defects; scoped MCP injection and enabled optional-module loading repairs now pass every local gate and await a clean commit plus exact-commit rerun
- Allowed scope: zero-debt ownership, isolated engine imports, bounded representation capabilities, public-result projection, default app entrypoints, Phase 1 journey, documentation/gotcha reconciliation, final verification, review, PR, and merge
- Stop condition: PR or merge begins before one clean candidate passes every final gate and a fresh independent Codex review returns READY with P0/P1/P2 at 0/0/0
- Code checkpoint: `555ae02` truthful zero-debt classification, app-owned default entrypoints, minimized task capabilities, encoded/typed public-result projection, engine isolation, docs, and regressions
- Result: all runtime files have one owner and temporary architecture debt remains empty; one exact reviewed app extension-host import preserves enabled optional-module behavior; the default CLI/HTTP/MCP path imports no legacy or connector modules; MCP stores only scoped retrieval; public task results hide raw/encoded protected values and storage-derived paths without changing Portable bytes; the default profile remains provider-none and connector-free

## Last verification

- Command: affected MCP/optional-integration regressions; exact P2-W5 engine-isolation and focused suites; installed Phase 1 journey; repository Ruff; strict MyPy; `make verify`; `git diff --check`; owner-approved release audit
- Result: passed 70 optional-integration tests, 1 isolation test, 227 focused architecture/residue/Portable/engine/service/connector tests, the installed journey, Ruff, strict MyPy on 439 source files, 2,981 total tests, wheel/sdist builds, artifact policy, diff integrity, and the owner-approved release audit

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
- Chosen: represent post-capture space changes as typed append-only route records linked by `supersedes`. Rejected: rewriting immutable capture records or keeping routing only in SQLite/search projections. Reason: current space membership must round-trip through Portable export/import while source evidence remains immutable.
- Chosen: bind validation, materialization, reopen, and promotion to one immutable Portable snapshot and one retained root identity. Rejected: repeated pathname reads or individually valid but unbound snapshots. Reason: accepted bytes must be exactly the bytes materialized and promoted.
- Chosen: document a trusted-owner local filesystem boundary for the pre-alpha single-user product. Rejected: claiming kernel protection against arbitrary hostile same-UID mutation. Reason: the implementation defends malformed input, crashes, target races, and cooperating processes; stronger hostile-local-user isolation requires a separate UID, container, VM, or immutable snapshot.
- Chosen: keep the Phase 2 connector seam internal to allow-listed repository-owned code and state that hostile Python reflection requires the separately deferred isolated-worker runtime. Rejected: expanding one reference proof into the forbidden public SDK, IPC worker, package-signing, or sandboxing scope. Reason: the reviewed architecture defers hostile third-party isolation until three internal proofs establish the shared contract.
- Chosen: meter connector operations at host-bound capture, transport, and checkpoint capabilities and reconstruct receipts from host evidence. Rejected: treating connector-mutated counters as authoritative. Reason: bounded output must reflect actual accepted captures, fetches, discoveries, and extractions.
- Chosen: require a sink-issued receipt identity, delivery ID, and source reference before a `SEEN` YouTube record can become `ACCEPTED`. Rejected: generic checkpoint replacement or connector-asserted commitment. Reason: replay state may advance only after the exact durable capture is evidenced.
- Chosen: compose the YouTube connector lazily in the real JOB-029 process path only when an absolute configuration reference is explicit. Rejected: package-default registration or test-only composition. Reason: the installed journey must work while the provider-none/default profile remains connector-free and egress-off performs no config, media, or transport work.
- Chosen: locate the unique portability capture recursively instead of hard-coding a local calendar month. Rejected: preserving a wall-clock/UTC boundary assumption. Reason: canonical bytes and identity remain exact across UTC month rollover.
- Chosen: classify the retained YouTube proof as five single-owner connector components instead of preserving the mapper's provisional one-file connector count. Rejected: labeling media, extractor, poll-state, or runtime files as shipping app/engine internals merely to match provisional arithmetic. Reason: the actual source graph and shared connector capability boundary are authoritative.
- Chosen: extract the default `single-user-local` composition and process startup into app-owned `phase1_application` and `phase1_entrypoints`, leaving predecessor and scheduled behavior behind explicit legacy facades. Rejected: package scripts that import the legacy monolith before selecting the current path. Reason: package entry-point metadata is a runtime dependency edge and must obey the same default/legacy boundary.
- Chosen: give each CLI family one task protocol, the UI only `Phase1TaskSet`, HTTP only capture, MCP scoped retrieval plus metadata feedback, and public jobs a capture-only sink. Rejected: representation access to `EngineTaskSet.profile` or portability. Reason: composition may retain the full set, but each consumer receives only its required authority.
- Chosen: apply one engine-owned output projection to bounded raw/percent/HTML-decoded protected values, digests, credentials, absolute paths, space slugs, and canonical paths, and make retrieval explanations generic. Rejected: renderer-specific redaction or query-term echo. Reason: every typed/JSON/text/HTML surface must consume the same safe result without altering durable or Portable bytes.
- Chosen: forward non-representation prefix flags to the selected CLI adapter and reject unsupported dry runs before mutation. Rejected: silently dropping `--dry-run` when it appears before the family name. Reason: argument placement cannot turn a non-mutating request into a write.
- Chosen: load the one allow-listed optional cloud module at the retained composition boundary while constructing the SDK client only after privacy and credential checks. Rejected: engine-owned dynamic imports or unrelated module-preload requirements. Reason: authorized compatibility remains functional without adding architecture debt or changing the provider-none default.
- Chosen: compare protected output literals after bounded decoding with case-insensitive matching. Rejected: exact-case replacement that lets equivalent scheme/host variants survive. Reason: public projection must fail closed across representation changes even when the underlying source canonicalization differs.
- Chosen: generate MCP retrieval IDs with cryptographic randomness independent of the query. Rejected: full or truncated query digests. Reason: dictionary-verifiable derivatives are not opaque metadata and can disclose private query membership.
- Chosen: define a committed handoff's `head` as its enclosing Git candidate while separately naming the implementation checkpoint. Rejected: claiming a handoff file can contain the SHA of the commit that contains itself. Reason: self-referential Git hashes are impossible; the packet must state the distinction explicitly.
- Chosen: remove every standalone SHA-256-shaped token from public task text after bounded decoding. Rejected: enumerating the unbounded digests of every case-equivalent protected value or exposing unrelated bare content hashes. Reason: bare hashes are dictionary-verifiable metadata; public correlation uses prefixed opaque IDs instead.
- Chosen: reject unsupported global dry-run requests before constructing `SingleUserLocalApplication`. Rejected: opening a root and relying on an adapter to avoid the requested write. Reason: profile/engine initialization itself creates durable layout and operational state, so process-level non-mutation must precede composition.
- Chosen: derive the caller's `ScopedRetrievalTask` in app composition and inject that capability into MCP. Rejected: storing the unrestricted retrieval task and deriving scope inside each tool method. Reason: the representation must not retain authority beyond its declared surface even when its normal calls apply filters.
- Chosen: retain lazy import behavior at the explicitly reviewed app-owned optional-integration extension host after capability enablement. Rejected: treating `sys.modules` preload state as package availability or moving arbitrary loading into engine code. Reason: enabled installed modules must work while disabled/default profiles remain import-free and temporary architecture debt stays empty.

## Dispatch ledger

- Codex coordinator: current Codex session; P2-W0 through P2-W3 grounding, diagnosis, verification, review reconciliation, and git integration; active
- P2-W0: `W0-LOCK-01`, `W0-ARCH-01`, and `W0-ARCH-IMPL-01`; 3 Codex children complete and coordinator-verified
- P2-W1 mapping: `W1-MAP-COMPOSITION-01` and `W1-MAP-VALUES-01`; 2 Codex children complete
- P2-W1 implementation: `W1-IMPLEMENT-01` ended on model capacity; `W1-RESUME-01` completed the preserved patch and focused gates
- P2-W1 review: `W1-REVIEW-01` returned NOT_READY; `W1-REVIEW-FIX-01` resolved all findings; `W1-REREVIEW-01` returned READY with no findings
- P2-W1 children: 7 total, 0 active. No Claude-family or other non-Codex agent was dispatched.
- P2-W2 mapping/reconciliation: four independent Codex mappers plus `W2-RECONCILE-01`; complete
- P2-W2 implementation: engine foundation and semantic repair completed; the surface worker exited incomplete; its resume patch was recovered and coordinator-verified
- P2-W2 review: `W2-INDEPENDENT-REVIEW-01` found JOB-005 rejected-page starvation; coordinator reproduced and fixed it; `W2-INDEPENDENT-REREVIEW-01` returned READY with no findings
- P2-W2 children: 11 total, 0 active. No Claude-family or other non-Codex agent was dispatched.
- P2-W3 mapping/reconciliation: four independent Codex mappers plus `W3-RECONCILE-01`; complete
- P2-W3 implementation/reconciliation: one implementation worker plus coordinator repairs implemented strict profile/ports, export/import/materialization, exact snapshot/promotion binding, schema parity, null occurrence preservation, and append-only routing replay
- P2-W3 review: seven normal-budget and five recorded-override read-only Codex verdicts exposed successive high/medium defects; every demonstrated issue was reproduced and repaired; `W3-ROUTING-FINAL-INDEPENDENT-REVIEW-01` returned READY with no in-scope high/medium finding
- P2-W3 children: 17 total, 0 active. Overrides and reasons are preserved in the milestone ledger. No Claude-family or other non-Codex agent was dispatched.
- P2-W4 mapping/reconciliation: three Codex mappers, one compact report retry, and one Codex reconciler; complete
- P2-W4 implementation/review: two implementation attempts plus eight independent review passes drove repairs for descriptor boundaries, global budgets, exact-value poisoning, real JOB-029 composition, host-owned metering, atomic discovery reservation, and receipt-bound checkpoint acceptance
- P2-W4 final review: `W4-RECEIPT-BOUND-FINAL-REVIEW-01` returned READY with no demonstrated in-scope high/medium finding
- P2-W4 children: 15 total, 0 active. Three recorded overrides were required because successive mandatory fresh reviews found new in-scope defects after the normal budget was exhausted. No Claude-family or other non-Codex agent was dispatched.
- P2-W5 mapping/reconciliation: four Codex mappers plus one Codex reconciler; complete
- P2-W5 implementation: separate Codex source and documentation workers completed the zero-debt source/security/classification and docs/gotcha changes; coordinator reproduced the worker-local macOS sandbox limitation and the exact test passed
- P2-W5 pre-review: one fresh read-only Codex review returned NEEDS_FIX with P0/P1/P2 `0/2/2`; one Codex repair worker and coordinator changes resolved installed legacy loading, encoded/query residue, direct typed path residue, cloud loading, command-specific help, and prefix dry-run safety
- P2-W5 exact-candidate review: `W5-FINAL-REVIEW-01` returned NEEDS_FIX with P0/P1/P2 `0/2/2`; it demonstrated case-varied source residue, query-derived MCP IDs, root-required combined version flags, and an ambiguous handoff head
- P2-W5 exact-candidate rereview: `W5-FINAL-REREVIEW-01` passed all four prior-finding checks and returned NEEDS_FIX with P0/P1/P2 `0/0/1` for the bare digest of a case-varied protected reference
- P2-W5 final normal-budget review: `W5-FINAL-READY-REVIEW-01` passed the digest and all earlier privacy/architecture checks, then returned NEEDS_FIX with P0/P1/P2 `0/0/1` because global dry-run opened the Brain root before adapter rejection
- P2-W5 first override review: `W5-OVERRIDE-FINAL-REVIEW-01` passed the dry-run and every earlier recheck, then returned NEEDS_FIX with P0/P1/P2 `0/0/2` because MCP retained the unrestricted retrieval task and enabled installed optional integrations required an unrelated preload
- P2-W5 children: 13 total, 0 active: 12 normal plus one recorded mandatory-review override. A fresh post-repair review requires one new narrowly recorded mandatory-review override. No Claude-family or other non-Codex agent was dispatched.

## Next action

Commit the verified scoped-capability and optional-loader repair, rerun every final gate on the clean candidate, then record one narrowly bounded mandatory-review override and obtain the fresh exact-candidate READY verdict.
