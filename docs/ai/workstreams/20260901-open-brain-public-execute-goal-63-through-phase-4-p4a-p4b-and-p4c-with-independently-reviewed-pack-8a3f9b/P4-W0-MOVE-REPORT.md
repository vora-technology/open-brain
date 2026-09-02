# Phase 4 move report

Generated from `docs/v0-package-classification.json`; do not edit by hand.

- Total subjects: `555`
- app: `65`
- connectors: `8`
- engine: `103`
- legacy: `296`
- workspace: `83`

| Current subject | Kind | Distribution | Target | Artifacts |
|---|---|---|---|---|
| `.github/dependabot.yml` | `release-tool` | `workspace` | `.github/dependabot.yml` | `excluded` |
| `.github/workflows/ci.yml` | `release-tool` | `workspace` | `.github/workflows/ci.yml` | `excluded` |
| `.github/workflows/release-audit.yml` | `release-tool` | `workspace` | `.github/workflows/release-audit.yml` | `excluded` |
| `LICENSE` | `package-resource` | `workspace` | `LICENSE` | `app-native, app-sdist, app-wheel, connector-sdist, connector-wheel, engine-sdist, engine-wheel` |
| `Makefile` | `release-tool` | `workspace` | `Makefile` | `excluded` |
| `NOTICE` | `package-resource` | `workspace` | `NOTICE` | `app-native, app-sdist, app-wheel, connector-sdist, connector-wheel, engine-sdist, engine-wheel` |
| `README.md` | `package-resource` | `workspace` | `README.md` | `app-sdist` |
| `docs/ai/workstreams/20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b/P4-W0-EXPECTED-RED.json` | `generated-resource` | `workspace` | `docs/ai/workstreams/20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b/P4-W0-EXPECTED-RED.json` | `excluded` |
| `docs/ai/workstreams/20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b/P4-W0-IMPORT-REPORT.md` | `generated-resource` | `workspace` | `docs/ai/workstreams/20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b/P4-W0-IMPORT-REPORT.md` | `excluded` |
| `docs/ai/workstreams/20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b/P4-W0-MOVE-REPORT.md` | `generated-resource` | `workspace` | `docs/ai/workstreams/20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b/P4-W0-MOVE-REPORT.md` | `excluded` |
| `docs/architecture.md` | `package-resource` | `workspace` | `docs/architecture.md` | `app-sdist` |
| `docs/architecture/proposed-v0-system-architecture.md` | `package-resource` | `workspace` | `docs/architecture/proposed-v0-system-architecture.md` | `app-sdist` |
| `docs/artifact-characterization.md` | `package-resource` | `workspace` | `docs/artifact-characterization.md` | `app-sdist` |
| `docs/capture-contract.md` | `package-resource` | `workspace` | `docs/capture-contract.md` | `app-sdist` |
| `docs/cli-characterization.md` | `package-resource` | `workspace` | `docs/cli-characterization.md` | `app-sdist` |
| `docs/cli.md` | `package-resource` | `workspace` | `docs/cli.md` | `app-sdist` |
| `docs/configuration.md` | `package-resource` | `workspace` | `docs/configuration.md` | `app-sdist` |
| `docs/current-record-characterization.md` | `package-resource` | `workspace` | `docs/current-record-characterization.md` | `app-sdist` |
| `docs/operations.md` | `package-resource` | `workspace` | `docs/operations.md` | `app-sdist` |
| `docs/portable-brain-v1.md` | `package-resource` | `workspace` | `docs/portable-brain-v1.md` | `app-sdist` |
| `docs/privacy-model.md` | `package-resource` | `workspace` | `docs/privacy-model.md` | `app-sdist` |
| `docs/threat-model.md` | `package-resource` | `workspace` | `docs/threat-model.md` | `app-sdist` |
| `docs/v0-expansion-backlog.md` | `package-resource` | `workspace` | `docs/v0-expansion-backlog.md` | `app-sdist` |
| `docs/v0-package-classification.json` | `release-tool` | `workspace` | `docs/v0-package-classification.json` | `excluded` |
| `docs/v0-product-contract.md` | `package-resource` | `workspace` | `docs/v0-product-contract.md` | `app-sdist` |
| `docs/v0-release-boundary.md` | `package-resource` | `workspace` | `docs/v0-release-boundary.md` | `app-sdist` |
| `examples/config.example.toml` | `package-resource` | `workspace` | `examples/config.example.toml` | `app-sdist` |
| `examples/ios-shortcut.md` | `package-resource` | `workspace` | `examples/ios-shortcut.md` | `app-sdist` |
| `examples/synthetic-vault/README.md` | `package-resource` | `workspace` | `examples/synthetic-vault/README.md` | `app-sdist` |
| `pyproject.toml` | `release-tool` | `workspace` | `pyproject.toml` | `excluded` |
| `pyproject.toml#project.scripts.open-brain` | `entry-point` | `app` | `packages/app/pyproject.toml#project.scripts.open-brain` | `app-native, app-sdist, app-wheel` |
| `pyproject.toml#project.scripts.open-brain-mcp` | `entry-point` | `app` | `packages/app/pyproject.toml#project.scripts.open-brain-mcp` | `app-native, app-sdist, app-wheel` |
| `release/phase4-compatibility.json` | `release-resource` | `workspace` | `release/phase4-compatibility.json` | `app-sdist, connector-sdist, engine-sdist` |
| `release/phase4-toolchain.json` | `release-resource` | `workspace` | `release/phase4-toolchain.json` | `app-sdist, connector-sdist, engine-sdist` |
| `release/public-history-allowlist.json` | `release-resource` | `workspace` | `release/public-history-allowlist.json` | `app-sdist, connector-sdist, engine-sdist` |
| `release/v0-artifact-policy.json` | `release-resource` | `workspace` | `release/v0-artifact-policy.json` | `app-sdist, connector-sdist, engine-sdist` |
| `schemas/portable-brain/v1/action.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/action.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/batch-row.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/batch-row.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/canonical-page-frontmatter.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/canonical-page-frontmatter.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/capture.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/capture.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/common.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/common.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/decision.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/decision.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/event.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/event.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/manifest.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/manifest.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/measurement.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/measurement.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/proposal.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/proposal.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/publication.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/publication.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/reference-or-file.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/reference-or-file.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/routing.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/routing.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/space-frontmatter.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/space-frontmatter.json` | `engine-sdist, engine-wheel` |
| `schemas/portable-brain/v1/text.json` | `schema` | `engine` | `packages/engine/src/open_brain_engine/portable/schemas/v1/text.json` | `engine-sdist, engine-wheel` |
| `src/open_brain/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/__main__.py` | `runtime` | `app` | `packages/app/src/open_brain/__main__.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/capture/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/capture/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/capture/auth.py` | `runtime` | `app` | `packages/app/src/open_brain/capture/auth.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/capture/distillation.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/distillation.py` | `legacy-only` |
| `src/open_brain/capture/distillation_worker.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/distillation_worker.py` | `legacy-only` |
| `src/open_brain/capture/drain.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/drain.py` | `legacy-only` |
| `src/open_brain/capture/egress.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/egress.py` | `legacy-only` |
| `src/open_brain/capture/extractors/__init__.py` | `runtime` | `connectors` | `packages/connectors/src/open_brain_connectors/capture/extractors/__init__.py` | `connector-sdist, connector-wheel` |
| `src/open_brain/capture/extractors/article.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/extractors/article.py` | `legacy-only` |
| `src/open_brain/capture/extractors/social.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/extractors/social.py` | `legacy-only` |
| `src/open_brain/capture/extractors/text.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/extractors/text.py` | `legacy-only` |
| `src/open_brain/capture/extractors/youtube.py` | `runtime` | `connectors` | `packages/connectors/src/open_brain_connectors/capture/extractors/youtube.py` | `connector-sdist, connector-wheel` |
| `src/open_brain/capture/http.py` | `runtime` | `app` | `packages/app/src/open_brain/capture/http.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/capture/media.py` | `runtime` | `connectors` | `packages/connectors/src/open_brain_connectors/capture/media.py` | `connector-sdist, connector-wheel` |
| `src/open_brain/capture/models.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/capture/models.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/capture/poll.py` | `runtime` | `connectors` | `packages/connectors/src/open_brain_connectors/capture/poll.py` | `connector-sdist, connector-wheel` |
| `src/open_brain/capture/queue.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/queue.py` | `legacy-only` |
| `src/open_brain/capture/redaction.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/capture/redaction.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/capture/service.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/capture/service.py` | `legacy-only` |
| `src/open_brain/cli/__init__.py` | `runtime` | `app` | `packages/app/src/open_brain/cli/__init__.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/cli/_common.py` | `runtime` | `app` | `packages/app/src/open_brain/cli/_common.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/cli/_registry.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/_registry.py` | `legacy-only` |
| `src/open_brain/cli/capture.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/capture.py` | `legacy-only` |
| `src/open_brain/cli/config.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/config.py` | `legacy-only` |
| `src/open_brain/cli/doctor.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/doctor.py` | `legacy-only` |
| `src/open_brain/cli/explain.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/explain.py` | `legacy-only` |
| `src/open_brain/cli/ledger.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/ledger.py` | `legacy-only` |
| `src/open_brain/cli/main.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/main.py` | `legacy-only` |
| `src/open_brain/cli/migrate.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/migrate.py` | `legacy-only` |
| `src/open_brain/cli/operations.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/operations.py` | `legacy-only` |
| `src/open_brain/cli/phase1.py` | `runtime` | `app` | `packages/app/src/open_brain/cli/phase1.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/cli/phase1_registry.py` | `runtime` | `app` | `packages/app/src/open_brain/cli/phase1_registry.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/cli/phase6_adapters.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/phase6_adapters.py` | `legacy-only` |
| `src/open_brain/cli/production_adapters.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/production_adapters.py` | `legacy-only` |
| `src/open_brain/cli/proposals.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/proposals.py` | `legacy-only` |
| `src/open_brain/cli/query.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/query.py` | `legacy-only` |
| `src/open_brain/cli/review.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/review.py` | `legacy-only` |
| `src/open_brain/cli/scheduled.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/scheduled.py` | `legacy-only` |
| `src/open_brain/cli/social.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/social.py` | `legacy-only` |
| `src/open_brain/cli/status.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/cli/status.py` | `legacy-only` |
| `src/open_brain/config.py` | `runtime` | `app` | `packages/app/src/open_brain/config.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/core/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/core/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/core/ids.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/core/ids.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/core/locks.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/core/locks.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/core/models.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/core/models.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/core/policy.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/core/policy.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/core/ports.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/core/ports.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/dev/__init__.py` | `runtime` | `workspace` | `tools/open_brain_dev/__init__.py` | `excluded` |
| `src/open_brain/dev/artifact_policy.py` | `runtime` | `workspace` | `tools/open_brain_dev/artifact_policy.py` | `excluded` |
| `src/open_brain/dev/public_history_audit.py` | `runtime` | `workspace` | `tools/open_brain_dev/public_history_audit.py` | `excluded` |
| `src/open_brain/dev/release_audit.py` | `runtime` | `workspace` | `tools/open_brain_dev/release_audit.py` | `excluded` |
| `src/open_brain/engine/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/authority.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/authority.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/backup.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/backup.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/backup_ports.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/backup_ports.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/capture.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/capture.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/contracts.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/contracts.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/local.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/local.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/local_store.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/local_store.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/maintenance.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/maintenance.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/materializer.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/materializer.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/normalization.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/normalization.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/portability.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/portability.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/portability_ports.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/portability_ports.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/portable_index.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/portable_index.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/reconciliation.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/reconciliation.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/retrieval.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/retrieval.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/review.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/review.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/engine/spaces.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/engine/spaces.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/events/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/events/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/events/store.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/events/store.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/integrations/__init__.py` | `runtime` | `app` | `packages/app/src/open_brain/integrations/__init__.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/integrations/config.py` | `runtime` | `app` | `packages/app/src/open_brain/integrations/config.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/integrations/context.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/context.py` | `legacy-only` |
| `src/open_brain/integrations/dev_workflows.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/dev_workflows.py` | `legacy-only` |
| `src/open_brain/integrations/finance.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/finance.py` | `legacy-only` |
| `src/open_brain/integrations/hooks.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/hooks.py` | `legacy-only` |
| `src/open_brain/integrations/life_os.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/life_os.py` | `legacy-only` |
| `src/open_brain/integrations/life_os_runtime.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/life_os_runtime.py` | `legacy-only` |
| `src/open_brain/integrations/mail_calendar.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/mail_calendar.py` | `legacy-only` |
| `src/open_brain/integrations/mcp.py` | `runtime` | `app` | `packages/app/src/open_brain/integrations/mcp.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/integrations/messaging.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/messaging.py` | `legacy-only` |
| `src/open_brain/integrations/messaging_runtime.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/messaging_runtime.py` | `legacy-only` |
| `src/open_brain/integrations/obsidian.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/obsidian.py` | `legacy-only` |
| `src/open_brain/integrations/phase1_ui.py` | `runtime` | `app` | `packages/app/src/open_brain/integrations/phase1_ui.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/integrations/ports.py` | `runtime` | `app` | `packages/app/src/open_brain/integrations/ports.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/integrations/relationships.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/relationships.py` | `legacy-only` |
| `src/open_brain/integrations/repository_identity.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/repository_identity.py` | `legacy-only` |
| `src/open_brain/integrations/retrieval.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/retrieval.py` | `legacy-only` |
| `src/open_brain/integrations/runtime_audit.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/integrations/runtime_audit.py` | `legacy-only` |
| `src/open_brain/integrations/ui.py` | `runtime` | `app` | `packages/app/src/open_brain/integrations/ui.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/ledger/__init__.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/__init__.py` | `legacy-only` |
| `src/open_brain/ledger/age.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/age.py` | `legacy-only` |
| `src/open_brain/ledger/embed.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/embed.py` | `legacy-only` |
| `src/open_brain/ledger/index.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/index.py` | `legacy-only` |
| `src/open_brain/ledger/merge.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/merge.py` | `legacy-only` |
| `src/open_brain/ledger/models.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/models.py` | `legacy-only` |
| `src/open_brain/ledger/reconcile.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/reconcile.py` | `legacy-only` |
| `src/open_brain/ledger/reinforce.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/reinforce.py` | `legacy-only` |
| `src/open_brain/ledger/render.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/render.py` | `legacy-only` |
| `src/open_brain/ledger/requarantine.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/requarantine.py` | `legacy-only` |
| `src/open_brain/ledger/sanitize.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/sanitize.py` | `legacy-only` |
| `src/open_brain/ledger/scan.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/scan.py` | `legacy-only` |
| `src/open_brain/ledger/service.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/service.py` | `legacy-only` |
| `src/open_brain/ledger/slim.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/slim.py` | `legacy-only` |
| `src/open_brain/ledger/stage.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/stage.py` | `legacy-only` |
| `src/open_brain/ledger/store.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/store.py` | `legacy-only` |
| `src/open_brain/ledger/synthesis.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/synthesis.py` | `legacy-only` |
| `src/open_brain/ledger/synthesis_store.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/ledger/synthesis_store.py` | `legacy-only` |
| `src/open_brain/migrate/__init__.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/migrate/__init__.py` | `legacy-only` |
| `src/open_brain/migrate/_models.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/migrate/_models.py` | `legacy-only` |
| `src/open_brain/migrate/_support.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/migrate/_support.py` | `legacy-only` |
| `src/open_brain/migrate/config.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/migrate/config.py` | `legacy-only` |
| `src/open_brain/migrate/content.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/migrate/content.py` | `legacy-only` |
| `src/open_brain/migrate/state.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/migrate/state.py` | `legacy-only` |
| `src/open_brain/operations/__init__.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/__init__.py` | `legacy-only` |
| `src/open_brain/operations/backup.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/backup.py` | `legacy-only` |
| `src/open_brain/operations/backup_writer.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/backup_writer.py` | `legacy-only` |
| `src/open_brain/operations/capture_jobs.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/capture_jobs.py` | `legacy-only` |
| `src/open_brain/operations/catalog.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/catalog.py` | `legacy-only` |
| `src/open_brain/operations/curation_runtime.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/curation_runtime.py` | `legacy-only` |
| `src/open_brain/operations/cutover.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/cutover.py` | `legacy-only` |
| `src/open_brain/operations/cutover_doctor.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/cutover_doctor.py` | `legacy-only` |
| `src/open_brain/operations/cutover_verification.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/cutover_verification.py` | `legacy-only` |
| `src/open_brain/operations/doctor.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/doctor.py` | `legacy-only` |
| `src/open_brain/operations/git_sync_runtime.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/git_sync_runtime.py` | `legacy-only` |
| `src/open_brain/operations/index.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/index.py` | `legacy-only` |
| `src/open_brain/operations/index_writer.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/index_writer.py` | `legacy-only` |
| `src/open_brain/operations/local_effect.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/local_effect.py` | `legacy-only` |
| `src/open_brain/operations/models.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/models.py` | `legacy-only` |
| `src/open_brain/operations/now.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/now.py` | `legacy-only` |
| `src/open_brain/operations/now_runtime.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/now_runtime.py` | `legacy-only` |
| `src/open_brain/operations/optional_jobs.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/optional_jobs.py` | `legacy-only` |
| `src/open_brain/operations/probes.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/probes.py` | `legacy-only` |
| `src/open_brain/operations/production_bindings.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/production_bindings.py` | `legacy-only` |
| `src/open_brain/operations/recovery.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/recovery.py` | `legacy-only` |
| `src/open_brain/operations/render.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/render.py` | `legacy-only` |
| `src/open_brain/operations/replay_journal.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/replay_journal.py` | `legacy-only` |
| `src/open_brain/operations/retention.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/retention.py` | `legacy-only` |
| `src/open_brain/operations/runlog.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/runlog.py` | `legacy-only` |
| `src/open_brain/operations/runlog_store.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/runlog_store.py` | `legacy-only` |
| `src/open_brain/operations/scheduled_results.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/scheduled_results.py` | `legacy-only` |
| `src/open_brain/operations/scheduler.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/scheduler.py` | `legacy-only` |
| `src/open_brain/operations/shadow.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/shadow.py` | `legacy-only` |
| `src/open_brain/operations/status.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/status.py` | `legacy-only` |
| `src/open_brain/operations/writer_jobs.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/operations/writer_jobs.py` | `legacy-only` |
| `src/open_brain/parity/__init__.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/parity/__init__.py` | `legacy-only` |
| `src/open_brain/parity/harness.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/parity/harness.py` | `legacy-only` |
| `src/open_brain/parity/observation.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/parity/observation.py` | `legacy-only` |
| `src/open_brain/parity/runner.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/parity/runner.py` | `legacy-only` |
| `src/open_brain/portable/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/portable/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/portable/v1.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/portable/v1.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/production/__init__.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/__init__.py` | `legacy-only` |
| `src/open_brain/production/application.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/application.py` | `legacy-only` |
| `src/open_brain/production/assets.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/assets.py` | `legacy-only` |
| `src/open_brain/production/capture.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/capture.py` | `legacy-only` |
| `src/open_brain/production/capture_publication.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/capture_publication.py` | `legacy-only` |
| `src/open_brain/production/curation.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/curation.py` | `legacy-only` |
| `src/open_brain/production/errors.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/errors.py` | `legacy-only` |
| `src/open_brain/production/git_sync.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/git_sync.py` | `legacy-only` |
| `src/open_brain/production/imessage.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/imessage.py` | `legacy-only` |
| `src/open_brain/production/local_jobs.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/local_jobs.py` | `legacy-only` |
| `src/open_brain/production/media.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/media.py` | `legacy-only` |
| `src/open_brain/production/optional_automation.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/optional_automation.py` | `legacy-only` |
| `src/open_brain/production/personal_capture.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/personal_capture.py` | `legacy-only` |
| `src/open_brain/production/project_commit_bridge.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/project_commit_bridge.py` | `legacy-only` |
| `src/open_brain/production/providers.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/providers.py` | `legacy-only` |
| `src/open_brain/production/retention.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/retention.py` | `legacy-only` |
| `src/open_brain/production/runtime.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/runtime.py` | `legacy-only` |
| `src/open_brain/production/sqlite_backup.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/sqlite_backup.py` | `legacy-only` |
| `src/open_brain/production/transport.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/transport.py` | `legacy-only` |
| `src/open_brain/production/youtube_bridge.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/production/youtube_bridge.py` | `legacy-only` |
| `src/open_brain/production/youtube_poll.py` | `runtime` | `connectors` | `packages/connectors/src/open_brain_connectors/production/youtube_poll.py` | `connector-sdist, connector-wheel` |
| `src/open_brain/profile.py` | `runtime` | `app` | `packages/app/src/open_brain/profile.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/providers/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/providers/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/providers/base.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/providers/base.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/providers/deterministic.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/providers/deterministic.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/providers/local.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/providers/local.py` | `legacy-only` |
| `src/open_brain/providers/optional_cloud.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/providers/optional_cloud.py` | `legacy-only` |
| `src/open_brain/providers/transcription.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/providers/transcription.py` | `legacy-only` |
| `src/open_brain/release/__init__.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/release/__init__.py` | `legacy-only` |
| `src/open_brain/release/day_zero.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/release/day_zero.py` | `legacy-only` |
| `src/open_brain/release/evidence.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/release/evidence.py` | `legacy-only` |
| `src/open_brain/release/installation.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/release/installation.py` | `legacy-only` |
| `src/open_brain/release/replacement.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/release/replacement.py` | `legacy-only` |
| `src/open_brain/release/stabilization.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/release/stabilization.py` | `legacy-only` |
| `src/open_brain/review/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/review/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/review/maintenance.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/review/maintenance.py` | `legacy-only` |
| `src/open_brain/review/models.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/review/models.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/review/routing.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/review/routing.py` | `legacy-only` |
| `src/open_brain/review/service.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/review/service.py` | `legacy-only` |
| `src/open_brain/review/store.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/review/store.py` | `legacy-only` |
| `src/open_brain/services/__init__.py` | `runtime` | `app` | `packages/app/src/open_brain/services/__init__.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_application.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_application.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_auth.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_auth.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_daemon.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_daemon.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_entrypoints.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_entrypoints.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_entrypoints.py#run_http` | `entry-point` | `app` | `packages/app/src/open_brain/services/appliance_entrypoints.py#run_http` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_history.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_history.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_init.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_init.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_lifecycle.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_lifecycle.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_recovery.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_recovery.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_scheduler.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_scheduler.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_status.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_status.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/appliance_supervisors.py` | `runtime` | `app` | `packages/app/src/open_brain/services/appliance_supervisors.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/application.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/services/application.py` | `legacy-only` |
| `src/open_brain/services/capabilities.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/services/capabilities.py` | `legacy-only` |
| `src/open_brain/services/composition.py` | `runtime` | `app` | `packages/app/src/open_brain/services/composition.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/connectors.py` | `runtime` | `app` | `packages/app/src/open_brain/services/connectors.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/entrypoints.py` | `runtime` | `legacy` | `packages/legacy/src/open_brain_legacy/services/entrypoints.py` | `legacy-only` |
| `src/open_brain/services/http_server.py` | `runtime` | `app` | `packages/app/src/open_brain/services/http_server.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/mcp_stdio.py` | `runtime` | `app` | `packages/app/src/open_brain/services/mcp_stdio.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/phase1_application.py` | `runtime` | `app` | `packages/app/src/open_brain/services/phase1_application.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/phase1_entrypoints.py` | `runtime` | `app` | `packages/app/src/open_brain/services/phase1_entrypoints.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/services/runtime.py` | `runtime` | `app` | `packages/app/src/open_brain/services/runtime.py` | `app-native, app-sdist, app-wheel` |
| `src/open_brain/storage/__init__.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/__init__.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/filesystem.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/filesystem.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/frontmatter.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/frontmatter.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/locks.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/locks.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/markdown.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/markdown.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/operational.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/operational.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/sqlite.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/sqlite.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/staging.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/staging.py` | `engine-sdist, engine-wheel` |
| `src/open_brain/storage/writer_record.py` | `runtime` | `engine` | `packages/engine/src/open_brain_engine/storage/writer_record.py` | `engine-sdist, engine-wheel` |
| `tests/__init__.py` | `test` | `workspace` | `tests/__init__.py` | `excluded` |
| `tests/conftest.py` | `test` | `workspace` | `tests/conftest.py` | `excluded` |
| `tests/contract/test_current_record_characterization.py` | `test` | `workspace` | `tests/contract/test_current_record_characterization.py` | `excluded` |
| `tests/contract/test_portable_brain_v1.py` | `test` | `engine` | `packages/engine/tests/contract/test_portable_brain_v1.py` | `excluded` |
| `tests/fixtures/phase0/current_records.json` | `fixture` | `legacy` | `packages/legacy/tests/fixtures/phase0/current_records.json` | `legacy-only` |
| `tests/fixtures/phase0/public_cli.json` | `fixture` | `legacy` | `packages/legacy/tests/fixtures/phase0/public_cli.json` | `legacy-only` |
| `tests/fixtures/portable-brain/v1/brain-root/brain.toml` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/brain.toml` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/content/spaces/studio/_space.md` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/content/spaces/studio/_space.md` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/content/spaces/studio/notes/page_123e4567-e89b-42d3-a456-426614174005.md` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/content/spaces/studio/notes/page_123e4567-e89b-42d3-a456-426614174005.md` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/actions/2026/08/action_123e4567-e89b-42d3-a456-42661417400b.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/actions/2026/08/action_123e4567-e89b-42d3-a456-42661417400b.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/decisions/2026/08/decision_123e4567-e89b-42d3-a456-426614174009.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/decisions/2026/08/decision_123e4567-e89b-42d3-a456-426614174009.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/decisions/2026/08/decision_123e4567-e89b-42d3-a456-426614174019.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/decisions/2026/08/decision_123e4567-e89b-42d3-a456-426614174019.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174008.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174008.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174018.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/proposals/2026/08/proposal_123e4567-e89b-42d3-a456-426614174018.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/publications/2026/08/publication_123e4567-e89b-42d3-a456-42661417400a.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/publications/2026/08/publication_123e4567-e89b-42d3-a456-42661417400a.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/history/routes/2026/08/route_123e4567-e89b-42d3-a456-426614174012.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/history/routes/2026/08/route_123e4567-e89b-42d3-a456-426614174012.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/portable-manifest.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/portable-manifest.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/batches/2026/08/batch_123e4567-e89b-42d3-a456-426614174006.jsonl` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/batches/2026/08/batch_123e4567-e89b-42d3-a456-426614174006.jsonl` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/batches/2026/08/batch_123e4567-e89b-42d3-a456-426614174007.jsonl` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/batches/2026/08/batch_123e4567-e89b-42d3-a456-426614174007.jsonl` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/blobs/sha256/ea/ea8df5c802b7fcb7c952e1b143ee8d2670e7d8b8ae8843af2ce4f55e3e1ded49` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/blobs/sha256/ea/ea8df5c802b7fcb7c952e1b143ee8d2670e7d8b8ae8843af2ce4f55e3e1ded49` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174100.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174100.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174101.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174101.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174102.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174102.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174103.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/brain-root/sources/captures/2026/08/capture_123e4567-e89b-42d3-a456-426614174103.json` | `engine-sdist, engine-wheel` |
| `tests/fixtures/portable-brain/v1/cases.json` | `fixture` | `engine` | `packages/engine/src/open_brain_engine/portable/conformance/v1/cases.json` | `engine-sdist, engine-wheel` |
| `tests/integration/__init__.py` | `test` | `workspace` | `tests/integration/__init__.py` | `excluded` |
| `tests/integration/capture/test_capture_service.py` | `test` | `legacy` | `packages/legacy/tests/integration/capture/test_capture_service.py` | `excluded` |
| `tests/integration/capture/test_distillation.py` | `test` | `legacy` | `packages/legacy/tests/integration/capture/test_distillation.py` | `excluded` |
| `tests/integration/capture/test_distillation_queue.py` | `test` | `legacy` | `packages/legacy/tests/integration/capture/test_distillation_queue.py` | `excluded` |
| `tests/integration/capture/test_distillation_worker.py` | `test` | `legacy` | `packages/legacy/tests/integration/capture/test_distillation_worker.py` | `excluded` |
| `tests/integration/capture/test_share_http.py` | `test` | `app` | `packages/app/tests/integration/capture/test_share_http.py` | `excluded` |
| `tests/integration/capture/test_social_drain.py` | `test` | `legacy` | `packages/legacy/tests/integration/capture/test_social_drain.py` | `excluded` |
| `tests/integration/capture/test_social_transcription.py` | `test` | `legacy` | `packages/legacy/tests/integration/capture/test_social_transcription.py` | `excluded` |
| `tests/integration/capture/test_youtube_poll.py` | `test` | `connectors` | `packages/connectors/tests/integration/capture/test_youtube_poll.py` | `excluded` |
| `tests/integration/cli/test_capture.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_capture.py` | `excluded` |
| `tests/integration/cli/test_composition.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_composition.py` | `excluded` |
| `tests/integration/cli/test_config.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_config.py` | `excluded` |
| `tests/integration/cli/test_contract.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_contract.py` | `excluded` |
| `tests/integration/cli/test_cron.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_cron.py` | `excluded` |
| `tests/integration/cli/test_digest.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_digest.py` | `excluded` |
| `tests/integration/cli/test_doctor.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_doctor.py` | `excluded` |
| `tests/integration/cli/test_explain.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_explain.py` | `excluded` |
| `tests/integration/cli/test_okf.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_okf.py` | `excluded` |
| `tests/integration/cli/test_phase0_characterization.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_phase0_characterization.py` | `excluded` |
| `tests/integration/cli/test_phase6_adapters.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_phase6_adapters.py` | `excluded` |
| `tests/integration/cli/test_production_adapters.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_production_adapters.py` | `excluded` |
| `tests/integration/cli/test_proposals.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_proposals.py` | `excluded` |
| `tests/integration/cli/test_query.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_query.py` | `excluded` |
| `tests/integration/cli/test_registry.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_registry.py` | `excluded` |
| `tests/integration/cli/test_retention.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_retention.py` | `excluded` |
| `tests/integration/cli/test_review.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_review.py` | `excluded` |
| `tests/integration/cli/test_review_decisions.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_review_decisions.py` | `excluded` |
| `tests/integration/cli/test_scheduled_routes.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_scheduled_routes.py` | `excluded` |
| `tests/integration/cli/test_share.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_share.py` | `excluded` |
| `tests/integration/cli/test_status.py` | `test` | `legacy` | `packages/legacy/tests/integration/cli/test_status.py` | `excluded` |
| `tests/integration/connectors/test_youtube_reference.py` | `test` | `legacy` | `packages/legacy/tests/integration/connectors/test_youtube_reference.py` | `excluded` |
| `tests/integration/context/test_context.py` | `test` | `legacy` | `packages/legacy/tests/integration/context/test_context.py` | `excluded` |
| `tests/integration/dev_workflows/test_dev_workflows.py` | `test` | `legacy` | `packages/legacy/tests/integration/dev_workflows/test_dev_workflows.py` | `excluded` |
| `tests/integration/engine/__init__.py` | `test` | `workspace` | `tests/integration/engine/__init__.py` | `excluded` |
| `tests/integration/engine/test_backup.py` | `test` | `app` | `packages/app/tests/integration/engine/test_backup.py` | `excluded` |
| `tests/integration/engine/test_maintenance.py` | `test` | `app` | `packages/app/tests/integration/engine/test_maintenance.py` | `excluded` |
| `tests/integration/engine/test_portability.py` | `test` | `app` | `packages/app/tests/integration/engine/test_portability.py` | `excluded` |
| `tests/integration/engine/test_reconciliation.py` | `test` | `app` | `packages/app/tests/integration/engine/test_reconciliation.py` | `excluded` |
| `tests/integration/engine/test_vertical_slice.py` | `test` | `app` | `packages/app/tests/integration/engine/test_vertical_slice.py` | `excluded` |
| `tests/integration/finance/test_finance.py` | `test` | `legacy` | `packages/legacy/tests/integration/finance/test_finance.py` | `excluded` |
| `tests/integration/hooks/test_hooks.py` | `test` | `legacy` | `packages/legacy/tests/integration/hooks/test_hooks.py` | `excluded` |
| `tests/integration/integrations/test_integration_ports.py` | `test` | `app` | `packages/app/tests/integration/integrations/test_integration_ports.py` | `excluded` |
| `tests/integration/integrations/test_life_os_runtime.py` | `test` | `legacy` | `packages/legacy/tests/integration/integrations/test_life_os_runtime.py` | `excluded` |
| `tests/integration/integrations/test_messaging_runtime.py` | `test` | `legacy` | `packages/legacy/tests/integration/integrations/test_messaging_runtime.py` | `excluded` |
| `tests/integration/ledger/test_apply.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_apply.py` | `excluded` |
| `tests/integration/ledger/test_apply_cli.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_apply_cli.py` | `excluded` |
| `tests/integration/ledger/test_claim_lifecycle.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_claim_lifecycle.py` | `excluded` |
| `tests/integration/ledger/test_lifecycle_cli.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_lifecycle_cli.py` | `excluded` |
| `tests/integration/ledger/test_reconcile.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_reconcile.py` | `excluded` |
| `tests/integration/ledger/test_requarantine.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_requarantine.py` | `excluded` |
| `tests/integration/ledger/test_scan_cli.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_scan_cli.py` | `excluded` |
| `tests/integration/ledger/test_slim_cli.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_slim_cli.py` | `excluded` |
| `tests/integration/ledger/test_stage_cli.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_stage_cli.py` | `excluded` |
| `tests/integration/ledger/test_synthesis_cli.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_synthesis_cli.py` | `excluded` |
| `tests/integration/ledger/test_synthesis_persistence.py` | `test` | `legacy` | `packages/legacy/tests/integration/ledger/test_synthesis_persistence.py` | `excluded` |
| `tests/integration/life_os/test_life_os.py` | `test` | `legacy` | `packages/legacy/tests/integration/life_os/test_life_os.py` | `excluded` |
| `tests/integration/mail_calendar/test_mail_calendar.py` | `test` | `legacy` | `packages/legacy/tests/integration/mail_calendar/test_mail_calendar.py` | `excluded` |
| `tests/integration/mcp/test_mcp.py` | `test` | `app` | `packages/app/tests/integration/mcp/test_mcp.py` | `excluded` |
| `tests/integration/messaging/test_messaging.py` | `test` | `legacy` | `packages/legacy/tests/integration/messaging/test_messaging.py` | `excluded` |
| `tests/integration/migrate/__init__.py` | `test` | `workspace` | `tests/integration/migrate/__init__.py` | `excluded` |
| `tests/integration/migrate/_synthetic.py` | `test` | `engine` | `packages/engine/tests/integration/migrate/_synthetic.py` | `excluded` |
| `tests/integration/migrate/test_backfill.py` | `test` | `legacy` | `packages/legacy/tests/integration/migrate/test_backfill.py` | `excluded` |
| `tests/integration/migrate/test_config.py` | `test` | `legacy` | `packages/legacy/tests/integration/migrate/test_config.py` | `excluded` |
| `tests/integration/migrate/test_content_layout.py` | `test` | `legacy` | `packages/legacy/tests/integration/migrate/test_content_layout.py` | `excluded` |
| `tests/integration/migrate/test_processed_at.py` | `test` | `legacy` | `packages/legacy/tests/integration/migrate/test_processed_at.py` | `excluded` |
| `tests/integration/migrate/test_state.py` | `test` | `legacy` | `packages/legacy/tests/integration/migrate/test_state.py` | `excluded` |
| `tests/integration/operations/test_backup_filesystem.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_backup_filesystem.py` | `excluded` |
| `tests/integration/operations/test_curation_runtime.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_curation_runtime.py` | `excluded` |
| `tests/integration/operations/test_cutover.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_cutover.py` | `excluded` |
| `tests/integration/operations/test_cutover_doctor.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_cutover_doctor.py` | `excluded` |
| `tests/integration/operations/test_cutover_verification.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_cutover_verification.py` | `excluded` |
| `tests/integration/operations/test_doctor_status.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_doctor_status.py` | `excluded` |
| `tests/integration/operations/test_git_sync_runtime.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_git_sync_runtime.py` | `excluded` |
| `tests/integration/operations/test_local_effect.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_local_effect.py` | `excluded` |
| `tests/integration/operations/test_now_runtime.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_now_runtime.py` | `excluded` |
| `tests/integration/operations/test_probes.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_probes.py` | `excluded` |
| `tests/integration/operations/test_production_bindings.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_production_bindings.py` | `excluded` |
| `tests/integration/operations/test_replay_journal.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_replay_journal.py` | `excluded` |
| `tests/integration/operations/test_runlog_store.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_runlog_store.py` | `excluded` |
| `tests/integration/operations/test_shadow.py` | `test` | `legacy` | `packages/legacy/tests/integration/operations/test_shadow.py` | `excluded` |
| `tests/integration/production/test_capture_composition.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_capture_composition.py` | `excluded` |
| `tests/integration/production/test_curation_composition.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_curation_composition.py` | `excluded` |
| `tests/integration/production/test_git_sync_composition.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_git_sync_composition.py` | `excluded` |
| `tests/integration/production/test_imessage_ingress.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_imessage_ingress.py` | `excluded` |
| `tests/integration/production/test_local_jobs.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_local_jobs.py` | `excluded` |
| `tests/integration/production/test_maintenance.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_maintenance.py` | `excluded` |
| `tests/integration/production/test_media_adapters.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_media_adapters.py` | `excluded` |
| `tests/integration/production/test_media_asset_binding.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_media_asset_binding.py` | `excluded` |
| `tests/integration/production/test_optional_automation_config.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_optional_automation_config.py` | `excluded` |
| `tests/integration/production/test_project_commit_bridge.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_project_commit_bridge.py` | `excluded` |
| `tests/integration/production/test_provider_composition.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_provider_composition.py` | `excluded` |
| `tests/integration/production/test_runtime_primitives.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_runtime_primitives.py` | `excluded` |
| `tests/integration/production/test_youtube_bridge.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_youtube_bridge.py` | `excluded` |
| `tests/integration/production/test_youtube_poll_runtime.py` | `test` | `legacy` | `packages/legacy/tests/integration/production/test_youtube_poll_runtime.py` | `excluded` |
| `tests/integration/relationships/test_relationships.py` | `test` | `legacy` | `packages/legacy/tests/integration/relationships/test_relationships.py` | `excluded` |
| `tests/integration/release/test_day_zero.py` | `test` | `workspace` | `tests/integration/release/test_day_zero.py` | `excluded` |
| `tests/integration/release/test_release_evidence.py` | `test` | `workspace` | `tests/integration/release/test_release_evidence.py` | `excluded` |
| `tests/integration/release/test_replacement_evidence.py` | `test` | `workspace` | `tests/integration/release/test_replacement_evidence.py` | `excluded` |
| `tests/integration/release/test_stabilization.py` | `test` | `workspace` | `tests/integration/release/test_stabilization.py` | `excluded` |
| `tests/integration/release/test_v0_artifact_policy.py` | `test` | `workspace` | `tests/integration/release/test_v0_artifact_policy.py` | `excluded` |
| `tests/integration/retrieval/test_repository_identity.py` | `test` | `legacy` | `packages/legacy/tests/integration/retrieval/test_repository_identity.py` | `excluded` |
| `tests/integration/retrieval/test_retrieval.py` | `test` | `legacy` | `packages/legacy/tests/integration/retrieval/test_retrieval.py` | `excluded` |
| `tests/integration/review/__init__.py` | `test` | `workspace` | `tests/integration/review/__init__.py` | `excluded` |
| `tests/integration/review/test_maintenance.py` | `test` | `legacy` | `packages/legacy/tests/integration/review/test_maintenance.py` | `excluded` |
| `tests/integration/review/test_phase4_intent_routing.py` | `test` | `legacy` | `packages/legacy/tests/integration/review/test_phase4_intent_routing.py` | `excluded` |
| `tests/integration/review/test_saved_content_intent.py` | `test` | `legacy` | `packages/legacy/tests/integration/review/test_saved_content_intent.py` | `excluded` |
| `tests/integration/runtime_audit/test_runtime_audit.py` | `test` | `legacy` | `packages/legacy/tests/integration/runtime_audit/test_runtime_audit.py` | `excluded` |
| `tests/integration/services/test_appliance_control.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_control.py` | `excluded` |
| `tests/integration/services/test_appliance_daemon.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_daemon.py` | `excluded` |
| `tests/integration/services/test_appliance_entrypoints.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_entrypoints.py` | `excluded` |
| `tests/integration/services/test_appliance_init.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_init.py` | `excluded` |
| `tests/integration/services/test_appliance_recovery.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_recovery.py` | `excluded` |
| `tests/integration/services/test_appliance_run_history.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_run_history.py` | `excluded` |
| `tests/integration/services/test_appliance_scheduler.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_scheduler.py` | `excluded` |
| `tests/integration/services/test_appliance_supervisors.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_supervisors.py` | `excluded` |
| `tests/integration/services/test_appliance_uninstall.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_uninstall.py` | `excluded` |
| `tests/integration/services/test_appliance_upgrade.py` | `test` | `app` | `packages/app/tests/integration/services/test_appliance_upgrade.py` | `excluded` |
| `tests/integration/services/test_connectors.py` | `test` | `legacy` | `packages/legacy/tests/integration/services/test_connectors.py` | `excluded` |
| `tests/integration/services/test_entrypoints.py` | `test` | `app` | `packages/app/tests/integration/services/test_entrypoints.py` | `excluded` |
| `tests/integration/services/test_phase1_surfaces.py` | `test` | `legacy` | `packages/legacy/tests/integration/services/test_phase1_surfaces.py` | `excluded` |
| `tests/integration/services/test_phase2_surfaces.py` | `test` | `app` | `packages/app/tests/integration/services/test_phase2_surfaces.py` | `excluded` |
| `tests/integration/services/test_protocols.py` | `test` | `app` | `packages/app/tests/integration/services/test_protocols.py` | `excluded` |
| `tests/integration/services/test_service_composition.py` | `test` | `app` | `packages/app/tests/integration/services/test_service_composition.py` | `excluded` |
| `tests/integration/storage/test_obsidian_notes.py` | `test` | `legacy` | `packages/legacy/tests/integration/storage/test_obsidian_notes.py` | `excluded` |
| `tests/integration/ui/test_phase3_ui.py` | `test` | `app` | `packages/app/tests/integration/ui/test_phase3_ui.py` | `excluded` |
| `tests/integration/ui/test_ui.py` | `test` | `app` | `packages/app/tests/integration/ui/test_ui.py` | `excluded` |
| `tests/parity/cli/__init__.py` | `test` | `legacy` | `packages/legacy/tests/parity/cli/__init__.py` | `excluded` |
| `tests/parity/cli/test_command_ownership.py` | `test` | `legacy` | `packages/legacy/tests/parity/cli/test_command_ownership.py` | `excluded` |
| `tests/parity/cross_surface/__init__.py` | `test` | `legacy` | `packages/legacy/tests/parity/cross_surface/__init__.py` | `excluded` |
| `tests/parity/cross_surface/_preflight.py` | `test` | `legacy` | `packages/legacy/tests/parity/cross_surface/_preflight.py` | `excluded` |
| `tests/parity/cross_surface/test_one_writer_safety.py` | `test` | `legacy` | `packages/legacy/tests/parity/cross_surface/test_one_writer_safety.py` | `excluded` |
| `tests/parity/cross_surface/test_owner_gated_defers.py` | `test` | `legacy` | `packages/legacy/tests/parity/cross_surface/test_owner_gated_defers.py` | `excluded` |
| `tests/parity/cross_surface/test_status_and_redaction.py` | `test` | `legacy` | `packages/legacy/tests/parity/cross_surface/test_status_and_redaction.py` | `excluded` |
| `tests/parity/operations/test_backup_writer.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_backup_writer.py` | `excluded` |
| `tests/parity/operations/test_cutover_preflight.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_cutover_preflight.py` | `excluded` |
| `tests/parity/operations/test_job_001_doctor_probe.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_001_doctor_probe.py` | `excluded` |
| `tests/parity/operations/test_job_002_index_owner.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_002_index_owner.py` | `excluded` |
| `tests/parity/operations/test_job_003_now_owner.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_003_now_owner.py` | `excluded` |
| `tests/parity/operations/test_job_004_sqlite_snapshot.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_004_sqlite_snapshot.py` | `excluded` |
| `tests/parity/operations/test_job_005_imessage_ingress.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_005_imessage_ingress.py` | `excluded` |
| `tests/parity/operations/test_job_006_close_day_prepare.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_006_close_day_prepare.py` | `excluded` |
| `tests/parity/operations/test_job_007_signal_scan.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_007_signal_scan.py` | `excluded` |
| `tests/parity/operations/test_job_008_lint.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_008_lint.py` | `excluded` |
| `tests/parity/operations/test_job_009_hook_sync.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_009_hook_sync.py` | `excluded` |
| `tests/parity/operations/test_job_010_social_ledger.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_010_social_ledger.py` | `excluded` |
| `tests/parity/operations/test_job_011_capture_backup.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_011_capture_backup.py` | `excluded` |
| `tests/parity/operations/test_job_012_curation.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_012_curation.py` | `excluded` |
| `tests/parity/operations/test_job_013_writer_doctor.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_013_writer_doctor.py` | `excluded` |
| `tests/parity/operations/test_job_014_full_backup.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_014_full_backup.py` | `excluded` |
| `tests/parity/operations/test_job_015_git_sync.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_015_git_sync.py` | `excluded` |
| `tests/parity/operations/test_job_016_index.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_016_index.py` | `excluded` |
| `tests/parity/operations/test_job_016_writer.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_016_writer.py` | `excluded` |
| `tests/parity/operations/test_job_017_lifeos_midday.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_017_lifeos_midday.py` | `excluded` |
| `tests/parity/operations/test_job_018_lifeos_plan.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_018_lifeos_plan.py` | `excluded` |
| `tests/parity/operations/test_job_019_lifeos_reset.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_019_lifeos_reset.py` | `excluded` |
| `tests/parity/operations/test_job_020_message_extract.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_020_message_extract.py` | `excluded` |
| `tests/parity/operations/test_job_021_message_sync.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_021_message_sync.py` | `excluded` |
| `tests/parity/operations/test_job_022_now.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_022_now.py` | `excluded` |
| `tests/parity/operations/test_job_023_personal_backup.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_023_personal_backup.py` | `excluded` |
| `tests/parity/operations/test_job_024_retention.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_024_retention.py` | `excluded` |
| `tests/parity/operations/test_job_025_runtime_state_backup.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_025_runtime_state_backup.py` | `excluded` |
| `tests/parity/operations/test_job_026_ui.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_026_ui.py` | `excluded` |
| `tests/parity/operations/test_job_027_ingress.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_027_ingress.py` | `excluded` |
| `tests/parity/operations/test_job_028_share_ingest.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_028_share_ingest.py` | `excluded` |
| `tests/parity/operations/test_job_029_youtube_poll.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_029_youtube_poll.py` | `excluded` |
| `tests/parity/operations/test_job_030_now_single_writer.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_030_now_single_writer.py` | `excluded` |
| `tests/parity/operations/test_job_contracts.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_job_contracts.py` | `excluded` |
| `tests/parity/operations/test_phase_b_writer_specs.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_phase_b_writer_specs.py` | `excluded` |
| `tests/parity/operations/test_renderer.py` | `test` | `legacy` | `packages/legacy/tests/parity/operations/test_renderer.py` | `excluded` |
| `tests/parity/phase6/test_reconciliation.py` | `test` | `legacy` | `packages/legacy/tests/parity/phase6/test_reconciliation.py` | `excluded` |
| `tests/parity/phase7/__init__.py` | `test` | `legacy` | `packages/legacy/tests/parity/phase7/__init__.py` | `excluded` |
| `tests/parity/phase7/capture_scenarios.json` | `test-resource` | `legacy` | `packages/legacy/tests/parity/phase7/capture_scenarios.json` | `legacy-only` |
| `tests/parity/phase7/test_capture_scenarios.py` | `test` | `engine` | `packages/engine/tests/parity/phase7/test_capture_scenarios.py` | `excluded` |
| `tests/parity/phase7/test_executable_runner.py` | `test` | `legacy` | `packages/legacy/tests/parity/phase7/test_executable_runner.py` | `excluded` |
| `tests/parity/phase7/test_harness.py` | `test` | `legacy` | `packages/legacy/tests/parity/phase7/test_harness.py` | `excluded` |
| `tests/parity/phase7/test_observation.py` | `test` | `legacy` | `packages/legacy/tests/parity/phase7/test_observation.py` | `excluded` |
| `tests/parity/phase7/test_reconciliation.py` | `test` | `legacy` | `packages/legacy/tests/parity/phase7/test_reconciliation.py` | `excluded` |
| `tests/phase4/__init__.py` | `test` | `workspace` | `tests/phase4/__init__.py` | `excluded` |
| `tests/phase4/test_acceptance_harness.py` | `test` | `workspace` | `tests/phase4/test_acceptance_harness.py` | `excluded` |
| `tests/phase4/test_move_manifest.py` | `test` | `workspace` | `tests/phase4/test_move_manifest.py` | `excluded` |
| `tests/security/test_appliance_auth.py` | `test` | `workspace` | `tests/security/test_appliance_auth.py` | `excluded` |
| `tests/security/test_appliance_logs.py` | `test` | `workspace` | `tests/security/test_appliance_logs.py` | `excluded` |
| `tests/security/test_architecture_boundaries.py` | `test` | `workspace` | `tests/security/test_architecture_boundaries.py` | `excluded` |
| `tests/security/test_architecture_imports.py` | `test` | `workspace` | `tests/security/test_architecture_imports.py` | `excluded` |
| `tests/security/test_direct_edit_reconciliation.py` | `test` | `workspace` | `tests/security/test_direct_edit_reconciliation.py` | `excluded` |
| `tests/security/test_engine_isolation.py` | `test` | `workspace` | `tests/security/test_engine_isolation.py` | `excluded` |
| `tests/security/test_intent_policy_boundary.py` | `test` | `workspace` | `tests/security/test_intent_policy_boundary.py` | `excluded` |
| `tests/security/test_no_network.py` | `test` | `workspace` | `tests/security/test_no_network.py` | `excluded` |
| `tests/security/test_path_safety.py` | `test` | `workspace` | `tests/security/test_path_safety.py` | `excluded` |
| `tests/security/test_persistence_redaction.py` | `test` | `workspace` | `tests/security/test_persistence_redaction.py` | `excluded` |
| `tests/security/test_provider_privacy.py` | `test` | `workspace` | `tests/security/test_provider_privacy.py` | `excluded` |
| `tests/security/test_public_result_projection.py` | `test` | `workspace` | `tests/security/test_public_result_projection.py` | `excluded` |
| `tests/security/test_public_result_residue.py` | `test` | `workspace` | `tests/security/test_public_result_residue.py` | `excluded` |
| `tests/security/test_release_audit.py` | `test` | `workspace` | `tests/security/test_release_audit.py` | `excluded` |
| `tests/security/test_release_history_audit.py` | `test` | `workspace` | `tests/security/test_release_history_audit.py` | `excluded` |
| `tests/security/test_ssrf.py` | `test` | `workspace` | `tests/security/test_ssrf.py` | `excluded` |
| `tests/security/test_staged_executor.py` | `test` | `workspace` | `tests/security/test_staged_executor.py` | `excluded` |
| `tests/security/test_ui_sanitization.py` | `test` | `workspace` | `tests/security/test_ui_sanitization.py` | `excluded` |
| `tests/unit/__init__.py` | `test` | `workspace` | `tests/unit/__init__.py` | `excluded` |
| `tests/unit/capture/__init__.py` | `test` | `workspace` | `tests/unit/capture/__init__.py` | `excluded` |
| `tests/unit/capture/extractors/__init__.py` | `test` | `workspace` | `tests/unit/capture/extractors/__init__.py` | `excluded` |
| `tests/unit/capture/extractors/test_article.py` | `test` | `legacy` | `packages/legacy/tests/unit/capture/extractors/test_article.py` | `excluded` |
| `tests/unit/capture/extractors/test_media.py` | `test` | `connectors` | `packages/connectors/tests/unit/capture/extractors/test_media.py` | `excluded` |
| `tests/unit/capture/extractors/test_social.py` | `test` | `legacy` | `packages/legacy/tests/unit/capture/extractors/test_social.py` | `excluded` |
| `tests/unit/capture/extractors/test_text.py` | `test` | `legacy` | `packages/legacy/tests/unit/capture/extractors/test_text.py` | `excluded` |
| `tests/unit/capture/extractors/test_youtube.py` | `test` | `connectors` | `packages/connectors/tests/unit/capture/extractors/test_youtube.py` | `excluded` |
| `tests/unit/capture/test_models.py` | `test` | `engine` | `packages/engine/tests/unit/capture/test_models.py` | `excluded` |
| `tests/unit/capture/test_queue.py` | `test` | `legacy` | `packages/legacy/tests/unit/capture/test_queue.py` | `excluded` |
| `tests/unit/capture/test_redaction.py` | `test` | `engine` | `packages/engine/tests/unit/capture/test_redaction.py` | `excluded` |
| `tests/unit/core/test_ids.py` | `test` | `engine` | `packages/engine/tests/unit/core/test_ids.py` | `excluded` |
| `tests/unit/core/test_intent_policy.py` | `test` | `engine` | `packages/engine/tests/unit/core/test_intent_policy.py` | `excluded` |
| `tests/unit/core/test_models.py` | `test` | `engine` | `packages/engine/tests/unit/core/test_models.py` | `excluded` |
| `tests/unit/core/test_ports.py` | `test` | `engine` | `packages/engine/tests/unit/core/test_ports.py` | `excluded` |
| `tests/unit/engine/__init__.py` | `test` | `workspace` | `tests/unit/engine/__init__.py` | `excluded` |
| `tests/unit/engine/test_foundation_contracts.py` | `test` | `app` | `packages/app/tests/unit/engine/test_foundation_contracts.py` | `excluded` |
| `tests/unit/engine/test_local_store.py` | `test` | `engine` | `packages/engine/tests/unit/engine/test_local_store.py` | `excluded` |
| `tests/unit/engine/test_portability_ports.py` | `test` | `app` | `packages/app/tests/unit/engine/test_portability_ports.py` | `excluded` |
| `tests/unit/engine/test_profile.py` | `test` | `app` | `packages/app/tests/unit/engine/test_profile.py` | `excluded` |
| `tests/unit/ledger/__init__.py` | `test` | `workspace` | `tests/unit/ledger/__init__.py` | `excluded` |
| `tests/unit/ledger/test_merge.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_merge.py` | `excluded` |
| `tests/unit/ledger/test_sanitize.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_sanitize.py` | `excluded` |
| `tests/unit/ledger/test_scan.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_scan.py` | `excluded` |
| `tests/unit/ledger/test_slim.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_slim.py` | `excluded` |
| `tests/unit/ledger/test_stage.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_stage.py` | `excluded` |
| `tests/unit/ledger/test_store.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_store.py` | `excluded` |
| `tests/unit/ledger/test_synthesis.py` | `test` | `legacy` | `packages/legacy/tests/unit/ledger/test_synthesis.py` | `excluded` |
| `tests/unit/providers/__init__.py` | `test` | `workspace` | `tests/unit/providers/__init__.py` | `excluded` |
| `tests/unit/providers/test_base.py` | `test` | `engine` | `packages/engine/tests/unit/providers/test_base.py` | `excluded` |
| `tests/unit/providers/test_deterministic.py` | `test` | `engine` | `packages/engine/tests/unit/providers/test_deterministic.py` | `excluded` |
| `tests/unit/providers/test_local.py` | `test` | `legacy` | `packages/legacy/tests/unit/providers/test_local.py` | `excluded` |
| `tests/unit/providers/test_optional_cloud.py` | `test` | `legacy` | `packages/legacy/tests/unit/providers/test_optional_cloud.py` | `excluded` |
| `tests/unit/providers/test_transcription.py` | `test` | `legacy` | `packages/legacy/tests/unit/providers/test_transcription.py` | `excluded` |
| `tests/unit/review/__init__.py` | `test` | `workspace` | `tests/unit/review/__init__.py` | `excluded` |
| `tests/unit/review/test_models.py` | `test` | `engine` | `packages/engine/tests/unit/review/test_models.py` | `excluded` |
| `tests/unit/review/test_review_models.py` | `test` | `engine` | `packages/engine/tests/unit/review/test_review_models.py` | `excluded` |
| `tests/unit/review/test_store_schema.py` | `test` | `legacy` | `packages/legacy/tests/unit/review/test_store_schema.py` | `excluded` |
| `tests/unit/storage/__init__.py` | `test` | `workspace` | `tests/unit/storage/__init__.py` | `excluded` |
| `tests/unit/storage/_factories.py` | `test` | `engine` | `packages/engine/tests/unit/storage/_factories.py` | `excluded` |
| `tests/unit/storage/test_events.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_events.py` | `excluded` |
| `tests/unit/storage/test_filesystem.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_filesystem.py` | `excluded` |
| `tests/unit/storage/test_frontmatter.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_frontmatter.py` | `excluded` |
| `tests/unit/storage/test_locks.py` | `test` | `legacy` | `packages/legacy/tests/unit/storage/test_locks.py` | `excluded` |
| `tests/unit/storage/test_markdown.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_markdown.py` | `excluded` |
| `tests/unit/storage/test_operational.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_operational.py` | `excluded` |
| `tests/unit/storage/test_sqlite.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_sqlite.py` | `excluded` |
| `tests/unit/storage/test_staging.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_staging.py` | `excluded` |
| `tests/unit/storage/test_writer_record.py` | `test` | `engine` | `packages/engine/tests/unit/storage/test_writer_record.py` | `excluded` |
| `tests/unit/test_cli.py` | `test` | `legacy` | `packages/legacy/tests/unit/test_cli.py` | `excluded` |
| `tests/unit/test_config.py` | `test` | `app` | `packages/app/tests/unit/test_config.py` | `excluded` |
| `tests/unit/test_writer_effect_parameters.py` | `test` | `legacy` | `packages/legacy/tests/unit/test_writer_effect_parameters.py` | `excluded` |
| `tools/phase4/__init__.py` | `release-tool` | `workspace` | `tools/phase4/__init__.py` | `excluded` |
| `tools/phase4/acceptance_harness.py` | `release-tool` | `workspace` | `tools/phase4/acceptance_harness.py` | `excluded` |
| `tools/phase4/move_manifest.py` | `release-tool` | `workspace` | `tools/phase4/move_manifest.py` | `excluded` |
| `uv.lock` | `release-tool` | `workspace` | `uv.lock` | `excluded` |
