# Privacy model

Every capture receives an immutable privacy decision before persistence. The decision includes a tier, deterministic reason, and cloud/egress authority.

The Phase 2 profile is one owner and one private Brain root. Its provider mode is `none`, and its
connector allow-list is empty with egress disabled by default. An explicit internal `JOB-029`
configuration can enable the bounded YouTube reference proof, but it receives only a
capture-accept capability. It cannot route to a space, approve a review, publish owner output, or
perform an action.

Missing, invalid, or ambiguous classification is local-only `hold` with no cloud or external egress authority. Later components may narrow authority but cannot broaden it.

Tool-capable model processing must run through a staged-asset execution boundary with explicit readable assets, no inherited credentials, no access to host, home, or source trees, no host sockets, bounded network authority, and redacted failures.

Production staged execution is available only where the operating-system confinement matrix passes. The Linux local-model runtime uses bubblewrap with an empty environment, no network, explicit read-only assets, bounded output, and process, CPU, memory, and file limits. Darwin downloaded-media execution uses the separately verified native sandbox boundary. Unsupported hosts fail closed.

Work-tier capture events use the built-in, policy-version-locked redactor. Its receipt binds the exact normalized extraction and redacted output. Private raw captures remain unchanged.

Only owner-authored work text can publish directly to the work inbox. Third-party web,
social, and video captures publish to saved content with provenance. Third-party text does
not become owner-authored work, and derived ideas or actions still require owner review.

Provider selection receives the full immutable privacy decision. An authorized cloud route still scans the final prompt for credential, contact, network, and private-path findings before constructing an adapter or resolving a credential. Failure selects no fallback provider.

Connector counters and checkpoint claims are untrusted connector output. The host owns the
budget meters and metadata receipt, records the exact sink-issued capture receipt with its
delivery ID and source reference, and advances a checkpoint only when that host evidence matches.
Rejected rows may advance past an ineligible input; an eligible row whose sink submission fails
keeps the retry cursor so later work is not starved and the evidence remains retryable.

Ledger model text is untrusted. Sanitized leaves are one line, escaped, redaction-checked, directive-checked, and revalidated at merge and synthesis boundaries. Third-party source text can enter review records for audit, but owner-authored output contains only owner text and a deterministic opaque capture reference.

All public task and representation results use an engine-owned projection after storage and
ranking. It protects raw and bounded percent/HTML-encoded source references, their bare SHA-256
digests, absolute POSIX/Windows paths, credential assignments, storage-derived space slugs and
canonical paths, and other protected literals while retaining useful searchable text, opaque IDs,
and bounded provenance. Query explanations never echo query terms, and MCP retrieval IDs are
random opaque values rather than hashes or other derivatives of the query. Renderers consume the
projection; they do not implement separate redaction. Portable/source bytes and internal trusted
records remain unchanged.
