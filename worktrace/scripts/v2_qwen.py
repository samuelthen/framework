"""Qwen (Open-SWE-Traces v1.2) labeling, after the Task 5 benchmark review (user decisions 2026-10-25).

Step 1, pilot: 20 of the 2,000 sampled tasks (seed 0) x 3 harnesses, every op labelled with prompt v1 by the primary
annotator. It establishes the per-harness skip rule (unmatched ops labelled `distinct` >= 98% -> skip them in the main
run) and reports the uncertain share. Step 2 (500 tasks) and step 3 (GLM on 1,000 matched ops) wait for review.

usage: v2_qwen.py pilot          # labels -> data/labels/qwen_pilot.jsonl
       v2_qwen.py pilot_report   # -> results/v2/qwen/pilot/"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.label.annotate import client_from_env, label_runs  # noqa: E402
from v2_task5 import _load  # noqa: E402
from v2_viewb import _rci  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAB, OUT = f"{ROOT}/data/labels", f"{ROOT}/results/v2/qwen"
A = yaml.safe_load(open(f"{ROOT}/worktrace/config.yaml"))["annotator"]
N_PILOT, SEED = 20, 0
WORKERS = 2  # shares the key's small queue with the Gemini scale pass


def _pilot_runs():
    S = pd.read_parquet(f"{ROOT}/results/v2/task5/runs.parquet", columns=["task_id", "run_id", "harness"])
    tasks = sorted(S.task_id.unique())
    pick = set(np.random.default_rng(SEED).choice(tasks, size=N_PILOT, replace=False))
    S = S[S.task_id.isin(pick)].sort_values(["harness", "task_id"])
    assert len(S) == 3 * N_PILOT, len(S)
    return S, {rid: _load(rid) for rid in S.run_id}


def pilot():
    os.makedirs(f"{OUT}/pilot", exist_ok=True)
    S, runs = _pilot_runs()
    S.to_csv(f"{OUT}/pilot/pilot_runs.csv", index=False)
    print("runs", len(runs), "ops", sum(len(o) for _, o in runs.values()), flush=True)
    c = client_from_env(f"{ROOT}/soclaas.env")
    lab = label_runs(runs, Path(f"{LAB}/qwen_pilot.llm.jsonl"), Path(f"{LAB}/cache_qwen.jsonl"), c,
                     prompt_version=A["prompt_version"], n_chars=A["result_chars"], workers=WORKERS)
    with open(f"{LAB}/qwen_pilot.jsonl", "w") as f:
        for r in lab:
            f.write(json.dumps({**r, "label_source": "llm"}) + "\n")
    print({"labels": len(lab), "errors": sum(r["label_error"] for r in lab), "usage": c.usage,
           "served": c.served_model}, flush=True)


def pilot_report():
    S, runs = _pilot_runs()
    L = {r["op_id"]: r for r in map(json.loads, open(f"{LAB}/qwen_pilot.jsonl"))}
    rows = []
    for rid, (run, ops) in runs.items():
        h = S.set_index("run_id").harness[rid]
        for o in ops:
            l = L[o["op_id"]]
            rows.append({"harness": h, "task_id": run["task_id"], "matched": bool(o["cand_object"] or o["cand_output"]),
                         "contribution": l["contribution"], "relation": l["relation"], "error": l["label_error"]})
    D = pd.DataFrame(rows)
    out = []
    for h, g in [*D.groupby("harness"), ("all", D)]:
        u, m = g[~g.matched], g[g.matched]
        r = {"harness": h, "runs": g.groupby("task_id").ngroups if h != "all" else len(runs), "ops": len(g),
             "matched": len(m), "unmatched": len(u), "label_errors": int(g.error.sum())}
        for name, part, val in [("unmatched_distinct", u, "distinct"), ("uncertain_matched", m, "uncertain"),
                                ("uncertain_all", g, "uncertain"), ("non_distinct_matched", m, "non_distinct")]:
            est, lo, hi = _rci(part.assign(y=(part.contribution == val).astype(float)), "y")
            r[name], r[name + "_ci"] = round(100 * est, 1), f"[{100 * lo:.1f}, {100 * hi:.1f}]"
        r["passes_98_rule"] = r["unmatched_distinct"] >= 98.0 if h != "all" else None
        out.append(r)
    T = pd.DataFrame(out)
    T.to_csv(f"{OUT}/pilot/pilot_summary.csv", index=False)
    print(T.to_string(index=False))


if __name__ == "__main__":
    {"pilot": pilot, "pilot_report": pilot_report}[sys.argv[1]](*sys.argv[2:])
