"""Task 3: is the return-after-k pattern confounded by position, run length or model?
Logistic GEE (exchangeable, clustered by task) and a cluster-robust logit:
    non_distinct ~ k_bin + relative_position + log(run_length) + model
on every return (signature return_any, object view, v2 labels). k is unchanged: the number of distinct other objects
visited since the previous visit to the same object. Plus return-after-k by run-length tercile."""
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from v2_viewb import _rci  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
T2, OUT = f"{ROOT}/results/v2/task2", f"{ROOT}/results/v2/task3"


def data():
    S = pd.read_csv(f"{T2}/signature_matches.csv")
    S = S[(S.by == "object") & (S.signature == "return_any")]
    O = pd.read_csv(f"{T2}/ops_labeled.csv")[["op_id", "op_index"]]
    M = pd.read_csv(f"{T2}/run_measures.csv")[["run_id", "n_ops"]]
    d = S.merge(O, on="op_id").merge(M, on="run_id")
    d = d[d.contribution.isin(["distinct", "non_distinct"])].copy()   # uncertain dropped (reported)
    d["nd"] = (d.contribution == "non_distinct").astype(int)
    d["k_bin"] = pd.cut(d.k, [0, 1, 3, 1e9], labels=["1", "2-3", "4+"]).astype(str)
    d["rel_pos"] = d.op_index / (d.n_ops - 1).clip(lower=1)
    d["log_len"] = np.log(d.n_ops)
    d["model"] = d.model.str.replace("gpt-5.6-", "").str.replace("gemini-3.7-flash", "gemini")
    return d, S


def fit(d):
    f = "nd ~ C(k_bin, Treatment('1')) + rel_pos + log_len + C(model, Treatment('gemini'))"
    gee = smf.gee(f, groups="task_id", data=d, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
    logit = smf.glm(f, data=d, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.task_id)[0]})
    rows = []
    for name, r in (("GEE (exchangeable, task clusters)", gee), ("logit, task-clustered SE", logit)):
        ci = r.conf_int()
        for term in r.params.index:
            rows.append({"model": name, "term": term, "odds_ratio": np.exp(r.params[term]), "or_lo": np.exp(ci.loc[term, 0]),
                         "or_hi": np.exp(ci.loc[term, 1]), "p": r.pvalues[term]})
    return pd.DataFrame(rows), gee, logit


def by_tercile(d):
    runs = d.drop_duplicates("run_id")
    # terciles of run length over all pilot runs (not only runs with returns)
    M = pd.read_csv(f"{T2}/run_measures.csv")
    q = M.n_ops.quantile([1 / 3, 2 / 3]).values
    lab = lambda n: "short" if n <= q[0] else ("medium" if n <= q[1] else "long")  # noqa: E731
    d = d.assign(tercile=d.n_ops.map(lab))
    rows = []
    for (t, k), g in d.groupby(["tercile", "k_bin"]):
        pt, lo, hi = _rci(g, "nd")
        rows.append({"run_length": t, "k_bin": k, "returns": len(g), "runs": g.run_id.nunique(),
                     "non_distinct": f"{100 * pt:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"})
    out = pd.DataFrame(rows)
    out["run_length"] = pd.Categorical(out.run_length, ["short", "medium", "long"])
    return out.sort_values(["run_length", "k_bin"]), q, len(runs)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    d, S = data()
    print("returns:", len(S), "| used (distinct/non_distinct):", len(d), "| uncertain dropped:", len(S) - len(d),
          "| non_distinct:", d.nd.sum(), "| tasks:", d.task_id.nunique(), "| runs:", d.run_id.nunique())
    print(pd.crosstab([d.model, d.k_bin], d.nd, margins=True))
    T, gee, logit = fit(d)
    T.to_csv(f"{OUT}/coefficients.csv", index=False)
    pd.set_option("display.width", 200)
    print(T.round(3).to_string())
    R, q, nr = by_tercile(d)
    R.to_csv(f"{OUT}/return_after_k_by_run_length.csv", index=False)
    print("run-length tercile cut points (ops):", q)
    print(R.to_string())
