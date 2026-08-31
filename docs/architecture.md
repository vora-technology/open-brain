# Architecture

> This page describes the current implementation. The proposed self-hosted and hosted product-family target is documented in [`architecture/proposed-v0-system-architecture.md`](architecture/proposed-v0-system-architecture.md).

Open Brain is one ports-and-adapters monolith in one canonical repository.

The package map uses these ownership boundaries:

- `core`: immutable values, policies, and ports; no filesystem, network, provider, CLI, HTTP, configuration, integration, or operations imports.
- `capture`, `ledger`, and `review`: application services that depend on typed ports.
- `storage`, `providers`, and `integrations`: adapters selected by the composition root. Adapters do not import CLI/HTTP handlers or one another.
- `operations`: doctor, scheduling, retention, backup, and recovery behavior.
- `dev`: public development and release-safety tools only.

Private deployment configuration contains values and rendered manifests, never patched or copied application source.

The implemented application layers are:

- `capture`: durable intake, authenticated share handling, pinned egress, normalized extraction, versioned redaction, and recovery-safe raw/event/distillation orchestration.
- `providers`: exactly one selected local or optional cloud provider. JOB-010 loads its settings from an owner-only private file; local endpoints must be IP-literal loopback, while cloud construction requires both cloud and egress authority and resolves the named credential lazily only after immutable authority and content-secret checks pass.
- `ledger`: taxonomy-bound scan/stage records, opaque sanitized leaves, trusted citations, a metadata-only inflight journal, independently read-back-verified publication manifests, archive-first slimming, and atomically persisted structured synthesis outside writer locks.
- `review`: closed reference/hold/review-only routing, owner-only terminal decisions, atomic approval/outbox persistence, opaque capture references, receipt-verified owner-output delivery, and predecessor-parity target edit/archive maintenance.

Composition and production adapters remain separate. The production package now provides an
opt-in DNS-pinned HTTP transport, immutable content-addressed derived-asset storage, and a
Linux/bubblewrap staged model runtime with empty environment, no network, resource limits, and
bounded output. Service construction starts no listener or provider; the explicit process entry
point owns that transition. LifeOS and messaging runtimes persist only root-confined state;
calendar writes require an exact approval, and messaging actions stop at canonical review
proposals. The production scheduler binds all 30 catalog rows, preserves one writer identity, and
records replay-safe empty batches only for routes whose validated input batch is empty.
Approved curation, repository sync, index, backup, and NOW use their concrete effect-specific
production and recovery boundaries.
