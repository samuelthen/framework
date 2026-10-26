"""Section 4 scoring: assemble the evidence-linked labels, validate them, and compute per-run contribution bounds.

Inputs: annotations_raw/<order>.txt (one line per action: run|idx|role|label|reason|reqs|content|evidence|downstream|survives),
requirements_raw/<order>.json, packets/blinding_key.csv, sample_manifest.csv.
Outputs: action_annotations.jsonl, requirements.jsonl, scores_by_run.csv, pilot_pairs.csv.

usage: python scripts/one_day_precision/score.py"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, PRIMARY, log  # noqa: E402

LABELS = {"direct", "non_direct", "uncertain"}
ROLES = {"exploration", "edit", "verification", "administration"}
REASONS = {"negative_detour", "unused_context", "repeated_support", "discarded_edit", "superseded_check",
           "unrelated_check", "style_only", "scaffolding", "administration", "other"}
PROVENANCE = "Claude (Anthropic), model-coded, single pass, preliminary; not human-validated; blinded run labels X/Y"


def parse_raw(path):
    rows = []
    for line in open(path):
        if not line.strip() or line.startswith("#"):
            continue
        f = line.rstrip("\n").split("|")
        assert len(f) == 10, (path, line[:80])
        run, idx, role, label, reason, reqs, content, evidence, downstream, survives = f
        rows.append({"label_run": run, "action_index": int(idx), "role": role, "contribution_label": label,
                     "non_direct_reason": reason or None, "requirement_ids": [r for r in reqs.split(",") if r],
                     "contributed_content": content, "evidence_spans": evidence,
                     "downstream_support": [d for d in downstream.split(",") if d and d != "-"],
                     "survives_to_final": {"yes": True, "no": False}.get(survives)})
    return rows


def score_run(g):
    """Bounds for one run: lower D/N, upper (D+U)/N, uncertain U/N. g: that run's action rows (one per action)."""
    n = len(g)
    if n == 0:
        return {"N": 0, "D": 0, "U": 0, "P_lower": np.nan, "P_upper": np.nan, "uncertain_share": np.nan}
    d = int((g.contribution_label == "direct").sum())
    u = int((g.contribution_label == "uncertain").sum())
    return {"N": n, "D": d, "U": u, "P_lower": d / n, "P_upper": (d + u) / n, "uncertain_share": u / n}


def validate(rows, n_expected):
    idx = sorted(r["action_index"] for r in rows)
    assert idx == list(range(n_expected)), f"action indices incomplete: {len(idx)} vs {n_expected}"
    for r in rows:
        assert r["contribution_label"] in LABELS, r
        assert r["role"] in ROLES, r
        if r["contribution_label"] == "non_direct":
            assert r["non_direct_reason"] in REASONS, r
        else:
            assert r["non_direct_reason"] is None, r


def main():
    K = pd.read_csv(f"{OUT}/packets/blinding_key.csv")
    S = pd.read_csv(f"{OUT}/sample_manifest.csv").set_index("run_id")
    ann, reqs = [], []
    for path in sorted(glob.glob(f"{OUT}/annotations_raw/*.txt")):
        order = int(os.path.basename(path)[:2])
        rows = parse_raw(path)
        rj = json.load(open(f"{OUT}/requirements_raw/{order:02d}.json"))
        req_ids = {q["id"] for q in rj["requirements"]}
        for q in rj["requirements"]:
            reqs.append({"task_id": rj["task_id"], "requirement_id": q["id"], **{k: v for k, v in q.items() if k != "id"},
                         "verification_status": rj["verification_status"], "provenance": PROVENANCE})
        for lab, g in pd.DataFrame(rows).groupby("label_run"):
            k = K[(K.order == order) & (K.label == lab)].iloc[0]
            sub = [r for r in rows if r["label_run"] == lab]
            validate(sub, int(S.loc[k.run_id, "n_actions"]))
            for r in sub:
                assert set(r["requirement_ids"]) <= req_ids, (path, r)
                ann.append({"task_id": k.task_id, "run_id": k.run_id, "op_id": f"{k.run_id}#a{r['action_index']}",
                            "split": S.loc[k.run_id, "split"], "order": order, **{x: r[x] for x in r if x != "label_run"},
                            "relevant_state": "read from the logged trace (commands, outputs, final submission); not re-executed",
                            "uncertainty_reason": r["contributed_content"] if r["contribution_label"] == "uncertain" else None,
                            "guide_version": "v0 (calibration)" if S.loc[k.run_id, "split"] == "calibration" else "v1 (frozen)",
                            "annotator_provenance": PROVENANCE, "blinded_label": lab})
    A = pd.DataFrame(ann)
    with open(f"{OUT}/action_annotations.jsonl", "w") as f:
        for r in ann:
            f.write(json.dumps(r) + "\n")
    with open(f"{OUT}/requirements.jsonl", "w") as f:
        for r in reqs:
            f.write(json.dumps(r) + "\n")
    # per-run scores (all actions) and the sensitivity without submission actions
    out = []
    for (task, run), g in A.groupby(["task_id", "run_id"]):
        s = score_run(g)
        nosub = score_run(g[~g.contributed_content.str.lower().eq("submission")])
        m = S.loc[run]
        roles = {f"direct_{r}": int(((g.role == r) & (g.contribution_label == "direct")).sum()) for r in sorted(ROLES)}
        reasons = {f"nd_{r}": int((g.non_direct_reason == r).sum()) for r in sorted(REASONS)}
        out.append({"task_id": task, "run_id": run, "model": m.model, "split": m.split, "order": int(m.order),
                    "resolved": bool(m.resolved), **s,
                    "P_lower_excl_submit": nosub["P_lower"], "P_upper_excl_submit": nosub["P_upper"],
                    **roles, **reasons, "score_status": "computed (model-coded, preliminary)",
                    "Q_failure": None, "reference_requirement_coverage": None,
                    "recall_status": "not_applicable: successful run (failed-run extension not run; see status.json)"})
    R = pd.DataFrame(out).sort_values(["order", "model"])
    R.to_csv(f"{OUT}/scores_by_run.csv", index=False)
    # paired per-task differences (Gemini - Luna)
    pairs = []
    for (order, task), g in R.groupby(["order", "task_id"]):
        if set(g.model) != set(PRIMARY):
            continue
        a, b = g.set_index("model").loc[PRIMARY[0]], g.set_index("model").loc[PRIMARY[1]]
        pairs.append({"order": order, "task_id": task, "split": a.split, "N_gemini": a.N, "N_luna": b.N,
                      "P_lower_gemini": a.P_lower, "P_upper_gemini": a.P_upper, "P_lower_luna": b.P_lower, "P_upper_luna": b.P_upper,
                      "diff_lower": a.P_lower - b.P_lower, "diff_upper": a.P_upper - b.P_upper,
                      # range of the difference over all uncertain-label resolutions
                      "diff_min": a.P_lower - b.P_upper, "diff_max": a.P_upper - b.P_lower})
    P = pd.DataFrame(pairs)
    P.to_csv(f"{OUT}/pilot_pairs.csv", index=False)
    log(f"score: {len(A)} action labels, {A.run_id.nunique()} runs, {len(P)} complete task pairs "
        f"({(P.split == 'evaluation').sum()} evaluation)")
    pd.set_option("display.width", 220)
    print(R[["order", "split", "model", "N", "D", "U", "P_lower", "P_upper"]].round(3).to_string(index=False))
    return A, R, P


if __name__ == "__main__":
    main()
