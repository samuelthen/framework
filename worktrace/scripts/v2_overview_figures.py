"""Figures for OVERVIEW.md, drawn only from result files already in the repository (no raw data, no API).

usage: v2_overview_figures.py   -> figures/overview/*.png"""
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
R, FIG = f"{ROOT}/results", f"{ROOT}/figures/overview"
# reference palette (dataviz skill), light mode
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
S1, S2, S3, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#a9a8a2"
MODELS = [("gemini-3.7-flash", "Gemini 3.7 Flash"), ("gpt-5.6-luna", "GPT-5.6 Luna"), ("gpt-5.6-terra", "GPT-5.6 Terra")]
HARN = [("mini-swe-agent", "mini-swe-\nagent", S1), ("openhands", "Open-\nHands", S2), ("swe-agent", "SWE-\nagent", S3)]
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "text.color": INK, "axes.titlesize": 11, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})


def ci(s):
    """'12.3% [10.1, 14.2]' or '51.8 [50.5, 53.0]' -> (point, lo, hi) as floats."""
    v = [float(x) for x in re.findall(r"-?\d+\.?\d*", str(s))]
    return v[0], v[1], v[2]


def style(ax, grid="x"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def save(fig, name, note=None):
    if note:
        fig.text(0.01, -0.04, note, fontsize=8, color=INK2, ha="left", va="top")
    fig.savefig(f"{FIG}/{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def f1_work_breakdown():
    """How much of the work is repeated, judged non-distinct, and candidate-redundant (scale labels)."""
    M = pd.read_csv(f"{R}/v2/task6/run_measures.csv")
    X = pd.read_csv(f"{R}/v2/task6/matched_ops.csv")
    rows = [("repeat candidate\n(same object or output)", lambda m, x, n: len(x) / n, MUTED),
            ("exact repeat\n(counting baseline)", lambda m, x, n: (m.exact_repeat_rate * m.n_ops).sum() / n, INK2),
            ("judged non-distinct", lambda m, x, n: (x.contribution == "non_distinct").sum() / n, S2),
            ("candidate-redundant\n(non-distinct and reproduces)",
             lambda m, x, n: ((x.contribution == "non_distinct") & (x.relation == "reproduces")).sum() / n, S2)]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    for ax, (mid, name) in zip(axes, MODELS):
        m, x = M[M.model == mid], X[X.model == mid]
        n = m.n_ops.sum()
        vals = [100 * f(m, x, n) for _, f, _ in rows]
        y = np.arange(len(rows))[::-1]
        ax.barh(y, vals, height=0.55, color=[c for *_, c in rows], edgecolor=SURF, linewidth=2)
        for yi, v in zip(y, vals):
            ax.text(v + 0.4, yi, f"{v:.1f}%" if v >= 0.1 else f"{v:.2f}%", va="center", fontsize=9, color=INK)
        ax.set_yticks(y, [r for r, *_ in rows])
        ax.set_xlim(0, 30)
        ax.set_xlabel("share of all operations")
        scope = "all 2,100 runs" if mid.startswith("gemini") else "10% task sample, 204 runs"
        ax.set_title(f"{name}\n", loc="left")
        ax.text(0, 1.02, scope, transform=ax.transAxes, fontsize=8.5, color=INK2)
        style(ax)
    fig.suptitle("Most repeated work is not redundant: only 1–2% of operations are candidate-redundant",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.1)
    save(fig, "1_work_breakdown", "JetBrains SWE-bench Pro. Labels: LLM annotator (primary, prompt v1); not human-validated. "
         "Pooled over operations; the candidate-redundant bar counts uncertain as not redundant (lo).")


def f2_harness():
    T = pd.read_csv(f"{R}/v2/task5/table1_by_harness.csv").set_index("harness")
    panels = [("resolve_rate", "Resolve rate (%)"), ("tool_calls", "Tool calls per run"),
              ("same_object_revisit (pooled)", "Same-object revisit (% of ops)"),
              ("exact_repeat_rate (run mean)", "Exact-repeat rate (% of ops)")]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), gridspec_kw={"wspace": 0.35})
    for ax, (col, title) in zip(axes, panels):
        for i, (h, lab, c) in enumerate(HARN):
            p, lo, hi = ci(T.loc[h, col])
            ax.bar(i, p, width=0.6, color=c, edgecolor=SURF, linewidth=2)
            ax.errorbar(i, p, yerr=[[p - lo], [hi - p]], color=INK, lw=1.2, capsize=3)
            ax.text(i, hi * 1.02 + (0.004 if p < 1 else 0), f"{p + 1e-9:.2f}" if p < 1 else f"{p + 1e-9:.1f}", ha="center", va="bottom", fontsize=8.5)
        ax.set_xticks(range(3), [lab for _, lab, _ in HARN], rotation=0, fontsize=8.5)
        ax.set_title(title, fontsize=10)
        top = max(ci(T.loc[h, col])[2] for h, *_ in HARN)
        ax.set_ylim(0, top * 1.25)
        style(ax, "y")
    fig.suptitle("Same model (Qwen3.8-27B), three harnesses: the harness changes cost and revisits, not exact repetition",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.06)
    save(fig, "2_harness_comparison", "Open-SWE-Traces v1.2, the same 2,000 tasks in each harness; error bars: task-clustered 95% CIs. "
         "Facts only (no LLM).")


def f3_difficulty():
    J = pd.read_csv(f"{R}/benchmark/table2_difficulty.csv")
    J = J[J.proxy == "gold_patch_lines"]
    jb = J.groupby("bin", sort=False).apply(lambda g: pd.Series({
        "tool calls": np.average(g.tool_calls_mean, weights=g.runs), "exact-repeat rate": np.average(g.exact_repeat_rate, weights=g.runs * g.tool_calls_mean),
        "same-object revisit": np.average(g.same_object_repeat_rate, weights=g.runs * g.tool_calls_mean),
        "resolve rate": np.average(g.resolve_rate, weights=g.runs)}), include_groups=False)
    Q = pd.read_parquet(f"{R}/v2/task5/runs_benchmark.parquet")
    tv = Q.groupby("task_id").gold_lines.first().dropna()  # same bins as v2_task5.py benchmark
    Q["bin"] = Q.task_id.map(pd.qcut(tv.rank(method="first"), 4, labels=["Q1 easiest", "Q2", "Q3", "Q4 hardest"]))
    Q = Q[Q.task_id != "siliconcompiler_lambdapdk_pr114"].dropna(subset=["bin"])  # the stuck-loop case study
    qw = Q.groupby("bin", observed=True).apply(lambda g: pd.Series({
        "tool calls": g.n_ops.mean(), "exact-repeat rate": g.exact_repeats.sum() / g.n_ops.sum(),
        "same-object revisit": g.same_object.sum() / g.n_ops.sum(), "resolve rate": g.resolved_f.mean()}), include_groups=False)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    series = [("tool calls", S1, "-"), ("same-object revisit", S3, "-"), ("exact-repeat rate", S2, "-"), ("resolve rate", INK2, "--")]
    for ax, (D, title) in zip(axes, [(jb, "JetBrains (3 models, 6,300 runs)"), (qw, "Open-SWE (Qwen, 3 harnesses, 6,000 runs)")]):
        D = D / D.iloc[0]
        x = np.arange(len(D))
        for col, c, ls in series:
            ax.plot(x, D[col], color=c, lw=2, ls=ls, marker="o", ms=6, mec=SURF, mew=1.5)
            ax.text(x[-1] + 0.08, D[col].iloc[-1], f"{col}  ×{D[col].iloc[-1]:.2f}", va="center", fontsize=8.5, color=INK)
        ax.axhline(1, color=GRID, lw=1)
        ax.set_xticks(x, ["easiest", "Q2", "Q3", "hardest"])
        ax.set_xlim(-0.2, len(D) + 0.9)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("task bin by gold-patch size")
        style(ax, "y")
    axes[0].set_ylabel("relative to the easiest bin")
    fig.suptitle("Harder tasks cost more, but exact repetition does not grow with difficulty",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.03)
    save(fig, "3_difficulty", "Four equal task bins by gold-patch lines; rates pooled over operations. Open-SWE excludes the "
         "one stuck-loop task (164 identical probes in one run; a case study), which alone doubles its Q2 exact-repeat rate.")


def f4_return_after_k():
    D = pd.read_csv(f"{R}/v2/task6/return_after_k_raw.csv")
    D = D[D.model == "gemini"]
    C = pd.read_csv(f"{R}/v2/task6/return_after_k_coefficients.csv")
    C = C[(C.fit == "gemini, all runs") & C.estimator.str.startswith("GEE")].set_index("term")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = np.arange(len(D))
    p = np.array([ci(s) for s in D.non_distinct])
    ax.bar(x, p[:, 0], width=0.55, color=S2, edgecolor=SURF, linewidth=2)
    ax.errorbar(x, p[:, 0], yerr=[p[:, 0] - p[:, 1], p[:, 2] - p[:, 0]], color=INK, lw=1.2, capsize=3, ls="none")
    ors = ["reference", "OR {:.2f} [{:.2f}, {:.2f}]".format(*C.loc["C(k_bin, Treatment('1'))[T.2-3]", ["odds_ratio", "or_lo", "or_hi"]]),
           "OR {:.2f} [{:.2f}, {:.2f}]".format(*C.loc["C(k_bin, Treatment('1'))[T.4+]", ["odds_ratio", "or_lo", "or_hi"]])]
    for xi, (v, lo, hi), n, o in zip(x, p, D.returns, ors):
        ax.text(xi, hi + 1, f"{v:.1f}%", ha="center", fontsize=9.5, fontweight="bold")
    ax.set_xticks(x, [f"{k}\nn = {n:,}\n{o}" for k, n, o in zip(["k = 1", "k = 2–3", "k ≥ 4"], D.returns, ors)], fontsize=8.5)
    ax.set_ylim(0, 40)
    ax.set_ylabel("returns judged non-distinct (%)")
    style(ax, "y")
    ax.set_title("Returning after a long detour more often re-does earlier work", fontsize=11.5)
    save(fig, "4_return_after_k", "k = other objects visited before returning to an object. Gemini, all 2,100 runs, 16,352 returns.\nOdds ratios: logistic GEE (task clusters) adjusted for "
         "position and run length; 1,101 events per parameter. LLM labels, not human-validated.")


def f5_signatures():
    S = pd.read_csv(f"{R}/v2/task6/signatures_ci.csv")
    S = S[(S.model == "gemini") & S.signature.isin(["reread_unchanged_same_output", "return_any", "self_repeat", "error_loop",
                                                    "edit_test_identical_test", "new_to_new"])]
    names = {"reread_unchanged_same_output": "re-read unchanged content", "return_any": "return to an earlier object",
             "self_repeat": "same object twice in a row", "error_loop": "error loop", "edit_test_identical_test":
             "edit → identical test output", "new_to_new": "new object (control)"}
    S = S.assign(d=S.nd_minus_exact_pts.map(lambda s: ci(s)[0])).sort_values("d")
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    y = np.arange(len(S))
    for yi, r in zip(y, S.itertuples()):
        nd, ex = ci(r.non_distinct)[0], ci(r.exact_repeat_share)[0]
        ax.plot([ex, nd], [yi, yi], color=GRID, lw=3, zorder=1)
        ax.scatter([ex], [yi], s=60, color=INK2, zorder=2, edgecolor=SURF, linewidth=1.5)
        ax.scatter([nd], [yi], s=60, color=S2, zorder=3, edgecolor=SURF, linewidth=1.5)
        d, lo, hi = ci(r.nd_minus_exact_pts)
        ax.text(102, yi, f"{d:+.1f} pts [{lo:+.1f}, {hi:+.1f}]   n = {r.matches:,}", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, [names[s] for s in S.signature])
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of matched operations (%)")
    ax.scatter([], [], s=60, color=INK2, label="exact repeat (counting baseline)")
    ax.scatter([], [], s=60, color=S2, label="judged non-distinct (WorkTrace)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=9)
    style(ax)
    fig.suptitle("Structural signatures find non-distinct work that exact-repeat counting misses",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.07)
    save(fig, "5_signatures", "Gemini, all runs. Right: difference (non-distinct minus exact-repeat share) with task-clustered 95% CI. "
         "Re-read signature facts are shown to the annotator,\nso its share is partly by construction.")


def f6_final_verify():
    T = pd.read_csv(f"{R}/v2/reconcile/scale_summary.csv").iloc[0]
    sub = pd.read_csv(f"{R}/v2/reconcile/scale_class_iii_subtypes.csv").set_index("subtype")["All"].drop("All")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.3), gridspec_kw={"width_ratios": [1, 1.3], "wspace": 0.55})
    cls = [("identical rerun", ci(T.i_identical_share)[0], S2), ("same command,\nnew output", ci(T.ii_same_cmd_diff_out_share)[0], S3),
           ("different command", ci(T.iii_diff_cmd_share)[0], S1)]
    left = 0
    for lab, v, c in cls:
        a1.barh(0, v, left=left, color=c, height=0.4, edgecolor=SURF, linewidth=2)
        left += v
    a1.annotate(f"identical rerun {cls[0][1]:.1f}%", (cls[0][1] / 2, -0.2), (2, -0.42), fontsize=8.5, color=INK, arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.8})
    a1.annotate(f"same command, new output {cls[1][1]:.1f}%", (cls[0][1] + cls[1][1] / 2, 0.2), (2, 0.38), fontsize=8.5, color=INK, arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.8})
    a1.set_ylim(-0.55, 0.55)
    a1.text(50, 0, f"different command {cls[2][1]:.1f}%", ha="center", va="center", color="white", fontweight="bold")
    a1.set_xlim(0, 100); a1.set_yticks([]); a1.set_xlabel("share of verify runs on the final version (%)")
    a1.set_title(f"What the ~{ci(T.verify_final_per_run)[0]:.1f} final-version verify runs per run are", fontsize=10)
    style(a1)
    sub = (100 * sub / sub.sum()).sort_values()
    a2.barh(np.arange(len(sub)), sub.values, color=S1, height=0.6, edgecolor=SURF, linewidth=2)
    for yi, v in enumerate(sub.values):
        a2.text(v + 0.5, yi, f"{v:.0f}%", va="center", fontsize=9)
    a2.set_yticks(np.arange(len(sub)), sub.index)
    a2.set_xlabel("share of 'different command' verifies (%)")
    a2.set_title("Different commands: what kind of check", fontsize=10)
    style(a2)
    fig.suptitle("Gemini's extra work at the end is a widening set of checks, not reruns",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.04)
    save(fig, "6_final_verification", "Gemini, all 2,100 runs; View B variant (b). Facts only (no LLM). Sub-types from a rough command regex.")


def f7_versions():
    V = pd.read_csv(f"{R}/v2/viewb/support_no_version/runs_all.csv")
    V["nv"] = V.n_versions.clip(upper=8)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.4))
    for (mid, name), c in zip(MODELS, (S1, S2, S3)):
        g = V[V.model == mid]
        dist = g.nv.value_counts(normalize=True).sort_index() * 100
        a1.plot(dist.index, dist.values, color=c, lw=2, marker="o", ms=5, mec=SURF, label=name)
        r = g.groupby("nv").resolved.agg(["mean", "size"])
        r = r[r["size"] >= 30]
        a2.plot(r.index, 100 * r["mean"], color=c, lw=2, marker="o", ms=5, mec=SURF, label=name)
    for ax, t, yl in ((a1, "How many code versions a run makes", "share of runs (%)"),
                      (a2, "Resolve rate by number of versions", "resolved (%)")):
        ax.set_xticks(range(0, 9), ["0"] + [str(i) for i in range(1, 8)] + ["8+"])
        ax.set_xlabel("code versions in the run (View B)")
        ax.set_ylabel(yl); ax.set_title(t, fontsize=10)
        style(ax, "y")
    a1.legend(frameon=False, fontsize=9)
    fig.suptitle("Resolve rate falls as runs need more code versions, most clearly for the GPT models",
                 x=0.01, ha="left", fontweight="bold", fontsize=12, y=1.04)
    save(fig, "7_versions", "JetBrains, all 6,300 runs; View B variant (b): support-only changes (scratch/repro files) create no "
         "version. Points with fewer than 30 runs are omitted.")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    for f in (f1_work_breakdown, f2_harness, f3_difficulty, f4_return_after_k, f5_signatures, f6_final_verify, f7_versions):
        f()
