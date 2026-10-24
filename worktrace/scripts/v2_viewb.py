"""View B (code-version graph) and the Error Loop signature.

usage: v2_viewb.py scale    # facts only, all 6,300 JetBrains runs (no LLM)
       v2_viewb.py pilot    # the 50 pilot runs, with v2 labels on the evidence ops"""
import glob
import json
import os
import sys
from multiprocessing import Pool

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402
from worktrace.signatures import error_loops, error_signature  # noqa: E402
from worktrace.versions import build_version_graph, summarize, support_candidates  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = f"{ROOT}/results/v2/viewb"
OUT_EL = f"{ROOT}/results/v2/error_loop"


def compact(g):
    return {k: g[k] for k in ("run_id", "task_id", "model", "resolved", "n_versions", "final")} | {
        "nodes": [{k: n[k] for k in ("v", "x", "y", "entries", "verify", "verify_fail", "uncertain", "final", "first_op")} for n in g["nodes"]],
        "edges": [{k: e[k] for k in ("src", "dst", "label", "op_index")} for e in g["edges"]]}


def loop_rows(run, ops):
    rows = []
    for loop in error_loops(ops):
        rows.append({"run_id": run["run_id"], "task_id": run["task_id"], "model": run["model"], "start": loop[0]["op_index"],
                     "length": len(loop), "signature": error_signature(loop[0]),
                     "distinct_commands": len({o["command"] for o in loop}),
                     "exact_repeats": sum(o["exact_repeat"] for o in loop[1:]),
                     "kinds": "|".join(sorted({o["kind"] for o in loop})), "op_ids": [o["op_id"] for o in loop]})
    return rows


def process_file(path):
    graphs, known, supp, loops, n_err, n_ops = [], [], [], [], 0, 0
    subs = pd.read_parquet(f"{ROOT}/data/submissions.parquet").set_index("run_id")
    for row in (r for b in pq.ParquetFile(path).iter_batches(batch_size=25) for r in b.to_pylist()):
        if J.is_infra_failure(row):
            continue
        run, ops = J.load_row(row)
        extract_facts(ops)
        graphs.append(compact(build_version_graph(run, ops)))
        known.append(compact(build_version_graph(run, ops, unknown_creates_version=False)))
        sub = subs.loc[run["run_id"]] if run["run_id"] in subs.index else None
        sc = support_candidates(ops, list(sub.submission_files) if sub is not None else [],
                                list(sub.submission_new_files) if sub is not None else [])
        gb = compact(build_version_graph(run, ops, support_paths={p for p, v in sc.items() if v["candidate"]}))
        gb["support_files"] = sorted(p for p, v in sc.items() if v["candidate"])
        supp.append(gb)
        loops += loop_rows(run, ops)
        n_err += sum(error_signature(o) is not None for o in ops)
        n_ops += len(ops)
    print(os.path.basename(path), len(graphs), "runs", flush=True)
    return graphs, loops, n_err, n_ops, known, supp


def scale():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(OUT_EL, exist_ok=True)
    with Pool(2, maxtasksperchild=1) as p:
        res = p.map(process_file, sorted(glob.glob(f"{ROOT}/raw/jetbrains/*.parquet")))
    for i, name in ((0, "version_graphs_v2"), (4, "version_graphs_v2_known_writes"), (5, "version_graphs_v2_support")):
        with open(f"{ROOT}/data/{name}.jsonl", "w") as f:
            for r in res:
                for g in r[i]:
                    f.write(json.dumps(g) + "\n")
    pd.DataFrame([l for _, ls, _, _, _, _ in res for l in ls]).to_parquet(f"{OUT_EL}/loops_all.parquet")
    json.dump({"error_ops": sum(r[2] for r in res), "ops": sum(r[3] for r in res)}, open(f"{OUT_EL}/error_op_counts.json", "w"))


def _ci(df, f):
    from worktrace.stats import cluster_bootstrap
    pt, lo, hi = cluster_bootstrap(df, f, n=1000, seed=0)
    return pt, lo, hi


def _rci(df, num, den=None, cluster="task_id", n=1000, seed=0):
    """Fast task-clustered bootstrap of sum(num)/sum(den) (den=None: mean of num over rows). Same resampling scheme as
    stats.cluster_bootstrap (tasks with replacement, all rows of a task), vectorised over per-task sums."""
    import numpy as np
    d = df.assign(_n=num(df) if callable(num) else df[num], _d=(den(df) if callable(den) else df[den]) if den is not None else 1.0)
    d = d[d._n.notna()]
    t = d.groupby(cluster)[["_n", "_d"]].sum()
    N, D = t._n.values.astype(float), t._d.values.astype(float)
    pt = N.sum() / D.sum() if D.sum() else float("nan")
    if len(t) < 2:
        return pt, float("nan"), float("nan")
    idx = np.random.default_rng(seed).integers(0, len(t), size=(n, len(t)))
    with np.errstate(invalid="ignore", divide="ignore"):
        vals = N[idx].sum(1) / D[idx].sum(1)
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return pt, lo, hi


def _fmt(t, pct=True):
    pt, lo, hi = t
    return f"{100 * pt:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]" if pct else f"{pt:.2f} [{lo:.2f}, {hi:.2f}]"


def report(variant="spec"):
    """variant 'spec' (a): every write is a version, unknown writes are uncertain versions; 'support' (b): support-only
    changes (rule hint) create no version; 'known': sensitivity, only known repo writes."""
    from worktrace.versions import aggregate
    src, out, suf = {"spec": ("version_graphs_v2", OUT, ""),
                     "known": ("version_graphs_v2_known_writes", f"{OUT}/known_writes", "_known_writes"),
                     "support": ("version_graphs_v2_support", f"{OUT}/support_no_version", "_support")}[variant]
    os.makedirs(out, exist_ok=True)
    from worktrace.viz.versions import plot_aggregates, plot_version_graph
    FIG = f"{ROOT}/figures/v2"
    os.makedirs(FIG, exist_ok=True)
    G = [json.loads(l) for l in open(f"{ROOT}/data/{src}.jsonl")]
    R = pd.DataFrame([summarize_compact(g) for g in G])
    R.to_csv(f"{out}/runs_all.csv", index=False)

    # 1. how many runs have 0, 1, 2, ... versions
    R["nv_bin"] = R.n_versions.clip(upper=10).astype(int).astype(str).replace("10", "10+")
    order = [str(i) for i in range(10)] + ["10+"]
    dist = pd.crosstab(R.model, R.nv_bin).reindex(columns=order, fill_value=0)
    dist.to_csv(f"{out}/n_versions_distribution.csv")
    (dist.div(dist.sum(1), axis=0) * 100).round(1).to_csv(f"{out}/n_versions_distribution_pct.csv")

    # 2. per-model means with task-clustered CIs
    rows = []
    for m, g in R.groupby("model"):
        row = {"model": m, "runs": len(g)}
        for c in ("n_versions", "n_uncertain", "edge_correct", "edge_revise", "edge_backtrack", "verify_total"):
            row[c] = _fmt(_rci(g, c), pct=False)
        row["runs_with_backtrack"] = _fmt(_rci(g, lambda d: (d.edge_backtrack > 0).astype(float)))
        row["runs_with_uncertain_version"] = _fmt(_rci(g, lambda d: (d.n_uncertain > 0).astype(float)))
        # verify self-loop on the final version vs earlier (non-root) versions, runs with >= 2 versions
        g2 = g[g.n_versions >= 2]
        row["runs_ge2_versions"] = len(g2)
        row["verify_per_final_version"] = _fmt(_rci(g2, "verify_final"), pct=False)
        row["verify_per_earlier_version"] = _fmt(_rci(g2, "verify_other_mean"), pct=False)
        row["share_of_verifies_on_final"] = _fmt(_rci(g2, "verify_final", lambda d: d.verify_final + d.verify_other_total))
        row["final_verify_ge3"] = _fmt(_rci(g2, lambda d: (d.verify_final >= 3).astype(float)))
        rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(f"{out}/measures_by_model.csv", index=False)

    # 3. resolved by final verify count (descriptive)
    R["final_verify_bin"] = pd.cut(R.verify_final, [-1, 0, 1, 2, 4, 1e9], labels=["0", "1", "2", "3-4", "5+"])
    rv = R.groupby(["model", "final_verify_bin"], observed=True).agg(runs=("run_id", "size"), resolved=("resolved", "mean")).reset_index()
    rv.to_csv(f"{out}/resolved_by_final_verify.csv", index=False)

    # 4. Stage 4 pattern figures: per model, one panel per number of versions (>= 3 as in TRACE, plus 1-2 for reference)
    names = {"gemini-3.7-flash": "Gemini 3.7 Flash", "gpt-5.6-luna": "GPT-5.6 Luna", "gpt-5.6-terra": "GPT-5.6 Terra"}
    agg_out = {}
    for m in sorted(R.model.unique()):
        gm = [g for g in G if g["model"] == m]
        panels = []
        for nv in range(1, 9):
            grp = [g for g in gm if g["n_versions"] == nv]
            if len(grp) >= 20:
                a = aggregate(grp, threshold=0.3)
                agg_out[f"{m}|{nv}"] = a
                panels.append((f"{nv} version{'s' if nv > 1 else ''}", a))
        plot_aggregates(panels, f"{FIG}/viewb_patterns_{m}{suf}.png", ncols=4, suptitle=f"{names.get(m, m)}: code-version patterns (edges and nodes in < 30% of runs pruned)")
    json.dump(agg_out, open(f"{out}/aggregates.json", "w"), indent=1, default=str)

    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(dist); print((dist.div(dist.sum(1), axis=0) * 100).round(1)); print(T.T.to_string()); print(rv.to_string())


def pilot():
    """Pilot: example run figures, LLM contribution of evidence ops by version (final vs earlier), and the Error Loop
    contribution mix (v2 labels, prompt v1)."""
    sys.path.insert(0, os.path.dirname(__file__))
    import m4_pilot as P
    from worktrace.signatures import error_loops
    from worktrace.stats import cluster_bootstrap
    from worktrace.viz.versions import plot_version_graph
    FIG = f"{ROOT}/figures/v2/viewb_runs"
    os.makedirs(FIG, exist_ok=True)
    runs = P.load_pilot()
    labels = P.read_labels("pilot_v2")
    rows, ev = [], []
    graphs = {}
    for rid, (run, ops) in runs.items():
        g = build_version_graph(run, ops, labels)
        graphs[rid] = g
        rows.append(summarize(g))
        final = g["final"]
        for o, v in zip(ops, g["op_version"]):
            ev.append({"run_id": rid, "task_id": run["task_id"], "model": run["model"], "kind": o["kind"],
                       "on_final": v == final and v != 0, "on_root": v == 0,
                       "contribution": (labels.get(o["op_id"]) or {}).get("contribution")})
    pd.DataFrame(rows).to_csv(f"{OUT}/pilot_runs.csv", index=False)
    with open(f"{ROOT}/data/version_graphs_pilot_v2.jsonl", "w") as f:
        for g in graphs.values():
            f.write(json.dumps(g) + "\n")
    E = pd.DataFrame(ev)
    erows = []
    for m, g in list(E.groupby("model")) + [("ALL", E)]:
        for where, d in (("root", g[g.on_root]), ("earlier version", g[~g.on_root & ~g.on_final]), ("final version", g[g.on_final])):
            pt, lo, hi = cluster_bootstrap(d, lambda x: (x.contribution == "non_distinct").mean(), n=1000, seed=0)
            erows.append({"model": m, "ops_on": where, "ops": len(d), "non_distinct": f"{100 * pt:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"})
    pd.DataFrame(erows).to_csv(f"{OUT}/pilot_nd_by_version.csv", index=False)
    print(pd.DataFrame(erows).to_string())

    # example runs: per model, the run with the most versions, plus every run with a backtrack
    S = pd.DataFrame(rows)
    pick = set(S.sort_values("n_versions").groupby("model").run_id.last()) | set(S[S.edge_backtrack > 0].run_id)
    for rid in sorted(pick):
        r = runs[rid][0]
        t = f"{r['model']} · {r['task_id'].split('__')[1][:40]} · r{rid.rsplit(':r', 1)[-1]}"
        plot_version_graph(graphs[rid], f"{FIG}/{P._safe(rid)}.png", t)
    print("example figures:", len(pick))

    # Error Loop on the pilot
    lr = []
    for rid, (run, ops) in runs.items():
        for loop in error_loops(ops):
            for o in loop[1:]:
                lr.append({"run_id": rid, "model": run["model"], "op_id": o["op_id"], "exact_repeat": o["exact_repeat"],
                           "contribution": (labels.get(o["op_id"]) or {}).get("contribution")})
    pd.DataFrame(lr).to_csv(f"{OUT_EL}/pilot_members.csv", index=False)
    print(pd.DataFrame(lr))


def error_loop_report():
    """Error Loop at scale (facts only): prevalence with task-clustered CIs, loop shape, top signatures."""
    import re
    from worktrace.signatures import _ERR_STRONG, _ERR_WORD
    L = pd.read_parquet(f"{OUT_EL}/loops_all.parquet")
    # loops_all.parquet was built before error_signature required an error word; that rule can only remove a
    # signature, so dropping the loops whose signature has no error word is exactly what a rerun gives
    keep = L.signature.map(lambda x: bool(_ERR_WORD.search(x) or _ERR_STRONG.match(x)))
    print("dropped loops without an error line:", int((~keep).sum()), L[~keep].signature.value_counts().head(10).to_dict())
    L = L[keep]
    runs = pd.read_parquet(f"{ROOT}/data/runs.parquet")[["run_id", "task_id", "model", "resolved", "n_ops"]]
    per = L.groupby("run_id").agg(loops=("start", "size"), loop_ops=("length", "sum"), members=("length", lambda x: (x - 1).sum()))
    runs = runs.join(per, on="run_id").fillna({"loops": 0, "loop_ops": 0, "members": 0})
    rows = []
    for m, g in list(runs.groupby("model")) + [("ALL", runs)]:
        lm = L[L.run_id.isin(g.run_id)]
        row = {"model": m, "runs": len(g), "loops": len(lm),
               "runs_with_loop": _fmt(_rci(g, lambda d: (d.loops > 0).astype(float))),
               "loops_per_run": _fmt(_rci(g, "loops"), pct=False),
               "op_share_in_loop_after_first": _fmt(_rci(g, "members", "n_ops")),
               "resolved_with_loop": g[g.loops > 0].resolved.mean(), "resolved_without": g[g.loops == 0].resolved.mean()}
        if len(lm):
            row |= {"mean_length": lm.length.mean(), "share_loops_all_same_command": (lm.distinct_commands == 1).mean(),
                    "share_members_exact_repeat": lm.exact_repeats.sum() / (lm.length - 1).sum()}
        rows.append(row)
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT_EL}/prevalence_by_model.csv", index=False)
    top = L.groupby(["model", "signature"]).size().rename("loops").reset_index().sort_values("loops", ascending=False)
    top.groupby("model").head(8).to_csv(f"{OUT_EL}/top_signatures.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 90)
    print(T.T.to_string()); print(top.groupby("model").head(8).to_string())


def summarize_compact(g):
    """summarize() for the compact graphs stored at scale."""
    from collections import Counter
    lab = Counter(e["label"] for e in g["edges"])
    final = [n for n in g["nodes"] if n["final"]][0]
    others = [n for n in g["nodes"] if not n["final"] and n["v"] != 0]
    return {"run_id": g["run_id"], "task_id": g["task_id"], "model": g["model"], "resolved": bool(g["resolved"]),
            "n_versions": g["n_versions"], "n_rows": max(n["y"] for n in g["nodes"]),
            "n_uncertain": sum(n["uncertain"] for n in g["nodes"]), "final_x": final["x"],
            "verify_final": final["verify"], "verify_root": g["nodes"][0]["verify"],
            "verify_other_mean": (sum(n["verify"] for n in others) / len(others)) if others else float("nan"),
            "verify_other_total": sum(n["verify"] for n in others),
            "verify_total": sum(n["verify"] for n in g["nodes"]),
            **{f"edge_{k}": lab.get(k, 0) for k in ("initial", "correct", "revise", "backtrack", "noop", "final")}}


if __name__ == "__main__":
    {"scale": scale, "report": report, "pilot": pilot, "error_loop": error_loop_report}[sys.argv[1]](*sys.argv[2:])
