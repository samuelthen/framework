"""Small saved-data demonstration: first two frozen evaluation pairs.

Optional local raw shards enable response accounting. No task commands, model
jobs, downloads or new labels are executed. Inferred states are not checkpoints.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/worktrace-quickcheck-mpl')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'worktrace'))
from worktrace.resources import ROLE_MARKERS, CONTRIBUTION_COLORS
from worktrace.contributions import (CONTRIBUTION_LABELS, apply_reviews, contribution_score,
                                    review_sample)


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jetbrains-shard', type=Path, action='append', default=[])
    parser.add_argument('--contribution-review', type=Path,
                        help='Additive completed/pending four-label review overlay (at most the fixed 20 cases)')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    paths = dict(sample=ROOT / 'results/one_day_precision_20261026/sample_manifest.csv',
        labels=ROOT / 'results/precision_validation_20261026/reconciled_component_annotations.jsonl',
        inventory=ROOT / 'results/framework_validation_20261027/component_identity_join.csv',
        runs=ROOT / 'results/framework_validation_20261027/pilot_inventory_by_run.csv',
        graphs=ROOT / 'results/followup_20261026/corrected_version_graphs.jsonl')
    with paths['sample'].open() as f:
        sample = list(csv.DictReader(f))
    orders = sorted({int(r['order']) for r in sample if r['split'] == 'evaluation'})[:2]
    selected = [r for r in sample if r['split'] == 'evaluation' and int(r['order']) in orders]
    assert len(selected) == 4 and len({r['task_id'] for r in selected}) == 2
    ids = {r['run_id'] for r in selected}
    mapping = {(int(r['order']), r['model']): r for r in selected}
    with paths['runs'].open() as f:
        runs = {r['run_id']: r for r in csv.DictReader(f) if r['run_id'] in ids}
    with paths['inventory'].open() as f:
        joined = {r['component_id']: r for r in csv.DictReader(f) if r['run_id'] in ids}
    labels = [r for r in jsonl(paths['labels']) if int(r['order']) in orders]
    assert set(joined) == {r['component_id'] for r in labels}
    template = review_sample(labels)
    template_path = args.out / 'contribution_review_template.jsonl'
    if not template_path.exists():
        template_path.write_text(''.join(json.dumps(r) + '\n' for r in template))
    elif jsonl(template_path) != template:
        raise ValueError('Existing review template differs; use a fresh output directory or a separate review overlay')
    reviews = jsonl(args.contribution_review) if args.contribution_review else []
    if set(r['component_id'] for r in reviews) - {r['component_id'] for r in template}:
        raise ValueError('Review exceeds the fixed one-hour review sample')
    labels = apply_reviews(labels, reviews)
    packet = ['# Four-label review packet', '',
        'Up to 20 enriched cases: three legacy non-direct cases plus direct/uncertain controls per run.',
        'Read full requirements, final patch and trajectory first. Do not copy the old judgment as evidence.',
        'Complete a COPY of contribution_review_template.jsonl; preserve the pending template.', '',
        'Allowed labels: direct, indirect, no_demonstrated, uncertain. Indirect requires evidence that the result guided a later performed direct component, with its ID.',
        'No demonstrated means no supported observed contribution, not proof of zero causal effect. Missing context stays uncertain.', '']
    byid = {r['component_id']: r for r in labels}
    for entry in template:
        c = byid[entry['component_id']]
        sources = sorted((ROOT / 'results/one_day_precision_20261026/packets').glob(f"{int(c['order']):02d}_*.md"))
        packet += [f"## {c['component_id']} — {c['role']} / archived {c['archived_contribution_label']}", '',
            'Read full source: ' + ', '.join(str(p.relative_to(ROOT)) for p in sources), '',
            '```bash', c['command'], '```', '']
    (args.out / 'contribution_review_packet.md').write_text('\n'.join(packet).rstrip() + '\n')
    graphs = {r['run_id']: r for r in jsonl(paths['graphs']) if r['run_id'] in ids}
    write_csv(args.out / 'sample.csv', selected)
    (args.out / 'components.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in labels))
    write_csv(args.out / 'component_identity_join.csv', list(joined.values()))
    usage = {}
    if args.jetbrains_shard:
        command = [sys.executable, str(ROOT / 'scripts/followup/component_resources.py')]
        for path in args.jetbrains_shard:
            command += ['--jetbrains-shard', str(path)]
        command += ['--components', str(args.out / 'components.jsonl'), '--out', str(args.out / 'resources')]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        (args.out / 'resource_export.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('Resource export failed; inspect resource_export.log')
        usage = {r['component_id']: r for r in jsonl(args.out / 'resources/component_allocations.jsonl') if r['component_id']}

    per_role, reviewed_subset, examples = [], [], []
    for item in selected:
        group = [r for r in labels if joined[r['component_id']]['run_id'] == item['run_id']]
        for role in ['exploration', 'verification', 'edit', 'administration']:
            per_role.append(dict(order=item['order'], run_id=item['run_id'], model=item['model'], role=role,
                **contribution_score([r for r in group if r['role'] == role])))
            reviewed_subset.append(dict(order=item['order'], run_id=item['run_id'], model=item['model'], role=role,
                **contribution_score([r for r in group if r['role'] == role and r['contribution_review_status'] == 'reviewed'])))
        for contribution in [*CONTRIBUTION_LABELS, 'non_direct']:
            example = next((r for r in group if r['role'] == 'verification'
                and r['contribution_label'] == contribution and r['execution_status'] == 'executed'), None)
            if example is None:
                example = next((r for r in group if r['contribution_label'] == contribution
                                and r['execution_status'] == 'executed'), None)
            if example:
                cost = usage.get(example['component_id'])
                examples.append(dict(example, run_id=item['run_id'], model=item['model'],
                    input_tokens=cost['usage']['input_tokens'] if cost else None,
                    cached_input_tokens=cost['usage']['cached_input_tokens'] if cost else None,
                    output_tokens=cost['usage']['output_tokens'] if cost else None,
                    attribution=cost['allocation_method'] if cost else 'unavailable'))
    write_csv(args.out / 'role_precision_by_run.csv', per_role)
    write_csv(args.out / 'reviewed_subset_by_run.csv', reviewed_subset)
    (args.out / 'examples.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in examples))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    for order in orders:
        fig, axes = plt.subplots(1, 2, figsize=(15, 7), sharey=True, facecolor='#FCFCFA')
        max_version = max(max(n['v'] for n in graphs[mapping[(order, m)]['run_id']]['nodes'])
                          for m in ['gemini-3.7-flash', 'gpt-5.6-luna'])
        max_components = max(sum(joined[r['component_id']]['run_id'] == mapping[(order, m)]['run_id']
                                 for r in labels) for m in ['gemini-3.7-flash', 'gpt-5.6-luna'])
        for ax, model in zip(axes, ['gemini-3.7-flash', 'gpt-5.6-luna']):
            item = mapping[(order, model)]; rid = item['run_id']; run = runs[rid]; graph = graphs[rid]
            group = sorted([r for r in labels if joined[r['component_id']]['run_id'] == rid],
                           key=lambda r: (r['action_index'], r['component_index']))
            x = list(range(1, len(group) + 1))
            y = [int(joined[r['component_id']]['inferred_state_after_native_call']) for r in group]
            ax.plot(x, y, color='#BAC3C9', lw=1.1, zorder=1)
            for node in graph['nodes']:
                if node.get('uncertain'):
                    ax.axhspan(node['v'] - .3, node['v'] + .3, color='#E3E5E7', alpha=.5, zorder=0)
            for px, py, component in zip(x, y, group):
                ax.scatter(px, py, marker=ROLE_MARKERS[component['role']], s=56,
                    c=CONTRIBUTION_COLORS[component['contribution_label']], edgecolors='#FCFCFA',
                    linewidths=.45, alpha=.4 if component['execution_status'] == 'not_executed' else 1, zorder=3)
            ax.set_title(f"{model}\n{len(group)} components | {run['native_calls']} calls | {int(run['run_output_tokens']):,} run output tokens",
                         fontsize=11, loc='left', pad=14)
            ax.set(xlabel='Component order', xlim=(0, max_components + 2), ylim=(-.5, max_version + .6),
                   yticks=list(range(max_version + 1)), yticklabels=[f'V{i}' for i in range(max_version + 1)])
            ax.grid(axis='y', color='#E3E7E9', lw=.7)
            for s in ['top', 'right']: ax.spines[s].set_visible(False)
            evidence = [e for e in examples if e['run_id'] == rid]
            for j, e in enumerate(evidence):
                k = next(i for i, r in enumerate(group) if r['component_id'] == e['component_id'])
                ax.annotate(e['component_id'], (x[k], y[k]), xytext=(0, 22 + 17 * j), textcoords='offset points',
                            ha='center', fontsize=8, arrowprops=dict(arrowstyle='-', color='#84919A'))
        axes[0].set_ylabel('Inferred state AFTER parent native call')
        fig.suptitle(f'Archived example: evaluation task {order:02d} — {selected[0]["task_id"].split("__")[0].split("_")[-1]}',
                     x=.07, ha='left', fontsize=17, weight='bold')
        fig.text(.07, .885, 'REAL ARCHIVED ACTIONS / MODEL-CODED LABELS  |  Intermediate final-test outcomes: UNTESTED', fontsize=10, color='#53616B')
        fig.subplots_adjust(left=.07, right=.98, top=.77, bottom=.30, wspace=.12)
        role_handles = [Line2D([], [], marker=ROLE_MARKERS[role], ls='None', color='#43515B',
                               markersize=7, label=role.title())
                        for role in ['exploration', 'edit', 'verification', 'administration']]
        names = {'direct': 'Direct', 'indirect': 'Indirect', 'no_demonstrated': 'No demonstrated',
                 'uncertain': 'Uncertain', 'non_direct': 'Legacy unsplit'}
        present = {r['contribution_label'] for r in labels if int(r['order']) == order}
        contribution_handles = [Line2D([], [], marker='o', ls='None', color=CONTRIBUTION_COLORS[label],
                                      markersize=7, label=names[label])
                                for label in [*CONTRIBUTION_LABELS, 'non_direct'] if label in present]
        fig.legend(handles=role_handles, title='Shape = action type', loc='upper left',
                   bbox_to_anchor=(.065, .235), ncol=4, frameon=False, fontsize=10,
                   title_fontsize=10, handletextpad=.5, columnspacing=1.8)
        fig.legend(handles=contribution_handles, title='Color = contribution', loc='upper left',
                   bbox_to_anchor=(.60, .235), ncol=3, frameon=False, fontsize=10,
                   title_fontsize=10, handletextpad=.5, columnspacing=1.8)
        fig.text(.07, .08, 'States follow parent calls; gray bands mark uncertain inferred states. Execution timing inside compound calls is unresolved.', fontsize=9)
        fig.text(.07, .04, 'Tokens above are whole-run totals; component usage is unknown without raw responses. Faint symbols = known unexecuted candidates.', fontsize=9)
        for ext in ['png', 'pdf', 'svg']:
            path = args.out / f'task_{order:02d}_progression.{ext}'
            fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
            if ext == 'svg': path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines()) + '\n')
        plt.close(fig)

    report = ['# One-hour framework smoke study', '',
        'Real archived examples and an executable reduced sample. This is development evidence, not a model ranking.', '',
        f'Selection: first two frozen evaluation orders {orders}; four runs. No selection by observed redundancy.', '',
        '| Task order | Model | Components | Native calls | Run input | Cached input | Run output |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for item in selected:
        run = runs[item['run_id']]
        report.append(f"| {item['order']} | {item['model']} | {run['components']} | {run['native_calls']} | {int(run['run_input_tokens']):,} | {int(run['run_cached_input_tokens']):,} | {int(run['run_output_tokens']):,} |")
    report += ['', 'Input/cache/output are separate archived run fields. These amounts do not attribute cost to roles or components.', '',
        '## Role contribution bounds', '',
        'Known unexecuted candidates are excluded; uncertain execution remains as in the archived convention. Bounds reflect uncertain labels, not confidence intervals.', '',
        'Legacy non-direct remains unsplit between indirect and no demonstrated contribution. Unreviewed labels retain archived provenance; these are partial-review bounds, not a fully validated four-label result.', '',
        '| Task | Model | Role | Included | Direct | Indirect | No demonstrated | Uncertain | Legacy unsplit | Reviewed | Direct precision bounds |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for r in per_role:
        if r['role'] not in ['exploration', 'verification']: continue
        bounds = f"{r['lower']:.1%}–{r['upper']:.1%}" if r['included'] else 'undefined'
        report.append(f"| {r['order']} | {r['model']} | {r['role']} | {r['included']} | {r['direct']} | {r['indirect']} | {r['no_demonstrated']} | {r['uncertain']} | {r['legacy_non_direct']} | {r['reviewed']} | {bounds} |")
    reviewed_count = sum(r['contribution_review_status'] == 'reviewed' for r in labels)
    report += ['', f'Review packet: {len(template)} cases prepared; {reviewed_count} judgments completed.',
               'The enriched reviewed subset is reported separately in reviewed_subset_by_run.csv. It is not a population estimate.', '',
               '## Trajectory examples', '']
    for order in orders:
        report += [f'![Task {order} inferred progression](task_{order:02d}_progression.png)', '']
    report += ['## Component examples', '',
        'First executed verification example per available label/run, falling back to another action type if needed. Labels not observed are not fabricated. Legacy non-direct is explicitly unsplit. Qualitative illustrations, not prevalence estimates. Model reviews are not human ground truth.', '']
    for e in examples:
        report += [f"### {e['component_id']} — {e['model']}, {e['contribution_label']}", '',
                   '```bash', e['command'], '```', '', f"Archived reason: {e.get('reason', 'unknown')}", '',
                   f"Archived evidence: {e.get('evidence', 'unknown')}", '',
                   f"Component usage: input={e['input_tokens']}, cache={e['cached_input_tokens']}, output={e['output_tokens']}; attribution={e['attribution']}.", '']
        if e['contribution_review_status'] == 'reviewed':
            review = e['contribution_review']
            report += [f"Original label: {e['archived_contribution_label']}. Reviewed label: {e['contribution_label']}.", '',
                       f"Review evidence: {review['evidence']}", '',
                       f"Supporting components: {review.get('supporting_component_ids', [])}. Reviewer: {review['reviewer_name']} ({review['reviewer_type']}).", '']
    report += ['## Pipeline coverage', '',
        '- Real source/component/response identity joins: checked on this subset.',
        '- Existing labels preserved; optional four-label review is additive, with reviewer/evidence provenance. No independent human accuracy established.',
        '- Response resource accounting: ' + ('exported; inspect reconciliation and usage coverage.' if usage else 'not run empirically; local raw usage absent.'),
        '- Intermediate complete snapshots and final-test outcomes: not evaluated by this script.',
        '- Actual post-pass expenditure: unresolved until evaluated checkpoints and response usage are joined.',
        '- Synthetic accounting CLI tests pass separately; they cannot fill the missing empirical stages.', '',
        'Use CODEX_FRAMEWORK_ONE_HOUR.md to finish bounded raw-resource and checkpoint stages on the data machine.']
    (args.out / 'RESULTS.md').write_text('\n'.join(report) + '\n')
    manifest = dict(selection='first two existing evaluation orders; not outcome-pattern selected', orders=orders,
        tasks=2, runs=4, components=len(labels), native_calls=sum(int(runs[rid]['native_calls']) for rid in ids),
        native_response_ids=len({r['response_id'] for r in joined.values()}),
        real_response_usage_export_attempted=bool(args.jetbrains_shard), checkpoint_evaluations=0,
        complete_empirical_pipeline=False, actual_new_model_calls=0, source_labels_changed=False,
        contribution_rubric='four-label v2; non_direct is unresolved legacy metadata, not no_demonstrated',
        review_cases_prepared=len(template), reviewed_components=reviewed_count,
        review_input_sha256=sha(args.contribution_review) if args.contribution_review else None,
        remaining_legacy_non_direct=sum(r['contribution_label'] == 'non_direct' for r in labels),
        pipeline_stages=dict(identity_join='real-data checked',
                             contribution='additive reviews applied; inspect provenance; human accuracy unresolved' if reviewed_count else 'archived labels preserved; 20-case v2 packet pending',
                             response_accounting='export attempted; inspect coverage' if args.jetbrains_shard else 'synthetic CLI tests only; empirical usage unavailable',
                             state_progression='inferred native-call states; not complete snapshots',
                             checkpoint_outcomes='not evaluated', post_pass_expenditure='unresolved',
                             examples='real archived sources; no synthetic costs or PASS markers'),
        elapsed_seconds=round(time.monotonic() - started, 3),
        source_hashes={k:sha(p) for k, p in paths.items()})
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
