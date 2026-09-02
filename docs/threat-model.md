# Threat model

Primary threats include credential disclosure, private-content disclosure, path traversal, SSRF, prompt-injected filesystem access, unredacted logs, unauthorized cloud routing, review-gate bypass, duplicate writers, and unsafe migration or rollback.

Security controls are contract tests and release gates, not documentation claims. Public fixtures are synthetic. Unknown classifications fail closed. Deployment templates cannot contain private host values.

## Local filesystem authority

The self-hosted local profile assumes one trusted owner account and owner-only Brain and staging directories. Portable import and export defend against malformed input, pre-existing symlinks and hardlinks, path traversal, special files, target-creation races, crashes, and cooperating concurrent Open Brain processes. Leases coordinate those Open Brain processes. Native no-replace rename makes a new target name visible atomically only after the staged root passes validation.

Code already running as the Brain owner's operating-system user is inside the local trust boundary. Such code can change file permissions, replace directory entries between system calls, or alter the Brain after promotion. A user-space filesystem protocol cannot make the tree immutable against that principal. Here, “atomic promotion” means the target name changes from absent to a complete staged directory in one native rename under the trusted-owner boundary. It does not claim integrity against arbitrary concurrent mutation by another process with the same user ID.

Deployments that run untrusted code must use a separate operating-system account, container or virtual-machine boundary, or a platform-specific immutable snapshot service. Expanding the default profile to hostile same-user execution requires a separate design and conformance gate.

Multi-document ledger writes become visible only through an applied durable manifest that binds the complete document set and sink digests. IDs, dispositions, deterministic rendered-byte digests, and exact read-back through a separate approved root-confined reader must all verify first. Slimming uses the same split writer/reader rule for its transcript-free successor, derives authority from the durable ledger row, and records archive and successor digests before `slimmed`. Model synthesis requires three persisted citation IDs with deterministic destinations, the approved SQLite store with typed durable confirmation, an authoritative lock probe, and no held transaction or writer lock. Valid output persists its evaluating row, page, and link-backs in one SQLite transaction.

Review creation and delivery treat receipts as untrusted. Creation binds the canonical initial aggregate digest. Delivery binds the expected output ID, canonical digest, and created/duplicate disposition before the outbox can be marked delivered.

## Connector worker boundary

The optional connector distribution is trusted shipped code, but it does not load in the app
process. The app validates entry-point metadata, explicit enablement, manifest identity, and
declared capabilities before starting a fixed worker bootstrap. The child receives no inherited
environment or secret values. Direct sockets are disabled, process groups are reaped on timeout or
output overflow, and the response schema contains bounded metadata only.

The connector wheel scanner rejects app composition, unpublished app extension values, private
engine modules, undeclared dependencies, and dynamic import authority. This boundary limits the
shipped provisional connector. It is not containment for hostile code running as the Brain owner.
Untrusted third-party connectors require a separate operating-system account, container, or virtual
machine gate.
