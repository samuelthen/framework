"""Qwen (Open-SWE-Traces v1.2) labeling, after the Task 5 benchmark review (user decisions 2026-10-25).

Step 1, pilot: 20 of the 2,000 sampled tasks (seed 0) x 3 harnesses, every op labelled with prompt v1 by the primary
annotator. It establishes the per-harness skip rule (unmatched ops labelled `distinct` >= 98% -> skip them in the main
run) and reports the uncertain share.

Step 2, main (user go 2026-10-25): 500 of the 2,000 tasks (seed 0) x 3 harnesses, same tasks in every harness. All matched
ops are labelled; unmatched ops are skipped (rule label) in every harness, since all three passed the >=98% rule on the
pilot (99.4-99.7%). Labelled one harness at a time to bound memory.
Step 3, second: MODEL_2 (glm-5.3-flash) on a random 1,000 of the main run's matched ops (seed 0), for an annotator range.

usage: v2_qwen.py pilot          # labels -> data/labels/qwen_pilot.jsonl
       v2_qwen.py pilot_report   # -> results/v2/qwen/pilot/
       v2_qwen.py main [harness...]  # labels -> data/labels/qwen_main_<harness>.jsonl
       v2_qwen.py second         # labels -> data/labels/qwen_main_model2.jsonl"""
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
N_PILOT, N_MAIN, N_SECOND, SEED = 20, 500, 1000, 0
HARNESSES = ("mini-swe-agent", "openhands", "swe-agent")
PILOT_UNMATCHED_DISTINCT = {"mini-swe-agent": 0.997, "openhands": 0.994, "swe-agent": 0.997}  # pilot_summary.csv
SKIP_RULE = {h: v >= 0.98 for h, v in PILOT_UNMATCHED_DISTINCT.items()}
WORKERS = 2  # pilot only: it shared the key's small queue with the Gemini scale pass


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


def main_runs():
    S = pd.read_parquet(f"{ROOT}/results/v2/task5/runs.parquet", columns=["task_id", "run_id", "harness"])
    tasks = sorted(S.task_id.unique())
    pick = set(np.random.default_rng(SEED).choice(tasks, size=N_MAIN, replace=False))
    S = S[S.task_id.isin(pick)].sort_values(["harness", "task_id"])
    assert len(S) == 3 * N_MAIN, len(S)
    return S


def main(*harnesses):
    os.makedirs(f"{OUT}/main", exist_ok=True)
    S = main_runs()
    S.to_csv(f"{OUT}/main/main_runs.csv", index=False)
    for h in harnesses or HARNESSES:
        out = Path(f"{LAB}/qwen_main_{h}.jsonl")
        if out.exists():
            print("done already:", h)
            continue
        runs = {rid: _load(rid) for rid in S[S.harness == h].run_id}
        c = client_from_env(f"{ROOT}/soclaas.env")
        tmp = Path(f"{LAB}/qwen_main_{h}.llm.jsonl")
        lab = label_runs(runs, tmp, Path(f"{LAB}/cache_qwen.jsonl"), c, prompt_version=A["prompt_version"],
                         n_chars=A["result_chars"], workers=A["workers"], only_matched=SKIP_RULE[h])
        got = {r["op_id"] for r in lab}
        for r in lab:
            r["label_source"] = "llm"
        n_skip = 0
        for run, ops in runs.values():
            for o in ops:
                if o["op_id"] not in got:
                    assert SKIP_RULE[h] and not (o["cand_object"] or o["cand_output"]), o["op_id"]
                    lab.append({"op_id": o["op_id"], "purpose": "unspecified", "role": None, "relation": "unmatched",
                                "matched_op": None, "contribution": "distinct", "evidence_refs": [],
                                "evidence": "rule: unmatched op, skipped under the per-harness >=98% rule",
                                "label_error": False, "label_source": "rule_skip", "prompt_version": A["prompt_version"]})
                    n_skip += 1
        with out.open("w") as f:
            for r in lab:
                f.write(json.dumps(r) + "\n")
        tmp.unlink()
        row = {"harness": h, "skip_rule_applied": SKIP_RULE[h], "pilot_unmatched_distinct": PILOT_UNMATCHED_DISTINCT[h],
               "runs": len(runs), "ops": sum(len(o) for _, o in runs.values()), "llm_labels": len(got), "rule_labels": n_skip,
               "label_errors": sum(r["label_error"] for r in lab), "usage": json.dumps(c.usage), "served": c.served_model}
        print(row, flush=True)
        pd.DataFrame([row]).to_csv(f"{OUT}/main/labeling_log.csv", mode="a", index=False,
                                   header=not os.path.exists(f"{OUT}/main/labeling_log.csv"))
        runs = lab = None


def second():
    S = main_runs()
    assert all(os.path.exists(f"{LAB}/qwen_main_{h}.jsonl") for h in HARNESSES), "run `main` first"
    matched = []
    for rid in S.run_id:
        _, ops = _load(rid)
        matched += [o["op_id"] for o in ops if o["cand_object"] or o["cand_output"]]
    pick = set(np.random.default_rng(SEED).choice(sorted(matched), size=N_SECOND, replace=False))
    pd.DataFrame({"op_id": sorted(pick)}).to_csv(f"{OUT}/main/second_items.csv", index=False)
    keep = S[S.run_id.isin({o.rsplit(":", 1)[0] for o in pick})].run_id
    runs = {rid: _load(rid) for rid in keep}
    c = client_from_env(f"{ROOT}/soclaas.env")
    c.model = A["model_2_alias"]
    lab = label_runs(runs, Path(f"{LAB}/qwen_main_model2.jsonl"), Path(f"{LAB}/cache_qwen_model2.jsonl"), c,
                     prompt_version=A["prompt_version"], n_chars=A["result_chars"], workers=A["workers"],
                     op_filter=lambda o: o["op_id"] in pick)
    print({"labels": len(lab), "errors": sum(r["label_error"] for r in lab), "usage": c.usage, "served": c.served_model})


if __name__ == "__main__":
    {"pilot": pilot, "pilot_report": pilot_report, "main": main, "second": second}[sys.argv[1]](*sys.argv[2:])
