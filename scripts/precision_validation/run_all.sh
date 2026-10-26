#!/usr/bin/env bash
# Reads saved local public-data traces; no download or annotation API calls.
# Regenerates this validation directory only. Historical study stays read-only.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-.venv/bin/python}
OUT=results/precision_validation_20261026
mkdir -p "$OUT"
export MPLCONFIGDIR=/tmp/worktrace-validation-mpl
printf 'Started %s\n' "$(date -Iseconds)" > "$OUT/run.log"
printf '%s\n' 'prepare.py: syntax-only decomposition and blinded evidence' >> "$OUT/run.log"
"$PY" scripts/precision_validation/prepare.py
printf '%s\n' 'review_requirements.py: recorded requirement review' >> "$OUT/run.log"
"$PY" scripts/precision_validation/review_requirements.py
printf '%s\n' 'compare_states.py: pilot facts and graphs' >> "$OUT/run.log"
"$PY" scripts/precision_validation/compare_states.py
printf '%s\n' 'audit/reproduce_reliability.py: audit_checks.txt' >> "$OUT/run.log"
PYTHONPATH=worktrace "$PY" audit/reproduce_reliability.py > "$OUT/audit_checks.txt" 2>&1
printf '%s\n' 'pytest: test_results.txt' >> "$OUT/run.log"
PYTHONPATH=worktrace "$PY" -m pytest -q worktrace/tests scripts/one_day_precision/test_one_day.py scripts/precision_validation/test_validation.py > "$OUT/test_results.txt" 2>&1
printf '%s\n' 'analyze.py: complete-review validation, scores, comparisons, figures and manifest' >> "$OUT/run.log"
"$PY" scripts/precision_validation/analyze.py
printf '%s\n' 'compare_reviewers.py: independent component agreement and conservative uncertainty sensitivity' >> "$OUT/run.log"
"$PY" scripts/precision_validation/compare_reviewers.py
"$PY" scripts/precision_validation/report_final.py
printf 'Completed %s\n' "$(date -Iseconds)" >> "$OUT/run.log"
"$PY" -c 'import sys; sys.path.insert(0, "scripts/precision_validation"); from analyze import manifest; manifest()'
