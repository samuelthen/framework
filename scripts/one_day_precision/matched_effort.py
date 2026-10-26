"""Section 6: outcome-matched effort from saved run tables only (no semantic labels, no version graphs).

Action count = `n_ops`, the native executed tool operations parsed from each trajectory (the WorkTrace loaders); for the
JetBrains panel `api_calls` (model calls recorded by the dataset) is reported alongside as a sensitivity. Effort here is
recorded interaction effort conditional on outcome; it is not redundancy or semantic precision.

usage: python scripts/one_day_precision/matched_effort.py -> matched_effort.csv, matched_differences.csv, fig_matched_effort.*"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import N_BOOT, OUT, ROOT, SEED, boot_ci, log  # noqa: E402

CELLS = ["both_success", "first_only_success", "second_only_success", "both_failure", "unknown_outcome"]


def _cell(ra, rb):
    if pd.isna(ra) or pd.isna(rb):
        return "unknown_outcome"
    return {(True, True): "both_success", (True, False): "first_only_success",
            (False, True): "second_only_success", (False, False): "both_failure"}[(bool(ra), bool(rb))]


def compare(W, a, b, panel, comparison, variant, measure="n_ops", eligibility=""):
    """W: one row per task with columns resolved_<a>, resolved_<b>, <measure>_<a>, <measure>_<b>."""
    W = W.assign(cell=[_cell(x, y) for x, y in zip(W[f"resolved_{a}"], W[f"resolved_{b}"])])
    eff, dif = [], []
    for cell in CELLS + ["all_shared_tasks"]:
        g = W if cell == "all_shared_tasks" else W[W.cell == cell]
        base = {"panel": panel, "comparison": comparison, "variant": variant, "measure": measure, "cell": cell,
                "n_tasks": len(g), "eligibility": eligibility}
        for s in (a, b):
            v = g[f"{measure}_{s}"].dropna()
            q = v.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(1).tolist() if len(v) else [np.nan] * 5
            eff.append(base | {"system": s, "mean": round(v.mean(), 2) if len(v) else np.nan, "median": v.median() if len(v) else np.nan,
                               "p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p90": q[4]})
        d = (g[f"{measure}_{a}"] - g[f"{measure}_{b}"]).dropna()
        m, lo, hi = boot_ci(d.values)
        md, mlo, mhi = boot_ci(d.values, stat=np.median, n=N_BOOT)
        sa, sb = g[f"{measure}_{a}"].sum(), g[f"{measure}_{b}"].sum()
        nz = g[g[f"{measure}_{b}"] > 0]
        # ratio of means with a task bootstrap; zero denominators reported, not dropped silently
        if len(g) > 1 and sb > 0:
            idx = np.random.default_rng(SEED).integers(0, len(g), size=(N_BOOT, len(g)))
            A, B = g[f"{measure}_{a}"].values[idx].sum(1), g[f"{measure}_{b}"].values[idx].sum(1)
            with np.errstate(divide="ignore", invalid="ignore"):
                rl, rh = np.nanpercentile(A / B, [2.5, 97.5])
        else:
            rl = rh = np.nan
        dif.append(base | {"first": a, "second": b, "mean_diff_first_minus_second": round(m, 2), "mean_diff_lo": round(lo, 2),
                           "mean_diff_hi": round(hi, 2), "median_diff": md, "median_diff_lo": mlo, "median_diff_hi": mhi,
                           "ratio_of_means": round(sa / sb, 3) if sb > 0 else np.nan, "ratio_lo": round(rl, 3), "ratio_hi": round(rh, 3),
                           "median_per_task_ratio": round(float((nz[f"{measure}_{a}"] / nz[f"{measure}_{b}"]).median()), 3) if len(nz) else np.nan,
                           "zero_denominator_tasks": int((g[f"{measure}_{b}"] == 0).sum()),
                           "share_tasks_first_more": round(float((d > 0).mean()), 3) if len(d) else np.nan})
    return eff, dif


def model_panel():
    R = pd.read_parquet(f"{ROOT}/data/runs.parquet")
    a, b = "gemini-3.7-flash", "gpt-5.6-luna"
    eff, dif = [], []
    for rep in (1, 2, 3):
        W = None
        for s in (a, b):
            x = R[(R.model == s) & (R.run_index == rep)].set_index("task_id")[["resolved", "n_ops", "api_calls"]]
            x.columns = [f"{c}_{s}" for c in x.columns]
            W = x if W is None else W.join(x, how="inner")
        for measure in ("n_ops", "api_calls"):
            e, d = compare(W.reset_index(), a, b, "model (mini-swe-agent)", f"{a} vs {b}",
                           "primary: repeat 1" if rep == 1 else f"sensitivity: repeat {rep}", measure,
                           f"700 shared tasks, repeat {rep} of each model")
            eff += e; dif += d
    # task-level aggregation of successful runs: per task, mean actions over that model's successful repeats
    agg = []
    for s in (a, b):
        g = R[R.model == s].groupby("task_id")
        x = pd.DataFrame({f"resolved_{s}": g.resolved.apply(lambda v: bool(v.astype(bool).any())),
                          f"n_ops_{s}": g.apply(lambda d: d[d.resolved.astype(bool)].n_ops.mean() if d.resolved.astype(bool).any() else d.n_ops.mean(), include_groups=False),
                          f"n_success_{s}": g.resolved.apply(lambda v: int(v.astype(bool).sum()))})
        agg.append(x)
    W = agg[0].join(agg[1], how="inner").reset_index()
    e, d = compare(W, a, b, "model (mini-swe-agent)", f"{a} vs {b}", "sensitivity: task-level (mean over successful repeats)", "n_ops",
                   "task counts as success if any of 3 repeats succeeded; actions = mean over that model's successful repeats "
                   "(over all 3 repeats when none succeeded); one row per task")
    eff += e; dif += d
    return eff, dif


def harness_panel():
    Q = pd.read_parquet(f"{ROOT}/results/v2/task5/runs_benchmark.parquet")
    Q["resolved"] = Q.resolved.map(lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else bool(v))
    eff, dif = [], []
    for a, b, role in (("mini-swe-agent", "openhands", "primary"), ("mini-swe-agent", "swe-agent", "secondary")):
        for stratum in ("all", *sorted(Q.subset.unique())):
            q = Q if stratum == "all" else Q[Q.subset == stratum]
            W = None
            for s in (a, b):
                x = q[q.harness == s].set_index("task_id")[["resolved", "n_ops"]]
                x.columns = [f"{c}_{s}" for c in x.columns]
                W = x if W is None else W.join(x, how="inner")
            e, d = compare(W.reset_index(), a, b, "harness (Qwen3.8-27B fixed)", f"{a} vs {b}",
                           f"{role}" + ("" if stratum == "all" else f"; stratum {stratum}"), "n_ops",
                           "Open-SWE-Traces v1.2 Task 5 sample: one run per harness per task (2,000 shared tasks)")
            eff += e; dif += d
    return eff, dif


def figure(D):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
    COL = {"both_success": "#2a78d6", "first_only_success": "#1baf7a", "second_only_success": "#eda100", "both_failure": "#a9a8a2"}
    NAME = {"both_success": "both succeed", "first_only_success": "first only succeeds", "second_only_success": "second only succeeds",
            "both_failure": "both fail"}
    rows = [("model (mini-swe-agent)", "gemini-3.7-flash vs gpt-5.6-luna", "primary: repeat 1", "Gemini 3.7 Flash − GPT-5.6 Luna\n(mini-swe-agent, repeat 1)"),
            ("harness (Qwen3.8-27B fixed)", "mini-swe-agent vs openhands", "primary", "mini-swe-agent − OpenHands\n(Qwen3.8-27B)"),
            ("harness (Qwen3.8-27B fixed)", "mini-swe-agent vs swe-agent", "secondary", "mini-swe-agent − SWE-agent\n(Qwen3.8-27B)")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True, facecolor=SURF)
    for ax, (p, c, v, title) in zip(axes, rows):
        g = D[(D.panel == p) & (D.comparison == c) & (D.variant == v) & (D.measure == "n_ops") & D.cell.isin(COL)]
        for i, r in enumerate(g.set_index("cell").reindex(list(COL)).itertuples()):
            y = 3 - i
            ax.errorbar(r.mean_diff_first_minus_second, y, xerr=[[r.mean_diff_first_minus_second - r.mean_diff_lo], [r.mean_diff_hi - r.mean_diff_first_minus_second]],
                        fmt="o", color=COL[r.Index], ms=8, mec=SURF, lw=2, capsize=3)
            ax.text(ax.get_xlim()[1] if False else r.mean_diff_hi + 1.5, y, f"{r.mean_diff_first_minus_second:+.1f}  (n = {r.n_tasks})", va="center", fontsize=8.5, color=INK)
        ax.axvline(0, color=INK2, lw=1)
        ax.set_yticks([3, 2, 1, 0], [NAME[k] for k in COL])
        ax.set_title(title, fontsize=10, loc="left", fontweight="bold")
        ax.set_xlabel("paired difference in tool actions per task\n(mean, 95% task-bootstrap CI)")
        ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_facecolor(SURF)
        xl = ax.get_xlim(); ax.set_xlim(xl[0], xl[1] + (xl[1] - xl[0]) * 0.35)
    fig.suptitle("Outcome-matched effort: recorded tool actions per task, paired on task, within each outcome cell",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.04)
    fig.text(0.01, -0.06, "Saved run tables only; 5,000 task-bootstrap replicates, seed 20261026. Effort is recorded interaction effort conditional on outcome, "
             "not redundancy or semantic precision.\nHarness call packaging differs (one editor change per call in OpenHands/SWE-agent), so harness differences are not normalized productive work.",
             fontsize=8, color=INK2, va="top")
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/fig_matched_effort.{ext}", dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


if __name__ == "__main__":
    e1, d1 = model_panel()
    e2, d2 = harness_panel()
    E, D = pd.DataFrame(e1 + e2), pd.DataFrame(d1 + d2)
    E.to_csv(f"{OUT}/matched_effort.csv", index=False)
    D.to_csv(f"{OUT}/matched_differences.csv", index=False)
    figure(D)
    log(f"matched effort: {len(E)} effort rows, {len(D)} difference rows; figure fig_matched_effort.pdf/png")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(D[D.measure == "n_ops"][["comparison", "variant", "cell", "n_tasks", "mean_diff_first_minus_second", "mean_diff_lo", "mean_diff_hi",
                                   "median_diff", "ratio_of_means", "ratio_lo", "ratio_hi"]].to_string(index=False))
