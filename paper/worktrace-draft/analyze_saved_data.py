"""Additional descriptive analyses for the 26 October manuscript revision.

No agent execution, command execution from traces, model calls, or new labels.
Requires numpy, pandas, and pyarrow. Run from any working directory.
"""
from pathlib import Path
import hashlib
import json
import platform
import sys

import numpy as np
import pandas as pd
import pyarrow

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "results/paper_revision_20261026"
OUT.mkdir(parents=True, exist_ok=True)
SEED, B = 20261026, 5000
MODELS = ["gemini-3.7-flash", "gpt-5.6-luna", "gpt-5.6-terra"]
VARIANTS = {"all_writes": "results/v2/viewb/runs_all.csv",
            "known_writes": "results/v2/viewb/known_writes/runs_all.csv",
            "exclude_support": "results/v2/viewb/support_no_version/runs_all.csv"}
INPUTS = [*VARIANTS.values(), "results/v2/task5/runs_benchmark.parquet",
          "results/v2/reconcile/scale_per_run.csv"]


def ci(df, num, den=None):
    """Resample whole tasks, then recompute a ratio of sums or row mean.

    The same seed for every contrast gives identical task draws when task sets
    agree. The interval is a descriptive percentile interval, not a fresh test.
    """
    d = df[["task_id", num] + ([den] if den else [])].dropna().copy()
    d["_den"] = d[den] if den else 1.0
    g = d.groupby("task_id", sort=True)[[num, "_den"]].sum()
    n, w = g[num].to_numpy(float), g["_den"].to_numpy(float)
    assert len(g) >= 2 and w.sum() > 0
    rng = np.random.default_rng(SEED)
    samples = []
    for start in range(0, B, 250):
        ix = rng.integers(0, len(g), size=(min(250, B-start), len(g)))
        samples.extend(n[ix].sum(1) / w[ix].sum(1))
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return {"estimate": n.sum()/w.sum(), "lo": lo, "hi": hi,
            "tasks": len(g), "rows": len(d)}


def version_analysis():
    data = {}
    summaries, strata, size_rows = [], [], []
    for variant, path in VARIANTS.items():
        r = pd.read_csv(ROOT / path)
        assert len(r) == 6300 and r.run_id.nunique() == 6300
        r["repeat"] = r.run_id.str.extract(r":r(\d+)$")[0].astype(int)
        r["gap"] = r.verify_final - r.verify_other_mean
        r["eligible"] = (r.n_versions >= 2) & (r.final_x > 0) & r.verify_other_mean.notna()
        data[variant] = r
        for model, g in r[r.eligible].groupby("model"):
            summaries.append({"variant": variant, "model": model, **ci(g, "gap"),
                              "final_mean": g.verify_final.mean(),
                              "earlier_mean": g.verify_other_mean.mean(),
                              "root_final_excluded": int(((r.model == model) & (r.n_versions >= 2) & (r.final_x == 0)).sum())})
            for status, s in g.groupby("resolved"):
                strata.append({"variant": variant, "model": model,
                               "resolved": bool(status), **ci(s, "gap")})
            for nv in [2, 3, 4, 5]:
                s = g[g.n_versions == nv]
                if s.task_id.nunique() >= 2:
                    size_rows.append({"variant": variant, "model": model,
                                      "versions": nv, **ci(s, "gap")})

    # Same task AND repeat index, eligible in all three models and all variants.
    common = None
    for r in data.values():
        by = r[r.eligible].groupby(["task_id", "repeat"]).model.nunique()
        keys = set(by[by == 3].index)
        common = keys if common is None else common & keys
    assert common
    common_rows, pair_rows = [], []
    for variant, r in data.items():
        s = r[[ (t, k) in common for t, k in zip(r.task_id, r.repeat) ]].copy()
        assert len(s) == 3*len(common) and s.eligible.all()
        for model, g in s.groupby("model"):
            common_rows.append({"variant": variant, "model": model, **ci(g, "gap"),
                                "final_mean": g.verify_final.mean(),
                                "earlier_mean": g.verify_other_mean.mean()})
        w = s.pivot(index=["task_id", "repeat"], columns="model", values="gap")
        for a, b in [(MODELS[0], MODELS[1]), (MODELS[0], MODELS[2]), (MODELS[1], MODELS[2])]:
            d = (w[a]-w[b]).rename("difference").reset_index()
            pair_rows.append({"variant": variant, "first": a, "second": b,
                              **ci(d, "difference")})
    for name, rows in [("version_gaps", summaries), ("version_by_outcome", strata),
                       ("version_by_count", size_rows), ("version_common_sample", common_rows),
                       ("version_paired_differences", pair_rows)]:
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)
    return {"common_task_repeat_pairs": len(common),
            "common_tasks": len({t for t, _ in common})}


def paired_harness():
    r = pd.read_parquet(ROOT / "results/v2/task5/runs_benchmark.parquet")
    assert len(r) == 6000 and r.run_id.nunique() == 6000
    assert (r.groupby("task_id").harness.nunique() == 3).all()
    r["revisit_rate"] = 100*r.same_object/r.n_ops.clip(lower=1)
    r["repeat_rate"] = 100*r.exact_repeats/r.n_ops.clip(lower=1)
    r["resolved_pct"] = 100*r.resolved.astype(float)
    summaries, pairs, strata = [], [], []
    hs = sorted(r.harness.unique())
    assert "mini-swe-agent" in hs
    outlier_task = r.loc[r.exact_repeats.idxmax(), "task_id"]
    assert r.exact_repeats.max() == 163  # 164 probe executions, excluding the first
    for sample, s in [("all", r), ("without_outlier_task", r[r.task_id != outlier_task])]:
        for h, g in s.groupby("harness"):
            for metric in ["revisit_rate", "repeat_rate", "n_ops", "resolved_pct"]:
                summaries.append({"sample": sample, "harness": h,
                                  "metric": metric, **ci(g, metric)})
        for a, b in [(h, "mini-swe-agent") for h in hs if h != "mini-swe-agent"]:
            for metric in ["revisit_rate", "repeat_rate", "n_ops", "resolved_pct"]:
                w = s.pivot(index="task_id", columns="harness", values=metric)
                assert w.notna().all().all()
                d = (w[a]-w[b]).rename("difference").reset_index()
                pairs.append({"sample": sample, "first": a, "second": b,
                              "metric": metric, **ci(d, "difference")})
    # Source-domain strata keep exactly the same task set within each contrast.
    r["domain"] = r.file.str.extract(r"/(swe-rebench-v2|scale-swe)/")[0]
    assert r.domain.notna().all()
    assert (r.groupby("task_id").domain.nunique() == 1).all()
    for domain, s in r.groupby("domain"):
        for a in [h for h in hs if h != "mini-swe-agent"]:
            w = s.pivot(index="task_id", columns="harness", values="revisit_rate")
            d = (w[a]-w["mini-swe-agent"]).rename("difference").reset_index()
            strata.append({"domain": domain, "first": a,
                           "second": "mini-swe-agent", **ci(d, "difference")})
    for name, rows in [("harness_run_means", summaries), ("harness_paired_differences", pairs),
                       ("harness_by_source", strata)]:
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)
    return {"tasks": int(r.task_id.nunique()), "outlier_task": outlier_task,
            "domains": r.groupby("domain").task_id.nunique().to_dict()}


def final_command_analysis():
    r = pd.read_csv(ROOT / "results/v2/reconcile/scale_per_run.csv")
    assert len(r) == 2100
    # First check has no earlier check. Remove it from the novelty numerator
    # and denominator before interpreting subsequent command diversity.
    r["later_checks"] = (r.verify_final - 1).clip(lower=0)
    r["later_different"] = (r.diff_cmd_final - (r.verify_final > 0).astype(int)).clip(lower=0)
    assert (r.later_different <= r.later_checks).all()
    assert (r.later_checks == r.later_different+r.identical_reruns_final+r.same_cmd_diff_out_final).all()
    rows = []
    for name, s in [("all", r), ("at_least_two_versions", r[r.n_versions >= 2])]:
        for c in ["later_different", "identical_reruns_final", "same_cmd_diff_out_final"]:
            rows.append({"sample": name, "category": c, **ci(s, c, "later_checks"),
                         "checks": int(s.later_checks.sum())})
    pd.DataFrame(rows).to_csv(OUT / "final_checks_after_first.csv", index=False)


def patch_size_analysis():
    """Restore patch-size profiles with the current per-run rate definition.

    Patch size is a reference-patch proxy, not an independent difficulty label.
    These profiles are means, with no new uncertainty estimates.
    """
    r = pd.read_parquet(ROOT / "results/v2/task5/runs_benchmark.parquet")
    assert (r.groupby("task_id").gold_lines.nunique() <= 1).all()
    sizes = r.groupby("task_id", sort=True).gold_lines.first().dropna()
    bins = pd.qcut(sizes.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"])
    r["bin"] = r.task_id.map(bins)
    r["revisit_rate"] = r.same_object / r.n_ops.clip(lower=1)
    r["repeat_rate"] = r.exact_repeats / r.n_ops.clip(lower=1)
    rows = []
    for (bin_name, harness), g in r.groupby(["bin", "harness"], observed=True):
        assert len(g) == 500 and g.task_id.nunique() == 500
        rows.append({"bin": str(bin_name), "harness": harness, "runs": len(g),
                     "tasks": g.task_id.nunique(), "min_patch_lines": g.gold_lines.min(),
                     "max_patch_lines": g.gold_lines.max(), "tool_calls_mean": g.n_ops.mean(),
                     "resolve_rate": g.resolved.mean(), "exact_repeat_rate": g.repeat_rate.mean(),
                     "same_object_repeat_rate": g.revisit_rate.mean()})
    pd.DataFrame(rows).to_csv(OUT / "harness_patch_size_profiles.csv", index=False)


if __name__ == "__main__":
    checks = {"version": version_analysis(), "harness": paired_harness()}
    final_command_analysis()
    patch_size_analysis()
    manifest = {"date": "2026-10-26", "seed": SEED, "bootstrap_replicates": B,
                "interval": "task-clustered percentile, 95%; exploratory, unadjusted",
                "python": sys.version, "numpy": np.__version__, "pandas": pd.__version__,
                "pyarrow": pyarrow.__version__, "platform": platform.platform(),
                "scope": "Reanalysis of saved measurements; no parser fixes or new labels.",
                "checks": checks,
                "inputs": [{"path": p, "sha256": hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
                           for p in INPUTS]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(checks, indent=2))
    for f in ["version_paired_differences", "harness_paired_differences", "final_checks_after_first"]:
        print(f, pd.read_csv(OUT/f"{f}.csv").to_string(index=False))
