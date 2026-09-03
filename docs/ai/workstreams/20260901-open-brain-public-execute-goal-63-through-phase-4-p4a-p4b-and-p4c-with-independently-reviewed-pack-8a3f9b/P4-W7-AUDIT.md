# P4-W7 exact-candidate audit

Status: audit complete; blocked before independent review. P4-W7 and P4B are
not accepted.

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
| Fresh P4B review | One new read-only reviewer must bind source, artifacts, manifest, host evidence, D-054, and every P4A/P4B criterion after the gates above. Three dispatches failed at the shared Codex response endpoint before any reviewer executed. | Blocked; no verdict |

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
| P4-W7 exact-candidate boundary | This audit binds the exact CI outputs, direct candidate checks, public-state absence checks, and D-054. It remains incomplete until the new reviewer returns `READY`, P0/P1/P2 `0/0/0`. |

P4C recovery, rehearsal, production, and day-0 criteria are outside this audit.
None ran.

## Required reviewer adjudication

1. Decide whether D-054 satisfies the plan's CI rebuild requirement. CI rebuilt
   the six Python artifacts, Linux archive, and macOS source-equivalent native
   subject. The timestamped final DMG remained a coordinator-only Developer ID
   signing and notarization transform under D-052, then received fresh direct
   hash, signature, staple, Gatekeeper, unpacked-tree, host, and manifest
   validation. A byte-identical CI rebuild would create a new signed candidate.
2. Decide whether the fresh audit plus the unchanged accepted private-denylist
   result is sufficient. The private denylist was not present in this shell,
   so the fresh scan used the tool's exact no-additional-terms marker and
   Gitleaks while retaining the earlier accepted private scan.
3. Decide whether publication absence is sufficiently direct. The available
   token lacks package-list scope, so the audit checked zero tags/releases/
   release assets, all expected public package pages, and all three PyPI
   project endpoints. Authenticated Actions artifacts remain CI evidence and
   are not release assets.

Any rejected adjudication is a P4-W7 blocker. It does not authorize a rebuild,
repair, publication, deployment, or P4-W8.

## Review dispatch outcome

- Child 19 used the Codex CLI with `gpt-5.6-sol`. Both WebSocket and HTTPS
  transports returned HTTP 404 before execution. No report was produced.
- Child 20 changed to the documented `gpt-5.6` family selector. The same two
  transports returned the same pre-execution 404, closing the CLI path under
  the two-identical-failure breaker.
- Child 21 changed to the separate in-app subagent channel with
  `gpt-5.6-sol`. The shared response endpoint returned the same 404 before
  execution. The agent was closed with no result and no file change.

No reviewer inspected or adjudicated the audit. P4-W7 must resume at the fresh
read-only review after the response endpoint or account routing is restored.
