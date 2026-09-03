# P4-W7 exact-candidate audit

Status: complete. Child 22 returned final `READY`, P0/P1/P2 `0/0/0`, after
closing one sandbox-induced false positive in the same review lineage. P4-W7
and aggregate P4B are accepted. P4-W8 has not started.

## Frozen identities

| Subject | Identity |
|---|---|
| Accepted source | `537bc4f1059ef4b4e8f0916702f38f4e531b13fe` |
| Docs-only evidence head | `ab3f860e23abab2177341c9598011487eaf5ab2b` |
| P4-W5 accepted source | `c7c4fad1b109ac7d7c55d55cdfa57b64a9c910db` |
| Readiness snapshot | `753a1635aa2be81f3ebe6b3723dbc8e46a6d6aa46f1b39003b9d9c39da769d1b` |
| Candidate manifest | `e5891a2dab80034199be0102d39fc6ee5ff84499d1fb10c7f3d27e7f7e337ab5` |
| Candidate file-set aggregate | `82c5ee005ed008e6681a401e598ba485650c68def3d6982d504d158d92645a90` |
| Exact source tree | `1fd73d629664e7284f2be4a9640be73982b5c7272b74ffaabcae0c5da74a2a11` |

The current head changes only governed evidence and the gotcha registry after
the accepted source. P4-W5's phase record and the readiness snapshot still
match their baseline hashes. No P4-W5 target or readiness probe ran.

## P4-W7 gates

| Gate | Direct evidence | Result |
|---|---|---|
| Exact-source CI | CI `33714932363`, attempt 1, source `537bc4f`; 16 of 16 jobs passed. Python 3.12, 3.13, and 3.14 root verification, Phase 4 contracts, isolated connector jobs, Python artifacts, Linux build and three clean hosts, macOS 14 source-equivalent build/lifecycle, and aggregate native checks are green. | Passed |
| CI artifact binding | Six retained bundles were downloaded again. All six Python artifacts, Linux media and checksum, Linux build evidence, three Linux host records, and the macOS 14 source-equivalent record match the final candidate where they are candidate coordinates. | Passed |
| Signed candidate | The standalone verifier rehashed all 23 coordinates. The Linux archive is `aa84da386b70a8be826290d08342636de68ea275b47d9eaecbd74b456e5c72a2`; the macOS DMG is `aa78303a1b1ac7b42215adada8d7932fe55114391292f622073b9aec825a95ac`. Both checksum files pass. | Passed |
| Native media and residue | Fresh unpacked audits reproduce Linux 111/0 members/symlinks and macOS 144/4. Membership and tree digests match. DMG integrity, strict signature, staple, and Gatekeeper checks pass. Candidate inventory has no extra file. | Passed |
| Clean-host lifecycle | Ubuntu 24.04, Ubuntu 26.04, Debian 13, macOS 14 source-equivalent, and exact-signed macOS 26 records pass. They cover install, backup and exact-byte disposable restore, doctor, Portable round trip, prior-schema upgrade, rollback, uninstall, residue, `V0-GATE-07`, and `V0-GATE-13`, with no source checkout or system Python. The exact signed macOS 14 record uses the accepted unavailable-runner code. | Passed |
| Release and history audit | Release audit `33714932452` passed artifact policy, source plus six artifacts, complete reachable history, and Gitleaks. A fresh generic-denylist rerun also passed source plus the exact six candidate Python artifacts and all reachable history; Gitleaks 8.30.1 found no leak across 114 commits. | Passed with the private-input limit below |
| CodeQL | CodeQL `33714929770` passed Python and Actions analysis at `537bc4f`. | Passed |
| License, SBOM, compatibility | The candidate verifier rechecks SPDX 2.3, license bindings, supervisor resources, version `0.1.0`, Portable schema 1 through 1, supported hosts, checksums, and every evidence hash. | Passed |
| Publication absence | The repository has zero tags, releases, release assets, and deployments. The three expected PyPI projects and 15 expected public GitHub package coordinates return not found. The manifest records empty package, release, and tag sets. | Passed with the package-API limit below |
| Fresh P4B review | After Codex CLI 0.153.0 restored execution, child 22 bound source, artifacts, manifest, host evidence, D-054, and every P4A/P4B criterion. Its initial `P4W7-001` signature finding reproduced only in the CLI's macOS read-only sandbox. The same-lineage rerun, the coordinator shell, and all relative, absolute, and deep strict variants passed against unchanged DMG bytes. Child 22 closed the false positive and completed the skipped live checks. | `READY`; P0/P1/P2 `0/0/0` |

## P4A and P4B completion map

| Contract area | Evidence available to the reviewer |
|---|---|
| Gate 0 and P4-W0 inventory | The plan hash is `7fe6e5d1e48b44fb4fba232661a8b01eeca019e4f35a43f1b2c162914905bfd2`. The canonical move manifest, generated reports, acceptance harness, and baseline records remain in the governed workstream. |
| Four distributions and old-path removal | The manifest validator and architecture tests pass at the later accepted source. P4A source `9098ff5` and child 14's final review closed P4A with `READY`, P0/P1/P2 `0/0/0`. |
| Engine and app isolation | Exact-source root tests and artifact verification pass on Python 3.12 through 3.14. The engine-wheel-only and app-plus-engine wheel journeys remain part of the accepted test suite and artifact policy. |
| Wheel-only product gates | The accepted app wheel journey covers first value, daemon, status/doctor, recovery, Portable, upgrade, uninstall, `V0-GATE-07`, and `V0-GATE-13` without connectors, legacy, workspace tools, or source. |
| Connector boundary | Connector isolation passes on Python 3.12 through 3.14. Conformance uses published extension/engine values and the isolated worker; the default app remains valid without the connector distribution. |
| Legacy and private residue | Legacy and workspace code, private fixtures, and unselected optional cloud dependencies are excluded by artifact policy, release audit, architecture tests, and exact candidate validation. |
| P4-W5 native boundary | Accepted source `c7c4fad` and child 15's `READY`, P0/P1/P2 `0/0/0`, bind target-native PyInstaller subjects, lifecycle behavior, no checkout/system-Python dependency, and unchanged P4-W5 evidence. |
| P4-W6 release boundary | Accepted source `537bc4f`, the 23-coordinate manifest, signed/checksummed media, five passed host records, the bounded macOS 14 record, and child 18's P4-W6 `READY`, P0/P1/P2 `0/0/0`, remain unchanged. |
| P4-W7 exact-candidate boundary | This audit binds the exact CI outputs, direct candidate checks, public-state absence checks, and D-054. Child 22 returned final `READY`, P0/P1/P2 `0/0/0`; P4-W7 and P4B are complete. |

P4C recovery, rehearsal, production, and day-0 criteria are outside this audit.
None ran.

## Reviewer adjudication

1. **ACCEPTED:** D-054 satisfies the plan's CI rebuild requirement. Exact-source
   CI rebuilt the six Python artifacts, Linux archive, and macOS
   source-equivalent native subject. The timestamped final DMG remains a
   coordinator-only transform bound by its exact hash and direct final-byte
   checks; rebuilding it would create a different candidate identity.
2. **ACCEPTED:** the fresh generic and Gitleaks audits plus the unchanged
   accepted private-denylist result are sufficient because all bound source
   and artifact identities remain unchanged.
3. **ACCEPTED:** direct publication-absence checks are sufficient despite the
   package-list API scope limit. Tags, releases, release assets, deployments,
   15 expected public GitHub package pages, and three PyPI endpoints remain
   absent. The six retained Actions artifacts require authentication and are
   CI evidence rather than public release assets.

No D-054 adjudication remains rejected or unresolved. This acceptance does not
authorize publication, deployment, or P4-W8.

## Review dispatch outcome

- Child 19 used the Codex CLI with `gpt-5.6-sol`. Both WebSocket and HTTPS
  transports returned HTTP 404 before execution. No report was produced.
- Child 20 changed to the documented `gpt-5.6` family selector. The same two
  transports returned the same pre-execution 404, closing the CLI path under
  the two-identical-failure breaker.
- Child 21 changed to the separate in-app subagent channel with
  `gpt-5.6-sol`. The shared response endpoint returned the same 404 before
  execution. The agent was closed with no result and no file change.
- Child 22 ran after the explicit Codex CLI update from 0.152.1 to 0.153.0 and
  a healthy Doctor check. Its first report was `NOT_READY`, P0/P1/P2 `0/1/0`,
  because `codesign --verify --strict` returned a misleading
  signature-modified result only inside the CLI's macOS read-only sandbox.
  The coordinator immediately ran relative, absolute, and deep strict checks
  against the same SHA-256 and each passed. The same reviewer lineage then
  repeated those checks with a workspace-write sandbox but retained an
  explicit no-write scope; every signature variant passed, the DMG hash and
  worktree were unchanged, and `P4W7-001` was closed as a sandbox-induced
  false positive.
- Child 22 completed the previously skipped exact-run and publication-absence
  queries, accepted all three D-054 adjudications, and returned final `READY`,
  P0/P1/P2 `0/0/0`, with no file change or concern.

P4-W7 and aggregate P4B are complete. P4C and P4-W8 remain unstarted.
