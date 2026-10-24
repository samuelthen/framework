"""M5: export the blind human-annotation sample (B.8) and compute agreement once humans have filled it in.

usage: m5_annotation.py export | agree <filled.csv>
The filled CSV must keep the exported columns and add: h1_relation, h1_contribution, h1_role, h2_relation,
h2_contribution, h2_role, and (after adjudication) adj_relation, adj_contribution, adj_role."""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from m4_pilot import CFG, ROOT, _kappa, load_pilot, read_labels  # noqa: E402
from worktrace.label.annotate import short, sid  # noqa: E402

OUT = f"{ROOT}/annotation"


def _hard_case(o, by_id, lab):
    c = by_id.get(o["cand_object"])
    f = o["cand_facts"].get(o["cand_object"], {}) if c else {}
    if o["kind"] == "read" and c and lab.get("relation") == "revisits":
        return "reread_new_purpose"
    if o["kind"] == "search" and (o["exit_code"] not in (0, None) or len((o["output"] or "").strip()) == 0):
        return "failed_search"
    if o["kind"] == "run" and c and f.get("any_code_written_since") == "yes":
        return "test_after_edit"
    if o["kind"] == "run" and c and f.get("any_code_written_since") == "no" and not f.get("same_output"):
        return "nondeterministic_test"
    if lab.get("relation") == "reproduces":
        return "model_reproduces"
    return ""


def export():
    os.makedirs(OUT, exist_ok=True)
    runs = load_pilot()
    labels = read_labels("pilot")
    rng = np.random.default_rng(CFG["pilot"]["seed"])
    rows = []
    for rid, (run, ops) in runs.items():
        by_id = {o["op_id"]: o for o in ops}
        for o in ops:
            lab = labels.get(o["op_id"], {})
            def cand(cid):
                c = by_id.get(cid)
                if not c:
                    return ""
                f = o["cand_facts"][cid]
                return (f"{sid(c)} | $ {short(c['command'], 400)}\n(exit {c['exit_code']})\n{short(c['output'], 800)}\n"
                        f"[same output={f['same_output']}; object written since={f['object_written_since']}; any code written since={f['any_code_written_since']}]")
            rows.append({"item": None, "op_id": o["op_id"], "model": run["model"], "hard_case": _hard_case(o, by_id, lab),
                         "has_cand": bool(o["cand_object"] or o["cand_output"]),
                         "issue": short(run["issue"], 700), "op": sid(o), "agent_message": short(o["agent_message"], 600),
                         "command": short(o["command"], 600), "exit_code": o["exit_code"], "output": short(o["output"], 1000),
                         "candidate_A": cand(o["cand_object"]),
                         "candidate_B": cand(o["cand_output"]) if o["cand_output"] != o["cand_object"] else "(same as A)" if o["cand_output"] else "",
                         "kinds": ",".join(o["part_kinds"]), "write": o["write"]})
    D = pd.DataFrame(rows)
    n = CFG["annotation_sample"]["pilot_ops"]
    # half enriched hard cases (stratified across types), half stratified random by model, preferring matched ops
    hard = D[D.hard_case != ""]
    per_type = max(1, (n // 2) // max(1, hard.hard_case.nunique()))
    picked = pd.concat([g.sample(min(len(g), per_type), random_state=0) for _, g in hard.groupby("hard_case")])
    rest = D.drop(picked.index)
    k = n - len(picked)
    per_model = k // rest.model.nunique()
    rnd = pd.concat([g.sample(min(len(g), per_model), random_state=0, weights=np.where(g.has_cand, 3.0, 1.0)) for _, g in rest.groupby("model")])
    S = pd.concat([picked, rnd]).sample(frac=1, random_state=0).reset_index(drop=True)
    S["item"] = range(1, len(S) + 1)
    key = S[["item", "op_id", "model", "hard_case"]]
    key.to_csv(f"{OUT}/pilot_key.csv", index=False)
    blind = S.drop(columns=["op_id", "model", "hard_case", "has_cand"])
    for c in ("h1_relation", "h1_contribution", "h1_role", "h2_relation", "h2_contribution", "h2_role", "adj_relation", "adj_contribution", "adj_role", "notes"):
        blind[c] = ""
    blind.to_csv(f"{OUT}/pilot.csv", index=False)
    print(len(S), "items;", key.hard_case.replace("", "random").value_counts().to_dict(), key.model.value_counts().to_dict())


def _f1(y, p, classes):
    f = []
    for c in classes:
        tp = sum((a == c) and (b == c) for a, b in zip(y, p))
        fp = sum((a != c) and (b == c) for a, b in zip(y, p))
        fn = sum((a == c) and (b != c) for a, b in zip(y, p))
        f.append(0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f))


def agree(path):
    H = pd.read_csv(path).merge(pd.read_csv(f"{OUT}/pilot_key.csv"), on="item")
    L = read_labels("pilot")
    H["m_relation"] = H.op_id.map(lambda i: L[i]["relation"])
    H["m_contribution"] = H.op_id.map(lambda i: L[i]["contribution"])
    H["m_role"] = H.op_id.map(lambda i: L[i]["role"])
    res = {}
    for f in ("relation", "contribution", "role"):
        h = H.dropna(subset=[f"h1_{f}", f"h2_{f}"])
        res[f"human_kappa_{f}"] = _kappa(h[f"h1_{f}"], h[f"h2_{f}"])
        a = H.dropna(subset=[f"adj_{f}"])
        classes = sorted(set(a[f"adj_{f}"]))
        res[f"model_macroF1_{f}"] = _f1(list(a[f"adj_{f}"]), list(a[f"m_{f}"]), classes)
        res[f"confusion_{f}"] = pd.crosstab(a[f"adj_{f}"], a[f"m_{f}"]).to_dict()
    a = H.dropna(subset=["adj_relation", "adj_contribution"])
    mflag = (a.m_relation == "reproduces") & (a.m_contribution == "non_distinct")
    hflag = (a.adj_relation == "reproduces") & (a.adj_contribution == "non_distinct")
    res["cand_redundancy_precision"] = float((mflag & hflag).sum() / mflag.sum()) if mflag.sum() else None
    res["cand_redundancy_recall"] = float((mflag & hflag).sum() / hflag.sum()) if hflag.sum() else None
    hc = a[a.hard_case.fillna("") != ""]
    res["hard_case_contribution_accuracy"] = float((hc.m_contribution == hc.adj_contribution).mean()) if len(hc) else None
    g = CFG["go_no_go"]
    res["go_no_go"] = {"1_kappa": (res["human_kappa_contribution"] or 0) >= g["min_human_kappa"],
                       "2_f1": res["model_macroF1_contribution"] >= g["min_macro_f1"],
                       "2_precision": (res["cand_redundancy_precision"] or 0) >= g["min_cand_redundancy_precision"]}
    json.dump(res, open(f"{ROOT}/results/agreement.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    if sys.argv[1] == "export":
        export()
    else:
        agree(sys.argv[2])
