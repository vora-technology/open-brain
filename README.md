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

### Run the Phase 1 local slice

Set one Brain root. The command creates the private runtime layout with owner-only
permissions and reuses its stable local identity on later runs.

```bash
export OPEN_BRAIN_ROOT="$HOME/open-brain-data"
uv run open-brain spaces create "Projects" --delivery=setup-projects --json
uv run open-brain capture quick text "Review the roadmap" --delivery=capture-roadmap --json
uv run open-brain inbox list --json
uv run open-brain query roadmap --json
```

Canonical text capture requires the `space_id` returned by `spaces create`, because Portable Brain
canonical-page frontmatter always carries a stable space identity:

```bash
uv run open-brain capture canonical text "Project context" \
  --delivery=capture-project-context \
  --space=space_REPLACE_WITH_RETURNED_ID \
  --json
```

Every mutating command requires a caller-supplied delivery ID. Repeating the same request
with the same delivery ID returns the existing identifiers. Reusing a delivery ID for a
different request fails closed and records metadata-only quarantine evidence.

### Verify the repository

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

The Phase 1 in-place vertical slice supports one local Brain root, stable portable identities,
typed capture, spaces, inbox routing, sibling review proposals, terminal decisions, canonical
Markdown publication, and lexical retrieval. The CLI and authenticated framework-neutral UI
handler use the same engine and return the same identifiers. With no model configured, captures
remain usable and report `pending_enrichment`.

This is pre-alpha software. Phase 1 does not include a bound HTTP service, model-backed
enrichment, export/import, connector ingestion, package extraction, hosted operation, migration,
or production cutover. The older modules remain in place until their later architecture phases.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
