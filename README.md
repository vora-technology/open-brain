# Open Brain

Open Brain is a local-first capture, provenance, review, and knowledge pipeline. It is being built as the single public implementation that will replace two private predecessor codebases after behavioral parity and a controlled production cutover.

The Phase 2 boundary is one single-user local profile rooted at one private Brain directory. An engine task set supplies capture, inbox/spaces, review, retrieval, and Portable Brain operations to the CLI, authenticated HTTP/share, local UI, scoped stdio MCP, and public-job representations. The internal connector host is optional and empty by default. Private deployment configuration, live service state, migration evidence, and cutover receipts remain outside this repository.

## Principles

- Preserve the owner's one-line reason for saving something as first-class provenance.
- Route intent through a closed enum: `reference`, `idea`, `action_candidate`, or `hold`.
- Require review before third-party content can become an owner-authored idea or action.
- Default unknown or personal content to local-only handling.
- Keep private content, credentials, host configuration, and runtime state outside the repository.
- Maintain one canonical application repository rather than public and private forks.

## Development

Requirements: Python 3.12–3.14 and [uv](https://docs.astral.sh/uv/).

### Run the local single-user slice

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

The Phase 2 in-place vertical slice supports one local Brain root, stable portable identities,
typed capture, spaces, inbox routing, sibling review proposals, terminal decisions, canonical
Markdown publication, and lexical retrieval. The CLI, authenticated HTTP/share boundary, local
UI, scoped MCP, and public-job sinks use bounded capabilities over the same engine task objects.
With no model configured, captures remain usable and report `pending_enrichment`.

This is pre-alpha software. Phase 2 implements engine-level Portable Brain validation, export,
clean-root import, and disposable index rebuild. Export and import preserve portable identities,
history, routing, and exact source bytes while excluding operational state such as credentials,
databases, leases, runtime files, and indexes. The default profile uses provider `none` and
loads no connectors. A retained synthetic `JOB-029` proof exercises the internal seam only with
an absolute private configuration reference, capture-only authority, and egress enabled; host
evidence binds accepted captures to checkpoint advancement.

The public result projection exposes opaque IDs, bounded provenance, and safe titles/excerpts,
not raw or encoded protected references, absolute paths, credentials, storage-derived slugs and
paths, or reversible source-reference digests.
Phase 2 does not include the Phase 3 appliance lifecycle: initialization, one supervised daemon,
internal scheduling, launchd/systemd integration, backup/restore, upgrade, or uninstall. Phase 4
defers the physical distributions and `packages/` split, isolated connector workers, public
Connector SDK, signing, and bundler/native artifact work. Predecessor modules remain retained
legacy compatibility code and are excluded from the default application path.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
