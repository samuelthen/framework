"""Render real Luna trajectories with once-per-response cost headings.

Alternating bands group chronological components by generating response. Marker
shape and color keep their action/contribution meanings. No new evaluations,
labels, price estimates or component-cost measurements are produced.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/worktrace-cost-band-mpl')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'worktrace'))
from worktrace.resources import ROLE_MARKERS
from worktrace.contributions import CONTRIBUTION_COLORS


def apply_reviewed_components(components, reviewed):
    """Apply a complete reviewed-run view without changing identity or costs."""
    indexed = {r['component_id']: r for r in components}
    if len(indexed) != len(components) or len({r['component_id'] for r in reviewed}) != len(reviewed):
        raise ValueError('Duplicate component IDs')
    selected_runs = {r['run_id'] for r in reviewed}
    expected = {r['component_id'] for r in components if r['run_id'] in selected_runs}
    if {r['component_id'] for r in reviewed} != expected:
        raise ValueError('Supply complete reviewed runs with known component IDs')
    result = {cid: dict(row) for cid, row in indexed.items()}
    for row in reviewed:
        old = indexed[row['component_id']]
        if any(row.get(k) != old.get(k) for k in ['run_id', 'response_id', 'role', 'execution_status']):
            raise ValueError('Review view must preserve identity, roles and execution')
        if row.get('contribution_review_status') != 'reviewed' or row.get('contribution_label') not in {
                'direct', 'indirect', 'no_demonstrated', 'uncertain'}:
            raise ValueError('Only completed four-label contribution reviews are accepted')
        result[row['component_id']]['contribution'] = row['contribution_label']
        result[row['component_id']]['review_status'] = 'reviewed'
    return [result[r['component_id']] for r in components]


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def token(value):
    return 'NA' if value is None else f'{value:,.0f}'


def money(value):
    return 'USD unavailable' if value is None else f'${value:.6f}'


def percentage(value, total):
    return None if value is None or total is None or total <= 0 else 100 * value / total


def percent_label(value):
    return 'NA' if value is None else f'{value:.1f}%'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=ROOT / 'results/framework_one_hour_run_20261027_0230')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contribution-view', choices=['merged', 'detailed'], default='merged',
                        help='Merged displays indirect/no-demonstrated/legacy non-direct together as Indirect; source labels are preserved')
    parser.add_argument('--task-order', type=int, choices=[3, 4], action='append',
                        help='Render only these task orders; default is both')
    parser.add_argument('--reviewed-components', type=Path,
                        help='Complete reviewed-run components; overlay labels without changing resources')
    parser.add_argument('--contribution-caption', help='Explicit scheme note for an alternative contribution view')
    args = parser.parse_args()
    inputs = [args.run_dir / 'component_usage.csv', args.run_dir / 'reviewed/resources/response_usage.jsonl',
              args.run_dir / 'resource_coverage.csv']
    with inputs[0].open() as stream:
        components = list(csv.DictReader(stream))
    if args.reviewed_components:
        args.reviewed_components = args.reviewed_components.resolve()
        components = apply_reviewed_components(components, read_jsonl(args.reviewed_components))
        inputs.append(args.reviewed_components)
    responses = read_jsonl(inputs[1])
    ledger = {r['response_id']: r for r in responses}
    assert len(ledger) == len(responses), 'Duplicate response ID'
    with inputs[2].open() as stream:
        coverage = {r['run_id']: r for r in csv.DictReader(stream)}
    args.out.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    names = {'direct': 'Direct', 'indirect': 'Indirect', 'no_demonstrated': 'No demonstrated',
             'uncertain': 'Uncertain', 'non_direct': 'Legacy unsplit'}
    display_map = {label: ('indirect' if args.contribution_view == 'merged'
                            and label in {'indirect', 'no_demonstrated', 'non_direct'} else label)
                   for label in CONTRIBUTION_COLORS}
    band_rows, display_rows = [], []
    orders = sorted(set(args.task_order or [3, 4]))
    plotted_labels = {}
    for order in orders:
        group = [r for r in components if ':luna:' in r['run_id'] and r['component_id'].startswith(f'{order:02d}:')]
        assert group, f'Missing Luna task {order}'
        plotted_labels[str(order)] = {label: sum(c['contribution'] == label for c in group)
                                     for label in names}
        # The component CSV retains the source chronology used by the reviewed plot.
        group.sort(key=lambda r: tuple(int(s) for s in r['component_id'].split(':')[1][1:].split('.c')))
        rid = group[0]['run_id']
        run_responses = sorted((r for r in responses if r['run_id'] == rid), key=lambda r: r['turn_index'])
        by_response = {}
        for x, component in enumerate(group, 1):
            by_response.setdefault(component['response_id'], []).append((x, component))
        assert set(by_response) == {r['response_id'] for r in run_responses}, 'No-tool response needs a separate display slot'
        assert list(by_response) == [r['response_id'] for r in run_responses], 'Response groups are not chronological'
        for metric in ['input_tokens', 'cached_input_tokens', 'output_tokens']:
            values = [r['usage'][metric] for r in run_responses]
            assert all(v is not None for v in values)
            assert math.isclose(math.fsum(values), float(coverage[rid][metric]), rel_tol=1e-12)
        usd = [r['usage']['cost_usd'] for r in run_responses]
        total_usd = math.fsum(usd) if all(v is not None for v in usd) else None
        if total_usd is not None:
            assert math.isclose(total_usd, float(coverage[rid]['run_cost_usd']), rel_tol=1e-12)

        fig = plt.figure(figsize=(20, 9), facecolor='#FCFCFA')
        gs = fig.add_gridspec(2, 1, height_ratios=[2.15, 3.7], hspace=0,
                             left=.055, right=.985, bottom=.245, top=.86)
        head = fig.add_subplot(gs[0]); ax = fig.add_subplot(gs[1], sharex=head)
        fig.text(.055, .95, f'Luna · task {order:02d} — response costs over work progression',
                 fontsize=21, weight='bold', color='#17252D')
        totals = coverage[rid]
        fig.text(.055, .905,
            f"Recorded totals: input {int(totals['input_tokens']):,} (cached {int(totals['cached_input_tokens']):,})"
            f"  |  output {int(totals['output_tokens']):,}  |  USD {f'{total_usd:.8f}' if total_usd is not None else 'unavailable'}"
            f"  |  {len(run_responses)} responses / {len(group)} components",
            fontsize=11, color='#53616B')
        for i, response in enumerate(run_responses):
            points = by_response[response['response_id']]
            lo, hi = points[0][0] - .5, points[-1][0] + .5
            assert [x for x, _ in points] == list(range(points[0][0], points[-1][0] + 1))
            shade = '#ECF1F5' if i % 2 == 0 else '#FAFAF8'
            for axis in [head, ax]:
                axis.axvspan(lo, hi, color=shade, zorder=0)
                axis.axvline(lo, color='#CDD6DD', lw=.7, zorder=1)
            center = (lo + hi) / 2
            usage = response['usage']
            shares = {field: percentage(usage[field], float(totals[field]))
                      for field in ['input_tokens', 'cached_input_tokens', 'output_tokens']}
            cost_share = percentage(usage['cost_usd'], total_usd)
            head.text(center, .96, f'R{i + 1}', ha='center', va='top', fontsize=10, weight='bold', color='#17252D')
            head.text(center, .84, money(usage['cost_usd']), ha='center', va='top',
                      fontsize=8.2 if hi - lo <= 2 else 9.5, weight='bold', color='#17252D')
            head.text(center, .735, percent_label(cost_share), ha='center', va='top',
                      fontsize=9.5, weight='bold', color='#17252D')
            for y, prefix, field in [(.60, 'I', 'input_tokens'), (.38, 'C', 'cached_input_tokens'), (.16, 'O', 'output_tokens')]:
                head.text(center, y, f'{prefix} {token(usage[field])}\n{percent_label(shares[field])} of {prefix}',
                          ha='center', va='top', fontsize=8.5, linespacing=1.35, color='#43515B')
            band_rows.append(dict(task_order=order, run_id=rid, response_id=response['response_id'],
                displayed_response=f'R{i+1}', component_start=points[0][0], component_end=points[-1][0],
                component_ids='|'.join(c['component_id'] for _, c in points),
                input_tokens=usage['input_tokens'], cached_input_tokens=usage['cached_input_tokens'],
                output_tokens=usage['output_tokens'], cost_usd=usage['cost_usd'],
                cost_percent_of_run=cost_share, input_percent_of_run=shares['input_tokens'],
                cached_input_percent_of_run=shares['cached_input_tokens'], output_percent_of_run=shares['output_tokens'],
                cost_provenance=response['cost_provenance'], attribution='whole recorded response, counted once'))

        xx = list(range(1, len(group) + 1))
        yy = [int(r['inferred_state_after_parent_call']) for r in group]
        ax.plot(xx, yy, color='#8A969E', lw=1.5, zorder=2)
        for x, y, component in zip(xx, yy, group):
            displayed = display_map[component['contribution']]
            ax.scatter(x, y, s=90, marker=ROLE_MARKERS[component['role']],
                       color=CONTRIBUTION_COLORS[displayed], edgecolors='#FCFCFA',
                       linewidths=.7, alpha=.4 if component['execution_status'] == 'not_executed' else 1, zorder=4)
            display_rows.append(dict(component_id=component['component_id'],
                                     source_contribution=component['contribution'], display_contribution=displayed))
        for component_id in [f'{order:02d}:Y008.c0' if order == 3 else f'{order:02d}:Y012.c0']:
            index = next((i for i, c in enumerate(group) if c['component_id'] == component_id), None)
            if index is not None:
                ax.annotate('First saved-patch inspection\n' + component_id, (xx[index], yy[index]),
                            xytext=(0, 30), textcoords='offset points', ha='center', fontsize=9,
                            arrowprops=dict(arrowstyle='-', color='#84919A'))
        head.set(ylim=(0, 1), xlim=(.5, len(group) + .5))
        head.axis('off')
        ymax = max(yy)
        ax.set(ylim=(-.25, ymax + .7), xlim=(.5, len(group) + .5), xticks=xx,
               yticks=list(range(ymax + 1)), yticklabels=[f'V{i}' for i in range(ymax + 1)],
               xlabel='Component order — alternating bands group components from the same response',
               ylabel='Inferred state AFTER parent native call')
        ax.tick_params(axis='x', labelsize=8, length=3)
        ax.tick_params(axis='y', labelsize=11)
        ax.grid(axis='y', color='#D6DEE4', lw=.8)
        for side in ['top', 'right']:
            ax.spines[side].set_visible(False)
        role_handles = [Line2D([], [], marker=ROLE_MARKERS[r], ls='None', color='#43515B', markersize=8, label=r.title())
                        for r in ['exploration', 'edit', 'verification', 'administration']]
        present = {display_map[c['contribution']] for c in group}
        contribution_handles = [Line2D([], [], marker='o', ls='None', color=CONTRIBUTION_COLORS[r], markersize=8, label=names[r])
                                for r in CONTRIBUTION_COLORS if r in present]
        fig.legend(handles=role_handles, title='Shape = action type', loc='upper left', bbox_to_anchor=(.05, .20),
                   ncol=4, frameon=False, fontsize=10, title_fontsize=10)
        fig.legend(handles=contribution_handles, title='Color = contribution', loc='upper left', bbox_to_anchor=(.60, .20),
                   ncol=2, frameon=False, fontsize=10, title_fontsize=10)
        fig.text(.055, .075, 'Each band is one response. Bold % = share of run USD. I/C/O percentages use their respective run token totals; C is included in I. Values rounded; exact shares in CSV.',
                 fontsize=10, color='#53616B')
        fig.text(.055, .038, 'USD is harness-recorded. Shared component costs remain allocated estimates. Compound-call internal states are unresolved; independent checkpoints are UNTESTED.',
                 fontsize=10, color='#53616B')
        if args.contribution_caption:
            fig.text(.055, .012, args.contribution_caption, fontsize=9, color='#53616B')
        elif args.contribution_view == 'merged':
            fig.text(.055, .012, 'Display grouping: Indirect combines source indirect, no demonstrated contribution and legacy non-direct; original annotations and scores are preserved.',
                     fontsize=9, color='#53616B')
        for ext in ['png', 'pdf', 'svg']:
            path = args.out / f'luna_task_{order:02d}_response_costs.{ext}'
            fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
            if ext == 'svg':
                path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines()) + '\n')
        plt.close(fig)
    for order in orders:
        rows = [r for r in band_rows if r['task_order'] == order]
        for field in ['cost_percent_of_run', 'input_percent_of_run', 'cached_input_percent_of_run', 'output_percent_of_run']:
            shares = [r[field] for r in rows]
            if all(s is not None for s in shares):
                assert math.isclose(math.fsum(shares), 100, abs_tol=1e-9), (order, field)
    with (args.out / 'response_band_totals.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(band_rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(band_rows)
    with (args.out / 'component_display_labels.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(display_rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(display_rows)
    manifest = dict(method='alternating response bands on unchanged component-order axis; recorded response costs shown once',
                    model='gpt-5.6-luna', tasks=orders, bands=len(band_rows),
                    contribution_view=args.contribution_view, contribution_display_mapping=display_map,
                    source_annotations_changed=False, precision_scores_changed=False,
                    percentage_denominators=dict(cost_percent_of_run='complete recorded run USD',
                        input_percent_of_run='run input tokens', cached_input_percent_of_run='run cached-input tokens',
                        output_percent_of_run='run output tokens'),
                    contribution_caption=args.contribution_caption,
                    contribution_counts=plotted_labels,
                    imported_reviewed_components=sum(c.get('review_status') == 'reviewed' for c in components
                                                     if ':luna:' in c['run_id'] and int(c['component_id'].split(':')[0]) in orders),
                    new_labels=0, new_agent_runs=0, checkpoint_evaluations=0,
                    source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
