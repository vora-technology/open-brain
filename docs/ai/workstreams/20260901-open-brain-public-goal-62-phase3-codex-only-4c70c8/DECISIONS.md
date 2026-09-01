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

## D-003: classify W1 runtime files before W2

- Chosen: add all five W1 runtime modules to
  `docs/v0-package-classification.json` and route public maintenance/read
  contracts through `open_brain.engine` in W1.
- Rejected: defer classification to W2 because the reviewed plan listed the
  registry there.
- Why: every wave must end with `make verify`, and repository architecture
  tests require every runtime file and cross-owner import to be classified.
  Deferral would knowingly leave W1 without a clean checkpoint.

## D-004: report queue evidence as unavailable until W2 owns it

- Chosen: keep the W1 queue field but report explicit `unavailable` state.
- Rejected: import the retained `capture/queue.py` reader, which is classified
  legacy and would create engine-to-app plus shipping-to-legacy violations.
- Rejected: report a missing queue as empty, which would be false evidence.
- Why: W2 owns the new durable scheduler and can supply real bounded queue
  age without coupling the shipping engine to legacy capture operations.

## D-005: fail fast in every remaining compound gate

- Chosen: start every remaining multi-command verification and commit batch
  with `set -euo pipefail`, then inspect the result before the next mutation.
- Rejected: rely on the shell's default continue-on-error behavior.
- Why: the W1 staged diff check correctly reported two EOF blank lines, but
  the following commit command still ran. History is preserved; a follow-up
  hygiene commit removes the lines, and future batches stop at the first
  failed gate.
