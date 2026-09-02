# P4-W0 read-only implementation map

Verdict: `READY`; P0/P1/P2 `0/2/2`.

## Observed boundary

- `docs/v0-package-classification.json` is the current canonical ownership
  inventory and contains all 224 runtime files, one dynamic-import review, and
  zero temporary live debt.
- The existing architecture validator covers runtime files only. P4-W0 must
  extend canonical coverage to 250 tracked Python files under `tests/`, 36
  schema/fixture files, entry points, package resources, generated reports, and
  release tools.
- Current packaging has two installed scripts and two Portable package-data
  trees. Current CI has root verification, macOS source-checkout lifecycle,
  public artifact safety, and CodeQL, but no dedicated Phase 4 contract job.

## Required implementation

- Extend the existing canonical JSON rather than creating a second ownership
  list. Preserve current runtime ownership fields and add movement fields;
  place every non-runtime subject in one sibling canonical subject map.
- Add `tools/phase4` validator/report and installed-artifact harness modules,
  `tests/phase4` self-tests, one bounded expected-red report outside the green
  gate, and generated move/import reports.
- Add dedicated real-subject CI for the validator/harness self-tests. Widen the
  release-audit trigger to include the manifest, Phase 4 tools, and Phase 4
  tests.
- Put `tools/phase4` under strict MyPy. Keep runtime-generated Portable
  manifests in identity-compatibility checks rather than source-path ownership.

## Findings incorporated

- P1: the release-audit path filter omitted the new manifest JSON, tools, and
  tests, so a P4-W0-only PR could skip required artifact safety.
- P1: strict MyPy covered only `src` and `tests`, leaving the validator and
  harness unchecked.
- P2: installed entry points and reserved internal entry-point functions must
  not be conflated.
- P2: generated-resource ownership must cover source-controlled package data,
  while runtime-generated Portable manifests remain runtime identity evidence.
