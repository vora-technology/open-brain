# Phase 4 plan and contract review 1

- Reviewer: fresh read-only Codex `gpt-5.4` high session
- Verdict: `NEEDS_FIX`
- Counts: P0/P1/P2/P3 `0/0/2/0`
- Coverage: 12 of 14 requested areas fully covered; all 14 inspected
- Files changed by reviewer: none

## P2 findings

1. The artifact and cutover checks used generic capture/review/retrieval
   wording and did not explicitly re-prove `V0-GATE-07` proposal terminal
   behavior or `V0-GATE-13` space routing and identity behavior. A physical
   split or native package could regress those contracts while satisfying the
   draft evidence chain.
2. P4-W0 asked for macOS/Linux native build and smoke CI before P4-W5 creates
   the native adapter or artifacts. The draft did not say whether those jobs
   were scaffolding-only, expected-red, non-required, or real pass gates.

## Required reconciliation

- Add explicit wheel-only, native-artifact, traceability, completion, and
  production checks for sibling proposals; CLI/UI approve, reject, and safe
  edit; space create/rename; later routing of an unassigned capture without
  identity change; and retrieval by one space or across spaces.
- Keep P4-W0 CI limited to checks with real subjects: root verification,
  manifest/harness self-tests, and current artifact safety. Add isolated
  distribution jobs with their owning P4A wave and native build/smoke jobs in
  P4-W5. Do not use placeholder green jobs or make expected-red future work a
  required check.

A fresh exact-file rereview is required after reconciliation because the plan
checksum and contract acceptance path will change.
