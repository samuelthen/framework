"""Wide task-03 comparison with independent component-order scales.

Uses the same partial-review source for both systems. Contribution merging is
display-only. No annotations, costs, code states or outcomes are inferred here.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/worktrace-paired-mpl')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'worktrace'))
from worktrace.resources import ROLE_MARKERS
from worktrace.contributions import CONTRIBUTION_COLORS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base = ROOT / 'results/framework_one_hour_run_20261027_0230'
    inputs = [base / 'component_usage.csv', base / 'resource_coverage.csv',
              ROOT / 'results/followup_20261026/corrected_version_graphs.jsonl']
    with inputs[0].open() as f: components = list(csv.DictReader(f))
    with inputs[1].open() as f: costs = {r['run_id']: r for r in csv.DictReader(f)}
    graphs = {r['run_id']: r for r in (json.loads(s) for s in inputs[2].read_text().splitlines())}
    mapping = {'direct': 'direct', 'indirect': 'indirect', 'no_demonstrated': 'indirect',
               'non_direct': 'indirect', 'uncertain': 'uncertain'}
    args.out.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    fig, axes = plt.subplots(1, 2, figsize=(21, 8.3), sharey=True, facecolor='#FCFCFA')
    tables = []
    for ax, model in zip(axes, ['gemini-3.7-flash', 'gpt-5.6-luna']):
        group = [r for r in components if r['component_id'].startswith('03:')
                 and costs[r['run_id']]['model'] == model]
        group.sort(key=lambda r: tuple(int(s) for s in r['component_id'].split(':')[1][1:].split('.c')))
        rid = group[0]['run_id']; totals = costs[rid]
        xx = list(range(1, len(group) + 1))
        yy = [int(r['inferred_state_after_parent_call']) for r in group]
        assert len(group) == int(totals['components'])
        ax.plot(xx, yy, color='#A8B3BB', lw=1.5, zorder=1)
        for node in graphs[rid]['nodes']:
            if node.get('uncertain'):
                ax.axhspan(node['v'] - .3, node['v'] + .3, color='#E3E5E7', alpha=.5, zorder=0)
        for x, y, r in zip(xx, yy, group):
            displayed = mapping[r['contribution']]
            ax.scatter(x, y, s=82, marker=ROLE_MARKERS[r['role']],
                       color=CONTRIBUTION_COLORS[displayed], edgecolors='#FCFCFA', linewidths=.6,
                       alpha=.4 if r['execution_status'] == 'not_executed' else 1, zorder=3)
            tables.append(dict(component_id=r['component_id'], model=model, order=x,
                state_after_parent_call=y, role=r['role'], source_contribution=r['contribution'],
                display_contribution=displayed, input_tokens=r['input_tokens'],
                cached_input_tokens=r['cached_input_tokens'], output_tokens=r['output_tokens'],
                cost_usd=r['cost_usd'], attribution=r['attribution_method']))
        heading = 'Gemini 3.7 Flash' if model.startswith('gemini') else 'GPT-5.6 Luna'
        ax.set_title(f"{heading}  |  {len(group)} components · {totals['native_calls']} calls · {totals['responses']} responses",
                     fontsize=14, weight='bold', loc='left', pad=52)
        ax.text(0, 1.035,
                f"Input {int(totals['input_tokens']):,}  (cached {int(totals['cached_input_tokens']):,})\n"
                f"Output {int(totals['output_tokens']):,}  |  recorded run cost ${float(totals['run_cost_usd']):.6f}",
                transform=ax.transAxes, fontsize=11, color='#53616B', linespacing=1.5)
        ticks = sorted(set([1, *range(5, len(group) + 1, 5), len(group)]))
        ax.set(xlim=(.4, len(group) + .6), ylim=(-.4, 7.5), xticks=ticks,
               yticks=list(range(8)), yticklabels=[f'V{i}' for i in range(8)],
               xlabel=f'Component order (1–{len(group)})')
        ax.tick_params(labelsize=10)
        ax.grid(axis='y', color='#E0E5E8', lw=.8)
        for side in ['top', 'right']: ax.spines[side].set_visible(False)
    axes[0].set_ylabel('Inferred code state after parent call', fontsize=12)
    fig.suptitle('Task 03 · Gemini and GPT work progression', x=.055, ha='left', y=.98,
                 fontsize=22, weight='bold', color='#17252D')
    fig.text(.055, .92, 'Independent horizontal ranges: 54 versus 30 components. Version axis shared; higher state IDs do not mean better code.',
             fontsize=11, color='#53616B')
    fig.subplots_adjust(left=.055, right=.98, top=.72, bottom=.265, wspace=.09)
    roles = [Line2D([], [], marker=ROLE_MARKERS[r], ls='None', color='#43515B', markersize=8, label=r.title())
             for r in ['exploration', 'edit', 'verification', 'administration']]
    colors = [Line2D([], [], marker='o', ls='None', color=CONTRIBUTION_COLORS[r], markersize=8, label=r.title())
              for r in ['direct', 'indirect', 'uncertain']]
    fig.legend(handles=roles, title='Shape = action type', bbox_to_anchor=(.05, .20), loc='upper left',
               ncol=4, frameon=False, fontsize=11, title_fontsize=11)
    fig.legend(handles=colors, title='Color = contribution', bbox_to_anchor=(.64, .20), loc='upper left',
               ncol=3, frameon=False, fontsize=11, title_fontsize=11)
    fig.text(.055, .09, 'Indirect is a broad display group combining source indirect, no demonstrated contribution and legacy non-direct. Source annotations and scores are unchanged.',
             fontsize=10, color='#53616B')
    fig.text(.055, .052, 'Both panels use the same partial model-review source (5 reviewed cases per run). Compound-call intermediate states are unresolved; independent checkpoints are UNTESTED.',
             fontsize=10, color='#53616B')
    fig.text(.055, .015, 'Cached tokens are included in input. USD provenance differs: Gemini source price-map estimate; GPT harness-recorded. Shared-component costs remain allocated estimates.',
             fontsize=10, color='#53616B')
    for ext in ['png', 'pdf', 'svg']:
        path = args.out / f'task_03_gemini_gpt_merged.{ext}'
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        if ext == 'svg': path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines()) + '\n')
    plt.close(fig)
    with (args.out / 'component_display.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(tables[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(tables)
    manifest = dict(task_order=3, panels=['gemini-3.7-flash', 'gpt-5.6-luna'],
        x_ranges=[54, 30], shared_x=False, shared_y=True, display_mapping=mapping,
        source_annotations_changed=False, actual_new_evaluations=0,
        inputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(args.out / 'task_03_gemini_gpt_merged.png')


if __name__ == '__main__':
    main()
