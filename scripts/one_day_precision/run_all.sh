#!/usr/bin/env bash
# Reproduce every completed analysis of the one-day precision study (CODEX_ONE_DAY_EXECUTION.md).
# No API calls, no downloads; reads local raw data (raw/jetbrains, raw/swebenchpro, results/v2/task5) and the
# hand-made inputs annotations_raw/ and requirements_raw/; writes only into results/one_day_precision_20261026/.
#
# usage (from the repository root):  bash scripts/one_day_precision/run_all.sh
# optional (not run here):
#   acquisition:  python worktrace/scripts/download_data.py jetbrains     # raw data, if missing
#   annotation:   edit results/one_day_precision_20261026/annotations_raw/*.txt following annotation_guide.md
#   sandboxed tests of task patches: not available in this environment (no task containers)
set -euo pipefail
PY=${PY:-.venv/bin/python}
D=scripts/one_day_precision
$PY $D/inventory.py          # availability.csv, sample_manifest.csv (deterministic, seed 20261026)
$PY $D/matched_effort.py     # Section 6: matched_effort.csv, matched_differences.csv, fig_matched_effort
$PY $D/packets.py            # blinded annotation packets (review material)
$PY $D/compact.py            # compact annotation views
$PY $D/score.py              # validates labels; action_annotations.jsonl, requirements.jsonl, scores_by_run.csv, pilot_pairs.csv
$PY $D/pilot_analysis.py     # summaries, decomposition, failed-run coverage, examples, figures
$PY -m pytest -q $D/test_one_day.py
$PY $D/finalize.py           # manifest.json, status.json
