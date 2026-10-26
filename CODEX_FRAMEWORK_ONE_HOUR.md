# WorkTrace: one-hour pipeline check

**This is the current execution scope. It supersedes the larger sample and
64-evaluation budget in `CODEX_FRAMEWORK_VALIDATION.md`.** Finish and write results
within 60 minutes. The goal is a working small pipeline and concrete examples,
not a model ranking or a complete paper experiment.

## Fixed reduced sample

Use the first two evaluation task pairs in the existing frozen manifest:

- Order 03: `instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0`.
- Order 04: `instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca`.
- Both archived Gemini and Luna runs: **2 tasks, 4 runs, 175 emitted candidate
  components, 109 native calls, 104 generating response IDs**.

Selection follows frozen order, not observed redundancy. Reuse the existing
component decomposition and model-coded contribution labels. No reannotation,
new paid model jobs, sample expansion, human-validation campaign or live agent
intervention belongs in this hour. Call this a development smoke study.

Write to a fresh `results/framework_one_hour_run_YYYYMMDD_HHMM/`. Preserve all
original data, labels, samples and papers. Do not overwrite the local archived
example output at `results/framework_one_hour_20261027/`.

## Minutes 0–5: inventory and real examples

Record start time and the 60-minute deadline. Read this file, the short result
report at `results/framework_one_hour_20261027/RESULTS.md`, and the resource schema
at `worktrace/RESOURCE_ATTRIBUTION.md`. Use an existing working Python environment.
Do not spend the hour rebuilding dependencies or reading every historical paper.

```bash
.venv/bin/python scripts/followup/framework_quickcheck.py \
  --out results/framework_one_hour_run_YYYYMMDD_HHMM
```

This immediately produces a fixed four-run subset, role-precision table, two real
trajectory figures and eight qualitative component examples. Its current figures
use inferred states AFTER parent calls; compound-call internal execution states
remain unresolved. Its whole-run token totals are real, but its component token
fields remain unknown without the next step. The archived labels are model-coded,
not independent human truth. No intermediate version is marked PASS by this script.

## Minutes 5–15: actual response accounting

Use the pinned raw files already on this machine. Do not download a full dataset
or expand the sample. Rerun in a separate output directory with raw extraction:

```bash
.venv/bin/python scripts/followup/framework_quickcheck.py \
  --jetbrains-shard raw/jetbrains/gemini_3_7_flash-run1.parquet \
  --jetbrains-shard raw/jetbrains/luna-run1.parquet \
  --out results/framework_one_hour_run_YYYYMMDD_HHMM_with_usage
```

The script exports only selected runs and invokes the conserved response exporter.
Inspect `resources/run_usage_reconciliation.jsonl`, coverage, no-tool responses,
source IDs and any retries. A completed export is not proof of complete usage.
Map provider fields only from inspected payloads; retain raw fields. Keep input,
cached input and output separate. If cache is included in input, do not add it
again. Shared-component costs are equal-share estimates. No-tool responses retain
their own expenditure. Unknown usage stays null; do not allocate a run total.

If raw files are missing or response usage is absent, record this by minute 15
and continue. Do not let recovery attempts consume the report window.

## Minutes 15–40: bounded checkpoint evaluation

Attempt **only task 03's two model runs**, using an already available benchmark
environment and runner. Allow at most **five minutes for setup**. Do not build
large task images or repair the machine for the remainder of the hour.

Reconstruct at most three checkpoints per run, in this fixed priority:

1. Final submitted implementation, to check evaluation/reconstruction validity.
2. Initial implementation.
3. First recoverable edited implementation that differs from the final one.

Deduplicate proven-identical content under the same environment/protocol. Maximum
**six evaluations total, 120 seconds each, two concurrent task containers**.
Retries count toward six. Stop all benchmark work at minute 40. Preserve timeouts
and infrastructure errors; they are not confirmed semantic failures.

Use complete file contents including relevant untracked/deleted files, the pinned
base/environment, and the fixed final benchmark protocol. Do not use inferred
graph IDs as snapshot proof or substitute a narrow local check for final tests.
Keep evaluator tests outside agent-controlled modifications. Execute only through
the isolated benchmark adapter, never arbitrary copied trajectory commands on
the host. A snapshot without reliable reconstruction remains unevaluated.

Use the checkpoint schema in `CODEX_FRAMEWORK_VALIDATION.md`. Save hashes, runner
configuration, logs, reports, version occurrence and the boundary component ID.
If the environment or snapshots are unavailable, write an explicit unavailable
status and continue with the real archived figures. Do not invent PASS markers.

For any passing intermediate checkpoint, calculate subsequent exploration/edit/
verification expenditure if real response usage is available. Include the edit
that creates it in reaching the state, not spending after it. Keep a response
crossing the boundary mixed or explicitly allocated, with a whole-response mixed
sensitivity. Missing no-tool timing stays unresolved. Use **earliest evaluated
passing version** because this sparse sample does not cover every earlier state.
Later work is not automatically redundant, and post-pass spending is not measured
safe savings. If checkpoints remain unknown, post-pass results remain unknown.

## Minutes 40–50: two empirical examples and minimal checks

Produce one paired figure per task. Use shape for action type (circle exploration,
diamond edit, square verification, triangle administration) and solid color for
contribution (green direct, orange non-direct, gray uncertain); do not split meaning
between marker fill and border. Keep marker sizes fixed in the primary view.
Show component classification and contribution,
and component input/cache/output plus attribution method in a table/linked data
where actual usage permits. Label inferred state placement and uncertain execution.
Add version PASS/FAIL only when supported by an exact independently evaluated
snapshot. Otherwise show UNTESTED. The final archived success field is separately
labeled and cannot establish intermediate validity.

Use the eight already extracted component examples, with their commands, archived
reasons and evidence. Include examples that support and challenge the proposed
excess-work interpretation. Do not relabel a broad baseline check or environment
failure as repeated-support over-verification. Preserve alternative valid repairs.

Run existing tests and only the focused tests needed for any new join/summary
logic. Check conserved response sums, missing values, zero-role denominators,
pass→fail handling, and no passing checkpoint. A synthetic test may check code
behavior but must never appear as an empirical task result.

If the core work is finished before minute 45, an optional harness illustration
may use the first task by `selection_order` from the existing frozen cross-harness
joint-success sample, all three harnesses. Limit this to archived native effort
and available recorded fields; tokens remain null if missing. No new semantic
annotation. Skip it if it threatens the report deadline. No difficulty interaction
claim is justified by two tasks; retain patch-size metadata only as description.

## Minutes 50–60: report and deliver

Write `RESULTS.md` with:

- The fixed sample and a four-run count/token table.
- Exploration and verification precision bounds from existing labels.
- Actual response-usage availability, reconciliation and attribution coverage.
- Checkpoints attempted, outcomes, evidence and post-pass results where possible.
- Two trajectory figures and concrete evidence-linked component examples.
- A stage table: **real-data tested / synthetic-only tested / unavailable**.
- One paragraph on what worked, what remains unknown, and the next necessary test.

Save sample IDs, source hashes, commands, elapsed time and actual evaluation count
in `manifest.json`. Do not call the empirical pipeline complete if usage or
checkpoint evaluation is missing. Produce a useful partial report at the deadline
instead of extending the task or returning another plan.

Commit and push the instructions, small scripts and compact results. Exclude raw
datasets, task repositories/images, credentials and unrelated manuscript drafts.
Return the commit and report path plus the strongest observation the small data
actually supports.
