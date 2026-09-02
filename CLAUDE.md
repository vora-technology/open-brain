# Open Brain

**GitHub:** `vora-technology/open-brain`
**Stack:** Python 3.12–3.14, Hatch/uv workspace packages, filesystem/SQLite/Markdown persistence

## Quick reference

| Action | Command or state |
|---|---|
| Install | `uv sync --frozen --group dev` |
| Local CLI | `OPEN_BRAIN_ROOT=$HOME/open-brain-data uv run open-brain inbox list --json` |
| Full verification | `make verify` |
| Phase 4 contracts | `make phase4-contracts` |
| Python artifacts | `make verify-artifacts` builds and audits engine+app wheels/sdists |
| Release state | Engine/app artifacts are isolated and unpublished; native artifacts and deployment are pending |

## Architecture

| Boundary | Responsibility |
|---|---|
| `packages/engine/src/open_brain_engine` | App-independent domain engine, public task contracts, persistence, Portable schemas, and conformance data |
| `packages/app/src/open_brain` | Installed CLI/MCP entry points, appliance daemon, HTTP/UI, app configuration, and engine composition |
| `packages/connectors` | Connector distribution skeleton; not a default app dependency |
| `packages/legacy` | Legacy distribution skeleton; not a default app or engine dependency |
| `src/open_brain` | Classified connector, legacy, and workspace remainder awaiting later Phase 4 waves |
| `tools/phase4` | Canonical move-manifest validation and isolated built-artifact acceptance harnesses |
| `docs/v0-package-classification.json` | Source of truth for ownership, API status, movement, imports, tests, resources, and artifact membership |
| `release/v0-artifact-policy.json` | One unpublished release contract keyed by Python distribution and artifact kind |

The engine cannot import app, connector, legacy, or workspace modules. The app depends on exactly
`open-brain-engine==0.1.0` and may import only engine modules marked public in the canonical
manifest. Mutating installed CLI/UI requests go through the appliance daemon; MCP receives only
space-scoped read capabilities and metadata feedback.

## Key files

| File | Purpose |
|---|---|
| `pyproject.toml` | Workspace membership and root test/lint/typecheck configuration |
| `packages/engine/pyproject.toml` | Isolated `open-brain-engine` package and artifact configuration |
| `packages/app/pyproject.toml` | Isolated `open-brain` package, exact engine dependency, and installed scripts |
| `packages/engine/src/open_brain_engine/engine/__init__.py` | Explicit public engine facade |
| `packages/engine/src/open_brain_engine/portable/` | Portable schemas, validator, and conformance resources |
| `packages/app/src/open_brain/profile.py` | Single-user local Brain-root compiler and stable owner identity |
| `packages/app/src/open_brain/services/appliance_entrypoints.py` | Installed `open-brain` and `open-brain-mcp` callables |
| `packages/app/src/open_brain/services/appliance_daemon.py` | Sole installed mutation authority and control transport |
| `packages/app/src/open_brain/services/appliance_supervisors.py` | Source-checkout and installed-mode supervisor rendering |
| `packages/app/src/open_brain/resources/supervisors/` | Packaged launchd/systemd templates loaded with `importlib.resources` |
| `packages/app/src/open_brain/integrations/phase1_ui.py` | Authenticated local UI/API handler over app task capabilities |
| `packages/app/tests/contract/test_v0_wheel_gates.py` | Explicit wheel-only `V0-GATE-07` and `V0-GATE-13` journeys |
| `tools/phase4/acceptance_harness.py` | Wheel build/install isolation, membership, import, and installed-test contracts |
| `src/open_brain/dev/artifact_policy.py` | Multi-distribution wheel/sdist membership verifier |
| `docs/architecture.md` | Package and dependency boundaries |
| `docs/privacy-model.md` | Privacy, public-result projection, connector evidence, and provider-routing invariants |

## Common commands

```bash
uv sync --frozen --group dev
make lint
make typecheck
make test
make phase4-contracts
make verify-artifacts
make verify
PRIVATE_DENYLIST=/absolute/path/to/private-denylist.txt make audit
```

Run isolated app acceptance directly with:

```bash
uv run pytest -q tests/phase4/test_app_distribution.py
```

## Environment variables

| Variable | Purpose |
|---|---|
| `OPEN_BRAIN_ROOT` | One absolute private Brain root; required by installed stateful commands |
| `OPEN_BRAIN_CONFIG` | Absolute path to an untracked TOML application configuration |
| `OPEN_BRAIN_STATE_ROOT`, `OPEN_BRAIN_WORK_ROOT`, `OPEN_BRAIN_PERSONAL_ROOT`, `OPEN_BRAIN_CAPTURE_ROOT`, `OPEN_BRAIN_SAVED_CONTENT_ROOT`, `OPEN_BRAIN_BACKUP_ROOT` | Retained-root configuration; not a second single-user profile |
| `OPEN_BRAIN_PROVIDER`, `OPEN_BRAIN_CLOUD_ENABLED`, `OPEN_BRAIN_EGRESS_ENABLED` | Retained composition settings; the default single-user profile is provider-none and egress-off |
| `OPEN_BRAIN_PROVIDER_CONFIG` | Absolute private provider configuration reference |
| `OPEN_BRAIN_JOB_ID` | Retained legacy-facade route selector |
| `OPEN_BRAIN_YOUTUBE_CONFIG` | Absolute private YouTube connector configuration; absence keeps the default connector profile empty |
| `OPEN_BRAIN_MCP_ALLOWED_SPACE_IDS` | JSON array of caller-allowed opaque space IDs; `[]` creates an empty MCP scope |
| `OPEN_BRAIN_UI_BIND`, `OPEN_BRAIN_UI_PORT`, `OPEN_BRAIN_UI_ALLOW_PRIVATE` | HTTP bind settings; defaults are `127.0.0.1`, `8788`, and `false` |
| `OPEN_BRAIN_UI_EXTERNAL_TLS_TERMINATION`, `OPEN_BRAIN_UI_EXTERNAL_ORIGIN` | Required external encryption/origin declarations for an explicitly allowed private-network bind |

Core/config tests intentionally ignore ambient process variables. Other composition roots must pass
an explicit environment mapping.

## Deployment

No public deployment or package publication exists. The app wheel contains generic launchd/systemd
templates for installed-mode rendering without a checkout `PYTHONPATH`. Phase 4 native bundling,
signing, clean-host lifecycle proof, and production cutover remain separate gated work.

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

**Artifact isolation requires `uv build --no-sources`.** Workspace source substitution can make an invalid package appear healthy; installed acceptance must use only the built app and engine wheels.

**App tests cannot read checkout-relative engine fixtures or source.** Load packaged schemas, conformance data, and module source through installed package resources/paths so wheel-only tests remain real.

**Artifact uniqueness is per distribution and kind.** Two wheels are expected in P4-W2; reject duplicates by `(app|engine, wheel|sdist)`, not by kind alone.

**Supervisor rendering has two explicit modes.** Pass a checkout root only for source execution. Installed mode loads packaged templates and must not emit `PYTHONPATH` or a checkout working directory.

**The app cannot reach engine internals by convenience import.** Add an engine module to the canonical public API deliberately before importing it from app code; the wheel scanner rejects private imports.

> Full registry: `docs/engineering/gotchas/README.md`.
