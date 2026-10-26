"""Render manuscript figures from saved result artifacts; no inference or relabeling.

Run with Python and matplotlib as documented in README.md.
"""
from pathlib import Path
import csv
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "images"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "pdf.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False})
MODELS = ["gemini-3.7-flash", "gpt-5.6-luna", "gpt-5.6-terra"]
NAMES = ["Gemini 3.7 Flash", "GPT-5.6 Luna", "GPT-5.6 Terra"]


def interval(s):
    return tuple(float(x) for x in re.findall(r"\d+(?:\.\d+)?", s))


def verification():
    p = ROOT / "results/v2/viewb/support_no_version/measures_by_model.csv"
    rows = {r["model"]: r for r in csv.DictReader(p.open())}
    fig, ax = plt.subplots(figsize=(3.25, 2.45))
    for j, (field, name, color) in enumerate([
        ("verify_per_earlier_version", "Earlier version (per-run mean)", "#8fa5b2"),
        ("verify_per_final_version", "Final version", "#185b83"),
    ]):
        vals = [interval(rows[m][field]) for m in MODELS]
        x = [i + (j - .5) * .3 for i in range(3)]
        ax.bar(x, [v[0] for v in vals], width=.28, color=color, label=name)
        ax.errorbar(x, [v[0] for v in vals],
                    yerr=[[v[0]-v[1] for v in vals], [v[2]-v[0] for v in vals]],
                    fmt="none", color="#222222", capsize=2, lw=.8)
    ax.set_xticks(range(3), ["Gemini", "Luna", "Terra"])
    ax.set_ylabel("Verification operations per version")
    ax.set_ylim(0, 4.05)
    ax.legend(frameon=False, fontsize=6.5, loc="upper right")
    ax.yaxis.grid(True, alpha=.18)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=.6)
    fig.savefig(OUT / "verification.pdf", bbox_inches="tight")
    plt.close(fig)


def aggregate_patterns():
    p = ROOT / "results/v2/viewb/support_no_version/aggregates.json"
    data = json.loads(p.read_text())
    fig, axes = plt.subplots(3, 1, figsize=(3.3, 3.7))
    for ax, m, name in zip(axes, MODELS, NAMES):
        g = data[m + "|4"]
        for edge in g["edges"]:
            if edge["src"] == edge["dst"]:
                continue
            a, b = edge["src"], edge["dst"]
            color = "#5b6570" if edge["label"] == "initial" else "#bd6b24"
            ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9,
                                        lw=.5+1.6*edge["weight"], color=color,
                                        shrinkA=13, shrinkB=13))
        for node in g["nodes"]:
            x, y = node["x"], node["y"]
            ax.add_patch(Circle((x, y), .16, facecolor="#e0edf4" if x else "white",
                                edgecolor="#354652", lw=.8, zorder=3))
            ax.text(x, y, "R" if x == 0 else f"v{x}", ha="center", va="center", fontsize=6, zorder=4)
            ax.text(x, y-.27, f"{100*node['weight']:.0f}%", ha="center", va="top", fontsize=6.5, color="#53616b")
            w = node["verify"]
            if w > 0:
                ax.add_patch(FancyArrowPatch((x-.09,y+.13),(x+.09,y+.13),
                    connectionstyle="arc3,rad=-2.1",arrowstyle="-|>",mutation_scale=7,
                    lw=.65+.35*w,color="#185b83"))
                ax.text(x,y+.54,f"{w:.2f}",ha="center",fontsize=7,color="#185b83")
            if node["final_share"] >= g["threshold"]:
                ax.add_patch(Circle((x,y),.22,facecolor="none",edgecolor="#354652",lw=.8,ls="--",zorder=2))
        ax.text(-.40,1.95,f"{name}: {g['runs']} runs",
                fontsize=7,weight="bold",va="top")
        ax.set_xlim(-.45,4.5)
        ax.set_ylim(-.6,2.15)
        ax.set_aspect("equal",adjustable="box")
        ax.axis("off")
    fig.subplots_adjust(hspace=.13,left=.02,right=.98,top=.98,bottom=.02)
    fig.savefig(OUT / "patterns_four_versions.pdf", bbox_inches="tight")
    plt.close(fig)


def new_comparisons():
    src = ROOT / "results/paper_revision_20261026"
    gaps = list(csv.DictReader((src / "version_common_sample.csv").open()))
    harness = list(csv.DictReader((src / "harness_run_means.csv").open()))
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.65))
    ax = axes[0]
    for i, (variant, name, color, marker) in enumerate([
        ("all_writes", "All writes", "#8799a5", "o"),
        ("known_writes", "Known writes", "#bc7934", "s"),
        ("exclude_support", "Exclude support files", "#185b83", "D"),
    ]):
        rows = {r['model']: r for r in gaps if r['variant'] == variant}
        x = [j + (i-1)*.20 for j in range(3)]
        pts = [float(rows[m]['estimate']) for m in MODELS]
        ax.errorbar(x, pts, yerr=[
            [v-float(rows[m]['lo']) for v,m in zip(pts,MODELS)],
            [float(rows[m]['hi'])-v for v,m in zip(pts,MODELS)]],
            fmt=marker, markersize=4, color=color, capsize=2, label=name, lw=.8)
    ax.axhline(0, color='#555555', lw=.65)
    ax.set_xticks(range(3), ['Gemini', 'Luna', 'Terra'])
    ax.set_ylabel('Final checks minus mean earlier checks')
    ax.set_title('(a) Where models check code', fontsize=9, loc='left')
    ax.legend(frameon=False, fontsize=6.5, loc='upper right')
    ax.set_ylim(-.5,3.5)
    ax.yaxis.grid(alpha=.15)
    ax = axes[1]
    hs = ['mini-swe-agent','openhands','swe-agent']
    rows = {r['harness']:r for r in harness if r['sample']=='all' and r['metric']=='revisit_rate'}
    vals = [float(rows[h]['estimate']) for h in hs]
    ax.bar(range(3),vals,color=['#8799a5','#185b83','#5f8195'],width=.6)
    ax.errorbar(range(3),vals,yerr=[
        [v-float(rows[h]['lo']) for v,h in zip(vals,hs)],
        [float(rows[h]['hi'])-v for v,h in zip(vals,hs)]],
        fmt='none',color='#222222',capsize=2,lw=.8)
    for j,v in enumerate(vals):ax.text(j,v+1.2,f'{v:.1f}%',ha='center',fontsize=8)
    ax.set_xticks(range(3),['mini-swe-\nagent','OpenHands','SWE-agent'],fontsize=7)
    ax.set_ylabel('Mean target revisit rate (%)')
    ax.set_ylim(0,40)
    ax.set_title('(b) How often harnesses revisit targets',fontsize=9,loc='left')
    ax.set_axisbelow(True)
    ax.yaxis.grid(alpha=.15)
    fig.tight_layout(pad=.7,w_pad=1.6)
    fig.savefig(OUT/'matched_comparisons.pdf',bbox_inches='tight')
    plt.close(fig)


def patch_size_profiles():
    """Restore the vertical benchmark, using means within patch-size quartiles."""
    model_rows = [r for r in csv.DictReader((ROOT / "results/v2/benchmark/table2_difficulty.csv").open())
                  if r['proxy'] == 'gold_patch_lines' and r['model'] != 'ALL']
    harness_rows = list(csv.DictReader((ROOT / "results/paper_revision_20261026/harness_patch_size_profiles.csv").open()))
    fig, axes = plt.subplots(2, 4, figsize=(6.7, 3.8))
    metrics = [('tool_calls_mean', 'Calls per run', 1), ('resolve_rate', 'Success (%)', 100),
               ('exact_repeat_rate', 'Exact repeats (%)', 100),
               ('same_object_repeat_rate', 'Target revisits (%)', 100)]
    colors = ['#185b83', '#c17932', '#618665']
    groups = [(model_rows, 'model', MODELS, ['Gemini', 'Luna', 'Terra']),
              (harness_rows, 'harness', ['mini-swe-agent', 'openhands', 'swe-agent'],
               ['mini-swe-agent', 'OpenHands', 'SWE-agent'])]
    for i, (rows, field, keys, names) in enumerate(groups):
        for j, (metric, title, multiplier) in enumerate(metrics):
            ax = axes[i,j]
            for key, name, color in zip(keys, names, colors):
                rr = sorted([r for r in rows if r[field] == key], key=lambda r:r['bin'])
                assert len(rr) == 4
                ax.plot(range(1,5), [float(r[metric])*multiplier for r in rr],
                        marker='o', markersize=3, lw=1.2, color=color, label=name)
            ax.set_xticks(range(1,5), ['Q1','Q2','Q3','Q4'], fontsize=6.5)
            ax.tick_params(axis='y', labelsize=6.5)
            ax.yaxis.grid(alpha=.16)
            ax.set_title(title, fontsize=8, pad=5)
            if metric != 'tool_calls_mean': ax.set_ylim(bottom=0)
            if j == 0: ax.set_ylabel('Models' if i == 0 else 'Harnesses',fontsize=8)
            if j == 0: ax.legend(fontsize=5.5,frameon=False,loc='best')
    fig.text(.5,.015,'Reference-patch size: Q1 smallest to Q4 largest (separate task sets by row)',
             ha='center',fontsize=7)
    fig.tight_layout(pad=.8,h_pad=1.5,w_pad=1,rect=(0,.04,1,1))
    fig.savefig(OUT/'patch_size_profiles.pdf',bbox_inches='tight')
    plt.close(fig)


def return_profiles():
    rows = list(csv.DictReader((ROOT / 'results/v2/task2/return_after_k_ci.csv').open()))
    fig, ax = plt.subplots(figsize=(3.25,2.35))
    for model, name, color, offset in zip(MODELS,['Gemini','Luna','Terra'],
                                        ['#185b83','#c17932','#618665'],[-.08,0,.08]):
        rr = [r for r in rows if r['model'] == model]
        x = [j+offset for j in range(4)]
        vals = [interval(r['non_distinct'])[0] for r in rr]
        ax.plot(x,vals,marker='o',lw=.9,markersize=3,color=color,label=name)
        for pos,val,row in zip(x,vals,rr):
            nums=interval(row['non_distinct'])
            if len(nums)==3: ax.errorbar(pos,val,yerr=[[val-nums[1]],[nums[2]-val]],
                                       color=color,capsize=2,lw=.65)
    ax.set_xticks(range(4),['1','2','3','4+'])
    ax.set_xlabel('Distinct targets visited before a return')
    ax.set_ylabel('Non-distinct contribution (%)')
    ax.set_ylim(-3,110)
    ax.yaxis.grid(alpha=.15)
    ax.legend(fontsize=6.5,frameon=False,ncol=3,loc='upper center')
    fig.tight_layout(pad=.7)
    fig.savefig(OUT/'return_profiles.pdf',bbox_inches='tight')
    plt.close(fig)


if __name__ == "__main__":
    verification()
    aggregate_patterns()
    new_comparisons()
    patch_size_profiles()
    return_profiles()
    print("Rendered saved patterns and the new descriptive comparisons.")
