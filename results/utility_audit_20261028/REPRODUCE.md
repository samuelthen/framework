# Reproduce the local audit

Run from the repository root. Python needs `pyarrow` and `pandas`; tests need `pytest`; figures need `matplotlib` and `numpy`. No paid model credentials are used. The raw Parquet shards total about 584 MB. Source snapshots and Go module/build caches need additional disk space. Keep `raw/` excluded from Git.

## Recover frozen inputs

```sh
python3 scripts/utility_audit/download_inputs.py
PYTHONPATH=worktrace python3 scripts/utility_audit/prepare_inputs.py
PYTHONPATH=worktrace python3 scripts/utility_audit/reconstruct.py
```

The first script verifies the three archived SHA-256 values. The second uses the existing eight-task blinding key and downloads the exact source commits for Luna tasks 03 and 04. The third interprets only supported literal edits, reconstructs submitted/reference snapshots, and applies the independent evaluator test patch with exact context checks. Source archive compression can vary; the pinned commit and reconstruction's per-tree hashes identify the content.

## Audit labels, results and recurrences

```sh
PYTHONPATH=worktrace python3 scripts/utility_audit/trace_rounds.py --round 1
PYTHONPATH=worktrace python3 scripts/utility_audit/trace_rounds.py --round 2
PYTHONPATH=worktrace python3 scripts/utility_audit/trace_rounds.py --round 3
PYTHONPATH=worktrace python3 scripts/followup/component_resources.py \
  --jetbrains-shard raw/jetbrains/gemini_3_7_flash-run1.parquet \
  --jetbrains-shard raw/jetbrains/luna-run1.parquet \
  --components results/precision_validation_20261026/reconciled_component_annotations.jsonl \
  --out results/utility_audit_20261028/resources_16runs
```

These reuse archived model judgments; they do not perform new human annotation.

## Execute scoped checks

Docker must be running. The image digest is pinned in `container_checks.py`. Module preparation requires network; checks disable network. The scripts mount only reconstructed inputs and the two dedicated Go caches, with source read-only and work in disposable tmpfs. They execute authored fixed checker commands, not arbitrary trace shell commands.

```sh
docker pull golang@sha256:e47f121850f4e276b2b210c56df3fda9191278dd84a3a442bfe0b09934462a8f
python3 scripts/utility_audit/container_checks.py modules
python3 scripts/utility_audit/container_checks.py format
python3 scripts/utility_audit/container_checks.py tests
python3 scripts/utility_audit/container_checks.py requirements --task 4
PYTHONPATH=worktrace python3 scripts/utility_audit/cache_experiment.py
```

Cold build times vary. Original logs and summaries are retained; these commands overwrite their corresponding outputs when rerun. The original task-03 module setup failed once due to a read-only workspace; that failed attempt is retained separately, not included as a test outcome. The fixed runner makes a disposable work copy.

The Go cache experiment assumes fixed external module/build caches and a reviewed scoped test. This assumption is explicit; the prototype does not discover a complete dependency set automatically. It normalizes only test outcomes, not execution timestamps or durations. Its fresh command explicitly uses `-count=1`; do not compare its reuse times against an assumed uncached default Go workflow.

## Summarize, render and test

```sh
python3 scripts/utility_audit/summarize.py
python3 scripts/utility_audit/plot_results.py
PYTHONPATH=worktrace python3 -m pytest -q worktrace/tests
```

Inspect `summary.json`, the original container logs, and `figures/utility_audit.png`. Test and probe counts are measurements over two reconstructed cases, not new independent benchmark tasks. No agent continuation or original full-benchmark certification is performed.
