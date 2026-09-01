# Open Brain

**GitHub:** `vora-technology/open-brain`
**Stack:** Python 3.12–3.14, standard-library engine contracts, filesystem/SQLite/Markdown persistence, typed app and connector boundaries

## Quick reference

| Property | Value |
|---|---|
| Local development | `OPEN_BRAIN_ROOT=$HOME/open-brain-data uv run open-brain inbox list --json`; one private Brain root, no bound service port |
| Staging | TBD |
| Production | Python CLI/service with generic launchd/systemd templates; Docker deferred |

## Architecture

| Layer | Responsibility |
|---|---|
| `profile` | Compile one owner-only `single-user-local` Brain root, stable portable identity, provider-none mode, and optional starter spaces |
| `engine` | Capture, inbox/space, review, publication, recovery, retrieval, and Portable validate/export/clean-import/rebuild task surfaces |
| `services/phase1_application` | Compose one engine task set and inject bounded capabilities into each default representation and public job |
| `core` | Immutable capture/privacy values, deterministic IDs, intent policy, ports, provider/executor guards |
| `review` | Terminal review state machine and owner-authored approved-intent records |
| `storage` | Root-confined atomic raw/Markdown persistence and checksummed SQLite migrations |
| `events` | Idempotent SQLite event stream over redacted typed records |
| `config` | Explicit environment/TOML/default precedence with local-only safe defaults |
| `capture` | Durable intake, authenticated share parsing, pinned egress, bounded extractors, versioned redaction, and recovery-safe orchestration |
| `providers` | Retained legacy provider composition; the Phase 2 single-user profile uses provider `none` |
| `services/connectors` | Internal allow-listed connector host, host evidence, bounded receipts, and checkpoint binding |
| `legacy` | Retained predecessor and operational compatibility modules; never imported by the default Phase 2 path |
| `ledger` | Receipt-bound scan/stage, sanitized merge, durable publication, archive-first slim, and lock-guarded synthesis |
| `integrations/phase1_ui` | Bearer-authenticated, framework-neutral Phase 1 HTML/API handler over engine tasks |

Domain contracts do not import concrete adapters, CLI, HTTP, configuration, integrations, or operations. Private content and rendered host configuration stay outside this repository.

## Key files

| File | Purpose |
|---|---|
| `pyproject.toml` | Packaging, supported Python versions, tools, and extras |
| `src/open_brain/profile.py` | Single-user local Brain-root compiler and stable owner identity |
| `src/open_brain/engine/` | Public task contracts, local engine implementation, Portable operations, and public-result projection |
| `src/open_brain/services/phase1_application.py` | Default single-user app composition and bounded representation capabilities |
| `src/open_brain/services/phase1_entrypoints.py` | Installed CLI, HTTP, and MCP process entry points |
| `src/open_brain/services/connectors.py` | Internal connector contract and host-owned evidence boundary |
| `src/open_brain/production/youtube_poll.py` | Explicit, capture-only `JOB-029` reference proof |
| `src/open_brain/cli/main.py` | Retained legacy parser and scheduled-route shell |
| `src/open_brain/cli/phase1.py` | Thin Phase 1 CLI adapters over engine tasks |
| `src/open_brain/integrations/phase1_ui.py` | Authenticated local UI request handler |
| `src/open_brain/core/models.py` | Capture provenance and immutable privacy contracts |
| `src/open_brain/core/policy.py` | Closed intent routing and provider/executor guards |
| `src/open_brain/core/ports.py` | Private raw and redacted work-tier port records |
| `src/open_brain/review/models.py` | Review state machine and approval audit binding |
| `src/open_brain/storage/` | Atomic filesystem, frontmatter, and SQLite foundations |
| `src/open_brain/events/store.py` | Idempotent SQLite event adapter |
| `src/open_brain/config.py` | Immutable local-first configuration |
| `src/open_brain/capture/queue.py` | Process-safe durable capture recovery queue |
| `src/open_brain/capture/http.py` | Framework-neutral authenticated share boundary |
| `src/open_brain/capture/egress.py` | DNS/redirect/cookie-validated pinned egress policy |
| `src/open_brain/capture/service.py` | Raw-to-hold/event/distillation orchestration |
| `src/open_brain/capture/redaction.py` | Approved deterministic work-tier redaction policy |
| `src/open_brain/providers/base.py` | One-provider selection and fail-closed cloud boundary |
| `src/open_brain/providers/local.py` | Injected local text-model adapter |
| `src/open_brain/ledger/scan.py` | Work-item/event compound binding and trusted taxonomy routing |
| `src/open_brain/ledger/service.py` | Deterministic two-document ledger preparation and apply |
| `src/open_brain/ledger/store.py` | Metadata-only journal, publication manifest, and durable slim state |
| `src/open_brain/ledger/synthesis.py` | Strict structured synthesis outside authoritative locks |
| `src/open_brain/ledger/synthesis_store.py` | Atomic evaluating synthesis page/row/link-back persistence |
| `src/open_brain/review/service.py` | Review outbox and receipt-verified owner-output delivery |
| `src/open_brain/review/routing.py` | Closed reference/hold/review-only Phase 4 intent orchestration |
| `src/open_brain/dev/release_audit.py` | Public-tree and release-artifact safety audit |
| `docs/architecture.md` | Package and dependency boundaries |
| `docs/privacy-model.md` | Privacy, public-result projection, connector evidence, and provider-routing invariants |

## Common commands

```bash
uv sync --group dev
OPEN_BRAIN_ROOT=$HOME/open-brain-data uv run open-brain inbox list --json
make lint
make typecheck
make test
make build
PRIVATE_DENYLIST=/path/to/private-denylist.txt make audit
```

## Environment variables

| Variable | Purpose |
|---|---|
| `OPEN_BRAIN_ROOT` | One absolute private Brain root for the Phase 2 `single-user-local` profile; takes precedence over retained-root composition |
| `OPEN_BRAIN_CONFIG` | Absolute path to an untracked TOML file for retained legacy/application configuration |
| `OPEN_BRAIN_STATE_ROOT`, `OPEN_BRAIN_WORK_ROOT`, `OPEN_BRAIN_PERSONAL_ROOT`, `OPEN_BRAIN_CAPTURE_ROOT`, `OPEN_BRAIN_SAVED_CONTENT_ROOT`, `OPEN_BRAIN_BACKUP_ROOT` | Retained-root configuration; not a second Phase 2 profile |
| `OPEN_BRAIN_PROVIDER`, `OPEN_BRAIN_CLOUD_ENABLED`, `OPEN_BRAIN_EGRESS_ENABLED` | Retained composition settings; the single-user profile fixes provider `none`, and egress is off unless explicitly enabled for a connector |
| `OPEN_BRAIN_PROVIDER_CONFIG` | Absolute private provider configuration reference for retained scheduled composition |
| `OPEN_BRAIN_JOB_ID` | Retained legacy-facade route selector; synthetic connector proof uses `JOB-029` |
| `OPEN_BRAIN_YOUTUBE_CONFIG` | Absolute private YouTube connector configuration reference; without it, the default connector profile is empty |
| `OPEN_BRAIN_MCP_ALLOWED_SPACE_IDS` | JSON array of caller-allowed opaque space IDs; `[]` supplies an empty MCP scope |
| `OPEN_BRAIN_UI_BIND`, `OPEN_BRAIN_UI_PORT`, `OPEN_BRAIN_UI_ALLOW_PRIVATE` | Bounded local HTTP bind settings; defaults are `127.0.0.1`, `8788`, and `false` |

The installed CLI reads `OPEN_BRAIN_ROOT` at its Phase 1 process boundary and does not import the
retained legacy scheduler facade. MCP receives only retrieval plus the explicit space allow-list
and metadata feedback; it does not receive profile, portability, or writer authority. Other
composition roots must pass an explicit environment mapping. Core/config tests intentionally
ignore ambient process variables.

## Deployment

No deployment exists. Generic launchd/systemd templates arrive only after production transport, composition, and service contracts stabilize.

## Gotchas

**A redaction receipt does not authorize a sink.** Work-tier event and Markdown adapters must reject secret, unknown, classification-failure, explicit-local-only, and unconfirmed personal decisions before any I/O.

**Approval events are bound to one review.** Deserialization must match event review IDs and the exact deterministic approved record; otherwise a valid approval can be spliced onto another capture.

**SQLite paths are root capabilities, not arbitrary absolute paths.** Traverse parent directories without following symlinks and keep database, WAL, and SHM files at `0600`.

**Private raw storage preserves canonical capture bytes.** Redacting `shared_text` there changes the capture identity; redaction applies to typed work-tier event/Markdown records instead.

**Secret-shaped test fixtures can fail the release audit.** Assemble detector canaries at runtime instead of committing assignment-shaped literals.

**Closed mode means unavailable adapters are unreachable.** Do not accept arbitrary staged executors or redactors while claiming their production gates are closed.

**Event-boundary recovery resumes from the durable event.** Re-extracting mutable content after an event append can create a second event with different bytes.

**Media limits must be enforced, not described.** On unsupported platforms the bounded runner returns `tool_unavailable`; command metadata alone is not isolation.

**Cloud authority does not prove prompt safety.** Scan the final cloud prompt before adapter construction or credential resolution; a finding must produce zero cloud-side effects.

**Frozen ledger values remain untrusted at boundaries.** Call `validate()` at merge, render, apply, and synthesis boundaries because Python objects can be forged without their constructor.

**Atomic files do not make an atomic document set.** Expose ledger documents only through the durable applied manifest; partial physical writes remain unofficial until reconciliation finalizes every digest.

**A writer cannot certify its own persistence.** Verify ledger and slim artifacts through separate approved root-confined readers; receipt type, disposition, ID, digest, and exact bytes must all match before durable state advances.

**Slim and synthesis safety evidence is mandatory and durable.** Derive slim authority from a store-issued row identity. Synthesis requires persisted citation IDs plus deterministic destinations, the approved SQLite store, typed durable read-back, and an authoritative lock probe.

**Public results are projections.** Apply the engine-owned projection after storage and ranking. Preserve useful text while replacing exact protected literals, source-reference digests, absolute paths, and credential assignments with bounded markers. Do not duplicate redaction in each renderer or change Portable/source bytes.

**Review receipts bind canonical state.** Review creation must bind the initial aggregate digest; delivery emits only owner text plus the opaque capture reference and verifies output ID, canonical digest, and disposition before closing the outbox.

**One Brain root has one writer.** Every mutating engine task and recovery pass acquires the root-confined shared-writer lease. Treat `LockBusyError` as a retryable ownership conflict; never bypass it with direct store calls.

**Delivery IDs are idempotency keys, not labels.** Reuse one only for the exact same mutation. A conflicting payload is rejected and writes metadata-only quarantine evidence.

**Space slugs are stable storage keys.** Renaming a space changes its display name but does not move the directory or change its ID; routing and references remain stable.

> Full registry: `docs/engineering/gotchas/README.md`.

## Available skills

No project-specific skill exists yet.
