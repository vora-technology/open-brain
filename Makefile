.PHONY: dev build test lint typecheck audit audit-history phase4-contracts verify-artifacts verify

dev:
	PYTHONPATH=packages/engine/src:src uv run python -m open_brain --version

build:
	rm -rf dist
	uv build --no-sources --project packages/engine --out-dir dist

test:
	uv run pytest -q

lint:
	uv run ruff check .

typecheck:
	uv run mypy

audit:
	@test -n "$(PRIVATE_DENYLIST)" || (echo "PRIVATE_DENYLIST is required" >&2; exit 2)
	PYTHONPATH=packages/engine/src:src uv run python -m open_brain.dev.release_audit --root . --private-denylist "$(PRIVATE_DENYLIST)"

audit-history:
	@test -n "$(PRIVATE_DENYLIST)" || (echo "PRIVATE_DENYLIST is required" >&2; exit 2)
	PYTHONPATH=packages/engine/src:src uv run python -m open_brain.dev.public_history_audit --repository . --private-denylist "$(PRIVATE_DENYLIST)"

phase4-contracts:
	uv run pytest -q tests/phase4 tests/security/test_architecture_imports.py
	uv run ruff check tools/phase4 tests/phase4 tests/security/test_architecture_imports.py
	uv run mypy
	uv run python -m tools.phase4.move_manifest validate --root .

verify-artifacts: build
	PYTHONPATH=packages/engine/src:src uv run python -m open_brain.dev.artifact_policy --policy release/v0-artifact-policy.json --artifacts dist/*

verify: lint typecheck test verify-artifacts
