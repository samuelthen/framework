"""Task 2: relabel the pilot ops whose facts changed under v2 facts (prompt v1, same annotator), merge with the
unchanged v1 labels, and report contribution tables (matched ops, then all ops) with task-clustered 95% CIs.

usage: v2_task2.py label | analyze"""
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.label.annotate import client_from_env, label_runs  # noqa: E402
from worktrace.stats import cluster_bootstrap  # noqa: E402
import m4_pilot as P  # noqa: E402

ROOT, CFG, LAB = P.ROOT, P.CFG, P.LAB
OUT = f"{ROOT}/results/v2/task2"
FACT_KEYS = ("write", "cand_object", "cand_output", "cand_facts", "object", "part_kinds")


def changed_ops() -> set[str]:
    out = set()
    for f in glob.glob(f"{P.EV}/*.jsonl"):
        v1 = {o["op_id"]: o for o in map(json.loads, open(f.replace("/data/events/", "/data/v1_snapshot/events/")))}
        for o in map(json.loads, open(f)):
            if any(o[k] != v1[o["op_id"]][k] for k in FACT_KEYS):
                out.add(o["op_id"])
    return out


def label():
    ch = changed_ops()
    runs = P.load_pilot()
    client = client_from_env(f"{ROOT}/soclaas.env")
    new = label_runs(runs, Path(f"{LAB}/pilot_v2_relabel.jsonl"), Path(f"{LAB}/cache_pilot.jsonl"), client,
                     prompt_version=CFG["annotator"]["prompt_version"], n_chars=CFG["annotator"]["result_chars"],
                     workers=CFG["annotator"]["workers"], op_filter=lambda o: o["op_id"] in ch)
    old = P.read_labels("pilot")
    merged = {**old, **{r["op_id"]: r for r in new}}
    with open(f"{LAB}/pilot_v2.jsonl", "w") as f:
        for r in merged.values():
            f.write(json.dumps(r) + "\n")
    print("changed ops", len(ch), "relabeled", len(new), "errors", sum(r["label_error"] for r in new), "usage", client.usage)


def ci(df, f):
    pt, lo, hi = cluster_bootstrap(df, f, n=CFG["bootstrap"]["n"], seed=CFG["bootstrap"]["seed"])
    return pt, lo, hi


def fmt(t):
    pt, lo, hi = t
    return f"{100 * pt:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def contribution_table(O):
    rows = []
    for view, d in (("b_matched", O[O.has_cand]), ("a_all", O)):
        for m, g in list(d.groupby("model")) + [("ALL", d)]:
            r = {"view": view, "model": m, "ops": len(g), "tasks": g.task_id.nunique()}
            for c in ("distinct", "non_distinct", "uncertain"):
                r[c] = fmt(ci(g, lambda x, c=c: (x.contribution == c).mean()))
            r["cand_redundant"] = fmt(ci(g, lambda x: x.cand_redundant.mean()))
            r["exact_repeat"] = fmt(ci(g, lambda x: x.exact_repeat.mean()))
            r["nd_given_exact"] = fmt(ci(g, lambda x: (x[x.exact_repeat].contribution == "non_distinct").mean())) + f" (n={int(g.exact_repeat.sum())})"
            r["nd_given_not_exact"] = fmt(ci(g, lambda x: (x[~x.exact_repeat].contribution == "non_distinct").mean()))
            r["cand_red_not_exact"] = fmt(ci(g, lambda x: (x.cand_redundant & ~x.exact_repeat).mean()))
            rows.append(r)
    return pd.DataFrame(rows)


def analyze():
    os.makedirs(OUT, exist_ok=True)
    P.analyze("pilot_v2", RES=OUT, graphs=f"{ROOT}/data/graphs_v2")
    O = pd.read_csv(f"{OUT}/ops_labeled.csv")
    O["cand_redundant"] = (O.relation == "reproduces") & (O.contribution == "non_distinct")
    CT = contribution_table(O)
    CT.to_csv(f"{OUT}/contribution_tables.csv", index=False)

    # what the relabel changed
    v1 = pd.read_csv(f"{ROOT}/results/pilot/ops_labeled.csv").set_index("op_id")
    ch = changed_ops()
    C = O[O.op_id.isin(ch)].set_index("op_id")
    flips = pd.DataFrame({"v1": v1.loc[C.index, "contribution"], "v2": C.contribution})
    rel = pd.DataFrame({"v1": v1.loc[C.index, "relation"], "v2": C.relation})
    cm = pd.crosstab(flips.v1, flips.v2)
    cm.to_csv(f"{OUT}/relabel_contribution_v1_vs_v2.csv")
    pd.crosstab(rel.v1, rel.v2).to_csv(f"{OUT}/relabel_relation_v1_vs_v2.csv")

    # signatures (object view) with CIs on the non-distinct share, exact-repeat share and their difference
    S = pd.read_csv(f"{OUT}/signature_matches.csv")
    S = S[S.by == "object"]
    srows = []
    for name, g in S.groupby("signature"):
        r = {"signature": name, "matches": len(g), "runs": g.run_id.nunique()}
        r["non_distinct"] = fmt(ci(g, lambda x: (x.contribution == "non_distinct").mean()))
        r["exact_repeat"] = fmt(ci(g, lambda x: x.exact_repeat.astype(bool).mean()))
        pt, lo, hi = ci(g, lambda x: (x.contribution == "non_distinct").mean() - x.exact_repeat.astype(bool).mean())
        r["diff_pts"] = f"{100 * pt:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]"
        srows.append(r)
    ST = pd.DataFrame(srows)
    ST.to_csv(f"{OUT}/signatures_ci.csv", index=False)

    # measures with CIs come from P.analyze (measures_by_model.csv); return-after-k with CIs
    R = S[S.signature == "return_any"].copy()
    R["kbin"] = pd.cut(R.k, [0, 1, 2, 3, 1e9], labels=["1", "2", "3", "4+"])
    rk = []
    for (m, k), g in R.groupby(["model", "kbin"], observed=True):
        rk.append({"model": m, "k": k, "n": len(g), "non_distinct": fmt(ci(g, lambda x: (x.contribution == "non_distinct").mean()))})
    RK = pd.DataFrame(rk)
    RK.to_csv(f"{OUT}/return_after_k_ci.csv", index=False)

    M = pd.read_csv(f"{OUT}/measures_by_model.csv")
    summ = json.load(open(f"{OUT}/summary.json"))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(CT.to_string()); print(cm); print(ST.to_string()); print(RK.to_string())
    print(M[["model", "runs", "cand_redundancy_rate_lo", "cand_redundancy_rate_lo_ci", "cand_redundancy_rate_hi", "cand_redundancy_rate_hi_ci",
             "late_nd_rate_lo", "late_nd_rate_lo_ci", "tail_ops_lo", "tail_ops_lo_ci"]].to_string())
    print(json.dumps({k: summ[k] for k in ("uncertain_share_matched", "disagreement_exact_vs_candidate_redundant", "go_no_go")}, indent=1, default=str))


if __name__ == "__main__":
    {"label": label, "analyze": analyze}[sys.argv[1]]()
