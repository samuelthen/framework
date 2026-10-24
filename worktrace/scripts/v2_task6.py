"""Task 6: scale labeling (primary annotator, prompt v1, current facts).

Scope (user decision 2026-10-24): all Gemini runs now; a 10% task-stratified sample of Luna and Terra now; Qwen
(Open-SWE-Traces) only after the Task 5 benchmark is reviewed.

Skip rule, applied per model (`SKIP_RULE`): an unmatched op (no object or output candidate) is not sent to the LLM
only if, on the pilot, the primary annotator labelled unmatched ops of that model `distinct` >= 98% of the time
(results/v2/task4: Gemini 99.4%, Terra 98.3%, Luna 97.8%). Skipped ops get a rule label (contribution `distinct`,
relation `unmatched`, `label_source: rule_skip`) so that every op has a label. Luna fails the threshold, so all of its
ops are labelled.

usage: v2_task6.py sample              # the Luna/Terra task sample -> results/v2/task6/sample_tasks.csv
       v2_task6.py label [models...]   # default order: terra luna gemini; labels -> data/labels/scale_<shard>.jsonl"""
import glob
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.label.annotate import client_from_env, label_runs  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAB, OUT = f"{ROOT}/data/labels", f"{ROOT}/results/v2/task6"
CFG = yaml.safe_load(open(f"{ROOT}/worktrace/config.yaml"))
A = CFG["annotator"]
PILOT_UNMATCHED_DISTINCT = {"gemini": 0.994, "terra": 0.983, "luna": 0.978}  # results/v2/task4, primary annotator
SKIP_RULE = {m: v >= 0.98 for m, v in PILOT_UNMATCHED_DISTINCT.items()}
SAMPLE_FRAC, SEED = 0.10, 0


def sample():
    """10% of tasks within each gold-patch-size quartile (seed 0); the same tasks for Luna and Terra (all 3 runs)."""
    os.makedirs(OUT, exist_ok=True)
    R = pd.read_parquet(f"{ROOT}/data/runs.parquet", columns=["task_id", "gold_lines"])
    t = R.groupby("task_id").gold_lines.first().reset_index()
    t["stratum"] = pd.qcut(t.gold_lines.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)
    t.loc[t.gold_lines.isna(), "stratum"] = "no_gold"
    rng = np.random.default_rng(SEED)
    pick = []
    for s, g in t.sort_values("task_id").groupby("stratum"):
        k = int(round(SAMPLE_FRAC * len(g)))
        pick.append(g.iloc[rng.choice(len(g), size=k, replace=False)])
    P = pd.concat(pick).sort_values("task_id")
    P.to_csv(f"{OUT}/sample_tasks.csv", index=False)
    print(P.stratum.value_counts().sort_index().to_dict(), "tasks:", len(P))


def _load_shard(path, tasks=None):
    runs = {}
    for row in (r for b in pq.ParquetFile(path).iter_batches(batch_size=25) for r in b.to_pylist()):
        if J.is_infra_failure(row) or (tasks is not None and row["instance_id"] not in tasks):
            continue
        run, ops = J.load_row(row)
        extract_facts(ops)
        runs[run["run_id"]] = (run, ops)
    return runs


def label(*models):
    models = models or ("terra", "luna", "gemini")
    os.makedirs(OUT, exist_ok=True)
    cache = Path(f"{LAB}/cache_scale.jsonl")
    if not cache.exists():  # identical prompts from the pilot are free hits
        shutil.copy(f"{LAB}/cache_pilot.jsonl", cache)
    tasks = set(pd.read_csv(f"{OUT}/sample_tasks.csv").task_id)
    log = []
    for m in models:
        for path in sorted(glob.glob(f"{ROOT}/raw/jetbrains/{m}*.parquet")):
            shard = os.path.basename(path).replace(".parquet", "")
            out = Path(f"{LAB}/scale_{shard}.jsonl")
            if out.exists():
                print("done already:", shard)
                continue
            runs = _load_shard(path, None if m == "gemini" else tasks)
            c = client_from_env(f"{ROOT}/soclaas.env")
            tmp = Path(f"{LAB}/scale_{shard}.llm.jsonl")
            lab = label_runs(runs, tmp, cache, c, prompt_version=A["prompt_version"], n_chars=A["result_chars"],
                             workers=A["workers"], only_matched=SKIP_RULE[m])
            got = {r["op_id"] for r in lab}
            for r in lab:
                r["label_source"] = "llm"
            n_skip = 0
            for run, ops in runs.values():
                for o in ops:
                    if o["op_id"] not in got:
                        assert SKIP_RULE[m] and not (o["cand_object"] or o["cand_output"]), o["op_id"]
                        lab.append({"op_id": o["op_id"], "purpose": "unspecified", "role": None, "relation": "unmatched",
                                    "matched_op": None, "contribution": "distinct", "evidence_refs": [],
                                    "evidence": "rule: unmatched op, skipped under the per-model >=98% rule",
                                    "label_error": False, "label_source": "rule_skip", "prompt_version": A["prompt_version"]})
                        n_skip += 1
            with out.open("w") as f:
                for r in lab:
                    f.write(json.dumps(r) + "\n")
            tmp.unlink()
            row = {"shard": shard, "model": m, "skip_rule_applied": SKIP_RULE[m],
                   "pilot_unmatched_distinct": PILOT_UNMATCHED_DISTINCT[m], "runs": len(runs),
                   "ops": sum(len(o) for _, o in runs.values()), "llm_labels": len(got), "rule_labels": n_skip,
                   "label_errors": sum(r["label_error"] for r in lab), "usage": json.dumps(c.usage), "served": c.served_model}
            log.append(row)
            print(row, flush=True)
            pd.DataFrame([row]).to_csv(f"{OUT}/labeling_log.csv", mode="a", index=False,
                                       header=not os.path.exists(f"{OUT}/labeling_log.csv"))


if __name__ == "__main__":
    {"sample": sample, "label": label}[sys.argv[1]](*sys.argv[2:])
