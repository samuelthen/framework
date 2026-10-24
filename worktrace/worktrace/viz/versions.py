"""TRACE-style figures for View B (code-version graphs): one run, and the Stage 4 aggregate of a group of runs.

Layout: x = version order (root at 0), y = row (a backtrack followed by a new version goes up one row).
Edges are coloured by their rule label; the self-loop above a version is its verify runs; the final version has a
dashed ring and its resolved / unresolved status (from the dataset). Intermediate versions are not marked correct.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Circle  # noqa: E402

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
EDGE = {  # categorical slots 1-3 (validated all-pairs) + neutrals
    "correct": ("#2a78d6", "-"),
    "revise": ("#eb6834", "-"),
    "backtrack": ("#1baf7a", "--"),
    "initial": (INK2, "-"),
    "noop": (MUTED, ":"),
}
NODE_FILL, ROOT_FILL = "#dcdad3", "#ffffff"


def _arrow(ax, p, q, color, ls, lw, back):
    rad = 0.35 if back else 0.0
    ax.add_patch(FancyArrowPatch(p, q, connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>", mutation_scale=11,
                                 color=color, lw=lw, ls=ls, shrinkA=13, shrinkB=13, zorder=2))


def _loop(ax, x, y, w, label):
    if w <= 0:
        return
    ax.add_patch(FancyArrowPatch((x - 0.09, y + 0.12), (x + 0.09, y + 0.12), connectionstyle="arc3,rad=-2.4",
                                 arrowstyle="-|>", mutation_scale=8, color=INK2, lw=min(0.8 + 0.6 * w, 7), zorder=1))
    ax.text(x, y + 0.5, label, ha="center", va="bottom", fontsize=7.5, color=INK2)


def _node(ax, x, y, text, size=0.16, fill=NODE_FILL, dashed=False, alpha=1.0):
    ax.add_patch(Circle((x, y), size, facecolor=fill, edgecolor=INK if not dashed else MUTED, lw=1.0,
                        ls="--" if dashed else "-", alpha=alpha, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=7.5, color=INK, zorder=4)


def _final(ax, x, y, size, text):
    ax.add_patch(Circle((x, y), size + 0.08, facecolor="none", edgecolor=INK, lw=1.2, ls=(0, (3, 2)), zorder=3))
    ax.text(x, y - size - 0.16, text, ha="center", va="top", fontsize=7.5, color=INK)


def _legend(ax, labels, aggregate=False):
    hs = [plt.Line2D([], [], color=EDGE[k][0], ls=EDGE[k][1], lw=1.6, label=k) for k in labels if k in EDGE]
    hs.append(plt.Line2D([], [], color=INK2, lw=2.5, label="self-loop: verify runs"))
    if aggregate:
        hs.append(plt.Line2D([], [], color="none", label="C x% = share of the move\nthat is 'correct'"))
    ax.legend(handles=hs, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7.5, frameon=False)


def _frame(ax, xmax, ymax, title):
    ax.set_xlim(-0.5, xmax + 0.6)
    ax.set_ylim(-0.6, ymax + 0.9)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, xmax + 1))
    ax.set_xticklabels(["root"] + [str(i) for i in range(1, xmax + 1)], fontsize=7.5, color=INK2)
    ax.set_yticks(range(0, ymax + 1))
    ax.tick_params(length=0, labelsize=7.5, labelcolor=INK2)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("version (order of first appearance)", fontsize=8, color=INK2)
    ax.set_ylabel("row", fontsize=8, color=INK2)
    ax.set_title(title, fontsize=9, color=INK, loc="left")


def plot_version_graph(g: dict, path: str, title: str | None = None):
    xy = {n["v"]: (n["x"], n["y"]) for n in g["nodes"]}
    xmax, ymax = max(p[0] for p in xy.values()), max(p[1] for p in xy.values())
    fig, ax = plt.subplots(figsize=(1.6 + 1.0 * (xmax + 1), 1.6 + 0.9 * (ymax + 1)))
    _frame(ax, xmax, ymax, title or g["run_id"])
    seen = []
    for e in g["edges"]:
        if e["dst"] == "final" or e["src"] == e["dst"]:
            continue
        c, ls = EDGE[e["label"]]
        _arrow(ax, xy[e["src"]], xy[e["dst"]], c, ls, 1.4, e["label"] == "backtrack")
        seen.append(e["label"])
    for n in g["nodes"]:
        x, y = xy[n["v"]]
        _loop(ax, x, y, n["verify"], f"{n['verify']}" if n["verify"] else "")
        _node(ax, x, y, "R" if n["v"] == 0 else f"v{n['v']}", fill=ROOT_FILL if n["v"] == 0 else NODE_FILL,
              dashed=n.get("uncertain", False))
        if n["final"]:
            _final(ax, x, y, 0.16, "final: " + ("resolved" if g["resolved"] else "unresolved"))
    _legend(ax, list(dict.fromkeys(seen)))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_aggregates(groups: list[tuple[str, dict]], path: str, ncols: int = 3, suptitle: str = ""):
    """groups: [(panel title, aggregate dict from versions.aggregate)]."""
    import math
    nrows = math.ceil(len(groups) / ncols)
    xmax = max((max((n["x"] for n in a["nodes"]), default=0) for _, a in groups), default=1)
    ymax = max((max((n["y"] for n in a["nodes"]), default=0) for _, a in groups), default=1)
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * (1.2 + 0.8 * (xmax + 1)), nrows * (1.8 + 0.8 * (ymax + 1))),
                             squeeze=False)
    labels_seen = []
    for ax, (title, a) in zip(axes.flat, groups):
        _frame(ax, xmax, ymax, f"{title}\n{a['runs']} runs, {100 * a['resolved']:.0f}% resolved")
        pos = {(n["x"], n["y"]) for n in a["nodes"]}
        for e in a["edges"]:
            if e["src"] == e["dst"] or e["src"] not in pos or e["dst"] not in pos:
                continue
            c, ls = EDGE[e["label"]]
            _arrow(ax, e["src"], e["dst"], c, ls, 0.6 + 3.5 * e["weight"], e["label"] == "backtrack")
            labels_seen.append(e["label"])
            mix = e.get("labels") or {}
            if "correct" in mix and e["label"] != "initial":
                mx, my = (e["src"][0] + e["dst"][0]) / 2, (e["src"][1] + e["dst"][1]) / 2
                ax.text(mx, my - 0.22, f"C {100 * mix['correct']:.0f}%", ha="center", va="top", fontsize=6.5, color=INK2)
        for n in a["nodes"]:
            x, y = n["x"], n["y"]
            _loop(ax, x, y, n["verify"], f"{n['verify']:.1f}")
            _node(ax, x, y, "R" if (x, y) == (0, 0) else f"{100 * n['weight']:.0f}%", size=0.12 + 0.1 * n["weight"],
                  fill=ROOT_FILL if (x, y) == (0, 0) else NODE_FILL)
            if n["final_share"] >= a["threshold"]:
                _final(ax, x, y, 0.12 + 0.1 * n["weight"],
                       f"final {100 * n['final_share']:.0f}%\nresolved {100 * (n['final_resolved'] or 0):.0f}%")
    for ax in list(axes.flat)[len(groups):]:
        ax.axis("off")
    _legend(axes.flat[min(len(groups), ncols) - 1], list(dict.fromkeys(labels_seen)) or ["initial"], aggregate=True)
    if suptitle:
        fig.suptitle(suptitle, fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
