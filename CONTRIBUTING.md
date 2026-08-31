# Contributing

Open Brain is pre-production. Discuss substantial behavior changes before implementation so the capture, privacy, provenance, provider, ledger, review, and migration contracts remain coherent.

## Development checks

```bash
uv sync --group dev
uv run ruff check .
uv run mypy
uv run pytest -q
uv run python -m build
```

Contributions must use synthetic fixtures. Never include private notes, captures, transcripts, credentials, hostnames, infrastructure addresses, logs, databases, or generated private configuration.

By intentionally submitting a contribution for inclusion, you agree that it is provided under the Apache License, Version 2.0, unless you explicitly state otherwise.
