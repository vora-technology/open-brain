# Open Brain

Open Brain is a local-first capture, provenance, review, and knowledge pipeline. It is being built as the single public implementation that will replace two private predecessor codebases after behavioral parity and a controlled production cutover.

This repository contains the local pipeline and its production composition boundaries: immutable capture/provenance/privacy contracts, durable capture recovery, authenticated share intake, fail-closed outbound egress, bounded extraction, explicit local/cloud provider composition, receipt-bound ledger staging and publication, archive-first slimming, structured synthesis, review-gated saved-content intent, typed CLI adapters, work-only stdio MCP, authenticated HTTP/UI composition, scheduler applications, backup/recovery, retention, and runtime audit tooling. Private deployment configuration, live service state, migration evidence, and cutover receipts remain outside this repository.

## Principles

- Preserve the owner's one-line reason for saving something as first-class provenance.
- Route intent through a closed enum: `reference`, `idea`, `action_candidate`, or `hold`.
- Require review before third-party content can become an owner-authored idea or action.
- Default unknown or personal content to local-only handling.
- Keep private content, credentials, host configuration, and runtime state outside the repository.
- Maintain one canonical application repository rather than public and private forks.

## Development

Requirements: Python 3.12–3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
uv run open-brain --version
uv run ruff check .
uv run mypy
uv run pytest -q
uv run python -m build
```

Release auditing requires a local, uncommitted private denylist:

```bash
PRIVATE_DENYLIST=/path/to/private-denylist.txt make audit
```

The denylist contains one private term per line. Blank lines and lines beginning with `#` are ignored. Release mode refuses to pass without it.

## Status

The historical Phase 5 synthetic checkpoint has been superseded by the Goal #24 terminal
contract. Its release validator accepts all 83 capability rows only when every row is
`open-brain-live` and carries hash-bound implementation, focused-test, parity, and production
binding evidence. Synthetic readiness is not live parity, deployment, migration, cutover, or
compatibility proof. Cloud routing requires explicit authority and secret-free input. Media
execution fails closed where the required operating-system limits cannot be enforced.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
