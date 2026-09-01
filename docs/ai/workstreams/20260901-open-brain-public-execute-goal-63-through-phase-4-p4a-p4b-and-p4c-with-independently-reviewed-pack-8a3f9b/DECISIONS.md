# Phase 4 execution decisions

## D-001: carry the reviewed planning commit onto a fresh implementation branch

- Chosen: create `goal/open-brain-phase4` directly from freshly fetched
  `origin/main`, then cherry-pick the exact reviewed planning commit.
- Rejected: implement on `phase4-planning`, because the goal requires a new
  implementation branch from the fresh public base.
- Rejected: merge a separate planning PR first, because one Phase 4 draft PR
  can carry the reviewed plan and implementation without changing the base
  requirement or adding an unnecessary review cycle.
- Why: this preserves the exact reviewed plan, starts implementation from the
  required base, and keeps one coordinator-owned writer surface.

## D-002: treat Goal #24's earlier apply as immutable history

- Chosen: retain and reference the prior Goal #24 receipts, but build a new,
  separately bound Phase 4 rehearsal and full-stop transaction.
- Rejected: rerun or repurpose the old production apply.
- Why: the latest private handoff explicitly says the earlier apply and stage
  cleanup are complete and must never be rerun. Goal #63 authorizes a later
  transaction only after new P4A, P4B, recovery, and P4-W8 gates pass.

## D-003: use project-local durable context when context-mode is unavailable

- Chosen: search the project gotcha registry, Phase 3 decisions/evidence, and
  the work-brain filesystem for relevant Phase 4 context.
- Rejected: infer prior decisions without a durable-context search.
- Why: no `ctx_search` capability is installed in this runtime, and no Phase
  4-specific work-brain page was found. Project-local verified records remain
  available and authoritative for implementation behavior.

## D-004: classify all 250 tracked Python files under tests

- Chosen: treat all 250 currently tracked Python files under `tests/` as
  manifest subjects, including root `tests/__init__.py` and
  `tests/conftest.py`.
- Rejected: preserve the planning snapshot's count of 248 by omitting the two
  root files.
- Why: the goal says every test must have one owner and disposition, and every
  creation-time count must be reverified. The broader current inventory is the
  stronger and mechanically complete boundary.

## D-005: continue P4A preparation while preserving the notarization blocker

- Chosen: record unavailable notarization credentials as a mandatory P4B
  prerequisite while continuing reversible source-only P4-W0/P4A work.
- Rejected: weaken the signed/notarized macOS requirement or claim readiness
  from the presence of `notarytool` and a local Developer ID identity alone.
- Why: neither checked authorized host has a ready standard notary credential
  profile. No current source milestone consumes that credential, and the goal
  remains able to make meaningful progress before P4B signing.
