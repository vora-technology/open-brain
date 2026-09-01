# Phase 3 execution evidence

## Gate 0: implementation baseline

- `git fetch --prune origin`: passed.
- `main`, `origin/main`, and launch HEAD:
  `d93c6dae2a22ef028390f30c990b27968229178e`; ahead/behind `0/0`.
- Reviewed plan SHA-256:
  `e842eac8a5a933d20405bc84bde0ecf87474c7d4317018f32ac6ef95ef0263b7`.
- Goal `cbolden15/agent-config#62`: open with `goal` label; parent `#41` open;
  completed Phase 2 child `#51` closed.
- Open product PRs: only unrelated Dependabot PR `#1`; untouched.
- Protected-branch checks: `verify (3.12)`, `verify (3.13)`, `verify (3.14)`,
  and `public-artifacts` required with strict branch freshness.
- Baseline `make verify`: passed Ruff, strict MyPy on 439 source files, 2,981
  tests, wheel/sdist builds, and artifact policy.
- Planning-only commit: `e8a4ec2`.
- Forbidden-scope evidence: no source/test implementation preceded the
  planning commit; no production, live Brain, private predecessor, package
  publication, deployment, service install, or unrelated PR action occurred.

## P3-W0: frozen appliance seams

- Worker: `P3-W0-IMPLEMENT-01`, Codex `gpt-5.4` high, exclusive W0 scope.
- Red evidence: focused collection failed because the new
  `DaemonMutationPathUnavailableError` contract did not yet exist.
- Green focused Pytest: 92 passed.
- Focused Ruff: passed.
- Strict MyPy: passed on 439 source files.
- Full `make verify`: passed Ruff, MyPy, 2,984 tests, wheel/sdist builds, and
  artifact policy.
- `git diff --check`: passed.
- Behavior: `open_brain.services.appliance_application` and
  `open_brain.services.appliance_entrypoints` are reserved without repointing
  current scripts; `.open-brain/run/control.sock` is daemon-owned and fails
  closed until lifecycle implementation.
- Failure gate: no `open_brain.operations` or release import in shipping W0
  surfaces, no Phase 4 package work, and no current service behavior change.
- Worker environment note: default uv cache access was sandbox-denied before
  tests started; the worker changed strategy to a disposable cache and then
  produced the required red/green evidence. Coordinator checks used the
  normal project environment and passed.
