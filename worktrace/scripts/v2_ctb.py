"""Task 4 external check on CodeTraceBench (verified split, SWE-bench trajectories, pinned revision).

usage: v2_ctb.py extract   # unpack the downloaded artifacts (data only) into raw/codetracebench/extracted
       v2_ctb.py load      # adapters + facts for all runs; step-count alignment check; event logs to data/events/ctb
       v2_ctb.py show RUN  # print a run's ops next to the raw steps (for the hand check)
       v2_ctb.py label     # primary annotator, prompt v1, on every op with a match candidate
       v2_ctb.py eval      # precision / recall / F1 vs human "unuseful" steps; exact and same-object baselines"""
import glob
import io
import json
import os
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.loaders import codetracebench as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = f"{ROOT}/raw/codetracebench"
EV = f"{ROOT}/data/events/ctb"
OUT = f"{ROOT}/results/v2/task4/codetracebench"
REV = "aa213b84ffb6690fc37ca15766d6ca174ec36d4d"


def manifest():
    m = pd.read_parquet(f"{D}/bench_manifest.verified.parquet")
    return m[m.source_relpath.str.startswith("swe_raw")].reset_index(drop=True)


def extract():
    import zstandard
    n = 0
    for p in sorted(glob.glob(f"{D}/bench_artifacts/full/*.tar.zst")):
        with open(p, "rb") as fh:
            t = tarfile.open(fileobj=io.BytesIO(zstandard.ZstdDecompressor().stream_reader(fh).read()))
            t.extractall(f"{D}/extracted", filter="data")
        n += 1
    print("extracted", n)


def _safe(rid):
    return rid.replace(":", "__").replace("/", "_")


def load():
    os.makedirs(EV, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for _, r in manifest().iterrows():
        try:
            run, ops = C.load(f"{D}/extracted", r)
        except (IndexError, FileNotFoundError, ValueError) as e:
            rows.append({"traj_id": r.traj_id, "agent": r.agent, "error": str(e)[:100]})
            continue
        extract_facts(ops)
        with open(f"{EV}/{_safe(run['run_id'])}.jsonl", "w") as f:
            for o in ops:
                f.write(json.dumps(o) + "\n")
        json.dump(run, open(f"{EV}/{_safe(run['run_id'])}.run.json", "w"))
        rows.append({"traj_id": r.traj_id, "run_id": run["run_id"], "agent": r.agent, "task": r.task_name,
                     "step_count": run["step_count"], "n_ops": len(ops), "aligned": len(ops) == run["step_count"],
                     "unuseful": len(run["unuseful_steps"]), "unuseful_out_of_range": sum(s > len(ops) for s in run["unuseful_steps"]),
                     "matched_ops": sum(bool(o["cand_object"] or o["cand_output"]) for o in ops),
                     "exact_repeats": sum(o["exact_repeat"] for o in ops)})
    A = pd.DataFrame(rows)
    A.to_csv(f"{OUT}/alignment.csv", index=False)
    print(A.groupby("agent").agg(runs=("traj_id", "size"), aligned=("aligned", "mean"), steps=("step_count", "sum"),
                                 unuseful=("unuseful", "sum"), matched=("matched_ops", "sum"), exact=("exact_repeats", "sum")))
    if "error" in A:
        print("errors:", A.error.notna().sum())
    print(A[~A.aligned.fillna(False)].head(10).to_string())


def show(run_id, n=None):
    m = manifest().set_index("traj_id")
    tid = run_id.split("ctb:", 1)[-1]
    run = json.load(open(f"{EV}/{_safe('ctb:' + tid)}.run.json"))
    ops = [json.loads(l) for l in open(f"{EV}/{_safe('ctb:' + tid)}.jsonl")]
    print(run["harness"], tid, "steps", run["step_count"], "ops", len(ops), "unuseful", run["unuseful_steps"], "incorrect", run["incorrect_steps"])
    for o in ops[: int(n) if n else None]:
        flag = "U" if o["step_id"] in run["unuseful_steps"] else ("I" if o["step_id"] in run["incorrect_steps"] else " ")
        print(f"{flag} {o['step_id']:3d} {o['kind']:7s} w={o['write']:7s} ex={str(o['exit_code']):4s} rep={int(o['exact_repeat'])} "
              f"A={'y' if o['cand_object'] else '-'} | {o['command'][:110]!r} | {(o['output'] or '')[:70]!r}")


def _load_all():
    out = {}
    for f in sorted(glob.glob(f"{EV}/*.run.json")):
        run = json.load(open(f))
        ops = [json.loads(l) for l in open(f.replace(".run.json", ".jsonl"))]
        if len(ops) == run["step_count"]:
            out[run["run_id"]] = (run, ops)
    return out


def label():
    from worktrace.label.annotate import client_from_env, label_runs
    import yaml
    A = yaml.safe_load(open(f"{ROOT}/worktrace/config.yaml"))["annotator"]
    runs = _load_all()
    c = client_from_env(f"{ROOT}/soclaas.env")
    out = label_runs(runs, Path(f"{ROOT}/data/labels/ctb.jsonl"), Path(f"{ROOT}/data/labels/cache_ctb.jsonl"), c,
                     prompt_version=A["prompt_version"], n_chars=A["result_chars"], workers=A["workers"], only_matched=True)
    print("labels", len(out), "errors", sum(r["label_error"] for r in out), c.usage, c.served_model)


def _prf(df, pred):
    from v2_viewb import _rci
    tp = lambda d: (d[pred] & d.gold).astype(float)  # noqa: E731
    p = _rci(df, tp, lambda d: d[pred].astype(float), cluster="task")
    r = _rci(df, tp, lambda d: d.gold.astype(float), cluster="task")
    f1 = 2 * p[0] * r[0] / (p[0] + r[0]) if (p[0] + r[0]) else 0.0
    return {"predicted": int(df[pred].sum()), "tp": int((df[pred] & df.gold).sum()),
            "precision": f"{100 * p[0]:.1f}% [{100 * p[1]:.1f}, {100 * p[2]:.1f}]",
            "recall": f"{100 * r[0]:.1f}% [{100 * r[1]:.1f}, {100 * r[2]:.1f}]", "f1": round(100 * f1, 1)}


def evaluate():
    runs = _load_all()
    lab = {r["op_id"]: r for r in map(json.loads, open(f"{ROOT}/data/labels/ctb.jsonl"))} if os.path.exists(f"{ROOT}/data/labels/ctb.jsonl") else {}
    rows = []
    for rid, (run, ops) in runs.items():
        for o in ops:
            l = lab.get(o["op_id"], {})
            rows.append({"run_id": rid, "task": run["task_id"], "agent": run["harness"], "step": o["step_id"],
                         "gold": o["step_id"] in run["unuseful_steps"], "gold_incorrect": o["step_id"] in run["incorrect_steps"],
                         "exact_repeat": bool(o["exact_repeat"]), "same_object": bool(o["cand_object"]),
                         "non_distinct": l.get("contribution") == "non_distinct",
                         "cand_redundant": l.get("contribution") == "non_distinct" and l.get("relation") == "reproduces",
                         # uncertain counted as redundant (the "hi" end of the uncertain range)
                         "non_distinct_hi": l.get("contribution") in ("non_distinct", "uncertain"),
                         "cand_redundant_hi": (l.get("contribution") == "non_distinct" and l.get("relation") == "reproduces")
                         or l.get("contribution") == "uncertain" or l.get("relation") == "uncertain",
                         "labeled": bool(l)})
    S = pd.DataFrame(rows)
    S.to_csv(f"{OUT}/steps.csv", index=False)
    res = []
    for agent, g in list(S.groupby("agent")) + [("ALL", S)]:
        for pred in ("exact_repeat", "same_object", "non_distinct", "non_distinct_hi", "cand_redundant", "cand_redundant_hi"):
            res.append({"agent": agent, "runs": g.run_id.nunique(), "steps": len(g), "gold_unuseful": int(g.gold.sum()),
                        "predictor": pred} | _prf(g, pred))
    R = pd.DataFrame(res)
    R.to_csv(f"{OUT}/prf.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.to_string())
    print("labeled ops:", S.labeled.sum(), "| gold unuseful also labelled incorrect:", int((S.gold & S.gold_incorrect).sum()))


if __name__ == "__main__":
    {"extract": extract, "load": load, "show": show, "label": label, "eval": evaluate}[sys.argv[1]](*sys.argv[2:])
