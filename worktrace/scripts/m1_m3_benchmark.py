"""M1-M3: load all JetBrains runs, extract facts, compute the Section 3 benchmark (no LLM).
Writes data/ops_compact.parquet (one row per op, no outputs), data/runs.parquet, results/benchmark/*.csv."""
import glob
import json
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402
from worktrace.stats import cluster_bootstrap  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW, DATA = f"{ROOT}/raw", f"{ROOT}/data"
RES = os.environ.get("WT_RESULTS", f"{ROOT}/results/benchmark")


def gold_table():
    out = {}
    for f in ("default", "v1"):  # v1 first wins below
        d = pd.read_parquet(f"{RAW}/swebenchpro/{f}.parquet", columns=["instance_id", "patch"])
        for iid, p in zip(d.instance_id, d.patch):
            files = sorted(set(re.findall(r"^diff --git a/(\S+) b/", p or "", re.M)))
            lines = sum(1 for l in (p or "").splitlines() if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---")))
            out[iid] = (files, lines)
    return out


def process_file(path):
    runs, rows, dropped = [], [], 0
    for row in (r for b in pq.ParquetFile(path).iter_batches(batch_size=25) for r in b.to_pylist()):
        if J.is_infra_failure(row):
            dropped += 1
            continue
        run, ops = J.load_row(row)
        extract_facts(ops)
        by_id = {o["op_id"]: o for o in ops}
        runs.append(run)
        for o in ops:
            rows.append({k: o[k] for k in ("run_id", "task_id", "model", "op_id", "turn_id", "op_index", "kind", "object",
                                           "exact_repeat", "write", "truncated", "agent_saw_truncated", "exit_code")}
                        | {"has_cand_object": o["cand_object"] is not None, "has_cand_output": o["cand_output"] is not None,
                           "candA_same_output": (o["cand_facts"].get(o["cand_object"]) or {}).get("same_output"),
                           "candA_code_since": (o["cand_facts"].get(o["cand_object"]) or {}).get("any_code_written_since"),
                           "candA_object_since": (o["cand_facts"].get(o["cand_object"]) or {}).get("object_written_since"),
                           "candA_kind": by_id[o["cand_object"]]["kind"] if o["cand_object"] else None,
                           "candA_index": by_id[o["cand_object"]]["op_index"] if o["cand_object"] else None,
                           "missing_result": o["missing_result"], "n_parts": len(o["parts"]), "mixed": o["mixed"],
                           "command_len": len(o["command"] or "")})
    print(os.path.basename(path), len(runs), "runs, dropped", dropped, flush=True)
    return runs, rows, dropped


def main():
    os.makedirs(RES, exist_ok=True)
    files = sorted(glob.glob(f"{RAW}/jetbrains/*.parquet"))
    with Pool(2, maxtasksperchild=1) as p:
        res = p.map(process_file, files)
    runs = pd.DataFrame([r for rs, _, _ in res for r in rs])
    ops = pd.DataFrame([o for _, os_, _ in res for o in os_])
    gold = gold_table()
    runs["gold_file_list"] = runs.task_id.map(lambda t: gold.get(t, (None, None))[0])
    runs["gold_files"] = runs.gold_file_list.map(lambda x: len(x) if x is not None else np.nan)
    runs["gold_lines"] = runs.task_id.map(lambda t: gold.get(t, (None, None))[1])
    per = ops.groupby("run_id").agg(n_ops=("op_id", "size"), exact_repeats=("exact_repeat", "sum"),
                                    same_object=("has_cand_object", "sum"), lost=("missing_result", "sum")).reset_index()
    runs = runs.drop(columns=["n_ops"]).merge(per, on="run_id", how="left").fillna({"n_ops": 0, "exact_repeats": 0, "same_object": 0})
    runs["exact_repeat_rate"] = runs.exact_repeats / runs.n_ops.clip(lower=1)
    runs["same_object_rate"] = runs.same_object / runs.n_ops.clip(lower=1)
    runs.drop(columns=["issue"]).to_parquet(f"{DATA}/runs.parquet")
    runs[["run_id", "issue"]].to_parquet(f"{DATA}/issues.parquet")
    ops.to_parquet(f"{DATA}/ops_compact.parquet")
    dropped = sum(d for _, _, d in res)

    # Table 1
    t1 = []
    for m, g in runs.groupby("model"):
        row = {"model": m, "harness": "mini-swe-agent", "runs": len(g), "tasks": g.task_id.nunique()}
        for col, stat in [("resolve_rate", lambda d: d.resolved.astype(float).mean()),
                          ("turns_mean", lambda d: d.n_turns.mean()),
                          ("tool_calls_mean", lambda d: d.n_ops.mean()),
                          ("input_tokens_mean", lambda d: d.input_tokens.mean()),
                          ("output_tokens_mean", lambda d: d.output_tokens.mean()),
                          ("exact_repeat_rate", lambda d: d.exact_repeat_rate.mean()),
                          ("same_object_repeat_rate", lambda d: d.same_object_rate.mean()),
                          ("share_runs_with_any_exact_repeat", lambda d: (d.exact_repeats > 0).mean())]:
            pt, lo, hi = cluster_bootstrap(g, stat, n=300)
            row[col], row[col + "_lo"], row[col + "_hi"] = pt, lo, hi
        t1.append(row)
    pd.DataFrame(t1).to_csv(f"{RES}/table1_by_model.csv", index=False)

    # Table 2: difficulty bins
    runs["gold_size"] = runs.gold_lines
    emp = runs.groupby("task_id").resolved.mean().rename("emp_solve")
    runs = runs.merge(emp, on="task_id")
    t2 = []
    for proxy, col, asc in [("gold_patch_lines", "gold_size", True), ("empirical_difficulty", "emp_solve", False)]:
        sub = runs.dropna(subset=[col]).copy()
        task_val = sub.groupby("task_id")[col].first()
        ranks = task_val.rank(method="first", ascending=asc)
        bins = pd.qcut(ranks, 4, labels=["Q1 easiest", "Q2", "Q3", "Q4 hardest"])
        sub["bin"] = sub.task_id.map(bins)
        for (b, m), g in sub.groupby(["bin", "model"], observed=True):
            t2.append({"proxy": proxy, "bin": b, "model": m, "runs": len(g), "tasks": g.task_id.nunique(),
                       "proxy_range": f"{task_val[bins == b].min():.3g}-{task_val[bins == b].max():.3g}",
                       "resolve_rate": g.resolved.astype(float).mean(), "tool_calls_mean": g.n_ops.mean(),
                       "exact_repeat_rate": g.exact_repeat_rate.mean(), "same_object_repeat_rate": g.same_object_rate.mean(),
                       "share_runs_with_any_exact_repeat": (g.exact_repeats > 0).mean()})
        for b, g in sub.groupby("bin", observed=True):
            t2.append({"proxy": proxy, "bin": b, "model": "ALL", "runs": len(g), "tasks": g.task_id.nunique(),
                       "resolve_rate": g.resolved.astype(float).mean(), "tool_calls_mean": g.n_ops.mean(),
                       "exact_repeat_rate": g.exact_repeat_rate.mean(), "same_object_repeat_rate": g.same_object_rate.mean(),
                       "share_runs_with_any_exact_repeat": (g.exact_repeats > 0).mean()})
    pd.DataFrame(t2).to_csv(f"{RES}/table2_difficulty.csv", index=False)
    kinds = ops.groupby(["model", "kind"]).size().unstack(fill_value=0)
    kinds.to_csv(f"{RES}/op_kinds_by_model.csv")
    meta = {"files": [os.path.basename(f) for f in files], "runs": len(runs), "ops": len(ops), "dropped_infra": dropped,
            "lost_results": int(runs.lost.sum()), "gold_coverage": float(runs.gold_files.notna().mean()),
            "jetbrains_revision": J.REVISION}
    json.dump(meta, open(f"{RES}/meta.json", "w"), indent=1)
    print(json.dumps(meta, indent=1))
    print(pd.DataFrame(t1)[["model", "runs", "resolve_rate", "tool_calls_mean", "exact_repeat_rate", "same_object_repeat_rate", "share_runs_with_any_exact_repeat"]].to_string())


if __name__ == "__main__":
    main()
