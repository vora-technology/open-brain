# Phase 4 execution evidence

## Gate 0 launch

- Explicit user launch received on 2026-09-01.
- Runtime goal registered for Goal #63.
- Fresh fetch confirmed `origin/main` at
  `3b89a4ba4787a378e6040ff042bd117da881918d`.
- Exact reviewed plan SHA-256 confirmed as
  `7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`.
- New branch `goal/open-brain-phase4` created from that base; reviewed planning
  commit cherry-picked as `68c34d723e8f0bbdc7a51d5c5070e63e994b335d`.
- New implementation workstream created; planning task IDs and state were not
  reused.
- Public required checks, current workflow hosts, open parent goals, local
  ARM64/Python/uv/signing tools, project gotchas, and latest private Goal #24
  handoff were inspected.
- No runtime source moved, no native artifact built, and no production or live
  Brain state was accessed during launch.

## Gate 0 baseline verification

- `make verify`: passed Ruff, strict MyPy on 474 source files, all 3,114 tests,
  isolated wheel/sdist builds, and artifact policy.
- Current source-ownership validator: 53 tests passed.
- Source plus wheel/sdist release audit: passed with one untracked synthetic
  denylist.
- Reachable-history audit: passed with the same denylist.
- Explicit artifact-policy rerun and `git diff --check`: passed.
- Inventory equality: all 224 tracked runtime Python files exactly match the
  canonical classification; owner counts are engine 46, app 34, connector 5,
  legacy 135, and workspace 4; temporary live debt is zero.
- Additional manifest subjects observed: 250 tracked Python files under
  `tests/` and 36 tracked schema/fixture files.
- Required public checks: strict linear `main`, `verify (3.12)`, `verify
  (3.13)`, `verify (3.14)`, and `public-artifacts`; force pushes and branch
  deletion disabled.
- Successful CI logs directly identify macOS 14 ARM64 and Ubuntu 24.04 x86_64
  builders.
- Local build host: ARM64, Python 3.12, `uv`, `notarytool`, and one valid
  Developer ID Application identity. A ready notary credential profile was not
  found on either checked authorized host.
- Private read-only preflight: exact scoped helper and host identity checks
  passed; arbitrary sudo and root SSH remained denied; service, writer,
  synchronization, executable-reference, and recovery-readiness inventories
  completed with zero mutations and no private output in this repository.
- Private recovery access is not currently ready and must be remediated and
  re-proved before P4-W8. The prior Goal #24 apply remains historical and will
  not be rerun.
- Launch status comments:
  `cbolden15/agent-config#63` comment `5502133708`, parent `#41` comment
  `5502134010`, and parent `#24` comment `5502134267`.
