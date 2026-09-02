# Phase 4 Codex dispatch ledger

## Milestone budget

- Coordinator: current P4-W4 continuation from clean source `18dd32b`
- Maximum active children: 6
- Maximum total children per milestone: 12
- Current active children: 0
- Total child lineages used in P4-W4: 0
- Implementation writers: 0
- Independent reviewers in P4-W4: 0

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

## P4-W3 milestone budget

- Status: active
- Active children: 0 of 6
- Total children: 1 of 12
- Identical failures: 0 of 2
- Consecutive timeouts: 0 of 2
- Implementation writer: coordinator only; no child write scope is reserved
- Review lineage: child 13 reserved after exact-head CI, Release audit, and
  CodeQL passed at `2c05dead068ef517ed365d100f3b6273c29eeba9`
- Reset authority: D-031 closes the P4-W2 lineage and starts this milestone
  with a fresh child budget

## Child 13: P4-W3 connector-isolation final review

- Status: complete; lineage closed
- Agent ID: `01a06202-4d7a-7331-a038-239a6e93a630`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only independent reviewer
- Write scope: none
- Source scope: public repository through
  `2c05dead068ef517ed365d100f3b6273c29eeba9`
- Required result: `READY` with P0/P1/P2 `0/0/0`; otherwise return bounded
  findings with exact source evidence
- Result: `NOT_READY`; P0/P1/P2 `0/1/0`. `P4W3-001` proved the default
  in-process `ConnectorRegistry.resolve()` can load and execute the installed
  `open_brain.connectors.v1` entry point outside the bounded worker. Repair must
  make installed connector resolution child-only and add a wheel-only parent
  non-load regression.
- Rereview source scope:
  `27344c6cf83b8b74c11d6ec0c1c3075cbfa98e09`
- Rereview evidence: exact-head CI `33629757827`, Release audit `33629757695`,
  and CodeQL `33629754431` passed before resuming the same lineage
- Final result: `READY`; P0/P1/P2 `0/0/0`. The reviewer reproduced the
  installed parent non-load boundary, confirmed `P4W3-001` closed, found no new
  issues, and declared P4-W3 ready for milestone closure

## P4-W4 milestone budget

- Status: complete
- Active children: 0 of 6
- Total children: 1 of 12
- Identical failures: 0 of 2
- Consecutive timeouts: 0 of 2
- Implementation writer: coordinator only; no child write scope is reserved
- Review lineage: child 14 returned final `READY` at
  `9098ff5e676a76ef1637f30dee99ff6508d46a30`; lineage closed
- Reset authority: D-038 closes the P4-W3 lineage and starts P4-W4 with a fresh
  child budget

## Child 14: P4-W4 and P4A final review

- Status: complete; lineage closed
- Agent ID: `01a0628c-d723-73e0-96cc-f2b3d8ca3f63`
- Model: `gpt-5.6-sol`
- Reasoning effort: `xhigh`
- Role: read-only independent reviewer
- Write scope: none
- Source scope: public repository through
  `7927162096330355520f2de756aa45b48ccb6493`
- Evidence: exact-head CI `33642529540`, Release audit `33642529483`, and
  CodeQL `33642524132` are green
- Required result: `READY` with P0/P1/P2 `0/0/0`; otherwise return bounded
  findings with exact source evidence
- Result: `NOT_READY`; P0/P1/P2 `0/1/1`. `P4A-001` rejects D-040's broad
  legacy-to-app/connector dependency as weaker than the governing plan and
  published migration-interface boundary. `P4A-002` identifies the removed
  artifact-policy path retained in `CLAUDE.md`.
- First rereview source scope:
  `b86beacbc7005b0a7f2ceeb5c009f0a2849579a6`
- First rereview evidence: exact-head CI `33650699793`, Release audit
  `33650699895`, and CodeQL `33650693028` passed before resuming the same
  lineage
- First rereview result: `NOT_READY`; P0/P1/P2 `0/1/1`. The reviewer closed
  `P4A-001` and `P4A-002`. `P4A-003` found the sole external `_compat` import,
  an ambient undeclared `openai` loader. `P4A-004` proved that readiness probe
  `SystemExit` escaped with raw detail. The lineage remains retained for one
  rereview after the focused regressions, full local gates, and new exact-head
  remote checks pass.
- Final source scope:
  `9098ff5e676a76ef1637f30dee99ff6508d46a30`
- Final evidence: exact-head CI `33654478123`, Release audit `33654478071`,
  and CodeQL `33654473793` passed before the second same-lineage rereview
- Final result: `READY`; P0/P1/P2 `0/0/0`. The reviewer independently
  reproduced the focused repair checks and private artifact hashes, explicitly
  closed `P4A-001` through `P4A-004`, found no new issue, and declared P4-W4
  and P4A ready for milestone closure.

## P4-W5 milestone budget

- Status: active
- Active children: 0 of 6
- Total children: 1 of 12
- Identical failures: 0 of 2
- Consecutive timeouts: 0 of 2
- Implementation writer: coordinator only; no child write scope is reserved
- Review lineage: child 15 is closed during source repair and reserved for
  same-lineage rereview after a new exact candidate passes every local and
  remote gate
- Reset authority: P4-W4 child 14 is closed; D-031 and D-048 start P4-W5 with
  a fresh milestone budget and separate source/evidence identities

## Child 15: P4-W5 native artifact and lifecycle review

- Status: repair active; lineage closed and retained for rereview
- Agent ID: `01a0636c-3ef9-7823-ad08-d8dcdb5a48d9`
- Nickname: Kierkegaard
- Role: read-only independent reviewer
- Write scope: none
- Initial source scope:
  `6c2c82de89b554cca8ec6c27b10a57959766c39e`
- Initial evidence: exact-head CI `33667187568`, Release audit `33667187309`,
  and CodeQL `33667180599` passed before review
- Initial result: `NOT_READY`; findings `P4W5-001` through `P4W5-007`
- First rereview source scope:
  `28f1fa7055a9194e433caea666a0c13bf2c126da`
- First rereview evidence: exact-head CI `33672312445`, Release audit
  `33672312619`, and CodeQL `33672307671` passed
- First rereview result: `NOT_READY`; P0/P1/P2 `0/3/1`
- Second rereview source scope:
  `47aee48e248156816b863071b7df199513a7da43`
- Second rereview evidence: local frozen gates and macOS native proof passed;
  exact-head CI `33675602201`, Release audit `33675602206`, and CodeQL
  `33675596478` passed. CI used one failed-only retry for Python 3.12 and did
  not rerun either native job.
- Second rereview result: `NOT_READY`; P0/P1/P2 `0/4/0`. D-050 was accepted.
  `P4W5-002`, `P4W5-003`, `P4W5-005`, and `P4W5-006` are closed.
  `P4W5-001`, `P4W5-004`, and `P4W5-007` remain open; `P4W5-008` is new.
- Third rereview source scope:
  `e55d7488a60a98f2bf5f06cebc18f8fe485e169f`
- Third rereview evidence: exact-head CI `33681462262`, Release audit
  `33681462105`, and CodeQL `33681457587` passed on their first attempt; the
  two target-native jobs and separate local macOS subject are digest-bound in
  `EVIDENCE.md`
- Third rereview result: `NOT_READY`; P0/P1/P2 `0/2/0`. D-050 and D-051 were
  accepted. `P4W5-001`, `P4W5-002`, `P4W5-003`, `P4W5-005`, `P4W5-006`,
  and `P4W5-007` are closed. `P4W5-004` and `P4W5-008` remain open.
- Next review scope: the next frozen source SHA, its fresh local and
  target-native artifact digests, exact-head checks, all prior finding
  dispositions, and D-051
