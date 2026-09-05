# v0 release-boundary evidence

Status: accepted Phase 0 evidence

Authority: [v0 product contract](v0-product-contract.md), version 0.5, revised
2026-09-04. The [Option C architecture plan](plans/option-c-architecture.md) and
[proposed v0 system architecture](architecture/proposed-v0-system-architecture.md)
interpret that contract; they do not replace it.

## Change control

The approved v0 outcomes are fixed: `single-user-local`, provider mode `none`, one
daemon with internal schedules, the four payload families with optional connectors,
and the Portable Brain foundation and release gates. Implementation work may refine
details, but it cannot weaken those outcomes without a new product decision recorded
in the product contract.

An unlisted feature, platform, payload, connector promise, hosted behavior, or
release-artifact change goes on the expansion backlog. It is not implemented,
advertised, or used to reinterpret a v0 exit gate until the owner accepts a contract
change. An accepted change updates the contract and names the required replacement
evidence before implementation begins.

The concrete backlog is maintained in [`docs/v0-expansion-backlog.md`](v0-expansion-backlog.md).
Anything not named in the approved contract or that backlog receives a new `EXP-*` row before
design or implementation starts.

Phase 0 does not move packages. If a release-boundary rule needs package movement to
be true, record that as Phase 1 work instead of weakening the rule or adding a broad
exception.

## Current namespace import evidence

`docs/v0-package-classification.json` classifies every immediate
`src/open_brain/` package directory and records its target owner, current mixed scope,
and extraction action. `tests/security/test_architecture_imports.py` AST-scans real
Python imports in those directories, verifies all current namespace endpoints have a
classification, and enforces the current safe engine scope: `core` cannot import an
app, connector, hosted, or legacy package.

This narrow scope is intentional evidence, not a claim that the whole current graph
already matches the target architecture. `capture`, `integrations`, `operations`,
`production`, `providers`, `release`, and `storage` remain explicitly mixed; `migrate`
and `parity` remain explicitly legacy. Their recorded Phase 1 extraction work is the
path to broader import enforcement.

The checker is static AST evidence for direct Python imports. Dynamic import targets
remain outside this Phase 0 proof and require review when the relevant package is
extracted.
