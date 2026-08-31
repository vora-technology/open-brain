# Phase 0 public-history audit

- Date: 2026-08-30
- Scope: every blob reachable from every local Git ref
- Output: commit ID, redacted repository path, and rule ID only
- Project-specific denylist: owner declared no additional private terms on 2026-08-30
- Result: existing history remains private; clean-history publication approved

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

## Publication disposition

The owner selected the clean-history path on 2026-08-30:

- preserve the original repository and all migration history as a private archive;
- create the public repository from the verified Phase 0 source tree with no parent history;
- record exact Gitleaks fingerprints for synthetic replay keys and idempotency digests;
- rerun the full build, test, artifact, generic-history, release, and Gitleaks gates before making
  the replacement repository public.

The clean repository passed the generic history audit and Gitleaks scan. The 101 legacy-history
occurrences remain only in the private archive and are not ancestors of the public root commit.
The full metadata-only legacy report remains private and is not copied into the public repository.
