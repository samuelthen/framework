# WorkTrace framework validation — 27 October 2026

The response-accounting implementation passes its software checks. A real
saved-data inventory also verifies complete identity coverage for the existing
eight-task pilot. **Per-component token costs and intermediate passing versions
have not been empirically established in this checkout.**

## Completed checks

- 149 project, study and follow-up tests passed, including three new end-to-end
  exporter tests. The exporter preserves shared-response budgets, unassigned
  no-tool expenditure and generated-but-unexecuted expenditure. Missing usage
  remains null, and duplicate response IDs fail before output creation.
- Seven original reliability probes passed.
- Three restore-scope probes passed. These and the broader regression suite are
  implementation checks, not benchmark-task evaluations.
- All 769 candidate IDs agree between the original component inventory and the
  reconciled annotations. Their source order, action index, component index and
  parent operation identity are preserved.
- The candidates cover all 449 native calls across 16 runs and eight paired tasks.
  Native-call totals agree with the saved run table. There are 413 distinct
  generating response IDs among those operations.

The response and native-operation joins use exact run/action identities, not
command-string similarity. `component_identity_join.csv` exports this join and
keeps input/cache/output fields null. Inferred native-call states are explicitly
separate from unresolved within-call component execution states.

## Real archived pilot inventory

These are totals over eight successful runs per model, conditional on the
original joint-success development sample. Output tokens are recorded **run
totals**, not extracted per-response or role-attributed usage.

| Model | Candidate components | Native calls | Generating response IDs | Recorded output tokens |
| --- | ---: | ---: | ---: | ---: |
| Gemini | 391 | 333 | 316 | 241,344 |
| Luna | 378 | 116 | 97 | 23,998 |

Counts depend strongly on work packaging: candidate-component totals are close,
while native-call and response counts differ. The archived token totals also
differ. This supports keeping these units separate; it does not identify which
role caused the resource difference or establish annotation accuracy.

Across all emitted candidates there are 233 direct, 331 non-direct and 205
uncertain labels. These are an inventory, **not performed-component precision**:
known unexecuted candidates must be excluded from that precision denominator.
Role inventory: 270 exploration, 159 verification, 58 edit and 282 administration.
Existing semantic labels and reported precision results were not changed.

## Missing empirical inputs and boundaries

The `raw/jetbrains/` shards and `raw/swebenchpro/` files are absent locally.
`data/ops_compact.parquet` has turn IDs but no per-response usage payloads. Run
totals cannot establish a component's token usage. Do not distribute run totals
over these 413 response IDs or use character counts as tokens.

Corrected version graphs exist, but an inferred state ID is not a complete code
snapshot. No benchmark checkpoint evaluator was configured or run during this
check. No intermediate version was independently marked PASS or FAIL. Both
graphs in `output/figures/` remain synthetic illustrations, including their
token amounts, contribution examples and checkpoint outcomes.

Human contribution validation, semantic confirmation on the frozen model/harness
samples and live controller utility remain pending. This local run made zero
new model calls, zero annotation changes and zero benchmark task evaluations.

## Execute next

Use [`CODEX_FRAMEWORK_VALIDATION.md`](../../CODEX_FRAMEWORK_VALIDATION.md) on the
machine holding the pinned raw shards. It specifies the usage export, source
reconciliation, bounded checkpoint evaluation, post-pass spending analysis,
existing frozen confirmation samples and empirical figure requirements.

The first informative milestone is actual response-usage recovery for the 16
pilot runs and checkpoint feasibility on the first two task pairs. The protocol
preserves missing cases rather than replacing them with favorable examples.

## Reproduce the saved-data check

```bash
.venv/bin/python scripts/followup/framework_inventory.py \
  --out results/framework_validation_run_YYYYMMDD/inventory
```

See `inventory_manifest.json` for input hashes and `status.json` for test commands
and implementation versus empirical status. The checked code was based on
`94e8ca1` plus the framework files in this commit.

| Claim | Evidence |
| --- | --- |
| Identity coverage of the pilot | `component_identity_join.csv`, `pilot_inventory_by_run.csv`, `inventory_manifest.json` |
| Software regressions pass | `project_tests.txt`, `original_audit_checks.txt`, `restore_scope_checks.txt` |
| Recorded run tokens exist | `pilot_inventory_by_run.csv`, source `data/runs.parquet` |
| Component token values remain unknown | Null resource columns in `component_identity_join.csv`; source operation schema |
| Intermediate PASS outcomes remain untested | Zero actual task evaluations in `status.json`; protocol's pending evaluator step |
