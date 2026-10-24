"""Build report.html: RESULTS.md content + embedded charts (one self-contained file)."""
import base64, io, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.viz.static import MODEL_COLORS, CONTRIB, INK, INK2, SURF, _style

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
B, P = f"{ROOT}/results/benchmark", f"{ROOT}/results/pilot"
MODELS = ["gemini-3.7-flash", "gpt-5.6-luna", "gpt-5.6-terra"]


FIGDIR = f"{ROOT}/figures"


def png(fig, name=None):
    if name:
        os.makedirs(FIGDIR, exist_ok=True)
        fig.savefig(f"{FIGDIR}/{name}.png", dpi=140, bbox_inches="tight")
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=140, bbox_inches="tight"); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def bars(ax, cats, series, fmt="{:.1%}"):
    w = 0.8 / len(series)
    for i, (name, vals) in enumerate(series.items()):
        xs = [j + (i - (len(series) - 1) / 2) * w for j in range(len(cats))]
        bs = ax.bar(xs, vals, width=w - 0.03, color=MODEL_COLORS.get(name, "#6250d6"), label=name)
        for b, v in zip(bs, vals):
            ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 2),
                        textcoords="offset points", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(range(len(cats))); ax.set_xticklabels(cats, fontsize=8, color=INK2)


def fig_benchmark():
    t = pd.read_csv(f"{B}/table1_by_model.csv").set_index("model").loc[MODELS]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.2), facecolor=SURF)
    for ax, col, title, fmt in [(axs[0], "exact_repeat_rate", "Exact-repeat rate (share of tool calls)", "{:.2%}"),
                                (axs[1], "same_object_repeat_rate", "Same-object revisit rate", "{:.1%}"),
                                (axs[2], "resolve_rate", "Resolve rate", "{:.1%}")]:
        _style(ax)
        ax.bar(range(3), t[col], color=[MODEL_COLORS[m] for m in MODELS], width=0.6)
        for i, v in enumerate(t[col]):
            ax.annotate(fmt.format(v), (i, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=8, color=INK2)
        ax.set_xticks(range(3)); ax.set_xticklabels(MODELS, fontsize=7.5, color=INK2)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
    return png(fig, "benchmark_by_model")


def fig_difficulty():
    t = pd.read_csv(f"{B}/table2_difficulty.csv")
    t = t[(t.proxy == "gold_patch_lines") & (t.model != "ALL")]
    bins = ["Q1 easiest", "Q2", "Q3", "Q4 hardest"]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.2), facecolor=SURF)
    for ax, col, title in [(axs[0], "tool_calls_mean", "Tool calls per run"), (axs[1], "resolve_rate", "Resolve rate"),
                           (axs[2], "exact_repeat_rate", "Exact-repeat rate")]:
        _style(ax)
        for m in MODELS:
            s = t[t.model == m].set_index("bin").loc[bins, col]
            ax.plot(range(4), s.values, color=MODEL_COLORS[m], lw=2, marker="o", ms=5, label=m)
        ax.set_xticks(range(4)); ax.set_xticklabels(bins, fontsize=7.5, color=INK2)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        if col != "tool_calls_mean":
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=1 if col == "exact_repeat_rate" else 0))
    axs[0].legend(frameon=False, fontsize=7)
    fig.suptitle("By task difficulty (gold-patch size quartiles)", fontsize=10, color=INK, x=0.01, ha="left")
    return png(fig, "difficulty")


def fig_pilot_rates():
    t = pd.read_csv(f"{P}/measures_by_model.csv").set_index("model").loc[MODELS]
    cols = ["exact_repeat_rate", "same_object_repeat_rate", "cand_redundancy_rate_lo", "cand_redundancy_rate_hi"]
    labs = ["exact repeat", "same-object revisit", "candidate redundant\n(uncertain = distinct)", "candidate redundant\n(uncertain = non-distinct)"]
    fig, ax = plt.subplots(figsize=(10, 3.4), facecolor=SURF); _style(ax)
    bars(ax, labs, {m: [t.loc[m, c] for c in cols] for m in MODELS})
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(frameon=False, fontsize=8); ax.set_title("Pilot (50 runs): repetition vs. LLM-judged redundancy, share of operations", fontsize=9, color=INK, loc="left")
    return png(fig, "pilot_repetition_vs_redundancy")


def fig_repeat_contrib():
    o = pd.read_csv(f"{P}/ops_labeled.csv")
    o["redundant"] = (o.relation == "reproduces") & (o.contribution == "non_distinct")
    ex, rd = o.exact_repeat, o.redundant
    vals = [(ex & rd).sum(), (ex & ~rd).sum(), (~ex & rd).sum()]
    labs = ["exact repeat AND\njudged redundant", "exact repeat but\njudged useful/not redundant", "judged redundant but\nNOT an exact repeat"]
    fig, ax = plt.subplots(figsize=(8, 3), facecolor=SURF); _style(ax)
    b = ax.bar(range(3), vals, color=["#6250d6", "#2a78d6", "#eb6834"], width=0.55)
    for r, v in zip(b, vals):
        ax.annotate(str(v), (r.get_x() + r.get_width() / 2, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(3)); ax.set_xticklabels(labs, fontsize=8, color=INK2)
    ax.set_ylabel("operations", fontsize=8, color=INK2)
    ax.set_title("Repeat counts and structural labels disagree (pilot, 1,432 ops)", fontsize=9, color=INK, loc="left")
    return png(fig, "repeats_vs_labels")


def fig_signatures():
    s = pd.read_csv(f"{P}/signatures.csv")
    s = s[(s.by == "object") & (s.matches > 0)].sort_values("matches", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(s) + 1.3), facecolor=SURF); _style(ax)
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color="#e4e3df", lw=0.6)
    for i, r in enumerate(s.itertuples()):
        left = 0
        for v, k in ((r.distinct, "distinct"), (r.non_distinct, "non_distinct"), (r.uncertain, "uncertain")):
            ax.barh(i, v, left=left, color=CONTRIB[k], height=0.6, edgecolor=SURF, lw=2, label=k.replace("_", "-") if i == 0 else None)
            left += v
        ax.plot([r.exact_repeat_share] * 2, [i - 0.38, i + 0.38], color=INK, lw=2.2, label="exact-repeat share" if i == 0 else None)
    ax.set_yticks(range(len(s))); ax.set_yticklabels([f"{r.signature} (n={r.matches})" for r in s.itertuples()], fontsize=8, color=INK2)
    ax.invert_yaxis(); ax.set_xlim(0, 1); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.set_title("Signatures: LLM contribution mix vs. what exact repeats suggest (black tick)", fontsize=9, color=INK, loc="left")
    return png(fig, "signatures")


def fig_return_k():
    r = pd.read_csv(f"{P}/return_after_k.csv")
    fig, ax = plt.subplots(figsize=(7, 3), facecolor=SURF); _style(ax)
    g = r[r.model == "gemini-3.7-flash"]
    ax.plot(range(len(g)), g.non_distinct, color=CONTRIB["non_distinct"], lw=2, marker="o", label="judged non-distinct")
    ax.plot(range(len(g)), g.exact_repeat, color=INK2, lw=2, marker="o", ls="--", label="exact repeat")
    ax.set_xticks(range(len(g))); ax.set_xticklabels([f"k={k}\n(n={int(n)})" for k, n in zip(g.kbin, g.n)], fontsize=8, color=INK2)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Gemini: returns to a file after k other targets — share judged non-distinct", fontsize=9, color=INK, loc="left")
    return png(fig, "return_after_k")


def main():
    figs = [("Benchmark: all 6,300 runs", fig_benchmark(), "Gemini repeats far more than the GPT-5.6 models, but the rates are small overall."),
            ("Difficulty", fig_difficulty(), "Harder tasks take more tool calls and are solved less often, yet the exact-repeat rate stays flat — the draft's 'repetition grows with difficulty' claim is not supported."),
            ("Pilot: repetition vs. redundancy", fig_pilot_rates(), "LLM-judged redundant work is 0–2.4% of operations."),
            ("Repeats vs. structural labels", fig_repeat_contrib(), "Most exact repeats were useful (e.g. test reruns after an edit); most redundant ops were not exact repeats (e.g. same content read with a different command)."),
            ("Signatures", fig_signatures(), "Rows above the black tick show where the structural labels differ from repeat counts. Only the first, fact-defined signatures are evidence; return_distinct/non_distinct are defined by the labels themselves."),
            ("Returns after detours", fig_return_k(), "Too few returns per bin (see n) to show a trend yet; needs the full run set.")]
    sec = "\n".join(f'<section><h2>{t}</h2><p>{c}</p><img src="{d}" alt="{t}"></section>' for t, d, c in figs)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WorkTrace Pilot Report</title><style>
body{{background:#fcfcfb;color:#0b0b0b;font:15px/1.5 system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:16px}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:28px}} p{{color:#52514e}} img{{max-width:100%;height:auto;border:1px solid #e4e3df;border-radius:6px}}
table{{border-collapse:collapse;font-size:13px}} td,th{{border-bottom:1px solid #e4e3df;padding:4px 8px;text-align:left}}
</style></head><body><h1>WorkTrace pilot report (2026-10-24)</h1>
<p>JetBrains SWE-bench Pro trajectories, mini-swe-agent. Full numbers and caveats: RESULTS.md. Per-run interactive graphs: <a href="viewer/index.html">viewer/index.html</a>.</p>
<table><tr><th>Go / no-go criterion</th><th>Status</th></tr>
<tr><td>1. Human–human κ ≥ 0.6</td><td>Pending human annotation</td></tr>
<tr><td>2. Model–human F1 ≥ 0.7, precision ≥ 0.8</td><td>Pending human annotation</td></tr>
<tr><td>3. Uncertain share ≤ 20%</td><td>Pass (4.9%)</td></tr>
<tr><td>4. Signature ≥ 10 pts from exact repeats</td><td>Pass, but thin (n = 11 and 60)</td></tr></table>
{sec}</body></html>"""
    open(f"{ROOT}/report.html", "w").write(html)
    print(f"{ROOT}/report.html")


if __name__ == "__main__":
    main()
