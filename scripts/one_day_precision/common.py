"""Shared paths, constants and helpers for the one-day contribution-precision study (CODEX_ONE_DAY_EXECUTION.md).

Local adaptation: the brief names /Users/samuelthen/Desktop/framework and a Codex runtime; this study ran in the same
repository checked out at /home/user/framework with the project's .venv (Python 3.12). See run.log."""
import datetime
import hashlib
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = f"{ROOT}/results/one_day_precision_20261026"
SEED = 20261026
N_BOOT = 5000
PRIMARY = ("gemini-3.7-flash", "gpt-5.6-luna")      # dataset identifiers in data/runs.parquet (`model`)
SHARD = {"gemini-3.7-flash": "gemini_3_7_flash", "gpt-5.6-luna": "luna", "gpt-5.6-terra": "terra"}
sys.path.insert(0, f"{ROOT}/worktrace")


def log(msg):
    os.makedirs(OUT, exist_ok=True)
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}  {msg}"
    with open(f"{OUT}/run.log", "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def boot_ci(per_task_values, stat=np.mean, n=N_BOOT, seed=SEED):
    """Task bootstrap: resample tasks with replacement; returns (point, lo, hi) for `stat` of per-task values."""
    v = np.asarray(per_task_values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return (np.nan, np.nan, np.nan)
    pt = float(stat(v))
    if len(v) < 2:
        return (pt, np.nan, np.nan)
    idx = np.random.default_rng(seed).integers(0, len(v), size=(n, len(v)))
    vals = np.apply_along_axis(stat, 1, v[idx]) if stat is not np.mean else v[idx].mean(1)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return (pt, float(lo), float(hi))
