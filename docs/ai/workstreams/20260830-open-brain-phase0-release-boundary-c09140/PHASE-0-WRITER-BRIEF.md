# Phase 0 writer brief

## Milestone

Complete the six work items under “Phase 0: freeze the release boundary” in `docs/plans/option-c-architecture.md` and satisfy its five exit gates. The approved v0 product contract is authoritative. This milestone does not implement Phase 1 behavior.

The coordinator baseline passed on 2026-08-30:

```text
make lint typecheck test build
Ruff: passed
mypy: passed across 387 source files
pytest: 2,683 passed
build: open_brain-0.1.0 wheel and sdist built
```

## Fixed boundaries

- Brain-root layout version 1 and its JSON/JSONL/Markdown/blob/SQLite roles are approved.
- The v0 host matrix is macOS 14 or newer on Apple Silicon and Linux x86_64 on Ubuntu 24.04 LTS, Ubuntu 26.04 LTS, and Debian 13.
- PyInstaller 6 onedir gets the Phase 1 spike. Nuitka standalone is the accepted fallback. Do not run either spike in Phase 0.
- Stable tenant, actor, role, and space identities and the four payload families are part of the shared foundation.
- Existing typed records may supply tested primitives, but they are not automatically the new Portable Brain v1 contract.
- Do not move packages, add Phase 1 commands, implement provider mode `none`, or build connector/hosted behavior.

## Mapping evidence

- Package graph: every top-level package needs an explicit release classification. Current risks include `storage -> operations`, `config -> ledger`, `capture <-> providers`, `production -> cli/migrate`, and legacy `operations/parity` coupling. Use path-scoped rules where a top-level package is mixed. The architecture test must scan current source and must also fail on a synthetic forbidden import.
- Public CLI: the parser currently exposes 29 parser-visible families, 30 scheduled routes, global `--version`, `--json`, `--dry-run`, and help flags. Exit classes include 0, 1, 2, 3, 75, and 78. Phase 0 records this surface; it does not add missing `init`, lifecycle, or Portable Brain commands.
- Portable contract: reusable primitives include canonical JSON and hash helpers, typed record codecs, deterministic Markdown writers, and manifest patterns. The approved v1 schemas and synthetic fixtures must remain separate from legacy runtime records.
- Artifacts and history: the Hatch wheel selects `src/open_brain`; sdist exclusions are not explicit; the wheel still contains legacy-sensitive namespaces; current release auditing scans trees and archives but not Git history. Native artifact work remains Phase 1.

## Worker ownership

Writers may edit only their assigned paths. Shared files such as `pyproject.toml`, `uv.lock`, `Makefile`, workflow files, package exports, and this brief belong to the coordinator unless a prompt says otherwise. Workers do not commit or push.

Each writer runs only its targeted tests and lint for touched Python files. The coordinator runs the full suite and build after integration.
