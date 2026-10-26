"""Small saved-data demonstration: first two frozen evaluation pairs.

Optional local raw shards enable response accounting. No task commands, model
jobs, downloads or new labels are executed. Inferred states are not checkpoints.
"""
import argparse
from collections import Counter
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
from worktrace.resources import ROLE_COLORS, CONTRIBUTION_COLORS


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

    per_role, examples = [], []
    for item in selected:
        group = [r for r in labels if joined[r['component_id']]['run_id'] == item['run_id']]
        for role in ['exploration', 'verification', 'edit', 'administration']:
            included = [r for r in group if r['role'] == role and r['execution_status'] != 'not_executed']
            counts = Counter(r['contribution_label'] for r in included)
            n, d, u = len(included), counts['direct'], counts['uncertain']
            per_role.append(dict(order=item['order'], run_id=item['run_id'], model=item['model'], role=role,
                included=n, direct=d, non_direct=counts['non_direct'], uncertain=u,
                lower=d / n if n else None, upper=(d + u) / n if n else None))
        for contribution in ['direct', 'non_direct']:
            example = next((r for r in group if r['role'] == 'verification'
                and r['contribution_label'] == contribution and r['execution_status'] == 'executed'), None)
            if example:
                cost = usage.get(example['component_id'])
                examples.append(dict(example, run_id=item['run_id'], model=item['model'],
                    input_tokens=cost['usage']['input_tokens'] if cost else None,
                    cached_input_tokens=cost['usage']['cached_input_tokens'] if cost else None,
                    output_tokens=cost['usage']['output_tokens'] if cost else None,
                    attribution=cost['allocation_method'] if cost else 'unavailable'))
    write_csv(args.out / 'role_precision_by_run.csv', per_role)
    (args.out / 'examples.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in examples))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
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
                ax.scatter(px, py, marker='D' if component['role'] == 'edit' else 'o', s=44,
                    c=ROLE_COLORS[component['role']], edgecolors=CONTRIBUTION_COLORS[component['contribution_label']],
                    linewidths=1.8, alpha=.45 if component['execution_status'] == 'not_executed' else 1, zorder=3)
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
        fig.subplots_adjust(left=.07, right=.98, top=.77, bottom=.26, wspace=.12)
        fig.text(.07, .17, 'Fill: blue exploration, purple edit, teal verification, gray administration. Diamond = edit.', fontsize=10)
        fig.text(.07, .125, 'Border: green direct, orange non-direct, gray uncertain. Labels are archived model judgments; no new annotation.', fontsize=10)
        fig.text(.07, .08, 'States follow parent calls; gray bands mark uncertain inferred states. Execution timing inside compound calls is unresolved.', fontsize=9)
        fig.text(.07, .04, 'Token amounts above are whole-run totals. Component input/cache/output remain unknown unless actual response usage is recovered.', fontsize=9)
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
        '| Task | Model | Role | Included | Direct | Non-direct | Uncertain | Precision bounds |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | --- |']
    for r in per_role:
        if r['role'] not in ['exploration', 'verification']: continue
        bounds = f"{r['lower']:.1%}–{r['upper']:.1%}" if r['included'] else 'undefined'
        report.append(f"| {r['order']} | {r['model']} | {r['role']} | {r['included']} | {r['direct']} | {r['non_direct']} | {r['uncertain']} | {bounds} |")
    report += ['', '## Trajectory examples', '']
    for order in orders:
        report += [f'![Task {order} inferred progression](task_{order:02d}_progression.png)', '']
    report += ['## Component examples', '',
        'First executed direct and non-direct verification examples per selected run. Qualitative illustrations, not prevalence estimates. The same-family model reviews are not human ground truth.', '']
    for e in examples:
        report += [f"### {e['component_id']} — {e['model']}, {e['contribution_label']}", '',
                   '```bash', e['command'], '```', '', f"Archived reason: {e.get('reason', 'unknown')}", '',
                   f"Archived evidence: {e.get('evidence', 'unknown')}", '',
                   f"Component usage: input={e['input_tokens']}, cache={e['cached_input_tokens']}, output={e['output_tokens']}; attribution={e['attribution']}.", '']
    report += ['## Pipeline coverage', '',
        '- Real source/component/response identity joins: checked on this subset.',
        '- Existing classification and contribution labels: reused, no independent semantic validation.',
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
        complete_empirical_pipeline=False, actual_new_model_calls=0, labels_changed=False,
        pipeline_stages=dict(identity_join='real-data checked',
                             contribution='archived model labels reused; human accuracy unresolved',
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
