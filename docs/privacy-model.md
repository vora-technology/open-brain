# Privacy model

Every capture receives an immutable privacy decision before persistence. The decision includes a tier, deterministic reason, and cloud/egress authority.

Missing, invalid, or ambiguous classification is local-only `hold` with no cloud or external egress authority. Later components may narrow authority but cannot broaden it.

Tool-capable model processing must run through a staged-asset execution boundary with explicit readable assets, no inherited credentials, no host/home/source access, no host sockets, bounded network authority, and redacted failures.

Production staged execution is available only where the operating-system confinement matrix passes. The Linux local-model runtime uses bubblewrap with an empty environment, no network, explicit read-only assets, bounded output, and process, CPU, memory, and file limits. Darwin downloaded-media execution uses the separately verified native sandbox boundary. Unsupported hosts fail closed.

Work-tier capture events use the built-in, policy-version-locked redactor. Its receipt binds the exact normalized extraction and redacted output. Private raw captures remain unchanged.

Only owner-authored work text can publish directly to the work inbox. Third-party web,
social, and video captures publish to saved content with provenance. Third-party text does
not become owner-authored work, and derived ideas or actions still require owner review.

Provider selection receives the full immutable privacy decision. An authorized cloud route still scans the final prompt for credential, contact, network, and private-path findings before constructing an adapter or resolving a credential. Failure selects no fallback provider.

Ledger model text is untrusted. Sanitized leaves are one line, escaped, redaction-checked, directive-checked, and revalidated at merge and synthesis boundaries. Third-party source text can enter review records for audit, but owner-authored output contains only owner text and a deterministic opaque capture reference.
