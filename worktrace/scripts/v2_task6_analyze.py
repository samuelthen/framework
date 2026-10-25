"""Task 6 analysis: B.7 measures, signatures and return-after-k on the scale labels (all Gemini runs; the 10% Luna and
Terra task samples). Labels: data/labels/scale_<shard>.jsonl (prompt v1, primary annotator, current facts; unmatched ops
of Gemini and Terra carry the rule_skip label). Runs are processed one at a time (memory: one shard with facts ~4.7 GB).

usage: v2_task6_analyze.py build   # per-run measures, signature matches, matched-op table -> results/v2/task6/
       v2_task6_analyze.py report  # measures with CIs, signatures, return-after-k (GEE + logit) with events per parameter"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.graph import build_graph  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402
from worktrace.measures import run_measures  # noqa: E402
from worktrace.signatures import run_signatures  # noqa: E402
from v2_viewb import _rci  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAB, OUT = f"{ROOT}/data/labels", f"{ROOT}/results/v2/task6"
SHORT = {"gemini-3.7-flash": "gemini", "gpt-5.6-luna": "luna", "gpt-5.6-terra": "terra"}


def build():
    meas, sig, mat = [], [], []
    for lf in sorted(glob.glob(f"{LAB}/scale_*.jsonl")):
        shard = os.path.basename(lf)[6:-6]
        labels = {r["op_id"]: r for r in map(json.loads, open(lf))}
        n = 0
        for b in pq.ParquetFile(f"{ROOT}/raw/jetbrains/{shard}.parquet").iter_batches(batch_size=25):
            for row in b.to_pylist():
                if J.is_infra_failure(row):
                    continue
                run, ops = J.load_row(row)
                if ops and ops[0]["op_id"] not in labels:
                    continue  # task not in the Luna/Terra sample
                extract_facts(ops)
                assert all(o["op_id"] in labels for o in ops), run["run_id"]
                meas.append({**run_measures(run, ops, labels), "shard": shard})
                g = build_graph(run, ops, labels, by="object")
                for name, matches in run_signatures(g, ops).items():
                    for mt in matches:
                        sig.append({"run_id": run["run_id"], "task_id": run["task_id"], "model": run["model"], "signature": name,
                                    "op_id": mt.get("op_id"), "contribution": mt.get("contribution"),
                                    "exact_repeat": mt.get("exact_repeat"), "k": mt.get("k")})
                for o in ops:
                    if o["cand_object"] or o["cand_output"]:
                        l = labels[o["op_id"]]
                        mat.append({"run_id": run["run_id"], "task_id": run["task_id"], "model": run["model"], "op_id": o["op_id"],
                                    "op_index": o["op_index"], "n_ops": len(ops), "exact_repeat": o["exact_repeat"],
                                    "contribution": l["contribution"], "relation": l["relation"], "label_error": l["label_error"]})
                n += 1
        print(shard, "runs", n, flush=True)
    pd.DataFrame(meas).to_csv(f"{OUT}/run_measures.csv", index=False)
    pd.DataFrame(sig).to_csv(f"{OUT}/signature_matches.csv", index=False)
    pd.DataFrame(mat).to_csv(f"{OUT}/matched_ops.csv", index=False)


def _f(t, pct=True):
    return f"{100 * t[0]:.2f}% [{100 * t[1]:.2f}, {100 * t[2]:.2f}]" if pct else f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"


def measures():
    M = pd.read_csv(f"{OUT}/run_measures.csv").assign(m=lambda d: d.model.map(SHORT))
    X = pd.read_csv(f"{OUT}/matched_ops.csv").assign(m=lambda d: d.model.map(SHORT))
    rows = []
    for m in ("gemini", "luna", "terra"):
        g, x = M[M.m == m], X[X.m == m]
        rows.append({"model": m, "scope": "all runs" if m == "gemini" else "10% task sample", "runs": len(g),
                     "tasks": g.task_id.nunique(), "ops": int(g.n_ops.sum()), "matched_ops": len(x),
                     "non_distinct_share_matched": _f(_rci(x, lambda d: (d.contribution == "non_distinct").astype(float))),
                     "uncertain_share_matched": _f(_rci(x, lambda d: (d.contribution == "uncertain").astype(float))),
                     "cand_redundancy_rate_lo (run mean)": _f(_rci(g, "cand_redundancy_rate_lo")),
                     "cand_redundancy_rate_hi (run mean)": _f(_rci(g, "cand_redundancy_rate_hi")),
                     "exact_repeat_rate (run mean)": _f(_rci(g, "exact_repeat_rate")),
                     "tail_ops_lo": _f(_rci(g, "tail_ops_lo"), False), "tail_ops_hi": _f(_rci(g, "tail_ops_hi"), False),
                     "runs_with_tail_hi>0": f"{100 * (g.tail_ops_hi > 0).mean():.1f}%",
                     "late_nd_rate_lo": _f(_rci(g, "late_nd_rate_lo")), "late_nd_rate_hi": _f(_rci(g, "late_nd_rate_hi")),
                     "label_errors": int(x.label_error.sum())})
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/measures.csv", index=False)
    print(T.T.to_string())


def signatures():
    S = pd.read_csv(f"{OUT}/signature_matches.csv").assign(m=lambda d: d.model.map(SHORT))
    rows = []
    for (m, s), g in [*S.groupby(["m", "signature"]), *((("all", s), g) for s, g in S.groupby("signature"))]:
        g = g.assign(nd=(g.contribution == "non_distinct").astype(float), ex=g.exact_repeat.astype(float))
        rows.append({"model": m, "signature": s, "matches": len(g), "runs_with": g.run_id.nunique(),
                     "non_distinct": _f(_rci(g, "nd")), "exact_repeat_share": _f(_rci(g, "ex")),
                     "nd_minus_exact_pts": "{:.1f} [{:.1f}, {:.1f}]".format(*(100 * v for v in _rci(g.assign(d=g.nd - g.ex), "d")))})
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/signatures_ci.csv", index=False)
    print(T.to_string(index=False))


def return_after_k():
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    S = pd.read_csv(f"{OUT}/signature_matches.csv")
    S = S[S.signature == "return_any"]
    X = pd.read_csv(f"{OUT}/matched_ops.csv")[["op_id", "op_index", "n_ops"]]
    d = S.merge(X, on="op_id")
    assert len(d) == len(S), (len(d), len(S))  # every return has a candidate (same object)
    n_unc = int((d.contribution == "uncertain").sum())
    d = d[d.contribution.isin(["distinct", "non_distinct"])].copy()
    d["nd"] = (d.contribution == "non_distinct").astype(int)
    d["k_bin"] = pd.cut(d.k, [0, 1, 3, 1e9], labels=["1", "2-3", "4+"]).astype(str)
    d["rel_pos"] = d.op_index / (d.n_ops - 1).clip(lower=1)
    d["log_len"] = np.log(d.n_ops)
    d["model"] = d.model.map(SHORT)
    coef, epp = [], []
    for name, dd, f in [("gemini, all runs", d[d.model == "gemini"], "nd ~ C(k_bin, Treatment('1')) + rel_pos + log_len"),
                        ("pooled: gemini all + luna/terra 10% sample", d,
                         "nd ~ C(k_bin, Treatment('1')) + rel_pos + log_len + C(model, Treatment('gemini'))")]:
        groups = pd.factorize(dd.task_id)[0]
        gee = smf.gee(f, groups=groups, data=dd, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        logit = smf.glm(f, data=dd, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": groups})
        k_par = len(gee.params) - 1
        ev = int(min(dd.nd.sum(), len(dd) - dd.nd.sum()))
        epp.append({"fit": name, "returns_used": len(dd), "non_distinct": int(dd.nd.sum()), "distinct": int(len(dd) - dd.nd.sum()),
                    "events (minority class)": ev, "parameters (excl. intercept)": k_par,
                    "events_per_parameter": round(ev / k_par, 1), "task_clusters": dd.task_id.nunique(), "runs": dd.run_id.nunique()})
        for est, r in (("GEE (exchangeable, task clusters)", gee), ("logit, task-clustered SE", logit)):
            ci = r.conf_int()
            for t in r.params.index:
                coef.append({"fit": name, "estimator": est, "term": t, "odds_ratio": np.exp(r.params[t]),
                             "or_lo": np.exp(ci.loc[t, 0]), "or_hi": np.exp(ci.loc[t, 1]), "p": r.pvalues[t]})
    E, C = pd.DataFrame(epp), pd.DataFrame(coef)
    E.to_csv(f"{OUT}/return_after_k_epp.csv", index=False)
    C.to_csv(f"{OUT}/return_after_k_coefficients.csv", index=False)
    # raw non-distinct share by k bin and model
    R = []
    for (m, k), g in d.groupby(["model", "k_bin"]):
        R.append({"model": m, "k_bin": k, "returns": len(g), "non_distinct": _f(_rci(g, "nd"))})
    R = pd.DataFrame(R)
    R.to_csv(f"{OUT}/return_after_k_raw.csv", index=False)
    pd.set_option("display.width", 220)
    print("returns:", len(S), "uncertain dropped:", n_unc)
    print(E.to_string(index=False)); print(R.to_string(index=False)); print(C.round(3).to_string(index=False))


def report():
    measures(); signatures(); return_after_k()


if __name__ == "__main__":
    {"build": build, "report": report}[sys.argv[1]](*sys.argv[2:])
