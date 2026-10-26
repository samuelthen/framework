"""Write manifest.json (input/output hashes, versions, commands) and status.json (per-deliverable status, missing
inputs, required human review) for the one-day study.

usage: python scripts/one_day_precision/finalize.py"""
import glob
import importlib.metadata as md
import os
import platform
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, ROOT, SEED, N_BOOT, log, sha256, write_json  # noqa: E402

INPUTS = ["raw/jetbrains/gemini_3_7_flash-run1.parquet", "raw/jetbrains/luna-run1.parquet",
          "raw/jetbrains/gemini_3_7_flash-run2.parquet", "raw/swebenchpro/v1.parquet", "raw/swebenchpro/default.parquet",
          "data/runs.parquet", "results/v2/task5/runs_benchmark.parquet", "worktrace/config.yaml",
          "worktrace/worktrace/loaders/jetbrains.py", "CODEX_ONE_DAY_EXECUTION.md"]


def main():
    head = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    inputs = {p: {"sha256": sha256(f"{ROOT}/{p}"), "bytes": os.path.getsize(f"{ROOT}/{p}")} for p in INPUTS if os.path.exists(f"{ROOT}/{p}")}
    scripts = {os.path.relpath(p, ROOT): sha256(p) for p in sorted(glob.glob(f"{ROOT}/scripts/one_day_precision/*.py")) +
               [f"{ROOT}/scripts/one_day_precision/run_all.sh"]}
    outputs = {}
    for p in sorted(glob.glob(f"{OUT}/*")):
        if os.path.isfile(p) and not p.endswith(("manifest.json", "status.json", "run.log")):
            outputs[os.path.basename(p)] = sha256(p)
    for sub in ("annotations_raw", "requirements_raw"):
        for p in sorted(glob.glob(f"{OUT}/{sub}/*")):
            outputs[f"{sub}/{os.path.basename(p)}"] = sha256(p)
    versions = {k: md.version(k) for k in ("numpy", "pandas", "pyarrow", "matplotlib", "pytest")}
    versions["python"] = platform.python_version()
    manifest = {
        "study": "one-day contribution-precision study (CODEX_ONE_DAY_EXECUTION.md)",
        "repository_head_at_finalize": head, "working_directory": ROOT,
        "path_adaptation": "brief names /Users/samuelthen/Desktop/framework and a Codex python runtime; executed in /home/user/framework with .venv",
        "seed": SEED, "bootstrap_replicates": N_BOOT,
        "dataset_revisions": {"jetbrains": "a5ec6ad8428715a689ee62cf7cef82334773c958",
                              "swebench_pro": "2d52cb3df914a3fcf80c7f66738b3a88ae37fc50",
                              "open_swe_traces_v1.2": "a85dc97891bd18942ef6f3ab87750af99f487bba (via results/v2/task5)"},
        "inputs": inputs, "scripts": scripts, "outputs": outputs, "versions": versions,
        "annotation": {"annotator": "Claude (Anthropic), model-coded, single pass, preliminary",
                       "guide": "annotation_guide.md v1 (frozen after calibration; hash in run.log)",
                       "blinding": "run labels X/Y via packets/blinding_key.csv (seeded); weak in practice (run length)",
                       "human_validation": "none"},
        "commands": {"reproduce_all": "bash scripts/one_day_precision/run_all.sh",
                     "reliability_audit": "python audit/reproduce_reliability.py  (7/7 fail; audit_reliability_output.txt)",
                     "project_tests": "PYTHONPATH=worktrace python -m pytest worktrace/tests  (79 passed; pytest_output.txt)",
                     "study_tests": "python -m pytest scripts/one_day_precision/test_one_day.py  (8 passed)",
                     "optional_acquisition": "python worktrace/scripts/download_data.py jetbrains",
                     "optional_annotation": "edit annotations_raw/*.txt per annotation_guide.md, then rerun score.py and pilot_analysis.py",
                     "optional_sandboxed_tests": "not available: no task containers in this environment"}}
    write_json(f"{OUT}/manifest.json", manifest)

    status = {
        "route": "A (full traces and accepted reference evidence available; code state read from traces, not executed)",
        "deliverables": {
            "1_availability.csv": {"status": "completed"},
            "2_sample_manifest.csv": {"status": "completed", "note": "3 calibration + 8 evaluation pairs completed in frozen order; 295 reserve"},
            "3_requirements.jsonl": {"status": "completed", "note": "11 tasks, model-written from dataset requirements/reference; not independently verified; tests not executed"},
            "4_action_annotations.jsonl": {"status": "completed (preliminary)", "note": "675 actions, model-coded, single annotator"},
            "5_scores_by_run.csv": {"status": "completed (preliminary)", "note": "P bounds for 22 successful runs; Q_failure/coverage null with reasons; failed-run coverage in failed_run_coverage.csv"},
            "6_matched_effort.csv/matched_differences.csv": {"status": "completed"},
            "7_diagnostics.md": {"status": "completed"},
            "8_figures": {"status": "completed", "files": ["fig_matched_effort", "fig_precision_bounds", "fig_effort_decomposition", "fig_trajectory_example"],
                          "coverage_curve": "not produced: intermediate states not reconstructed; only one eligible failed run"},
            "9_RESULTS.md": {"status": "completed"},
            "10_manifest/run.log/status": {"status": "completed"},
            "tests": {"status": "completed", "note": "8 study tests pass; project tests 79 pass; 7 audit probes fail (not repaired: no inferred states used)"},
            "failed_run_extension": {"status": "partial", "recall_status": "identifiable for 1 run (static terminal coverage 4/5)",
                                     "not_identifiable": "peak coverage (no state reconstruction); Q_failure (failed run actions not annotated)"}},
        "missing_inputs": ["independent second annotator / human reviewer for the pilot labels",
                           "task execution environments (containers) to run fail-to-pass tests and verify code states",
                           "agent-visible outputs in packets for truncated observations (handled manually from task 05)",
                           "a defensible common action unit across models that bundle commands differently"],
        "human_review_required": ["blind re-annotation of the 8 evaluation pairs with the frozen guide",
                                  "review of requirements.jsonl (two reference/requirement conflicts noted)",
                                  "adjudication of the 17 uncertain actions"]}
    write_json(f"{OUT}/status.json", status)
    log(f"finalize: manifest.json ({len(inputs)} inputs, {len(scripts)} scripts, {len(outputs)} outputs), status.json")


if __name__ == "__main__":
    main()
