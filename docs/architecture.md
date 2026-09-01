# Architecture

> This page describes the current implementation. The proposed self-hosted and hosted product-family target is documented in [`architecture/proposed-v0-system-architecture.md`](architecture/proposed-v0-system-architecture.md).

Open Brain is one retained monolith in one canonical repository. Phase 2 makes the runtime
boundary explicit without creating distributions: one `single-user-local` profile opens one
engine task set for one owner and one Brain root.

The package map uses these ownership boundaries:

- `core`: immutable values, policies, and ports; no filesystem, network, provider, CLI, HTTP, configuration, integration, or operations imports.
- `capture`, `ledger`, and `review`: application services that depend on typed ports.
- `engine`: the public task surface for Portable identities, generic capture, spaces, independent
  review, publication, recovery, lexical retrieval, and validate/export/clean-import/index-rebuild.
- `app`: profile and application composition. It owns the five representations and supplies only
  the capability each one needs: CLI, authenticated HTTP/share, local UI, scoped stdio MCP, and
  public-job sinks.
- `connector`: the internal allow-listed connector implementation boundary. `services/connectors.py`
  owns host meters, metadata receipts, and checkpoint evidence; connector code has capture-only
  authority.
- `storage`, `providers`, and `integrations`: retained adapters selected by composition. Adapters
  do not import CLI/HTTP handlers or one another.
- `operations`: doctor, scheduling, retention, backup, and recovery behavior.
- `dev`: public development and release-safety tools only.
- `legacy`: retained predecessor and operational compatibility files. The default Phase 2 path
  does not import them; physical removal or distribution movement is deferred.

Private deployment configuration contains values and rendered manifests, never patched or copied application source.

The file-level classification is authoritative for this retained monolith: every runtime file has
one owner, such as `engine`, `app`, `connector`, `legacy`, or `workspace`. A mixed top-level
package may remain in place during Phase 2, but no file is unclassified or assigned to multiple
owners.

The app-owned `profile` module compiles one `single-user-local` Brain root into an
engine-owned context. The engine does not import profile, CLI, UI, service, migration,
or parity code.

`services/phase1_application.py` is the default app composition root, and
`services/phase1_entrypoints.py` owns the installed CLI, HTTP, and MCP processes.
`services/application.py` and `services/entrypoints.py` retain predecessor and scheduled
compatibility behind the legacy boundary; package metadata does not point a default process at
either module.

Every engine mutation and recovery pass holds the root-confined shared-writer lease across
its SQLite reservation and portable file transitions. Reads remain available outside that
lease and observe only durable stages or atomically replaced files.

`EngineTaskSet` is the composition object, not a representation capability. The Phase 1 UI gets
the narrower Phase 1 task set, each CLI adapter gets its one task protocol, HTTP gets capture,
MCP gets scoped retrieval plus app feedback, and public jobs get a `PublicJobCaptureSink`.
All of them share the underlying task identities created for the same root.

The implemented application layers are:

- `capture`: durable intake, authenticated share handling, pinned egress, normalized extraction, versioned redaction, and recovery-safe raw/event/distillation orchestration.
- `providers`: retained legacy provider composition. The Phase 2 single-user profile uses provider
  `none`; provider configuration is not loaded by the default local journey.
- `ledger`: taxonomy-bound scan/stage records, opaque sanitized leaves, trusted citations, a metadata-only inflight journal, independently read-back-verified publication manifests, archive-first slimming, and atomically persisted structured synthesis outside writer locks.
- `review`: closed reference/hold/review-only routing, owner-only terminal decisions, atomic approval/outbox persistence, opaque capture references, receipt-verified owner-output delivery, and predecessor-parity target edit/archive maintenance.

Composition starts with no listener, scheduler, provider, connector, or network operation. The
default application has no connector capability. The retained synthetic `JOB-029` proof is
composed explicitly with an absolute private YouTube configuration reference and egress authority.
It uses the internal connector contract, a capture-only public-job identity, and host-owned
evidence to bind accepted capture receipts to checkpoint advancement.

Public task results are projections produced after storage and ranking. They retain opaque IDs,
bounded provenance, canonical-state visibility, and useful titles/excerpts while excluding raw or
encoded protected references, absolute paths, credentials, storage-derived slugs and paths, and
reversible source-reference digests. This projection affects results only; Portable/source bytes
remain exact.

Phase 3 owns the appliance lifecycle: initialization, one supervised daemon, internal scheduling,
launchd/systemd integration, backup/restore, upgrade, and uninstall orchestration. Phase 4 owns
the physical distributions and `packages/` split, isolated connector workers, the public Connector
SDK and signing, and native artifact/bundler work. The retained monolith is the Phase 2 boundary.
