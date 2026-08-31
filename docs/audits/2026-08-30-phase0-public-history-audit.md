# Phase 0 public-history audit

- Date: 2026-08-30
- Scope: every blob reachable from every local Git ref
- Output: commit ID, redacted repository path, and rule ID only
- Project-specific denylist: unavailable
- Result: findings recorded; existing history is not approved for public publication

The bounded scanner read each reachable blob once and completed without hitting its commit, blob,
byte, or command-time limits. A synthetic denylist enabled the generic detectors without exposing
private terms.

## Findings

The run produced 101 occurrences across 25 commits and eight repository paths:

| Rule | Occurrences |
|---|---:|
| Credential-shaped assignment | 49 |
| Private IPv4 literal | 40 |
| Absolute home path | 12 |

The repeated paths are old versions of test fixtures, UI/private-binding examples, optional cloud
construction, and project-bridge/parity fixtures. Current source had already replaced or assembled
many detector canaries safely, but removal from the current tree does not remove the old blob from
history.

This result is not proof that a credential or customer record exists. The scanner deliberately
does not print matching bytes. It is proof that the existing history contains material that the
public-release rules require an owner-reviewed disposition.

## Publication gate

Before repository publication, choose one owner-authorized path:

1. publish a clean public repository from a verified source archive, preserving private migration
   commit IDs only in a private record; or
2. rewrite the existing publication history, then rerun the generic audit, the owner denylist,
   Gitleaks, and artifact checks.

Phase 0 does not rewrite or publish Git history. The full metadata-only report remains in the
session scratch ledger and is not copied into the repository. Project-specific name and term
coverage remains unverified until the owner denylist is supplied.
