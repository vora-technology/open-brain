# Portable Brain v1 implementation decisions

These rules close the representation choices left by the approved product contract. They do not change the fixed Brain-root layout, authority model, payload families, or host matrix.

## Stable IDs

Portable v1 IDs are a type prefix followed by a canonical lowercase UUIDv4. The UUID includes hyphens and must have the UUIDv4 version and RFC variant bits. Schemas use these prefixes where the record type exists: `tenant_`, `actor_`, `role_`, `role_claim_`, `space_`, `page_`, `capture_`, `batch_`, `event_`, `measurement_`, `proposal_`, `decision_`, `publication_`, `action_`, and `export_`.

An ID is generated once with the operating system CSPRNG, persisted, and preserved across replay, export, import, and mutable display-name or path changes. It is not derived from a clock, name, path, payload, or directory slug. Blob addresses remain lowercase SHA-256 digests. Existing content-derived legacy IDs are not silently treated as Portable v1 IDs.

## Measurements

Measurement values use canonical fixed-point decimal strings, never JSON numbers. A value has at most 128 digits and at most 130 total characters. It has no leading plus, exponent, leading integer zero, trailing fractional zero, nonfinite value, or negative zero. Plain `0` is the only zero representation. Units and dimensions remain separate fields. The original supplied payload remains available in its source record.

## Role claims

A security-sensitive record carries an immutable role-claim snapshot containing `role_claim_id`, `tenant_id`, `actor_id`, `role_id`, and a sorted unique capability list. The repeated tenant and actor IDs must match the enclosing record. Credentials, tokens, mutable role labels, and hosted control-plane metadata are forbidden.

## Schema and serialization policy

- Schemas use JSON Schema Draft 2020-12, immutable v1 URN identifiers, local-only references, required fields, and closed objects.
- Test-time conformance uses `jsonschema.Draft202012Validator`. Runtime validation remains standard-library typed validation plus exact canonical-byte checks.
- Canonical JSON uses UTF-8, NFC strings and keys, sorted object keys, no insignificant whitespace, and no floats or non-string object keys. A normalized-key collision is rejected instead of being collapsed.
- An individual `.json` record contains only its canonical JSON bytes. It has no trailing newline.
- Every `.jsonl` row contains one canonical JSON record followed by LF. A complete JSONL file also ends in LF.
- Capability snapshots are sorted and unique. JSON Schema enforces uniqueness; conformance tests enforce ordering and cross-field bindings.
- Import, export, schema validation, manifest checksum validation, and exact-byte round trips fail closed.

## Required evidence

The writer must provide positive and negative schema fixtures, canonical JSON fixtures for every payload and history family, event and measurement JSONL batches with append-only corrections, a complete synthetic Brain root, content-addressed blob evidence, SHA-256 manifest checksums, stable-space rename evidence, and a clean-root exact-byte round trip that excludes `.open-brain` operational state.
