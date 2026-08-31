.PHONY: dev build test lint typecheck audit audit-history verify-artifacts verify

dev:
	uv run open-brain --version

build:
	uv run python -m build

test:
	uv run pytest -q

lint:
	uv run ruff check .

typecheck:
	uv run mypy

audit:
	@test -n "$(PRIVATE_DENYLIST)" || (echo "PRIVATE_DENYLIST is required" >&2; exit 2)
	uv run python -m open_brain.dev.release_audit --root . --private-denylist "$(PRIVATE_DENYLIST)"

audit-history:
	@test -n "$(PRIVATE_DENYLIST)" || (echo "PRIVATE_DENYLIST is required" >&2; exit 2)
	uv run python -m open_brain.dev.public_history_audit --repository . --private-denylist "$(PRIVATE_DENYLIST)"

verify-artifacts: build
	uv run python -m open_brain.dev.artifact_policy --policy release/v0-artifact-policy.json --artifacts dist/*

verify: lint typecheck test verify-artifacts
