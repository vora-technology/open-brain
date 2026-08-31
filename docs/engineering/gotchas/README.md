# Gotcha registry

Non-obvious behaviors, sharp edges, and lessons learned belong here.

## Registry

### PRIVACY-001: A redaction receipt does not authorize a sink

Symptom: Redacted content appears safe but still carries a `secret`, `unknown`, classification-failure, explicit-local-only, or unconfirmed `personal` privacy decision.

Cause: Redaction and authorization answer different questions. A receipt records a transformation; it does not widen the original privacy authority.

Fix: Have every work-tier event or Markdown adapter enforce the immutable privacy decision before any I/O.

Discovered: 2026-08-13.

### REVIEW-001: Approval evidence must be bound to one review

Symptom: A valid approval event can be paired with another review or approved-intent record during deserialization.

Cause: The event shape was validated without checking its review ID and deterministic approved record against the enclosing review.

Fix: Reject mismatched review IDs and approved records at the model boundary.

Discovered: 2026-08-13.

### STORAGE-001: SQLite paths are root capabilities

Symptom: A database path under the configured root escapes through a symlink, or SQLite sidecar files receive permissive default modes.

Cause: Lexical path checks and default SQLite file creation do not enforce filesystem containment or private permissions.

Fix: Traverse parents without following symlinks and maintain database, WAL, and SHM files at `0600`.

Discovered: 2026-08-13.

### CAPTURE-001: Private raw storage preserves canonical bytes

Symptom: Persisting a capture changes its deterministic capture ID.

Cause: Redaction was applied to identity-bearing raw fields before private persistence.

Fix: Store canonical raw captures unchanged. Apply redaction only when producing typed work-tier records.

Discovered: 2026-08-13.

### INDEX-001: Excluded symlinks must not block canonical indexing

Symptom: An index rebuild fails even though a retained source symlink is explicitly outside
the indexed content policy.

Cause: Traversal rejected the presence of every symlink instead of excluding links without
following them.

Fix: Ignore source symlinks before file classification, never follow file or directory targets,
and regression-test that target content is absent from the index.

Discovered: 2026-08-19.

### RELEASE-001: Assemble detector canaries at runtime

Symptom: The release audit flags a test fixture that resembles a real credential assignment.

Cause: Secret scanners correctly inspect committed test text without knowing whether a value is synthetic.

Fix: Build detector canaries from harmless fragments at runtime instead of committing assignment-shaped literals.

Discovered: 2026-08-13.

### CAPTURE-002: Resume from a durable event after a crash

Symptom: A retry after event persistence fetches mutable source content again and creates a second event with different bytes.

Cause: Recovery restarted the full extraction pipeline instead of checking the event stream first.

Fix: If one matching durable extraction event exists, rebuild only the deterministic distillation item and continue from that boundary.

Discovered: 2026-08-13.

### CAPTURE-003: Extracted metadata does not always repeat the source URL

Symptom: A provenance-bound YouTube capture retries forever during saved-content
publication because its normalized extraction has a platform and video ID but no canonical
URL.

Cause: Publication required `metadata.canonical_url` even though some approved extractors
represent source identity through typed platform fields.

Fix: Require the immutable envelope URL to match its provenance source reference, prefer an
extracted canonical URL when present, and otherwise use the provenance-bound envelope URL.

Discovered: 2026-08-26.

### SECURITY-001: A closed gate must be unreachable

Symptom: Documentation says an executor or redactor is unavailable, but callers can inject any implementation through a public constructor.

Cause: Policy checks were mistaken for runtime confinement or approved-policy selection.

Fix: Reject arbitrary injection until a concrete adapter passes its gate; use one policy-version-locked redactor for work-tier events.

Discovered: 2026-08-13.

### MEDIA-001: Resource limits must be enforceable

Symptom: A command object lists timeout, memory, or process limits that the runtime never applies.

Cause: Descriptive metadata was treated as execution enforcement.

Fix: Apply operating-system limits, process-group cleanup, output bounds, and staging checks. Return `tool_unavailable` on unsupported platforms.

Discovered: 2026-08-13.

### PROVIDER-001: Cloud authority does not prove prompt safety

Symptom: A cloud-authorized privacy decision allows secret-shaped prompt text to reach adapter construction or credential resolution.

Cause: Routing authority and content redaction were treated as the same gate.

Fix: Scan the final cloud prompt before factory construction. A finding returns a closed code with zero factory, credential, import, or provider calls.

Discovered: 2026-08-13.

### LEDGER-001: Frozen dataclasses are not trusted constructors

Symptom: A caller directly constructs a sanitized leaf or trusted citation and injects Markdown structure or traversal into output.

Cause: Merge code checked the Python type but not the value's invariants.

Fix: Validate during construction and again at every merge, render, apply, and synthesis boundary.

Discovered: 2026-08-13.

### LEDGER-002: Two sink writes need one visibility decision

Symptom: A crash after the first Markdown write exposes half of a ledger publication.

Cause: Individual atomic files were mistaken for an atomic document set.

Fix: Readers use only the durable applied manifest that binds every intended document and sink digest. Reconciliation completes partial physical writes before publishing the manifest.

Discovered: 2026-08-13.

### LEDGER-003: Slim authorization comes from durable state

Symptom: Caller-provided booleans or citation tuples authorize archive/slim without a persisted applied ledger row.

Cause: Evidence was passed as mutable orchestration input instead of loaded from the store.

Fix: Use a store-issued row identity, verify persisted citations, and atomically record archive digest, successor digest, and `slimmed` after both writes verify.

Discovered: 2026-08-13.

### LEDGER-004: A writer cannot certify its own persistence

Symptom: A no-op or memory-only writer returns plausible IDs, digests, and cached read-back bytes, causing durable state to advance although no artifact exists.

Cause: Apply trusted caller-provided receipt fields or allowed the same adapter to attest both the write and its persistence.

Fix: Validate receipt type, disposition, ID, and deterministic rendered-byte digest, then read exact bytes through a separate approved root-confined reader before the manifest or slim state advances.

Discovered: 2026-08-13.

### LEDGER-005: A model lock guard cannot be optional

Symptom: Constructing synthesis with no lock probes invokes a model without proving transaction and writer locks are clear.

Cause: A safety invariant was represented as an optional callback tuple.

Fix: Reject construction without an authoritative probe and fail closed when a probe errors or reports a held lock.

Discovered: 2026-08-13.

### REVIEW-002: Review audit text is not owner output

Symptom: Third-party instructions in a source reference or proposal reason survive approval and appear in an owner-authored record.

Cause: Delivery copied audit fields instead of deriving an output-safe reference.

Fix: Render owner text plus a deterministic opaque capture reference only, then verify the sink receipt before marking the outbox delivered.

Discovered: 2026-08-13.

### REVIEW-003: Review creation receipts bind the initial aggregate

Symptom: Intent routing reports an open review after a no-op boundary returns the right review ID with unrelated bytes.

Cause: Routing checked identity and disposition but not the canonical aggregate digest.

Fix: Hash `ReviewAggregate.create(proposal)` canonically and require the creation receipt to match before returning `review_open`.

Discovered: 2026-08-13.

### SYNTHESIS-001: Citation authority includes destination and durable proof

Symptom: A persisted citation ID is paired with a forged destination, or a memory-only persistence port returns synthesis success.

Cause: Authority compared IDs only and accepted an unconstrained persistence result.

Fix: Recompute the deterministic destination from the published capture document and require the approved SQLite store to return and confirm an exact typed durable record.

Discovered: 2026-08-13.

### TAXONOMY-001: Printable labels only

Symptom: NEL or Unicode line/paragraph separators create extra structure inside a rendered topic heading.

Cause: Label validation rejected ASCII controls but not all non-printable Unicode characters.

Fix: Reject non-printable characters and Markdown structural punctuation before route construction.

Discovered: 2026-08-13.

### CLI-001: Dependency injection is not output authority

Symptom: A typed adapter returns success while echoing argv through a command value or dynamic JSON key, asserting reserved readiness fields, or pairing a failure status with exit zero.

Cause: The composition root trusted the adapter's result type without independently validating its public schema and process semantics.

Fix: Use closed command and schema-key allow-lists, scan converged encoded keys and values against argv and secret/path residuals, reserve live/parity/cutover fields for a separate evidence boundary, and enforce status/exit coherence.

Discovered: 2026-08-14.

### AUDIT-001: Unclassifiable runtime references are unsafe

Symptom: An old-source path passes audit because the deny-root set is empty or a path-bearing argument uses an unsupported representation.

Cause: No extracted path was treated as proof that no path existed.

Fix: Require a non-empty deny policy and reject executable, working-directory, referenced-file, or argument values that cannot be completely classified into the canonical path representation.

Discovered: 2026-08-14.

### HOOK-001: Path strings do not grant hook-install authority

Symptom: A manual hook installer can target a replaced, symlinked, or different repository after planning.

Cause: Installation authority was represented by caller-provided paths instead of a bound filesystem identity.

Fix: Bind an explicit capability to repository, Git, and hooks-directory identities; revalidate before descriptor-relative writes; keep dry-run as default; and make post-commit delivery bounded and fail-zero.

Discovered: 2026-08-14.

### MIGRATE-001: Atomic files do not make an atomic state generation

Symptom: A crash after the first migrated state file leaves readers with a partial seven-family target that cannot safely resume.

Cause: Per-file atomic replacement was mistaken for one visible migration commit.

Fix: Stage and verify a complete generation off-path, hold an identity-bound exclusive lease, publish one atomic `CURRENT` pointer as the reader-visible commit, and use a durable journal to recover pre- and post-pointer crashes.

Discovered: 2026-08-14.
