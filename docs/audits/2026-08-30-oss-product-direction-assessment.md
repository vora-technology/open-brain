# Open Brain OSS product direction assessment

- Date: 2026-08-30
- Repository snapshot: `41666f9`
- Product goal: a ready-to-install, always-on second brain for a Mac mini or small Linux home server, useful to a new person without maintainer-specific setup

> Scope note: this assessment predates product contract `0.2`. Its repository findings and OSS sequencing recommendation remain valid, but fixed work/personal organization, text/URL-only capture, and the absence of a hosted compatibility path were superseded by the approved 2026-08-30 product-family decisions.

## Executive assessment

Your concern is supported by the repository evidence. Open Brain has become two projects in one codebase:

1. A strong local-first knowledge engine with capture, provenance, privacy, review, Markdown publication, retrieval, and recovery.
2. A private-system replacement program with migration, parity, synthetic cutover, a 30-job deployment map, predecessor retirement evidence, and several environment-specific integrations.

The first project is the OSS product. The second project has consumed most of the recent implementation and documentation effort. That is why the repository can pass 2,683 tests and build clean packages while still lacking a complete path from install to first useful capture.

This is mainly a sequencing and product-boundary problem. It is not a reason to throw away the core. Keep the safety and durability work. Stop treating private parity, cutover, and integration breadth as the definition of public product completeness.

The recommended correction is to freeze expansion, define one `single-user-local` product profile, and ship one complete vertical path:

```text
install → initialize → capture → process → review/publish → retrieve → survive reboot/restore
```

## Scope and method

The assessment used four repository views and a local video corpus:

- Current code, executable entry points, docs, examples, tests, and configuration.
- Git history from the initial public-safe scaffold through `41666f9`.
- A clean-install thought experiment for macOS and Linux.
- The project's real checks: Ruff, mypy, pytest, and package build.
- 202 local YouTube transcript notes, narrowed to 20 relevant videos and split into product/workflow and technical/operations readings.

The supplied Obsidian Base currently points at a `saved-content` target that does not contain the transcript corpus. The video review therefore used the populated Markdown notes under `social-content/`. Creator benchmarks and promotional claims were not treated as verified facts.

## Current state

### The short version

Open Brain is an unusually well-tested pre-alpha engine, but it is not yet a ready-to-install product.

| Dimension | Current state | Assessment |
|---|---|---|
| Package | Python 3.12–3.14, version `0.1.0`, wheel and sdist build | Good engineering distribution base; no operator release path yet |
| Verification | Ruff passes, mypy passes across 387 files, 2,683 tests pass | Strong |
| Size and pace | 69 commits in 14 days, about 63,948 source lines and 48,087 test lines | Scope expanded much faster than the public user journey |
| Capture pipeline | Durable text/share/web/media paths, provenance, raw storage, distillation, publication | Strong core, but setup and worker operation are not packaged |
| Review | Domain and storage logic exist | Public approve/reject journey is incomplete |
| Retrieval | Lexical Markdown search, bounded work-only MCP, minimal authenticated page UI | Useful first layer; product UI and durable feedback are incomplete |
| Configuration | Six absolute non-overlapping roots plus private provider, service, writer, and integration inputs | Safe, but too manual for a default install |
| Always-on operation | 30 immutable job contracts and launchd/systemd renderers | Contracts exist; installation, enablement, lifecycle, and remediation do not |
| Platform support | Jobs 1–27 target launchd; only jobs 28–30 target systemd | Linux home-server support is not equivalent to Mac support |
| OSS release | License, CI, contributing/security basics, release audit | User onboarding, support/governance, release, and clean-host acceptance remain incomplete |

### What actually works

The code is not a paper architecture. It has real queues, filesystem and SQLite stores, local/cloud provider composition, capture workers, Markdown publication, lexical retrieval, HTTP and MCP processes, scheduled dispatch, backup, restore primitives, retention, and migration code.

The problem is composition for a new operator. A stranger still has to invent the directory layout, create private configuration, choose and run a local model endpoint, establish writer identity, render and install many jobs, understand which worker drains capture, and build their own upgrade and removal process.

The CLI illustrates the gap. It exposes 27 top-level names, but command-specific `--help` currently falls back to the same top-level help. The product has many capabilities without a clear first action.

### How the project got here

The git history has five clear arcs:

| Arc | Direction |
|---|---|
| Core capture, privacy, storage, review, and ledger | Directly supports the OSS product |
| Phase 5 application and operator seams | Mixed; valuable composition plus early breadth |
| Migration, parity, and synthetic cutover evidence | Primarily supports private predecessor replacement |
| Production replacement bindings and 30-job topology | Real code, but shaped around the existing deployment |
| OSS readiness and adjacent integration planning | Corrective intent, not yet a product implementation change |

The committed README still frames Open Brain as the replacement for two private predecessors. The operations docs spend more space on synthetic cutover receipts than on installing and using the product. The repository's center of gravity follows that framing.

## What you are doing well

### 1. The core data model is right

Markdown is readable, portable, and usable without Open Brain. SQLite is appropriate for queues, review state, run evidence, and rebuildable indexes. This is a better OSS foundation than making an opaque vector database the only source of truth.

Keep this distinction:

```text
canonical knowledge = human-readable files
operational state and indexes = SQLite, rebuildable where possible
```

### 2. Provenance and owner intent are first-class

Preserving why the owner saved something is a real product differentiator. So is separating owner-authored thought from third-party source material and requiring review before promotion. Many second-brain tools blur those boundaries.

### 3. Privacy failures are handled as product behavior

Unknown and personal content default local. Cloud use needs explicit authority. Credentials are resolved late. Egress and media execution are bounded. Public outputs omit private paths and secrets. These choices belong in the product itself, with the security appendix documenting them.

### 4. The durability work is valuable

Idempotent ingestion, immutable capture bytes, atomic publication, replay-safe queues, writer locks, verified backups, and disposable restore checks are appropriate for an unattended home-server process. Keep them even while simplifying the surrounding topology.

### 5. The architecture has useful seams

The ports-and-adapters boundaries, work-only MCP surface, optional cloud provider, and separate transport/composition roots make a course correction possible. You can define a much smaller release profile without rewriting the domain core.

## What is not going well

### 1. The private replacement goal displaced the public product goal

The parity harness, synthetic cutover state machines, predecessor migration, stabilization evidence, and retirement gates may be useful to the current private deployment. They do not help a new user install a second brain or complete their first capture.

The project has been measuring completeness against the old system instead of against a new user's outcome.

### 2. Breadth arrived before a golden path

Open Brain includes iMessage, YouTube, social/web ingestion, LifeOS, messaging, repository sync, a project commit bridge, backup profiles, retention, MCP, HTTP, and 30 scheduled jobs. Yet it does not have a five-command quickstart or a complete approve/reject path.

That is the clearest sign of scope drift. Optional integrations should follow a proven core journey, not define it.

### 3. Installability is treated as external deployment work

Rendering a launchd plist or systemd unit is not the same as installing a service. An always-on product must own initialization, service installation, status, restart, upgrade, rollback, and uninstall behavior. Today those steps are explicitly outside the application.

Linux support is also incomplete at the product level. The main writer and maintenance schedule is mapped to launchd, while systemd receives only three ingress jobs.

### 4. Safe defaults have become high-friction defaults

Six roots, several private files, provider configuration, service tokens, writer records, and many jobs are defensible advanced controls. They should not be the first-run interface.

A default profile can create those boundaries beneath one chosen base directory. Advanced operators can still override every root.

### 5. Internal assurance language dominates user language

Terms such as Goal #24, 83 capability rows, Phase 7/8 waves, synthetic parity, receipt chains, and owner-gated cutover are meaningful to the migration program. They should not lead the README or public roadmap.

The open-source readiness audit is useful, but it primarily assesses repository governance and release hygiene. Those tasks matter. They do not substitute for product readiness.

### Work to move off the v0 critical path

| Surface | Recommendation | Why |
|---|---|---|
| Phase 6–8 migration, parity, cutover, stabilization, retirement | Freeze and keep as a separate migration workstream | Private replacement evidence, not public first value |
| 30-job deployment topology | Keep contracts internally; expose one default daemon/service | Too much operator surface for a home install |
| LifeOS, messaging, iMessage, Git sync, project commit bridge | Convert to optional connectors after v0 | Environment-specific and high support burden |
| External plugin integration work | Keep the bounded MCP seam; defer new plugin implementation | The standalone product must work before it becomes another product's plugin |
| Vector/graph retrieval, 3D visualization, shared multi-agent memory | Benchmark and defer | No demonstrated v0 need; canonical files and lexical retrieval already exist |

This is a freeze recommendation, not a deletion recommendation. Do not start a large cleanup before the smaller product boundary has been proven.

## Patterns from the videos to implement

The selected corpus contains several larger AI platforms, but its most repeated and transferable patterns point toward a simpler product with transparent files, selective retrieval, visible curation, and dependable background operation.

### Technical patterns confirmed across the corpus

| Pattern | Video evidence | Open Brain today | Recommendation |
|---|---|---|---|
| Keep hot context small and durable memory outside the prompt | MemPalace, Hermes Fundamentals, the agent-system blueprint, and Deep Agents use small injected memory plus files, session search, or checkpoints | Canonical files and bounded retrieval already support this | Document the tier model and return why each source was selected |
| Use staged retrieval | Five sources support staged or task-specific retrieval; the graph/vector, SQLite, and code-graph sources provide the explicit mode tradeoffs | Public query is lexical; optional embedding index machinery exists | Benchmark exact, paraphrase, freshness, and multi-hop tasks before changing the default |
| Keep files plus local SQLite | MemPalace, Hermes, SQLite + AI, and Deep Agents converge on portable files plus local durable state | This is already Open Brain's strongest architectural choice | Keep indexes rebuildable and avoid a hosted database requirement |
| Treat always-on as a recovery property | Hermes and the two Buzz videos expose sleep, restart, host identity, key availability, and single-machine failure | Job contracts exist; service lifecycle and host recovery proof do not | Test reboot, provider outage, queued work, key/token recovery, backup, and restore |
| Expose a small governed capability surface | MemPalace, Code-Graph-RAG, and OpenWork show the tradeoff between many tools and discover/execute rails | Work-only `brain_query` plus feedback is already appropriately narrow | Keep capture, approval, publication, and egress behind separate scopes |
| Put deterministic workflows around model steps | The agent blueprint and Deep Agents both reserve agents for open-ended work | Capture, routing, review, and publication already follow this pattern | Let models extract or propose; let deterministic code authorize and commit |
| Preserve provenance and review through promotion | Code-Graph-RAG previews exact changes; OpenWork describes drafted memory for review | Open Brain is stronger here than most examples | Make this a headline product behavior and visible part of the UI |

The retrieval lesson is especially important. The corpus does not support choosing vectors or graphs as the new default. It supports a ladder:

```text
metadata/exact match → lexical or FTS → local semantic candidates → graph only for proven multi-hop needs
```

Each layer should return source identity, freshness, and a short selection reason. Canonical Markdown remains the authority.

### Product and workflow patterns

| Pattern | Video evidence | Open Brain today | Recommendation |
|---|---|---|---|
| Start with one default workspace and portable files | Four selected second-brain videos use a folder, small router/catalog, and default workspace; a fifth supports the adoption rationale | The file substrate exists, but first-run does not explain it | Make the promise simple: “your notes stay portable; Open Brain captures, finds, and safely promotes them” |
| Publish a canonical file contract | The strongest examples define stable folders, metadata, source links, and pointers before retrieval machinery | Frontmatter, capture references, taxonomy, and pages exist but are not taught as one contract | Version the minimum page/source/router schema and label every index as rebuildable |
| Tie capture to a visible daily outcome | The Obsidian system, sales brain, and Hermes examples connect capture to inbox, review, preparation, or output | Durable capture exists, but the next step is hard to see | Show where the item landed, what processing is pending, and what decision or review is next |
| Run conservative, reviewable curation on a cadence | Three videos use scheduled sync or nightly proposal reports with evidence and morning review | The review and curation machinery is strong | Expose an evidence-bound proposal report; auto-apply only trivial deterministic repairs |
| Make background work observable | Desktop and VPS examples expose missed schedules, wrong skill selection, and laptop-sleep failures | Run logs and doctor contracts exist, but service setup and remediation are missing | Show owner, last run, next run, failure, retry, queue age, and changed artifacts |
| Preserve source slices through transformation | Book, video, meeting, and sales examples retain chapter, timestamp, transcript, or call identity | Provenance is already a core strength | Keep capture IDs, URLs, timestamps, source digests, and transformation receipts visible |
| Earn complexity with workload evidence | The videos disagree on keyword, vector, graph, and multi-agent designs but agree on stable source files | The architecture already has ports for later acceleration | Add machinery only when a fixture shows a real retrieval or scale failure |

The most important product lesson is that capture alone is not the product. The user needs a short, visible loop:

```text
capture → see where it landed → review the proposed meaning → retrieve or act on it → close the loop
```

That loop should be coherent even though storage, retrieval, review, and external actions remain separate capabilities.

### Video evidence anchors

| Claim group | Representative transcript sources | Confidence and limit |
|---|---|---|
| Default workspace and file contract | [Ben AI](https://www.youtube.com/watch?v=d7VPnW1KsgA), [Nate Herk](https://www.youtube.com/watch?v=8QQ_INxAhRs), [The Next Era of Second Brains](https://www.youtube.com/watch?v=xHAZo1SmnhM), [Systems Thinking](https://www.youtube.com/watch?v=NWyTsKTKka8) | High as a repeated product pattern; not an adoption guarantee |
| Daily loop and reviewable curation | [Build an Obsidian SYSTEM](https://www.youtube.com/watch?v=OZ3ZNhrPbF4), [Nightly memory review](https://www.youtube.com/watch?v=jI4ZVB_MPhU), [Hermes memory and skills](https://www.youtube.com/watch?v=MFi3RUGzwtM) | High for visible inbox/review and evidence-bound proposals; auto-apply thresholds remain a design choice |
| Retrieval and local storage | [Graphs vs Vectors](https://www.youtube.com/watch?v=yqEekIQSVzQ), [SQLite + AI](https://www.youtube.com/watch?v=psSL3Fi5zJE), [Code-Graph-RAG](https://www.youtube.com/watch?v=54td1cCCkT0), [Deep Agents](https://www.youtube.com/watch?v=IZabCqyBJLg) | High for task-specific staging; creator benchmarks were not adopted |
| Always-on operation and capability boundaries | [Hermes Fundamentals](https://www.youtube.com/watch?v=5_N84t1rUU0), [Agent System Design](https://www.youtube.com/watch?v=p5e_b9GXHbg), [OpenWork](https://www.youtube.com/watch?v=Ex-eGzpS53s) | High for failure surfaces and scoped capabilities; no hosting vendor or framework is recommended |

### Patterns not to copy yet

The corpus also contains attractive ideas that would repeat the current scope mistake:

- 2D/3D knowledge graphs as a headline feature.
- Shared memory for fleets of agents.
- Automatic self-editing memory or skill creation without review.
- Broad enterprise connectors and live CRM/calendar automation.
- Hosted vector infrastructure before local retrieval is measured.

These may become useful. None is required to prove that Open Brain is a good second brain for one person on one always-on machine.

## High-level path forward

### Define the v0 product contract first

One supported `single-user-local` profile should do five things:

1. Install from a release artifact without cloning the repository.
2. Initialize one chosen base directory, safe subdirectories, configuration, and a smoke-test provider.
3. Install one supervised service that drains capture and serves review, retrieval, and MCP.
4. Capture text and URLs through CLI or authenticated share, then make them reviewable and queryable.
5. Survive reboot, backup, restore, upgrade, and uninstall while leaving readable Markdown behind.

The local model should improve the experience, not block first capture. The proposed v0 contract is that Open Brain can still store and retrieve source material while model enrichment remains pending. The current product does not yet prove that degraded path, so the vertical-slice acceptance test must settle it before release.

### Architecture options

| Option | Shape | Time | Assessment |
|---|---|---:|---|
| A. Wrap the current topology | Add docs, init, and installer around the existing jobs and roots | About 1 week | Fast, but preserves most operator complexity |
| B. Add a single-user product profile | Freeze legacy surfaces, add one root/profile and one daemon/control plane around the current core | About 2–4 weeks | Recommended near-term correction |
| C. Split the product properly | Core engine, distributable app/control plane, optional connectors, separate legacy-migration package/workstream, and native artifacts for supported hosts | About 4–8 additional weeks | Cleanest long-term architecture, but prove the vertical slice before moving code; evaluate containers separately |

Option B is the best next move. Treat Option C as the target boundary. Do not begin with a repo-wide package split because it could become another long detour before a user journey exists.

### Recommended sequence

| Phase | Outcome | Estimate |
|---|---|---:|
| 0. Reset the release boundary | One-page v0 contract, explicit non-goals, frozen expansion list | 1–2 days |
| 1. Prove the vertical slice | Synthetic text/URL capture through publication, review, and query | 3–5 days |
| 2. Make it an appliance | `init`, default profile, one daemon, launchd/systemd install/status/remove, provider preflight | 1–2 weeks |
| 3. Make daily use clear | Simple inbox/review/search UI, actionable doctor output, backup/restore/reboot test | 3–5 days |
| 4. Release the alpha | Clean-host matrix, artifacts, quickstart, support/security/release basics | 3–5 days |

These estimates assume the existing domain code is retained and the team resists adjacent feature work. A focused alpha is roughly 2–4 weeks for one experienced maintainer. A full architectural separation is a later program.

### Release gate

Do not call v0 ready until these five checks pass:

1. With a prebuilt artifact and one documented provider mode, a clean Mac and clean Ubuntu host meet a provisional 15-minute setup target, excluding model download time, without editing TOML by hand.
2. A text or URL capture becomes visible in the review/inbox flow and queryable after approval or safe publication.
3. Reboot and provider outage do not lose captures; pending enrichment resumes.
4. Backup, disposable restore, upgrade, rollback, and service removal are exercised on release artifacts.
5. Removing Open Brain leaves the user's canonical Markdown readable and documents exactly which operational state remains.

### The next decision

Write and approve the v0 product contract before implementing more uncommitted expansion work or another Phase 7/8 task. The contract should name supported inputs, outputs, platforms, provider and degraded-mode behavior, service model, data layout, and non-goals. Once that exists, every current module can be classified as required, optional, legacy migration, or deferred.

## Evidence

Repository evidence is concentrated in:

- `README.md`, especially the replacement framing and status section.
- `pyproject.toml` for package status and entry points.
- `docs/configuration.md` for required roots and private inputs.
- `docs/operations.md` for the 30-job topology and explicit deployment exclusions.
- `docs/audits/open-source-readiness.md` for public repository gaps.

Coordinator-run verification performed during this assessment:

```text
uv run ruff check .        → passed
uv run mypy                → passed, 387 files
uv run pytest -q           → 2,683 passed
uv run python -m build     → wheel and sdist built
```

The private-denylist release audit was not run. The pre-existing untracked plan was preserved and is not treated as an approved product decision in this document.
