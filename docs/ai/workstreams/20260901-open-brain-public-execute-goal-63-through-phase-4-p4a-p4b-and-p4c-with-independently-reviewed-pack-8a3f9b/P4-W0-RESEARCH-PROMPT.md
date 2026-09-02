# Research task

Objective: Independently map the exact P4-W0 implementation boundary for the canonical move manifest, validator, acceptance-harness self-tests, toolchain record, and real-subject CI without moving runtime source.
Source of truth and precedence: Goal #63 contract and docs/plans/phase-4-physical-split-native-artifacts-and-cutover.md at SHA-256 7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2; current docs/v0-package-classification.json; tests/security/test_architecture_imports.py; release/v0-artifact-policy.json; pyproject.toml; uv.lock; Makefile; .github/workflows/*.yml. Runtime Git state and project instructions outrank planning snapshots.
Allowed write scope: Read-only access to the public repository. Do not edit files, create commits, push, open PRs, mutate issues, access private state, or contact production.
Verification: Cite repository-relative paths and exact symbols/sections for every finding; account for all 224 runtime files, all 250 tracked Python files under tests, all 36 schema/fixture files, entry points, generated resources, and release tools; distinguish current facts from recommendations.
Stop condition: Stop after producing an implementation-ready P4-W0 map with schema fields, validator invariants, harness seams/self-tests, expected-red strategy, toolchain/CI requirements, and concrete risks. Do not implement or inspect outside the public repository.
Sensitive-data policy: The public repository is the only allowed data source. Do not read or emit credentials, private topology, local configuration, personal content, absolute paths in the deliverable, or raw environment values.
Output contract: Return: (1) observed current mechanisms, (2) minimal correct manifest schema extension, (3) validator and harness test matrix, (4) exact likely file changes, (5) conflicts or hidden risks ranked P0-P2, and (6) a clear READY or NEEDS_DECISION conclusion. No code changes.

Prefer primary, current sources. Separate observed facts, inferences, and open questions. Keep work read-only unless scope explicitly permits a bounded artifact. Cite source paths or links and stop when the stated evidence threshold is met.
