# Phase 3 execution decisions

## D-001: use governed Codex wave dispatch instead of generic plan runners

- Chosen: one serial Codex implementation worker per ordered wave, with the
  coordinator integrating, running full gates, and committing checkpoints.
- Rejected: `/run-plan`, because its configured worker tiers include
  non-Codex models and it requires an interactive confirmation path that does
  not produce the contract's Codex-only dispatch ledger.
- Rejected: `/plan-to-pr`, because its workflow uses non-Codex agents, stops
  at a draft PR, and forbids the gated merge required by goal `#62`.
- Why: the goal contract's Codex-only auditability and merge endgame are
  stricter than either generic runner.

## D-002: reuse the planning checkout for implementation

- Chosen: create `goal/open-brain-phase3` from freshly fetched `origin/main`
  in the existing checkout after the planning workstream reached a validated
  complete handoff.
- Rejected: a second worktree, because no concurrent workstream owns this
  checkout and no other worktree or overlapping branch exists.
- Why: this preserves the reviewed untracked planning bundle without copying
  files and keeps one coordinator-owned writer surface.
