"""Per-run static work-progression graph (D.8) and pilot summary figures."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
MODEL_COLORS = {"gpt-5.6-luna": "#2a78d6", "gpt-5.6-terra": "#eb6834", "gemini-3.7-flash": "#1baf7a"}
CONTRIB = {"distinct": "#2a78d6", "non_distinct": "#eb6834", "uncertain": "#a8a7a2", None: "#a8a7a2"}
REVISIT, REPRODUCE = "#008300", "#e34948"


def _style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def plot_run_graph(g: dict, path: str, max_targets: int = 25, title: str = ""):
    nodes = {n["id"]: n for n in g["nodes"]}
    order = sorted(nodes.values(), key=lambda n: n["first_visit"])
    collapse = len(order) > max_targets
    pos = {}
    x = 0
    for n in order:
        if collapse and n["visits"] == 1 and n["id"] != "<root>":
            continue
        pos[n["id"]] = (x, -n.get("row", 0))
        x += 1
    if collapse:
        pos["<other>"] = (x, 0)
    fig, ax = plt.subplots(figsize=(max(6, 0.55 * len(pos) + 2), 3.6), facecolor=SURF)
    ax.set_facecolor(SURF)
    p = lambda t: pos.get(t, pos.get("<other>"))  # noqa: E731
    loops = {}
    for e in g["edges"]:
        a, b = p(e["src"]), p(e["dst"])
        if a == b:
            loops.setdefault(e["dst"] if e["dst"] in pos else "<other>", []).append(e)
            continue
        back = b[0] < a[0]
        color = INK2
        if back:
            color = REPRODUCE if e["relation"] == "reproduces" else REVISIT if e["relation"] == "revisits" else "#a8a7a2"
        ax.add_patch(FancyArrowPatch(a, b, connectionstyle=f"arc3,rad={0.35 if back else 0.0}", arrowstyle="-|>",
                                     mutation_scale=8, lw=1.2 if back else 0.8, color=color, alpha=0.8 if back else 0.5))
    for t, es in loops.items():
        if t == "<other>":
            continue  # moves between collapsed singletons are not self-loops
        xy = pos[t]
        nd = sum(e["contribution"] == "non_distinct" for e in es)
        ax.add_patch(plt.Circle((xy[0], xy[1] + 0.28), 0.18, fill=False, lw=min(4.0, 0.8 + 0.6 * len(es)),
                                color=REPRODUCE if nd else REVISIT))
    for t, xy in pos.items():
        n = nodes.get(t, {"visits": 0, "id": t})
        size = 160 if t == "<other>" else 80 + 40 * min(n["visits"], 10)
        ax.scatter(*xy, s=size, color="#e34948" if n.get("gold") else "#c3c2b7", edgecolor=INK if n.get("final_edit") else SURF,
                   linewidths=1.5, linestyle="--" if n.get("final_edit") else "-", zorder=3)
        lab = t.split("::")[0][-22:]
        ax.annotate(lab, xy, xytext=(0, -14), textcoords="offset points", ha="center", va="top", fontsize=6.5, color=INK2, rotation=30)
    ax.set_xlim(-0.8, x + 0.8)
    ys = [v[1] for v in pos.values()]
    ax.set_ylim(min(ys) - 1.3, max(ys) + 0.9)
    ax.axis("off")
    ax.set_title(title or g["run_id"][-80:], fontsize=9, color=INK, loc="left")
    ax.text(0, max(ys) + 0.7, "red node = gold-patch file · dashed ring = final edit · green back-edge = revisit · red = reproduce · ring above node = self-loop",
            fontsize=6.5, color=INK2)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def bar_by_model(df, value_cols, labels, path, title, ylabel):
    """df: one row per model with value_cols. Grouped bars, one group per measure."""
    fig, ax = plt.subplots(figsize=(7, 3.4), facecolor=SURF)
    _style(ax)
    models = list(df.model)
    w = 0.8 / len(models)
    for i, m in enumerate(models):
        vals = [df.loc[df.model == m, c].iloc[0] for c in value_cols]
        xs = [j + (i - (len(models) - 1) / 2) * w for j in range(len(value_cols))]
        ax.bar(xs, vals, width=w - 0.03, color=MODEL_COLORS.get(m, "#6250d6"), label=m)
    ax.set_xticks(range(len(value_cols)))
    ax.set_xticklabels(labels, fontsize=8, color=INK2)
    ax.set_ylabel(ylabel, fontsize=8, color=INK2)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def stacked_contribution(rows, path, title):
    """rows: list of (label, distinct, non_distinct, uncertain, exact_repeat_share)."""
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(rows) + 1.2), facecolor=SURF)
    _style(ax)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.grid(axis="y", visible=False)
    for i, (lab, d, nd, u, ex) in enumerate(rows):
        left = 0
        for v, k in ((d, "distinct"), (nd, "non_distinct"), (u, "uncertain")):
            ax.barh(i, v, left=left, color=CONTRIB[k], height=0.6, edgecolor=SURF, linewidth=2,
                    label=k.replace("_", "-") if i == 0 else None)
            left += v
        ax.plot([ex, ex], [i - 0.38, i + 0.38], color=INK, lw=2, label="exact-repeat share" if i == 0 else None)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8, color=INK2)
    ax.set_xlim(0, 1)
    ax.invert_yaxis()
    ax.set_xlabel("share of matched operations", fontsize=8, color=INK2)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_labeled_trace(run: dict, ops: list[dict], labels: dict, path: str, max_rows: int = 28):
    """Redundancy-labelling view of one run: x = operation order, y = work target (by first visit).
    Each operation is a dot coloured by its LLM contribution label; the grey line is the agent's path, so a line
    going back up is a return to an earlier target. Black ring = exact repeat; large dot = candidate redundant."""
    first, visits = {}, {}
    for o in ops:
        first.setdefault(o["object"], len(first))
        visits[o["object"]] = visits.get(o["object"], 0) + 1
    keep = [t for t in first if visits[t] > 1]
    other = len(first) > max_rows
    rows = {t: i for i, t in enumerate(sorted(keep if other else list(first), key=first.get))}
    other_row = len(rows)
    y = [rows.get(o["object"], other_row) for o in ops]
    fig, ax = plt.subplots(figsize=(min(16, 4 + 0.16 * len(ops)), 0.32 * (len(rows) + other) + 1.8), facecolor=SURF)
    ax.set_facecolor(SURF)
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.plot(range(len(ops)), y, color="#c3c2b7", lw=0.9, zorder=1)
    for i, o in enumerate(ops):
        lab = labels.get(o["op_id"], {})
        c = lab.get("contribution")
        red = lab.get("relation") == "reproduces" and c == "non_distinct"
        ax.scatter(i, y[i], s=110 if red else 38, color=CONTRIB.get(c, CONTRIB[None]), zorder=3,
                   edgecolor=INK if o["exact_repeat"] else SURF, linewidths=1.6 if o["exact_repeat"] else 1.0)
    gold = set(run.get("gold_file_list") or [])
    names = [t if len(t) <= 48 else "…" + t[-47:] for t in rows] + (["(targets visited once)"] if other else [])
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7)
    for tl, t in zip(ax.get_yticklabels(), list(rows) + ([""] if other else [])):
        tl.set_color("#e34948" if t in gold else INK2)
    ax.invert_yaxis()
    ax.set_xlabel("operation (in order)", fontsize=8, color=INK2)
    ax.tick_params(axis="x", colors=INK2, labelsize=7)
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", color=CONTRIB["distinct"], label="distinct"),
         Line2D([], [], marker="o", ls="", color=CONTRIB["non_distinct"], label="non-distinct"),
         Line2D([], [], marker="o", ls="", color=CONTRIB["uncertain"], label="uncertain"),
         Line2D([], [], marker="o", ls="", color=CONTRIB["non_distinct"], ms=10, label="candidate redundant (reproduces + non-distinct)"),
         Line2D([], [], marker="o", ls="", mfc="none", mec=INK, mew=1.6, label="exact repeat"),
         Line2D([], [], color="#e34948", lw=0, label="red label = gold-patch file")]
    ax.legend(handles=h, frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12 - 0.6 / max(4, len(names))))
    n_nd = sum(labels.get(o["op_id"], {}).get("contribution") == "non_distinct" for o in ops)
    ax.set_title(f"{run['model']} · {run['task_id'][9:70]} · {len(ops)} ops, {n_nd} non-distinct · resolved={run['resolved']}",
                 fontsize=9, color=INK, loc="left")
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
