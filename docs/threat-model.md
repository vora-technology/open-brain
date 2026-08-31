# Threat model

Primary threats include credential disclosure, private-content disclosure, path traversal, SSRF, prompt-injected filesystem access, unredacted logs, unauthorized cloud routing, review-gate bypass, duplicate writers, and unsafe migration or rollback.

Security controls are contract tests and release gates, not documentation claims. Public fixtures are synthetic. Unknown classifications fail closed. Deployment templates cannot contain private host values.

Multi-document ledger writes become visible only through an applied durable manifest that binds the complete document set and sink digests. IDs, dispositions, deterministic rendered-byte digests, and exact read-back through a separate approved root-confined reader must all verify first. Slimming uses the same split writer/reader rule for its transcript-free successor, derives authority from the durable ledger row, and records archive and successor digests before `slimmed`. Model synthesis requires three persisted citation IDs with deterministic destinations, the approved SQLite store with typed durable confirmation, an authoritative lock probe, and no held transaction or writer lock. Valid output persists its evaluating row, page, and link-backs in one SQLite transaction.

Review creation and delivery treat receipts as untrusted. Creation binds the canonical initial aggregate digest. Delivery binds the expected output ID, canonical digest, and created/duplicate disposition before the outbox can be marked delivered.
