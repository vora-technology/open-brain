# Open Brain

**GitHub:** planned `cbolden15/open-brain`; no remote yet
**Stack:** Python 3.12–3.14, standard-library domain contracts, capture/provider/ledger/review services, filesystem/SQLite/Markdown adapters

## Quick reference

| Property | Value |
|---|---|
| Local development | `uv run open-brain --version`; no service port yet |
| Staging | TBD |
| Production | Python CLI/service with generic launchd/systemd templates; Docker deferred |

## Architecture

| Layer | Responsibility |
|---|---|
| `core` | Immutable capture/privacy values, deterministic IDs, intent policy, ports, provider/executor guards |
| `review` | Terminal review state machine and owner-authored approved-intent records |
| `storage` | Root-confined atomic raw/Markdown persistence and checksummed SQLite migrations |
| `events` | Idempotent SQLite event stream over redacted typed records |
| `config` | Explicit environment/TOML/default precedence with local-only safe defaults |
| `capture` | Durable intake, authenticated share parsing, pinned egress, bounded extractors, versioned redaction, and recovery-safe orchestration |
| `providers` | One selected local/cloud provider, lazy optional imports, and pre-construction privacy/content gates |
| `ledger` | Receipt-bound scan/stage, sanitized merge, durable publication, archive-first slim, and lock-guarded synthesis |

Domain contracts do not import concrete adapters, CLI, HTTP, configuration, integrations, or operations. Private content and rendered host configuration stay outside this repository.

## Key files

| File | Purpose |
|---|---|
| `pyproject.toml` | Packaging, supported Python versions, tools, and extras |
| `src/open_brain/cli/main.py` | Public CLI shell |
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
| `docs/privacy-model.md` | Privacy and provider-routing invariants |

## Common commands

```bash
uv sync --group dev
make lint
make typecheck
make test
make build
PRIVATE_DENYLIST=/path/to/private-denylist.txt make audit
```

## Environment variables

| Variable | Purpose |
|---|---|
| `OPEN_BRAIN_CONFIG` | Absolute path to an untracked TOML file |
| `OPEN_BRAIN_STATE_ROOT` | Required absolute private state root |
| `OPEN_BRAIN_CONTENT_ROOT` | Required absolute private content root |
| `OPEN_BRAIN_PROVIDER` | Provider name; safe default is `local` |
| `OPEN_BRAIN_CLOUD_ENABLED` | Exact `true`/`false`; safe default is `false` |
| `OPEN_BRAIN_EGRESS_ENABLED` | Exact `true`/`false`; safe default is `false` |

Composition roots must pass an explicit environment mapping. Core/config tests intentionally ignore ambient process variables.

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

**Review receipts bind canonical state.** Review creation must bind the initial aggregate digest; delivery emits only owner text plus the opaque capture reference and verifies output ID, canonical digest, and disposition before closing the outbox.

> Full registry: `docs/engineering/gotchas/README.md`.

## Available skills

No project-specific skill exists yet.
