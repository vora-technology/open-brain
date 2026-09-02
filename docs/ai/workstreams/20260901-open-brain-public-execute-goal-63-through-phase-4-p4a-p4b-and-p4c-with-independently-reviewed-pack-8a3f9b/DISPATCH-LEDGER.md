# Phase 4 Codex dispatch ledger

## Milestone budget

- Coordinator: resumed runtime goal thread `01a05fc4-2219-7251-8798-a74a1a200911`
- Maximum active children: 6
- Maximum total children per milestone: 12
- Current active children: 0
- Total child lineages used in P4-W2: 12
- Implementation writers: 0
- Independent reviewers: 11

The lineage budget resets when the coordinator crosses a verified milestone
boundary. A resumed child retains its existing lineage number.

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

## Child 5: P4-W1 final evidence rereview

- Status: complete
- Agent ID: not retained in the compact cross-session packet
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `aab6f1e0891d551a87a2968ef9fb0dae1a8e62e2`
- Result: `READY`; P0/P1/P2 `0/0/0`. Exact-head CI and repaired completion
  evidence closed P4-W1 before any P4-W2 movement began.

## Child 6: P4-W2 source-candidate review

- Status: complete
- Agent ID: `01a0605c-1ea9-7c43-80ce-eda630776e52`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `85428b125ddd370cfa6a6c2be20f2aab4669bf7e`
- Result: `NOT_READY`; P0/P1/P2 `0/3/1`. The review found unreachable
  installed supervisor mode, a hard-coded isolation interpreter, incomplete
  private/undeclared app import enforcement, and stale completion evidence.
  All three P1 findings are repaired at
  `7d87c3968e15de5d98f7e509c8c8a31c4c5b500c`; exact-head CI, release audit,
  and CodeQL passed before this bounded evidence repair.

## Child 7: P4-W2 dynamic-import rereview

- Status: complete
- Agent ID: `01a06077-219b-7cf3-a2e1-b5245ae2297f`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `579b45bc12247d34ed612798fc2a6021ccc1d30a`
- Result: `NOT_READY`; P0/P1/P2 `0/1/0`. Prior supervisor, interpreter-matrix,
  and evidence findings were closed. The sole P1 found dynamic-import
  bypasses through `builtins`, assignment aliases, and reflective access,
  plus a false positive for a shadowed local `importlib` object. The repair at
  `e27ac3c3ad7daa4748b094490fdadab6e66a3773` adds lexical provenance,
  exact callsite binding, unresolved-capability rejection, and focused
  positive and negative regressions.

## Child 8: P4-W2 reflective-import rereview

- Status: complete
- Agent ID: `01a0609c-413f-7443-a219-d3a1e6821517`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `0a67a26210b79d0c91fa8953846560db34903034`
- Result: `NOT_READY`; P0/P1/P2 `0/1/1`. Prior supervisor and interpreter
  findings were closed. The P1 reproduced an importer escape through
  `sys.modules["builtins"]` and identified related runtime namespace helpers.
  The P2 corrected the installed app-suite evidence from 402 tests to its
  exact 400-test scope. The repair at
  `d8e2cb20f0268e16ebdd5b46053d5081dab7ac7c` rejects reflective and dynamic
  evaluation capabilities, records the private target, and adds focused
  positive and negative regressions.

## Child 9: P4-W2 flow-sensitive import rereview

- Status: complete
- Agent ID: `01a060b9-cab4-7a83-b9b5-07b8fafe9081`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `e483973e7f8153b97aa5a44b049d787d08fd884f`
- Result: `NOT_READY`; P0/P1/P2 `0/1/0`. Prior supervisor, interpreter,
  evidence, direct dynamic import, and runtime namespace findings were closed.
  The P1 found bounded reflection through `sys.__dict__`,
  `sys.__getattribute__`, and function `__globals__`; path-insensitive
  rebinding; and false positives for loop, `with`, and exception shadows. The
  repair at `bd994a0288f8711f216e130c25c45f7a654eb90f` adds conservative
  provenance joins, complete binding scopes, reflective-path handling, and
  focused positive and negative regressions.

## Child 10: P4-W2 import-alias and comprehension rereview

- Status: complete
- Agent ID: `01a060e4-6405-7c11-8637-f637c056e0d1`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `0cff2ea6077b2450febd07f456310aff1f6ffd25`
- Result: `NOT_READY`; P0/P1/P2 `0/2/0`. Prior lifecycle, interpreter,
  evidence, reflection, and control-flow findings were closed. One P1 found
  missing provenance for aliases of modeled module members. The other found
  incorrect enclosing-scope semantics for assignment expressions inside
  comprehensions. The repair at
  `e103255b2ab03c3312206383b71ce38fcde67b8e` unifies member provenance,
  implements PEP 572 scope, and adds positive and shadow-negative regressions.

## Child 11: P4-W2 equivalent-loader and argument-provenance rereview

- Status: complete
- Agent ID: `01a06108-dde1-7571-85ce-51f0af170988`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- Source scope: public repository through
  `995bd781869901e772eee0c7fdfd0ab8132065d5`
- Result: `NOT_READY`; P0/P1/P2 `0/2/0`. Prior package, interpreter,
  reflection, scope, alias, and comprehension findings were closed. One P1
  found equivalent import and reflection spellings with untracked authority.
  The other found that a reviewed dynamic-import argument could be replaced
  without changing its approved name-based signature. The repair at
  `559690e14b9a1dd935566b54e97ec8f2b73f8d06` adds semantic capability and
  pristine-parameter provenance, rejects internal optional-loader roots, and
  adds focused positive, negative, and installed-wheel regressions.

## Child 12: P4-W2 closed-provider-registry final review and rereviews

- Status: complete
- Agent ID: `01a06141-8911-7f61-a7d6-159e04063ef5`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only reviewer
- Write scope: none
- First source scope: public repository through
  `ce909a525dbc66ec5d893892984f2814f7bb9e71`
- First result: no verdict. The coordinator stopped the in-progress review
  when the generic loader architecture was superseded.
- Completed source scope:
  `9ca31ba36c44e4e4a269e5c932fae27fa174831e`
- Evidence scope:
  `ee2f8c22ac1bd00fd6a3d2924071b8ff23a32238`
- Result: `NOT_READY`; P0/P1/P2 `0/0/1`. The sole P2 found a stale
  dynamic-import review in the canonical manifest and proved that the normal
  architecture gate filtered the moved source before stale-review validation.
  The repair at `30d49d31d35f86e26be3c0ac99b884a47d76b5f6` removes the stale
  record, validates reviews against current source locations, and adds a
  moved-source regression.
- Final source scope:
  `30d49d31d35f86e26be3c0ac99b884a47d76b5f6`
- Final evidence scope:
  `e20be9debc6cd68cd443a3df00f6c2cd76041cb3`
- Final result: `READY`; P0/P1/P2 `0/0/0`. The reviewer confirmed the prior
  P2 is closed and declared P4-W2 ready for milestone closure. The lineage was
  then closed. The reviewer budget resets for P4-W3.
