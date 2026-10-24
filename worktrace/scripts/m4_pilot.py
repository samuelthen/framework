"""M4-M7 on the pilot: sample runs, write event logs, LLM-label every op (full pipeline + LLM-only baseline),
build graphs/visit sequences/signatures, compute measures and the go/no-go items that do not need humans.

usage: m4_pilot.py sample | label [--llm-only] | analyze"""
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.graph import build_graph, fmt_visits, visit_sequences  # noqa: E402
from worktrace.label.annotate import client_from_env, label_runs  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402
from worktrace.measures import run_measures  # noqa: E402
from worktrace.signatures import SIGNATURES, run_signatures  # noqa: E402
from worktrace.stats import cluster_bootstrap  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CFG = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "config.yaml")))
EV = f"{ROOT}/data/events/jetbrains"
LAB = f"{ROOT}/data/labels"
RES = f"{ROOT}/results/pilot"
SPLITS = {"gpt-5.6-luna": "luna", "gpt-5.6-terra": "terra", "gemini-3.7-flash": "gemini_3_7_flash"}


def sample():
    os.makedirs(EV, exist_ok=True)
    from m1_m3_benchmark import gold_table
    gt = gold_table()
    p = CFG["pilot"]
    rng = np.random.default_rng(p["seed"])
    all_tasks = pd.read_parquet(f"{ROOT}/raw/jetbrains/luna-run1.parquet", columns=["instance_id"]).instance_id
    tasks = sorted(t for t in all_tasks if t in gt)
    chosen = list(rng.choice(tasks, size=p["tasks"], replace=False))
    picks = []
    for m in SPLITS:
        for t in chosen:
            idx = int(rng.integers(1, 4))
            picks.append((m, t, idx))
    picks = picks[: p["runs"]]
    by_file = defaultdict(list)
    for m, t, idx in picks:
        by_file[f"{ROOT}/raw/jetbrains/{SPLITS[m]}-run{idx}.parquet"].append(t)
    manifest = []
    for f, ts in by_file.items():
        df = pd.read_parquet(f, filters=[("instance_id", "in", ts)])
        for _, row in df.iterrows():
            run, ops = J.load_row(row)
            extract_facts(ops)
            run["gold_file_list"], run["gold_lines"] = gt[run["task_id"]][0], gt[run["task_id"]][1]
            run["gold_files"] = len(run["gold_file_list"])
            with open(f"{EV}/{_safe(run['run_id'])}.jsonl", "w") as fh:
                for o in ops:
                    fh.write(json.dumps(o) + "\n")
            json.dump(run, open(f"{EV}/{_safe(run['run_id'])}.run.json", "w"))
            manifest.append({"run_id": run["run_id"], "model": run["model"], "task_id": run["task_id"], "n_ops": len(ops),
                             "resolved": run["resolved"]})
    pd.DataFrame(manifest).to_csv(f"{ROOT}/data/pilot_manifest.csv", index=False)
    print(pd.DataFrame(manifest).groupby("model").agg(runs=("run_id", "size"), ops=("n_ops", "sum"), resolved=("resolved", "mean")))


def _safe(rid):
    return rid.replace(":", "__").replace("/", "_")


def load_pilot():
    man = pd.read_csv(f"{ROOT}/data/pilot_manifest.csv")
    out = {}
    for rid in man.run_id:
        run = json.load(open(f"{EV}/{_safe(rid)}.run.json"))
        ops = [json.loads(l) for l in open(f"{EV}/{_safe(rid)}.jsonl")]
        out[rid] = (run, ops)
    return out


def label(llm_only=False):
    os.makedirs(LAB, exist_ok=True)
    runs = load_pilot()
    client = client_from_env(f"{ROOT}/soclaas.env")
    pv = "llmonly_v1" if llm_only else CFG["annotator"]["prompt_version"]
    name = "pilot_llmonly" if llm_only else "pilot"
    out = label_runs(runs, __import__("pathlib").Path(f"{LAB}/{name}.jsonl"), __import__("pathlib").Path(f"{LAB}/cache_{name}.jsonl"),
                     client, prompt_version=pv, n_chars=CFG["annotator"]["result_chars"], workers=CFG["annotator"]["workers"],
                     llm_only=llm_only, reasoning_matched="off" if llm_only else "low", only_matched=llm_only)
    print(name, len(out), "labels; errors:", sum(r["label_error"] for r in out), "usage:", client.usage, "served:", client.served_model)


def read_labels(name):
    p = f"{LAB}/{name}.jsonl"
    return {r["op_id"]: r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def analyze(labels_name="pilot", RES=RES, graphs=f"{ROOT}/data/graphs"):
    os.makedirs(RES, exist_ok=True)
    os.makedirs(graphs, exist_ok=True)
    runs = load_pilot()
    labels = read_labels(labels_name)
    base = read_labels("pilot_llmonly")
    meas, sig_rows, opsrows, vis_rows = [], [], [], []
    for rid, (run, ops) in runs.items():
        g = build_graph(run, ops, labels, by="target")
        go = build_graph(run, ops, labels, by="object")
        json.dump(g, open(f"{graphs}/{_safe(rid)}.json", "w"))
        json.dump(go, open(f"{graphs}/{_safe(rid)}.object.json", "w"))
        assert len(g["edges"]) == len(ops) and len({e["op_id"] for e in g["edges"]}) == len(ops)
        meas.append(run_measures(run, ops, labels))
        for by, gg in (("target", g), ("object", go)):
            sigs = run_signatures(gg, ops)
            for name, matches in sigs.items():
                for mt in matches:
                    sig_rows.append({"run_id": rid, "task_id": run["task_id"], "model": run["model"], "by": by,
                                     "signature": name, **{k: mt.get(k) for k in ("op_id", "contribution", "exact_repeat", "relation", "k")}})
            if by == "object":
                for t, vs in visit_sequences(gg["edges"]).items():
                    if len(vs) > 1:
                        vis_rows.append({"run_id": rid, "model": run["model"], "target": t, "visits": len(vs), "sequence": fmt_visits(vs)})
        for o in ops:
            l, b = labels.get(o["op_id"], {}), base.get(o["op_id"], {})
            opsrows.append({"run_id": rid, "task_id": run["task_id"], "model": run["model"], "op_id": o["op_id"],
                            "op_index": o["op_index"], "kind": o["kind"], "object": o["object"], "exact_repeat": o["exact_repeat"],
                            "has_cand": bool(o["cand_object"] or o["cand_output"]), "cand_object": o["cand_object"],
                            "cand_output": o["cand_output"], "write": o["write"], "mixed": o["mixed"],
                            "same_output_vs_A": (o["cand_facts"].get(o["cand_object"]) or {}).get("same_output") if o["cand_object"] else None,
                            "role": l.get("role"), "relation": l.get("relation"), "contribution": l.get("contribution"),
                            "matched_op": l.get("matched_op"), "purpose": l.get("purpose"), "label_error": l.get("label_error"),
                            "evidence": l.get("evidence"),
                            "b_relation": b.get("relation"), "b_contribution": b.get("contribution"), "b_label_error": b.get("label_error")})
    M, S, O, V = pd.DataFrame(meas), pd.DataFrame(sig_rows), pd.DataFrame(opsrows), pd.DataFrame(vis_rows)
    M.to_csv(f"{RES}/run_measures.csv", index=False)
    S.to_csv(f"{RES}/signature_matches.csv", index=False)
    O.to_csv(f"{RES}/ops_labeled.csv", index=False)
    V.to_csv(f"{RES}/visit_sequences.csv", index=False)
    O["cand_redundant"] = (O.relation == "reproduces") & (O.contribution == "non_distinct")
    summary = {}

    # Label quality (M4 checkpoint)
    n = len(O)
    summary["labels"] = {"ops": n, "labeled": int(O.contribution.notna().sum()),
                         "valid_json_and_rules_share": float((O.label_error == False).mean()),  # noqa: E712
                         "label_errors": int((O.label_error == True).sum()),  # noqa: E712
                         "non_distinct_without_two_refs": 0,  # enforced by schema + retries; errors become uncertain
                         "contribution": O.contribution.value_counts().to_dict(), "relation": O.relation.value_counts().to_dict(),
                         "role": O.role.value_counts().to_dict()}
    matched = O[O.has_cand]
    summary["uncertain_share_matched"] = float(((matched.contribution == "uncertain") | (matched.relation == "uncertain")).mean()) if len(matched) else None
    summary["uncertain_contribution_share_matched"] = float((matched.contribution == "uncertain").mean()) if len(matched) else None

    # Repeat-contribution table (key comparison with the baseline)
    rc = pd.crosstab([O.model, O.exact_repeat], O.contribution, margins=True)
    rc.to_csv(f"{RES}/repeat_contribution_table.csv")
    rc_all = pd.crosstab(O.exact_repeat, O.contribution)
    rc_same = pd.crosstab(O.has_cand, O.contribution)
    summary["repeat_contribution"] = {"exact_repeat": rc_all.to_dict(), "same_object_or_output_candidate": rc_same.to_dict()}
    summary["disagreement_exact_vs_candidate_redundant"] = {
        "exact_repeat_and_cand_redundant": int((O.exact_repeat & O.cand_redundant).sum()),
        "exact_repeat_not_cand_redundant": int((O.exact_repeat & ~O.cand_redundant).sum()),
        "cand_redundant_not_exact_repeat": int((~O.exact_repeat & O.cand_redundant).sum())}

    # Signatures: prevalence + contribution mix vs exact-repeat share
    sig_tab = []
    nruns = M.groupby("model").size().to_dict()
    for (by, name), g in S.groupby(["by", "signature"]):
        row = {"by": by, "signature": name, "matches": len(g), "runs_with": g.run_id.nunique(),
               "prevalence": g.run_id.nunique() / len(M),
               "distinct": (g.contribution == "distinct").mean(), "non_distinct": (g.contribution == "non_distinct").mean(),
               "uncertain": (g.contribution == "uncertain").mean(), "exact_repeat_share": g.exact_repeat.mean()}
        row["nd_minus_exact_pts"] = 100 * (row["non_distinct"] - row["exact_repeat_share"])
        for m in sorted(nruns):
            gm = g[g.model == m]
            row[f"prev_{m}"] = gm.run_id.nunique() / nruns[m]
            row[f"nd_{m}"] = (gm.contribution == "non_distinct").mean() if len(gm) else np.nan
        sig_tab.append(row)
    ST = pd.DataFrame(sig_tab)
    ST.to_csv(f"{RES}/signatures.csv", index=False)

    # Return-after-k curve
    R = S[(S.signature == "return_any") & (S.by == "object")].copy()
    if len(R):
        R["kbin"] = pd.cut(R.k, [0, 1, 2, 3, 1e9], right=True, labels=["1", "2", "3", "4+"])
        rk = R.groupby(["model", "kbin"], observed=True).apply(lambda g: pd.Series({"n": len(g), "non_distinct": (g.contribution == "non_distinct").mean(),
                                                                                  "exact_repeat": g.exact_repeat.mean()})).reset_index()
        rk.to_csv(f"{RES}/return_after_k.csv", index=False)

    # Measures with cluster bootstrap
    mrows = []
    cols = ["n_ops", "exact_repeat_rate", "same_object_repeat_rate", "cand_redundancy_rate_lo", "cand_redundancy_rate_hi",
            "tail_ops_lo", "tail_ops_hi", "tail_share_lo", "tail_share_hi", "late_nd_rate_lo", "late_nd_rate_hi"]
    for m, g in list(M.groupby("model")) + [("ALL", M)]:
        row = {"model": m, "runs": len(g), "resolved": g.resolved.astype(float).mean()}
        for c in cols:
            pt, lo, hi = cluster_bootstrap(g, lambda d, c=c: d[c].mean(), n=CFG["bootstrap"]["n"], seed=CFG["bootstrap"]["seed"])
            row[c], row[c + "_ci"] = pt, f"[{lo:.3f}, {hi:.3f}]"
        if "gold_opened" in g:
            row["gold_opened"] = g.gold_opened.astype(float).mean()
        mrows.append(row)
    MT = pd.DataFrame(mrows)
    MT.to_csv(f"{RES}/measures_by_model.csv", index=False)

    # LLM-only baseline agreement
    if base:
        B = O[O.b_contribution.notna()]
        summary["llm_only_baseline"] = {
            "ops": len(B), "contribution_agreement": float((B.contribution == B.b_contribution).mean()),
            "relation_agreement": float((B.relation == B.b_relation).mean()),
            "kappa_contribution": _kappa(B.contribution, B.b_contribution), "kappa_relation": _kappa(B.relation, B.b_relation),
            "baseline_contribution": B.b_contribution.value_counts().to_dict(),
            "baseline_cand_redundant": int(((B.b_relation == "reproduces") & (B.b_contribution == "non_distinct")).sum()),
            "confusion_contribution": pd.crosstab(B.contribution, B.b_contribution).to_dict()}

    # Go / no-go items computable without humans
    # only signatures whose definition does not use the contribution label (others are circular for this test)
    label_free = ["new_to_new", "self_repeat", "edit_test_identical_test", "return_any", "reread_unchanged_same_output"]
    best = ST[(ST.by == "object") & ST.signature.isin(label_free) & (ST.matches >= 10)].assign(absdiff=lambda d: d.nd_minus_exact_pts.abs()).sort_values("absdiff", ascending=False)
    summary["go_no_go"] = {
        "1_human_human_kappa_contribution": "PENDING human annotation (annotation/pilot.csv)",
        "2_model_human_macroF1_and_precision": "PENDING human annotation",
        "3_uncertain_share_matched<=0.20": {"value": summary["uncertain_share_matched"], "pass": (summary["uncertain_share_matched"] or 0) <= CFG["go_no_go"]["max_uncertain_share"]},
        "4_signature_diff>=10pts": {"best": best.head(3)[["signature", "matches", "non_distinct", "exact_repeat_share", "nd_minus_exact_pts"]].to_dict("records"),
                                    "pass": bool((best.absdiff >= CFG["go_no_go"]["min_signature_diff_pts"]).any()),
                                    "note": "label-free signatures with >= 10 matches only"},
    }
    json.dump(summary, open(f"{RES}/summary.json", "w"), indent=1, default=str)
    print(json.dumps(summary, indent=1, default=str)[:6000])
    print(MT[["model", "runs", "resolved", "n_ops", "exact_repeat_rate", "cand_redundancy_rate_lo", "cand_redundancy_rate_hi", "tail_ops_lo", "tail_ops_hi", "late_nd_rate_lo", "late_nd_rate_hi"]].round(3).to_string())
    print(ST[ST.by == "object"][["signature", "matches", "prevalence", "distinct", "non_distinct", "uncertain", "exact_repeat_share", "nd_minus_exact_pts"]].round(3).to_string())


def _kappa(a, b):
    a, b = list(a), list(b)
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else None


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sample":
        sample()
    elif cmd == "label":
        label(llm_only="--llm-only" in sys.argv)
    elif cmd == "analyze":
        analyze()
