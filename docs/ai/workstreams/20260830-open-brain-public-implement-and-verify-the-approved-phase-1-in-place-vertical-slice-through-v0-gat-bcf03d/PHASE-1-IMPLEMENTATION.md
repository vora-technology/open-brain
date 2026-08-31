# Phase 1 implementation contract

## Objective

Prove the approved in-place, no-model vertical slice against one disposable Brain root. The implementation must pass `V0-GATE-02` through `V0-GATE-07` and `V0-GATE-13` without moving packages or pulling legacy, source-specific connector, graph, vector, or multi-agent product behavior into the default path.

## Authority

1. `docs/v0-product-contract.md`
2. `docs/plans/option-c-architecture.md`, Phase 1
3. Portable Brain v1 schemas and Phase 0 decisions
4. Current repository invariants and `CLAUDE.md`

The pre-implementation document review found two P1 issues outside this milestone: inconsistent Phase 2/4 package-split wording and an undefined Phase 3 owner-authentication mechanism. Phase 1 does not resolve either issue silently.

## Implementation boundary

Add an in-place `open_brain.engine` package. Its public surface is grouped into four concrete task facades, not a generic `execute()` bus:

- Capture: accept the four portable payload families, inspect capture state, and distinguish quick capture from explicit canonical-note publication.
- Inbox and spaces: list pending or unassigned captures, create and rename user-defined spaces, and route a capture without changing its identity.
- Review: create zero-to-many sibling proposals and apply one receipt-bound terminal decision to each proposal.
- Retrieval: search canonical pages and eligible source records lexically, across all spaces or within one space, with type, trust, provenance, and match explanation.

`single-user-local` composition lives in the current application package and creates one compatible Brain root, stable random tenant/owner/role identities, provider mode `none`, and optional ordinary starter spaces.

Generic durable intake keeps space optional. Explicit canonical-note publication requires an existing space because Portable Brain v1 canonical-page frontmatter requires a stable `space_id`; omitting it is rejected before acceptance, while quick capture of the same text remains the no-space inbox path.

## Durable sequence

Every accepted operation first reserves its random stable ID and immutable request bytes in the root-confined SQLite state database. Portable file writes then use the existing root-confined atomic filesystem primitives. The state machine records progress after each file transition. Recovery replays incomplete transitions from the persisted request, and duplicate delivery reuses the reserved identity. Conflicting bytes for one delivery identity are quarantined.

One root-confined shared-writer lease spans each mutating task and recovery pass, including both SQLite and portable file transitions. A competing process fails closed and may retry after the current writer releases the kernel-authoritative lease.

Required fault points cover capture reservation, source persistence, inbox or canonical routing, proposal persistence, decision persistence, publication persistence, space routing, and search projection refresh. Tests reopen the engine after each injected failure and prove one terminal artifact per identity.

## Surface boundary

CLI and local UI adapters receive only the public task facades. They may map typed results to JSON, text, or HTML, but cannot import the local SQLite or Markdown implementation. Both surfaces must report the same capture, space, proposal, and terminal decision IDs.

The Phase 1 UI is an authenticated, framework-neutral handler. Listener lifecycle and the final owner credential bootstrap remain Phase 3 work.

## Verification

The milestone is complete only when:

- a focused Phase 1 integration suite proves every listed gate against one disposable root;
- provider mode `none` constructs no local or cloud model adapter and leaves enrichment inspectably pending;
- a selected injected local provider can fail, leave the capture pending, and later retry without duplicate provider output, proposal, capture, or page;
- exact, lexical, space-filtered, typed-source, and freshness-after-edit retrieval fixtures pass with trust and provenance;
- restart and duplicate-delivery fixtures cover every declared durable transition;
- CLI and UI call the same task facades and observe identical stable IDs;
- `make verify`, `git diff --check`, the architecture import tests, and the release artifact policy pass.

## Stop condition

Stop and return to product review if the slice requires broad legacy work, source-specific connectors, graph or vector infrastructure, package movement, a generic plugin SDK, hosted control-plane behavior, or more than one canonical writer.
