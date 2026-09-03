# Workstream State

- ID: `20260901-open-brain-public-produce-an-executable-independently-reviewed-phase-4-plan-and-child-goal-contrac-d909e4`
- Repo root: <repo-root>
- Remote identity SHA-256 fingerprint: `cb5e9cd7ac71c16e5109717b4bc07f01aed1bbda2b18a99bfbc76f7bd98245bc`
- Worktree: <repo-root>
- Branch: phase4-planning
- Objective: Produce an executable independently reviewed Phase 4 plan and child goal contract for the physical distribution split, native artifacts, and owner-gated full-stop production cutover without implementing Phase 4
- Created date: 2026-09-01

## Current milestone

- Milestone: Phase 4 executable plan and child goal contract
- Status: complete; candidate drafted, locally verified, independently
  reviewed `READY`, and filed; implementation not started
- Allowed scope: planning documents, goal contract, workstream state, review
  evidence, planning-only commits, and child issue filing
- Stop condition: any runtime package move, native build implementation,
  package publication, deployment, production action, private predecessor
  access, live Brain access, or Phase 4 execution begins
- Baseline: clean public `main` and `origin/main` at
  `3b89a4ba4787a378e6040ff042bd117da881918d`
- Plan:
  `docs/plans/phase-4-physical-split-native-artifacts-and-cutover.md`
- Contract:
  `docs/ai/workstreams/20260901-open-brain-public-produce-an-executable-independently-reviewed-phase-4-plan-and-child-goal-contrac-d909e4/PHASE-4-GOAL-CONTRACT.md`
- Required review: fresh read-only Codex review of both exact files; all P0,
  P1, and P2 findings resolved before issue filing
- Parent goals: `cbolden15/agent-config#41` and `#24`; Phase 4 sequencing and
  downtime supersession must be explicit in the child contract
- Launch state: planning only; filing the child does not launch implementation

## Verification

- `make verify`: passed Ruff, strict MyPy on 474 source files, all 3,114
  tests, isolated wheel/sdist builds, and the current artifact policy
- Release audit: source, wheel, and sdist passed with a synthetic planning
  denylist
- Complete-history audit: passed with the same synthetic planning denylist
- Contract structure: all 11 required full-profile sections exist; every
  standing block matches the goal template verbatim
- Plan checksum:
  `7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`
- Independent review 1: `NEEDS_FIX`, P0/P1/P2/P3 `0/0/2/0`; explicit
  `V0-GATE-07/13` artifact checks and owning-wave CI activation were added
- Independent review 2: `READY`, P0/P1/P2/P3 `0/0/0/0`, 28/28 requested
  checks and 11/11 contract sections covered; candidate is ready to file

## Filing

- Child goal: `cbolden15/agent-config#63`, open with label `goal`
- Child title: `Goal: Open Brain Phase 4 split, native artifacts, and full-stop cutover complete`
- Body verification: remote issue body SHA-256 exactly matches the local
  reviewed contract
- Parent links: Goals `#41` and `#24` each contain the child link, exact
  sequencing/downtime supersession, preserved safety constraints, plan hash,
  and unlaunched status
- Durable capture: goal title, issue number, profile, plan hash, and unlaunched
  state captured through the normal thought pipeline
- Launch state: filed but not launched; no Phase 4 implementation or production
  action is authorized by this planning workstream
