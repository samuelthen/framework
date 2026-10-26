#!/usr/bin/env bash
# Local saved-data work and authored regression tests only. No model/API jobs.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-.venv/bin/python}
OUT=results/followup_20261026
mkdir -p "$OUT"
printf 'Started %s\n' "$(date -Iseconds)" > "$OUT/run.log"
for script in role_precision review_packets verification_audit freeze_samples expert_gate rebuild_states ablation_packets property_curves; do
  printf '%s\n' "$script.py" >> "$OUT/run.log"
  "$PY" "scripts/followup/$script.py"
done
PYTHONPATH=worktrace "$PY" -m pytest -q worktrace/tests scripts/one_day_precision/test_one_day.py scripts/precision_validation/test_validation.py scripts/followup/test_followup.py > "$OUT/test_results.txt" 2>&1
"$PY" audit/reproduce_reliability.py > "$OUT/original_audit_checks.txt" 2>&1
"$PY" audit/probe_restore_scope.py > "$OUT/restore_scope_checks.txt" 2>&1
"$PY" scripts/followup/report.py
printf 'Completed %s\n' "$(date -Iseconds)" >> "$OUT/run.log"
