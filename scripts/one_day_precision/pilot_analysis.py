"""Section 4-6 synthesis: pilot contribution summaries, the link to outcome-matched effort, the failed-run coverage
extension (one eligible run), declared example selection, and figures.

Inputs: scores_by_run.csv, pilot_pairs.csv, action_annotations.jsonl, requirements.jsonl, matched_differences.csv.
Outputs: pilot_summary.csv, pilot_decomposition.csv, failed_run_coverage.csv, examples.json,
         fig_precision_bounds.{pdf,png}, fig_effort_decomposition.{pdf,png}, fig_trajectory_example.{pdf,png}

usage: python scripts/one_day_precision/pilot_analysis.py"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, PRIMARY, SEED, boot_ci, log, write_json  # noqa: E402

G, L = PRIMARY
NAME = {G: "Gemini 3.7 Flash", L: "GPT-5.6 Luna"}
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
C_G, C_L = "#2a78d6", "#eb6834"
C_DIRECT, C_UNC = "#1baf7a", "#eda100"
REASON_ORDER = ["unused_context", "repeated_support", "superseded_check", "administration", "negative_detour",
                "discarded_edit", "style_only", "scaffolding", "unrelated_check", "other"]


def summaries(R, P, A):
    ev = R[R.split == "evaluation"]
    rows = []
    for m in PRIMARY:
        g = ev[ev.model == m]
        rows.append({"model": m, "runs": len(g), "actions_total": int(g.N.sum()), "direct_total": int(g.D.sum()),
                     "uncertain_total": int(g.U.sum()),
                     "P_lower_mean": g.P_lower.mean(), "P_lower_median": g.P_lower.median(),
                     "P_upper_mean": g.P_upper.mean(), "P_upper_median": g.P_upper.median(),
                     "P_lower_pooled": g.D.sum() / g.N.sum(), "P_upper_pooled": (g.D.sum() + g.U.sum()) / g.N.sum(),
                     "uncertain_share_mean": g.uncertain_share.mean(),
                     "P_lower_mean_excl_submit": g.P_lower_excl_submit.mean(),
                     "P_upper_mean_excl_submit": g.P_upper_excl_submit.mean(),
                     "actions_mean": g.N.mean(), "direct_mean": g.D.mean()})
    S = pd.DataFrame(rows)
    pe = P[P.split == "evaluation"]
    d = {"pairs": len(pe),
         "diff_lower_mean": pe.diff_lower.mean(), "diff_lower_median": pe.diff_lower.median(),
         "diff_upper_mean": pe.diff_upper.mean(), "diff_upper_median": pe.diff_upper.median(),
         "pairs_luna_higher_under_every_resolution": int((pe.diff_max < 0).sum()),
         "pairs_gemini_higher_under_every_resolution": int((pe.diff_min > 0).sum()),
         "pairs_order_depends_on_uncertain": int(((pe.diff_min <= 0) & (pe.diff_max >= 0)).sum())}
    lo = boot_ci(pe.diff_lower.values)
    up = boot_ci(pe.diff_upper.values)
    d.update({"diff_lower_mean_boot95": [lo[1], lo[2]], "diff_upper_mean_boot95": [up[1], up[2]],
              "boot_note": f"task bootstrap over the {len(pe)} evaluation pairs, 5000 replicates, seed {SEED}; "
                           "sampling uncertainty only, separate from the label bounds; illustrative at this n"})
    # sign test: probability of >= k pairs in the same direction under no difference (two-sided, exact)
    from math import comb
    k, n = d["pairs_luna_higher_under_every_resolution"], len(pe)
    d["sign_test_two_sided_p_strict"] = min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)
    return S, d


def decomposition(R, A):
    """Where the extra actions of the longer system go, on the evaluation pairs (paired on task)."""
    ev_runs = set(R[R.split == "evaluation"].run_id)
    E = A[A.run_id.isin(ev_runs)].copy()
    E["category"] = np.where(E.contribution_label == "direct", "direct",
                             np.where(E.contribution_label == "uncertain", "uncertain", "nd:" + E.non_direct_reason.fillna("other")))
    M = E.merge(R[["run_id", "model"]], on="run_id")
    T = M.groupby(["model", "category"]).size().unstack(0).fillna(0).astype(int)
    T["difference_gemini_minus_luna"] = T[G] - T[L]
    tot = T[G].sum() - T[L].sum()
    T["share_of_extra_actions"] = T["difference_gemini_minus_luna"] / tot
    T = T.sort_values("difference_gemini_minus_luna", ascending=False)
    roles = M.groupby(["model", "role", "contribution_label"]).size().unstack([0]).fillna(0).astype(int)
    return T, roles


def coverage_bounds(statuses):
    """reference_requirement_coverage bounds from terminal per-requirement statuses
    ('achieved' | 'not_achieved' | 'uncertain'): (H/K, (H+U)/K, H, U, K)."""
    assert all(v in ("achieved", "not_achieved", "uncertain") for v in statuses), statuses
    K = len(statuses)
    if K == 0:
        return float("nan"), float("nan"), 0, 0, 0
    H = sum(v == "achieved" for v in statuses)
    U = sum(v == "uncertain" for v in statuses)
    return H / K, (H + U) / K, H, U, K


def failed_run_coverage():
    """The only failed run on an evaluation task (Gemini repeat 2, vuls). Terminal coverage from a static reading
    of its final submission against the task's frozen requirements (requirements.jsonl). Model-coded, preliminary."""
    run_id = "jb:gemini_3_7_flash:instance_future-architect__vuls-aaea15e516ece43978cf98e09e52080478b1d39f:r2"
    judg = [
        ("R1", "not_achieved", "searchCache still takes *map[string]string and dereferences it; FillWordPress still takes a pointer"),
        ("R2", "achieved", "searchCache returns (value, ok); behaviour preserved"),
        ("R3", "achieved", "FillWordPress reads c.Conf.Servers[r.ServerName].WordPress.IgnoreInactive"),
        ("R4", "achieved", "removeInactives applied when the per-server or global setting is on; FilterInactiveWordPressLibs likewise"),
        ("R5", "achieved", "removeInactives unchanged (already satisfied in the base code)")]
    rows = [{"run_id": run_id, "task_id": run_id.split(":")[2], "model": G, "repeat": 2, "resolved": False,
             "requirement_id": r, "terminal_status": s, "evidence": e,
             "state_basis": "static reading of the final submission patch applied to the base commit; tests not executed",
             "annotator_provenance": "Claude (Anthropic), model-coded, preliminary"} for r, s, e in judg]
    C = pd.DataFrame(rows)
    lo_c, hi_c, H, U, K = coverage_bounds(list(C.terminal_status))
    repair = {"R1", "R3", "R4"}
    Hr = int(((C.terminal_status == "achieved") & C.requirement_id.isin(repair)).sum())
    summary = {"run_id": run_id, "K": K, "H": H, "U_req": U, "coverage_lower": lo_c, "coverage_upper": hi_c,
               "repair_requirements_K": len(repair), "repair_H": Hr, "repair_coverage": Hr / len(repair),
               "peak_coverage": None, "peak_status": "not computed: intermediate code states not reconstructed",
               "Q_failure": None, "Q_failure_status": "not computed: actions of this run were not annotated",
               "name": "reference_requirement_coverage (terminal), conditional on this task's reference requirements"}
    return C, summary


def select_examples(P):
    """Declared before looking at the action labels of the chosen tasks' figures: (a) the evaluation pair at the
    lower median of diff_lower (median-gap case), (b) the pair with the smallest |diff_lower| (closest/counterexample)."""
    pe = P[P.split == "evaluation"].sort_values(["diff_lower", "order"]).reset_index(drop=True)
    med = pe.iloc[(len(pe) - 1) // 2]
    close = pe.iloc[pe.diff_lower.abs().argsort().iloc[0]]
    return {"rule": "median-gap pair = lower median of diff_lower over evaluation pairs (ties by frozen order); "
                    "closest pair = smallest |diff_lower|",
            "median_gap": {"order": int(med.order), "task_id": med.task_id, "diff_lower": float(med.diff_lower)},
            "closest": {"order": int(close.order), "task_id": close.task_id, "diff_lower": float(close.diff_lower)}}


def bundling(R):
    """Commands per action (after a leading `cd X &&`; heredoc bodies ignored) in the evaluation runs."""
    import re
    from packets import load_runs
    ev = R[R.split == "evaluation"]
    runs = load_runs(ev.run_id)
    rows = []
    for r in ev.itertuples():
        for o in runs[r.run_id][1]:
            c = re.sub(r"^\s*cd\s+\S+\s*&&\s*", "", (o["command"] or "").split("<<")[0]).strip()
            rows.append({"model": r.model, "segments": 1 + len(re.findall(r"&&|;|\|\||\n(?=\S)", c))})
    B = pd.DataFrame(rows).groupby("model").segments.agg(
        mean="mean", median="median", share_multi=lambda x: (x > 1).mean(), actions="size")
    return B


def _style(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_facecolor(SURF)


def fig_bounds(R, plt):
    ev = R[R.split == "evaluation"].copy()
    order = sorted(ev.order.unique())
    fig, ax = plt.subplots(figsize=(9.5, 3.8), facecolor=SURF)
    for i, o in enumerate(order):
        for m, c, dx in ((G, C_G, -0.12), (L, C_L, 0.12)):
            r = ev[(ev.order == o) & (ev.model == m)].iloc[0]
            ax.plot([i + dx, i + dx], [100 * r.P_lower, 100 * r.P_upper], color=c, lw=4, solid_capstyle="round")
            ax.scatter([i + dx], [100 * r.P_lower], color=c, s=36, zorder=3, edgecolor=SURF, linewidth=1.2)
            ax.text(i + dx, 100 * r.P_upper + 2.5, f"N={r.N}", ha="center", fontsize=7.5, color=INK2)
    ax.set_xticks(range(len(order)), [f"task {o}" for o in order])
    ax.set_ylim(0, 85)
    ax.set_ylabel("direct actions / all actions (%)")
    for m, c in ((G, C_G), (L, C_L)):
        ax.plot([], [], color=c, lw=4, label=f"{NAME[m]}  (dot = lower bound D/N, bar top = upper bound (D+U)/N)")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    _style(ax)
    ax.set_title("Contribution precision in successful runs, paired on task (8 evaluation tasks)", loc="left",
                 fontsize=11, fontweight="bold")
    fig.text(0.01, -0.06, "Model-coded pilot labels (Claude, single pass, preliminary; not human-validated). Bounds cover "
             "unresolved (uncertain) labels only, not errors in apparently certain labels. mini-swe-agent, repeat 1.",
             fontsize=8, color=INK2, va="top")
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/fig_precision_bounds.{ext}", dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def fig_decomposition(T, plt):
    cats = ["direct", "uncertain"] + [f"nd:{r}" for r in REASON_ORDER if f"nd:{r}" in T.index]
    pal = {"direct": C_DIRECT, "uncertain": C_UNC}
    greys = ["#3f3e3a", "#5f5e59", "#7f7e78", "#a09f99", "#c3c2bb", "#5d6e7e", "#7f8f9e", "#9fb0bf", "#bfcbd6", "#dcdad3"]
    dark = set()
    for i, c in enumerate([c for c in cats if c.startswith("nd:")]):
        pal[c] = greys[i % len(greys)]
        if i in (0, 1, 2, 5, 6):
            dark.add(c)
    fig, ax = plt.subplots(figsize=(10, 3.4), facecolor=SURF)
    for yi, m in enumerate((L, G)):
        left = 0
        for c in cats:
            v = int(T.loc[c, m]) if c in T.index else 0
            if v == 0:
                continue
            ax.barh(yi, v, left=left, color=pal[c], height=0.55, edgecolor=SURF, linewidth=1.5,
                    label=c.replace("nd:", "non-direct: ").replace("_", " ") if yi == 1 else None)
            if v >= 9:
                ax.text(left + v / 2, yi, str(v), ha="center", va="center", fontsize=8,
                        color="white" if (c == "direct" or c in dark) else INK)
            left += v
        ax.text(left + 4, yi, f"{left} actions", va="center", fontsize=9, fontweight="bold")
    ax.set_yticks([0, 1], [NAME[L], NAME[G]])
    ax.set_xlabel("actions summed over the 8 evaluation tasks (both runs succeed)")
    _style(ax, "x")
    ax.set_xlim(0, ax.get_xlim()[1] * 1.08)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=4, frameon=False, fontsize=8)
    ax.set_title("Where the extra recorded effort goes: direct vs non-direct actions by reason", loc="left",
                 fontsize=11, fontweight="bold")
    fig.text(0.01, -0.3, "Model-coded pilot labels (Claude, single pass, preliminary; not human-validated).",
             fontsize=8, color=INK2, va="top")
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/fig_effort_decomposition.{ext}", dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def fig_trajectory(A, R, reqs, example, plt):
    task = example["task_id"]
    Q = reqs[reqs.task_id == task]
    rids = list(Q.requirement_id)
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 4.6), facecolor=SURF, sharex=True)
    xmax = int(A[A.task_id == task].action_index.max()) + 1
    for ax, m, c in zip(axes, (G, L), (C_G, C_L)):
        run = R[(R.task_id == task) & (R.model == m)].iloc[0].run_id
        g = A[A.run_id == run].sort_values("action_index")
        rows = rids + ["no direct link"]
        ypos = {r: len(rows) - 1 - i for i, r in enumerate(rows)}
        for r in g.itertuples():
            if r.contribution_label == "direct" and r.requirement_ids:
                for q in r.requirement_ids:
                    if q in ypos:
                        ax.scatter(r.action_index, ypos[q], s=34, color=c, marker={"edit": "s", "verification": "D"}.get(r.role, "o"),
                                   edgecolor=SURF, linewidth=0.8, zorder=3)
            else:
                col = C_UNC if r.contribution_label == "uncertain" else "#a9a8a2"
                ax.scatter(r.action_index, ypos["no direct link"], s=22, color=col, marker="|" if r.contribution_label != "uncertain" else "x", zorder=2)
        ax.set_yticks([ypos[r] for r in rows], rows, fontsize=8)
        ax.set_xlim(-1, xmax)
        _style(ax, "x")
        rr = R[R.run_id == run].iloc[0]
        ax.set_title(f"{NAME[m]}: {rr.N} actions, D={rr.D}, U={rr.U}  (P in [{rr.P_lower:.2f}, {rr.P_upper:.2f}])",
                     loc="left", fontsize=9.5)
    axes[1].set_xlabel("action index in the run")
    fig.suptitle(f"Trajectory-to-requirement links, median-gap example (task {example['order']}: {task.split('__')[1][:40]}…)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", y=1.02)
    fig.text(0.01, -0.04, "Marker shape: circle = exploration, square = edit, diamond = verification; a direct action appears on "
             "each requirement row it supports. Bottom row: non-direct (grey ticks) and uncertain (amber x). Model-coded, preliminary.",
             fontsize=8, color=INK2, va="top")
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/fig_trajectory_example.{ext}", dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    R = pd.read_csv(f"{OUT}/scores_by_run.csv")
    P = pd.read_csv(f"{OUT}/pilot_pairs.csv")
    A = pd.DataFrame(map(json.loads, open(f"{OUT}/action_annotations.jsonl")))
    reqs = pd.DataFrame(map(json.loads, open(f"{OUT}/requirements.jsonl")))
    S, d = summaries(R, P, A)
    S.to_csv(f"{OUT}/pilot_summary.csv", index=False)
    write_json(f"{OUT}/pilot_paired.json", d)
    T, roles = decomposition(R, A)
    T.to_csv(f"{OUT}/pilot_decomposition.csv")
    roles.to_csv(f"{OUT}/pilot_direct_by_role.csv")
    C, cov = failed_run_coverage()
    C.to_csv(f"{OUT}/failed_run_coverage.csv", index=False)
    write_json(f"{OUT}/failed_run_coverage_summary.json", cov)
    bundling(R).to_csv(f"{OUT}/bundling.csv")
    ex = select_examples(P)
    write_json(f"{OUT}/examples.json", ex)
    fig_bounds(R, plt)
    fig_decomposition(T, plt)
    fig_trajectory(A, R, reqs, ex["median_gap"], plt)
    log(f"pilot analysis: summaries, decomposition, failed-run coverage ({cov['H']}/{cov['K']}), examples {ex['median_gap']['order']}/{ex['closest']['order']}, 3 figures")
    pd.set_option("display.width", 220)
    print(S.round(3).T.to_string())
    print(json.dumps(d, indent=1, default=float))
    print(T.to_string())
    print(roles.to_string())
    print(cov)
    print(ex)


if __name__ == "__main__":
    main()
