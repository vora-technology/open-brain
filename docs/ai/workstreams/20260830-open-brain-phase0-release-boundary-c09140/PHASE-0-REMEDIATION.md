# Phase 0 remediation

The adversarial gate returned `NOT_READY`. Remediation is split so one writer owns the Portable Brain contract while the coordinator owns shared release and orchestration files.

## Portable writer scope

The writer repairs schemas, conformance fixtures, strict Portable serialization, and their focused tests.

Required corrections:

1. Preserve legacy `canonical_json_bytes` behavior, including float callers. Add a separate strict Portable v1 serializer that rejects floats, non-string keys, and NFC key collisions.
2. Use snake_case for structured JSON and Markdown frontmatter. This matches existing canonical records and avoids a mixed naming contract.
3. Make the capture envelope lossless: optional intent and reason, exact original supplied bytes or blob binding, complete privacy decision, separate trust metadata, immutable provenance, optional space, inline or batch payload binding, and append-only receipt references for later routing.
4. Make review history sufficient to continue elsewhere: proposed content and digest, evidence and sibling context, expected receipt/state binding, edited terminal decisions, publication byte/path binding, approved external-action request and result binding, and canonical-page privacy.
5. Make manifests root-confined and compatible: export ID, layout and schema versions, contract version, compatibility range, schema catalog digest, normalized relative paths, no traversal or absolute paths, symlink rejection, sorted unique entries, exact checksums, and operational-state exclusion.
6. Accept canonical values below one while enforcing at most 128 total decimal digits. Bind event and measurement row IDs and `supersedes` to the same payload family.
7. Remove checked-in `.open-brain` operational files. Tests create operational state at runtime to prove export exclusion.
8. Expand positive and negative fixtures so the tests cannot pass with any missing required field or cross-family binding.

## Coordinator scope

The coordinator owns `.gitignore`, package classification, import scanning, expansion backlog, current-record characterization, artifact manifests/build integration, release-audit fixture handling, history-audit performance and execution, Makefile/workflow changes, workstream state, and final full verification.
