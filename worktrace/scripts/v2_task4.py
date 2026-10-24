"""Task 4: proxy validation (no human labels).
  second   - MODEL_2 (config annotator.model_2_alias), same prompt v1, on all matched pilot ops + 200 random unmatched
  selfcons - primary annotator at temperature 0.7, 3 samples, on the same ops
  agree    - kappa, macro-F1, confusion (primary v2 labels vs MODEL_2; primary vs its samples)

usage: v2_task4.py second | selfcons | agree"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.label.annotate import client_from_env, label_runs  # noqa: E402
import m4_pilot as P  # noqa: E402

ROOT, CFG, LAB = P.ROOT, P.CFG, P.LAB
OUT = f"{ROOT}/results/v2/task4"
A = CFG["annotator"]


def item_set():
    """All matched ops + 200 random unmatched ops (seed 0), fixed once and saved."""
    path = f"{OUT}/items.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    rows = [{"op_id": o["op_id"], "run_id": rid, "task_id": run["task_id"], "model": run["model"],
             "matched": bool(o["cand_object"] or o["cand_output"])} for rid, (run, ops) in P.load_pilot().items() for o in ops]
    d = pd.DataFrame(rows)
    um = d[~d.matched]
    pick = um.iloc[np.random.default_rng(0).choice(len(um), size=200, replace=False)]
    out = pd.concat([d[d.matched], pick])
    out.to_csv(path, index=False)
    return out


def _run(client, name, cache_tag=""):
    ids = set(item_set().op_id)
    return label_runs(P.load_pilot(), Path(f"{LAB}/{name}.jsonl"), Path(f"{LAB}/cache_{name}.jsonl"), client,
                      prompt_version=A["prompt_version"], n_chars=A["result_chars"], workers=A["workers"],
                      op_filter=lambda o: o["op_id"] in ids, cache_tag=cache_tag)


def second():
    os.makedirs(OUT, exist_ok=True)
    c = client_from_env(f"{ROOT}/soclaas.env")
    c.model = A["model_2_alias"]
    out = _run(c, "pilot_model2")
    print("model2", len(out), "errors", sum(r["label_error"] for r in out), c.usage, c.served_model)


def selfcons():
    os.makedirs(OUT, exist_ok=True)
    sc = A["self_consistency"]
    for s in range(sc["samples"]):
        c = client_from_env(f"{ROOT}/soclaas.env")
        c.temperature = sc["temperature"]
        out = _run(c, f"pilot_selfcons_s{s}", cache_tag=f"@t{sc['temperature']}#s{s}")  # prompt text is v1
        print("sample", s, len(out), "errors", sum(r["label_error"] for r in out), c.usage)


def _kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in set(a) | set(b)) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def _macro_f1(ref, other, cats):
    f = []
    for c in cats:
        tp = sum((r == c) and (o == c) for r, o in zip(ref, other))
        p = tp / max(1, sum(o == c for o in other))
        r = tp / max(1, sum(r_ == c for r_ in ref))
        f.append(2 * p * r / (p + r) if p + r else 0.0)
    return float(np.mean(f))


def _compare(ref: dict, oth: dict, items: pd.DataFrame, name: str):
    rows, conf = [], {}
    for field, cats in (("contribution", ["distinct", "non_distinct", "uncertain"]),
                        ("relation", ["unmatched", "revisits", "reproduces", "uncertain"])):
        for subset, d in (("matched", items[items.matched]), ("unmatched_sample", items[~items.matched]), ("all", items)):
            ids = [i for i in d.op_id if i in ref and i in oth]
            a = [ref[i][field] for i in ids]
            b = [oth[i][field] for i in ids]
            present = [c for c in cats if c in a or c in b]
            rows.append({"comparison": name, "field": field, "subset": subset, "n": len(ids),
                         "agreement": float(np.mean([x == y for x, y in zip(a, b)])) if ids else np.nan,
                         "kappa": _kappa(a, b), "macro_f1": _macro_f1(a, b, present)})
            if subset != "all":
                conf[(field, subset)] = pd.crosstab(pd.Series(a, name="primary"), pd.Series(b, name=name))
    # candidate redundancy (reproduces & non_distinct) as a binary label
    ids = [i for i in items.op_id if i in ref and i in oth]
    cr = lambda l: l["relation"] == "reproduces" and l["contribution"] == "non_distinct"  # noqa: E731
    a, b = [cr(ref[i]) for i in ids], [cr(oth[i]) for i in ids]
    rows.append({"comparison": name, "field": "cand_redundant", "subset": "all", "n": len(ids),
                 "agreement": float(np.mean([x == y for x, y in zip(a, b)])), "kappa": _kappa(a, b),
                 "macro_f1": _macro_f1(a, b, [True, False])})
    return rows, conf


def agree():
    items = item_set()
    ref = P.read_labels("pilot_v2")
    out, confs = [], {}
    m2 = P.read_labels("pilot_model2")
    r, c = _compare(ref, m2, items, "model2")
    out += r; confs["model2"] = c
    samples = [P.read_labels(f"pilot_selfcons_s{s}") for s in range(A["self_consistency"]["samples"])]
    samples = [s for s in samples if s]
    for k, smp in enumerate(samples):
        r, c = _compare(ref, smp, items, f"self_s{k}")
        out += r
        if k == 0:
            confs["self_s0"] = c
    T = pd.DataFrame(out)
    T.to_csv(f"{OUT}/agreement.csv", index=False)
    with open(f"{OUT}/confusion.md", "w") as f:
        for name, cc in confs.items():
            for (field, subset), tab in cc.items():
                f.write(f"### primary vs {name}: {field}, {subset}\n\n{tab.to_markdown()}\n\n")
    if samples:
        # majority-vote stability: share of ops where all samples (and the T=0 label) give the same contribution
        ids = [i for i in items.op_id if i in ref and all(i in s for s in samples)]
        same = [len({ref[i]["contribution"], *[s[i]["contribution"] for s in samples]}) == 1 for i in ids]
        flips = pd.DataFrame({"op_id": ids, "stable": same}).merge(items, on="op_id")
        st = flips.groupby("matched").stable.mean().to_dict()
        print("contribution identical across T=0 and all samples:", st)
        json_out = {"stable_share_by_matched": {str(k): v for k, v in st.items()}, "n": len(ids)}
        import json
        json.dump(json_out, open(f"{OUT}/self_consistency_stability.json", "w"), indent=1)
    pd.set_option("display.width", 200)
    print(T.round(3).to_string())
    print(open(f"{OUT}/confusion.md").read()[:4000])


if __name__ == "__main__":
    {"second": second, "selfcons": selfcons, "agree": agree}[sys.argv[1]]()
