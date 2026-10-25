"""Task 5 follow-up (user decision 2026-10-25): run-mean exact-repeat rate is primary; pooled rates are reported with
and without the stuck-loop run siliconcompiler_lambdapdk_pr114 (a case study). Per harness, from runs_benchmark.parquet;
the task is dropped from every harness in the 'without' column so the comparison stays paired on task.
usage: v2_task5_outlier.py  -> results/v2/task5/exact_repeat_with_without_outlier.csv"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from v2_viewb import _rci  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = f"{ROOT}/results/v2/task5"
STUCK = "siliconcompiler_lambdapdk_pr114"

R = pd.read_parquet(f"{OUT}/runs_benchmark.parquet")
f = lambda t: f"{100 * t[0]:.2f}% [{100 * t[1]:.2f}, {100 * t[2]:.2f}]"  # noqa: E731
rows = []
for h, g in [*R.groupby("harness"), ("ALL", R)]:
    w = g[g.task_id != STUCK]
    rows.append({"harness": h, "runs": len(g), "run_mean (primary)": f(_rci(g, "exact_repeat_rate")),
                 "run_mean without stuck task": f(_rci(w, "exact_repeat_rate")),
                 "pooled": f(_rci(g, "exact_repeats", "n_ops")), "pooled without stuck task": f(_rci(w, "exact_repeats", "n_ops"))})
T = pd.DataFrame(rows)
T.to_csv(f"{OUT}/exact_repeat_with_without_outlier.csv", index=False)
print(T.to_string(index=False))
s = R[R.task_id == STUCK][["harness", "resolved", "n_ops", "exact_repeats"]]
print(s.to_string(index=False))
