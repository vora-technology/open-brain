# Open Brain OSS-readiness gap audit

- Date: 2026-08-30
- Repository baseline: `41666f9`
- Contract: `docs/v0-product-contract.md`
- Architecture: `docs/plans/option-c-architecture.md`
- Audit mode: strict
- Ship readiness: NOT READY

> Superseded requirement baseline: this audit measured product contract `0.1`. Contract `0.2` adds generic typed capture, spaces, portable identities, multi-output review, export/import, and hosted compatibility requirements. The implementation evidence remains useful, but the `17 of 64` count, `0 of 12` gate count, and exact priorities must be refreshed before they are used as current readiness numbers.

## Executive assessment

Open Brain has a strong local knowledge engine, but the current repository is not yet the product described by the v0 contract.

The implementation is strongest below the product surface. Capture identity, provenance, privacy policy, durable queues, review receipts, atomic Markdown writes, SQLite safety, writer locks, backup primitives, bounded HTTP, and read-only MCP are real and well tested. The repository passes Ruff, strict mypy, 2,683 tests, and package builds.

The missing work is composition. A new owner cannot initialize one Brain root, start one daemon, capture something, see it move through an inbox, review its meaning, retrieve it, and recover the system using a release artifact. The current build still reflects the private replacement program: six configured roots, a local provider assumption, 30 scheduled jobs, optional integrations, migration/parity code, and synthetic cutover machinery.

The most important finding is concrete: production capture publication writes owner text to `work_root/inbox/open-brain/`, while the active retriever scans only `work_root/pages/`. The lower-level pipeline can succeed and still fail the product promise. A real CLI smoke test confirmed that capture returned `queued`, then query returned `work_index_unavailable`.

Strict requirement completion is **17 of 64 requirements (27%)**. Partial and deviated requirements do not count as complete. More importantly, **0 of 12 release gates fully pass**.

## What is already solid

1. The privacy and trust boundaries are unusually strong. Unknown and personal content stay local, cloud authority is explicit, secrets resolve late, URL egress is bounded, and public representations are redacted.
2. Durability is designed for unattended operation. Queues, immutable identities, atomic writes, replay protection, leases, SQLite migrations, and backup verification are useful foundations for an always-on server.
3. Markdown and SQLite are the right storage split. Canonical knowledge can stay readable while operational state and indexes remain replaceable.
4. The CLI, HTTP, MCP, and application composition seams are enough to build a smaller product path without replacing the domain core.
5. Engineering verification is healthy: `make verify` passed Ruff, strict mypy across 387 files, all 2,683 tests, and wheel/sdist builds.

## Requirement status summary

`COMPLETE` means the behavior is wired and evidenced. `PARTIAL` means useful pieces exist but the contract outcome does not. `MISSING` means no usable implementation was found. `DEVIATED` means the current behavior conflicts with the contract.

| Contract area | COMPLETE | PARTIAL | MISSING | DEVIATED |
|---|---|---|---|---|
| Installation | none | none | `INSTALL-01` through `INSTALL-06` | none |
| Capture | `CAPTURE-02`, `CAPTURE-03`, `CAPTURE-04` | `CAPTURE-06`, `CAPTURE-07` | none | `CAPTURE-01`, `CAPTURE-05` |
| Review | `REVIEW-03`, `REVIEW-05` | `REVIEW-01`, `REVIEW-02`, `REVIEW-07` | `REVIEW-04` | `REVIEW-06` |
| Canonical data | `DATA-03`, `DATA-04` | `DATA-01`, `DATA-02` | none | `DATA-05` |
| Retrieval | `QUERY-05` | `QUERY-03` | `QUERY-02` | `QUERY-01`, `QUERY-04` |
| User surfaces | `SURFACE-04` | `SURFACE-02`, `SURFACE-05` | none | `SURFACE-01`, `SURFACE-03` |
| Always-on operations | none | `OPS-03` through `OPS-07` | `OPS-08`, `OPS-09` | `OPS-01`, `OPS-02` |
| Privacy and security | `PRIVACY-01` through `PRIVACY-08` | none | none | none |
| Release gates | none | `GATE-02` through `GATE-08` | `GATE-01`, `GATE-09`, `GATE-10`, `GATE-12` | `GATE-11` |

The privacy row reflects implementation-level compliance, not release proof. `GATE-11` remains deviated because no implemented `single-user-local` profile exists and provider configuration still defaults to `local`, not `none`.

## Prioritized gaps

### P0: prove the v0 product in place

| Rank | Gap | Evidence | Required outcome |
|---:|---|---|---|
| 1 | The contract and Option C plan are still drafts | `docs/v0-product-contract.md:3-7`; `docs/plans/option-c-architecture.md:3-7`; unresolved decisions at `docs/plans/option-c-architecture.md:552-560` | Approve the contract, layout version, supported host matrix, owner-text publication rule, and packaging spike boundary before more feature work. |
| 2 | No one-root `single-user-local` profile exists | `src/open_brain/config.py:33-62` requires separate inputs; `src/open_brain/config.py:539-598` builds five retained roots plus backup; provider defaults to `local` at `src/open_brain/config.py:57-61` | Compile one disposable Brain root into a versioned layout with provider `none`, cloud/egress off, and no hand-edited TOML. This is the Phase 1 profile compiler, not the full installer yet. |
| 3 | The no-model first-value journey is not executable | Publication writes `inbox/open-brain` at `src/open_brain/production/capture_publication.py:113-115`; retrieval scans `pages` at `src/open_brain/integrations/retrieval.py:226-264`; production provider selection permits only `local` or `cloud` at `src/open_brain/providers/base.py:41-58` | One black-box path must accept owner text and URL/share, persist before enrichment, expose inbox state, publish or propose under the owner rules, and retrieve the result with provider `none`. |
| 4 | Intent, source records, and retrieval do not form one coherent lifecycle | Public capture carries text and reason but no intent at `src/open_brain/cli/production_adapters.py:164-183`; proposal creation exists only behind a separate router; `RetrievalHit` lacks source kind and match explanation at `src/open_brain/integrations/ports.py:272-299` | Carry closed intent through capture, create proposals for `idea` and `action_candidate`, search eligible source records separately from canonical pages, and explain each match. |
| 5 | Required owner surfaces are incomplete | The UI exposes only `/health` and `/pages/<id>` at `src/open_brain/integrations/ui.py:72-115`; any command `--help` prints top-level help at `src/open_brain/cli/main.py:77-79` | CLI and UI must share capture, inbox, proposal, review, search, page, and run-state services. Add command-specific help and bounded remediation. |

### P1: turn the proven slice into an appliance

| Rank | Gap | Evidence | Required outcome |
|---:|---|---|---|
| 6 | No public initialization lifecycle exists | No `init` command appears in `src/open_brain/cli/_registry.py:35-58`; service credentials are manually referenced at `src/open_brain/services/entrypoints.py:146-170` | Add idempotent `init`, generated owner-only credential, permissions/schema/index creation, host/provider/supervisor preflight, and failed-init cleanup. |
| 7 | The runtime is still 30 jobs instead of one daemon | Routes enumerate `JOB-001` through `JOB-030` at `src/open_brain/cli/_registry.py:88-119`; `docs/operations.md:3-5` explicitly says the application does not install or control services | Build one daemon that owns the writer lease, drains capture/review queues, serves HTTP/UI, runs internal durable schedules, and records bounded run receipts. |
| 8 | Recovery is library capability, not owner workflow | Backup and restore primitives exist, but there are no `upgrade` or `uninstall` command families in `src/open_brain/cli/_registry.py:35-58` | Expose verified backup, disposable restore, compatibility preflight, migration, post-upgrade doctor, and data-preserving uninstall through the application. |
| 9 | No native release or clean-host install path exists | `pyproject.toml:5-49` builds one generic Python distribution; CI builds on Ubuntu; `src/open_brain/release/installation.py` creates plans but never installs | Produce supported macOS and Linux artifacts, launchd/systemd lifecycle adapters, checksums, release metadata, and a measured clean-host quickstart. |
| 10 | Option C boundaries are neither enforced nor reflected in artifacts | Current architecture tests inspect only a small `core` token set at `tests/security/test_architecture_boundaries.py:4-17`; production imports CLI, storage imports operations, and the wheel contains migration, parity, cutover, and optional integration namespaces | Add import-direction and artifact-content gates. After the vertical slice passes, separate engine, app, connectors, and legacy in the order defined by Option C. Do not claim that private data is present without a separate history/artifact audit. |

### P2: prepare the public OSS release

The existing repository-readiness audit remains relevant but should not replace product work: `docs/audits/open-source-readiness.md`.

| Gap | Current state | Release requirement |
|---|---|---|
| User documentation | README leads with predecessor replacement and internal capability language at `README.md:3-5,37-44` | Replace it with install, first capture, inbox/review/search, recovery, limitations, and support paths. |
| Community files | No conduct, support, governance, maintainer, CODEOWNERS, issue-form, or PR-template files are present | Add the contributor and ownership baseline before public launch. |
| Security intake | `SECURITY.md` promises a future reporting path and no supported-version policy | Publish a working private contact, supported versions, response expectations, and disclosure process. |
| Supply-chain and release automation | Actions use mutable major tags; no changelog or publishing workflow exists | Pin actions, add dependency updates, define release authority, publish checksums/attestations, and bind all artifacts to one release manifest. |
| Repository controls | Public branch rules, CodeQL, secret scanning, push protection, private vulnerability reporting, and Scorecard are not proven | Prepare these while private and activate/test them when the repository becomes public. |

## Important contract deviations

### Conflicting capture bytes are rejected, not quarantined

Same-byte replay is idempotent, but changed bytes under the same capture identity raise `QueueImmutableConflictError` at `src/open_brain/capture/queue.py:216-230`. HTTP returns `409 immutable_conflict` at `src/open_brain/capture/http.py:134-143`. The incoming conflict is not recorded in quarantine, which violates `V0-CAPTURE-05`.

### Authenticated HTTP does not accept owner text without a URL

CLI text capture exists, but the authenticated HTTP share schema requires both `url` and `why` at `src/open_brain/capture/http.py:204-233`. That does not meet the contract wording that owner-authored text is accepted through both CLI and authenticated HTTP intake.

### The default profile exists only in documents

The contract says provider `none`, lexical retrieval, text/share connectors, and one daemon. Runtime configuration defaults to provider `local`, requires several roots, ships optional bridge scripts, and exposes 30 scheduled routes. `V0-CAPTURE-07` is therefore partial and `V0-GATE-11` is deviated even though the privacy primitives themselves are strong.

### Direct Markdown edits are not reconciled safely

The retriever reloads Markdown on every search, which gives freshness, but it accepts files without validating the required page schema and records no remediation for invalid edits. It does not implement the bounded reconciliation behavior required by `V0-DATA-05`.

### Remote access is not documented as an encrypted path

Loopback and bearer authentication are sound defaults. The HTTP server is plain `ThreadingHTTPServer` at `src/open_brain/services/http_server.py:281-298`. No encrypted tunnel or authenticated TLS-termination contract is implemented and verified, so `V0-SURFACE-03` is deviated.

## Option C implementation status

| Phase | Current status | Assessment |
|---|---|---|
| Phase 0: freeze boundary | PARTIAL | Package ownership is described, but the contract is unapproved, host/layout decisions are open, import rules are not enforced, and the default artifact has no exclusion manifest. |
| Phase 1: vertical slice | NOT PASSED | Useful pieces exist, including a deterministic provider and production composition, but no one-root, provider-none, capture-to-review/publication-to-retrieval test passes. |
| Phase 2: deepen modules in place | NOT STARTED | Known dependency leaks remain. This work should follow the vertical slice, not replace it. |
| Phase 3: appliance control plane | NOT STARTED | No init, one daemon, lifecycle ownership, complete UI, upgrade, or uninstall exists. |
| Phase 4: physical split | INTENTIONALLY DEFERRED | This is correct sequencing. Moving packages now would create churn without user value. |
| Phase 5: public alpha | BLOCKED | No clean-host artifacts or release gates pass. |

## Work to keep off the critical path

1. Do not physically split the package tree before the first-value slice passes.
2. Do not build the Prism/Obsidian plugin as part of v0. Markdown compatibility and read-only MCP are enough for now.
3. Do not add graph, vector, or multi-agent memory as a default. First prove the lexical fixture and source-aware retrieval contract.
4. Do not expand LifeOS, messaging, iMessage, YouTube, Git, finance, or calendar integrations. Treat them as later connector candidates.
5. Do not continue parity, cutover, stabilization, retirement, or 30-job replacement work on the public v0 critical path.

## Recommended path forward

1. **Freeze the contract, about 1 to 2 days.** Approve the five change-control points, layout version, host matrix, and owner-text behavior. Add requirement IDs to the implementation backlog.
2. **Prove the in-place slice, about 3 to 5 days.** Implement a disposable one-root profile, provider `none`, shared task interface, conflict quarantine, and one text/URL path through inbox, proposal/publication, and retrieval.
3. **Complete the product surfaces and appliance, about 2 to 4 weeks.** Add shared CLI/UI state, init, one daemon, internal schedules, lifecycle controls, doctor remediation, backup/restore, upgrade, and uninstall.
4. **Enforce Option C and package the product, about 1 to 2 weeks.** Add import/artifact gates, separate optional and legacy code, and produce native artifacts for the frozen host matrix.
5. **Release the alpha, about 3 to 5 days.** Run all 12 gates on clean hosts, publish the quickstart and support/security material, and bind checksums and evidence to one release.

The architecture plan's total estimate of roughly 4 to 8 weeks remains credible if expansion stays frozen. The next implementation milestone should stop at `V0-GATE-02` through `V0-GATE-07` on one disposable root.

## Verification performed

- `make verify`: passed Ruff, strict mypy, 2,683 tests, wheel build, and sdist build.
- Public CLI smoke test with a disposable synthetic configuration: capture exited 0 with `status=queued`; query exited 1 with `work_index_unavailable`; proposals returned an empty list; doctor reported missing schema/writer/backup state.
- Built-wheel inspection: the wheel includes CLI, services, integrations, migration, operations, parity, production, release, and development namespaces. This proves no artifact-exclusion firewall. It does not prove private data is present.
- Three independent read-only audits covered the product journey, install/operations, and Option C boundaries. A separate adversarial verifier challenged 15 priority findings; 14 were confirmed and one was narrowed.
- Durable Brain context was used only to confirm prior adopted principles: one canonical writer, files plus local SQLite, and conservative review-gated curation. Repository code and the v0 contract remained authoritative.

The private-denylist release audit, live daemon testing, clean-host installation, real reboot testing, and external repository settings were not run. None of those missing checks is treated as passed.
