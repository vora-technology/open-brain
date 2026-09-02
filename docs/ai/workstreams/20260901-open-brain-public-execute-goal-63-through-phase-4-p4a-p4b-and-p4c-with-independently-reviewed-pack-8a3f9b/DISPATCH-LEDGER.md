# Phase 4 Codex dispatch ledger

## Milestone budget

- Coordinator: runtime goal thread `01a05f1b-de55-7a41-bc01-673d277a1995`
- Maximum active children: 6
- Maximum total children: 12
- Current active children: 0
- Total child lineages used: 4
- Implementation writers: 0
- Independent reviewers: 3

Shared package metadata, the move manifest, imports, root lockfile, shared
tests, Git state, external actions, and final verification remain
coordinator-owned.

## Child 1: P4-W0 read-only implementation map

- Status: complete
- Agent ID: `01a05f60-5e5d-7392-8a75-a5e983948511`
- Model: `gpt-5.4`
- Reasoning effort: `high`
- Role: read-only exploration
- Write scope: none
- Source scope: public Open Brain repository only
- Prompt: `P4-W0-RESEARCH-PROMPT.md`
- Required output: current mechanism map, proposed schema/invariants, harness
  seams, exact file list, ranked risks, and READY/NEEDS_DECISION
- Result: `READY`; P0/P1/P2 `0/2/2`. Both P1 findings are accepted into
  P4-W0: widen release-audit paths and place `tools/phase4` under strict MyPy.

## Child 2: prior-session P4-W1 read-only review

- Status: complete; invalidated by the later CI repair
- Agent ID: not retained in the compact cross-session packet
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `2174dc2cfbc0e942c0842991650427b8a75ef91f`
- Result: `READY`, P0/P1/P2 `0/0/0`; the later restart-test repair required a
  new exact-candidate review.

## Child 3: P4-W1 fresh read-only review after CI repair

- Status: complete
- Agent ID: `01a05fce-621c-78c2-a5cc-fff2de60a45a`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `4ab916d27dacdccefdf1619120d3b323da5dc707`
- Result: `NOT_READY`; P0/P1/P2 `0/0/4`. Three repository findings were fixed
  at `a82485dd699ca7cd56c86d1904da7487fa1f87c1`: exact artifact
  membership, installed-wheel engine tests, and current wave evidence. The
  fourth finding corrected the next review packet to the sole canonical
  manifest path; no second manifest was added.

## Child 4: P4-W1 rereview after artifact and Linux isolation repair

- Status: complete
- Agent ID: `01a06000-b402-7331-a920-893ba208ece5`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `7266e494f431ac84d9635b1a044bd15ce303c731`
- Result: `NOT_READY`; P0/P1/P2 `0/0/1`. Artifact membership, all moved
  engine tests under wheel isolation, and the sole canonical manifest path
  were independently resolved. The only P2 was stale completion evidence;
  this bounded evidence-only successor records the completed push, exact-head
  CI runs, and verdict before a fresh review.
