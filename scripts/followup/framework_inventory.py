"""Check pilot identity joins on saved data, without inventing response usage.

No model calls, task execution, downloads, or annotation changes. Requires pyarrow.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    paths = dict(
        components=ROOT / 'results/precision_validation_20261026/components.jsonl',
        labels=ROOT / 'results/precision_validation_20261026/reconciled_component_annotations.jsonl',
        key=ROOT / 'results/one_day_precision_20261026/packets/blinding_key.csv',
        runs=ROOT / 'data/runs.parquet', operations=ROOT / 'data/ops_compact.parquet',
        graphs=ROOT / 'results/followup_20261026/corrected_version_graphs.jsonl')
    original, labeled = read_jsonl(paths['components']), read_jsonl(paths['labels'])
    def index(records):
        result = {r['component_id']: r for r in records}
        if len(result) != len(records):
            raise ValueError('Duplicate component IDs')
        return result
    source, annotated = index(original), index(labeled)
    if source.keys() != annotated.keys():
        raise ValueError('Labeled components do not cover the candidate inventory')
    with paths['key'].open() as handle:
        key = {(int(r['order']), r['label']): r for r in csv.DictReader(handle)}
    selected = {key[(int(c['order']), c['blinded_label'])]['run_id'] for c in labeled}
    runs = {r['run_id']: r for r in pq.read_table(paths['runs']).to_pylist() if r['run_id'] in selected}
    if runs.keys() != selected:
        raise ValueError('Pilot run missing from saved run table')
    ops = pq.read_table(paths['operations'],
        columns=['run_id', 'op_id', 'turn_id', 'op_index'],
        filters=[('run_id', 'in', sorted(selected))]).to_pylist()
    op_index = {(r['run_id'], r['op_index']): r for r in ops}
    if len(op_index) != len(ops):
        raise ValueError('Duplicate native operation identities')
    graphs = {g['run_id']: g for g in read_jsonl(paths['graphs'])}
    joined, per_run, covered = [], defaultdict(list), set()
    for c in labeled:
        for field in ['order', 'blinded_label', 'action_index', 'component_index', 'parent_op_id']:
            if c[field] != source[c['component_id']][field]:
                raise ValueError(f'Component source identity changed: {field}')
        mapping = key[(int(c['order']), c['blinded_label'])]
        rid, position = mapping['run_id'], int(c['action_index'])
        operation = op_index[(rid, position)]
        covered.add((rid, position))
        graph = graphs.get(rid)
        states = graph['op_version'] if graph else []
        row = dict(component_id=c['component_id'], run_id=rid, task_id=mapping['task_id'],
                   model=mapping['model'], native_op_id=operation['op_id'],
                   response_id=operation['turn_id'], action_index=position,
                   role=c['role'], contribution_label=c['contribution_label'],
                   execution_status=c['execution_status'],
                   inferred_state_after_native_call=states[position] if position < len(states) else None,
                   component_execution_version='unresolved within native call',
                   input_tokens=None, cached_input_tokens=None, output_tokens=None,
                   usage_status='response usage absent from compact operation table',
                   checkpoint_evaluation='not_evaluated')
        joined.append(row); per_run[rid].append(row)
    if covered != op_index.keys():
        raise ValueError('Component inventory omits selected native operations')
    summary = []
    for rid, group in sorted(per_run.items()):
        run = runs[rid]
        n_ops = len({r['native_op_id'] for r in group})
        if n_ops != run['n_ops']:
            raise ValueError('Saved run and operation inventory disagree')
        summary.append(dict(run_id=rid, task_id=run['task_id'], model=run['model'],
            components=len(group), native_calls=n_ops,
            generating_responses_with_components=len({r['response_id'] for r in group}),
            recorded_model_turns=run['n_turns'], recorded_final_success=run['resolved'],
            run_input_tokens=run['input_tokens'], run_cached_input_tokens=run['cached_input_tokens'],
            run_output_tokens=run['output_tokens'],
            direct=sum(r['contribution_label'] == 'direct' for r in group),
            non_direct=sum(r['contribution_label'] == 'non_direct' for r in group),
            uncertain=sum(r['contribution_label'] == 'uncertain' for r in group),
            inferred_edit_versions=graphs[rid]['n_versions'] if rid in graphs else None,
            final_benchmark_evaluated_intermediate_versions=0))
    args.out.mkdir(parents=True, exist_ok=True)
    for name, records in [('component_identity_join.csv', joined), ('pilot_inventory_by_run.csv', summary)]:
        with (args.out / name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(records)
    counts = dict(components=len(joined), native_calls=len(ops), runs=len(per_run),
                  tasks=len({r['task_id'] for r in summary}),
                  generating_responses_with_components=len({r['response_id'] for r in joined}),
                  roles=dict(Counter(r['role'] for r in joined)),
                  contribution=dict(Counter(r['contribution_label'] for r in joined)))
    manifest = dict(status='saved-data identity coverage verified; token allocation and checkpoint validity unresolved',
        counts=counts, checks=dict(candidate_ids_preserved=True, native_call_coverage_complete=True,
                                  run_native_call_totals_match=True),
        response_usage_available=False, complete_code_snapshots_verified=False,
        actual_new_agent_runs=0, actual_new_model_labels=0, actual_task_evaluations=0,
        interpretation='run token totals are real archived fields; component token fields are deliberately null; inferred graph states are not evaluated snapshots',
        inputs={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths.values()})
    (args.out / 'inventory_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()
