"""Export conserved component allocations and graph-region summaries.

Input is either a normalized response ledger or selected local JetBrains raw
shards. No download, annotation API, price lookup, or trajectory execution.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "worktrace"))
from worktrace.resources import (METRICS, ROLE_MARKERS, CONTRIBUTION_COLORS,
    allocate_usage, region_totals, contribution_resource_bounds)
from worktrace.contributions import CONTRIBUTION_NAMES


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in rows))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1 << 20),b''):
            h.update(block)
    return h.hexdigest()


def export_from_shards(paths, components, key_path):
    import pyarrow.parquet as pq
    from worktrace.loaders.jetbrains import load_row, load_response_usage
    with key_path.open() as handle:
        key = {(int(r['order']), r['label']): r['run_id'] for r in csv.DictReader(handle)}
    components = [dict(c) for c in components]
    for c in components:
        c['run_id'] = c.get('run_id') or key[(int(c['order']), c['blinded_label'])]
    needed = {c['run_id'] for c in components}
    responses, operations, run_totals = [], {}, {}
    for path in paths:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=10):
            for row in batch.to_pylist():
                rid = f"jb:{row['model']}:{row['instance_id']}:r{int(row['run'])}"
                if rid not in needed:
                    continue
                if rid in run_totals:
                    raise ValueError(f'Duplicate raw run {rid}')
                run, ops = load_row(row)
                responses.extend(load_response_usage(row))
                run_totals[rid] = run
                operations.update({(rid, index): op for index, op in enumerate(ops)})
    missing = needed - set(run_totals)
    if missing:
        raise ValueError(f'Selected raw runs missing: {sorted(missing)}')
    for c in components:
        op = operations[(c['run_id'], int(c['action_index']))]
        c['response_id'] = op['response_id']
        c['native_op_id'] = op['op_id']
    # Export requires a complete inventory of native calls, not just useful
    # annotated components. Subsets would otherwise absorb shared costs.
    missing_ops = set(operations) - {(c['run_id'],int(c['action_index'])) for c in components}
    if missing_ops:
        raise ValueError('Component input omits native calls; use the complete candidate inventory')
    return responses, components, run_totals


def reconciliation(responses, run_totals):
    rows = []
    for rid, run in sorted(run_totals.items()):
        rs = [r for r in responses if r.get('run_id') == rid]
        for metric in METRICS:
            values = [r['usage'].get(metric) for r in rs]
            known = [v for v in values if v is not None]
            total = math.fsum(known) if known else None
            expected = run.get(metric)
            complete = len(known) == len(rs) and bool(rs)
            status = ('run_total_unavailable' if expected is None else
                      'response_usage_incomplete' if not complete else
                      'matches' if math.isclose(total,expected,abs_tol=1e-8) else 'mismatch')
            rows.append(dict(run_id=rid,metric=metric,responses=len(rs),responses_with_usage=len(known),
                             known_response_sum=total,recorded_run_total=expected,
                             difference=total-expected if complete and expected is not None else None,
                             status=status))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--responses', type=Path, help='Normalized response-ledger JSONL')
    source.add_argument('--jetbrains-shard', type=Path, action='append', help='Local pinned raw Parquet; repeat for selected shards')
    parser.add_argument('--components', type=Path, required=True, help='Complete candidate components with response_id, or anonymous reviewed components for raw export')
    parser.add_argument('--blinding-key', type=Path, default=ROOT/'results/one_day_precision_20261026/packets/blinding_key.csv')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    components = read_jsonl(args.components)
    run_totals = {}
    if args.responses:
        responses = read_jsonl(args.responses)
        inputs = [args.responses,args.components]
    else:
        responses, components, run_totals = export_from_shards(args.jetbrains_shard, components, args.blinding_key)
        inputs = [*args.jetbrains_shard,args.components,args.blinding_key]
    allocations = allocate_usage(responses,components)
    args.out.mkdir(parents=True,exist_ok=True)
    write_jsonl(args.out/'response_usage.jsonl',responses)
    write_jsonl(args.out/'components_with_responses.jsonl',components)
    write_jsonl(args.out/'component_allocations.jsonl',allocations)
    write_jsonl(args.out/'run_usage_reconciliation.jsonl',reconciliation(responses,run_totals))
    write_jsonl(args.out/'contribution_expenditure_bounds.jsonl',contribution_resource_bounds(allocations))
    regions = []
    for view,dims in [('role',('role',)),('version',('version_region',)),
                      ('role_version',('role','version_region')),('target',('target_region',)),
                      ('contribution',('contribution_label',))]:
        # Include run_id outside the grouping to avoid pooling different tasks.
        for run_id in sorted({r.get('run_id') or 'unknown' for r in allocations}):
            rs = [r for r in allocations if (r.get('run_id') or 'unknown') == run_id]
            for mixed in [False,True]:
                regions.extend(dict(run_id=run_id,view=view,**r) for r in region_totals(rs,dims,mixed))
    write_jsonl(args.out/'region_totals.jsonl',regions)
    overlay = dict(legend=dict(role_markers=ROLE_MARKERS,contribution_colors=CONTRIBUTION_COLORS,
                              contribution_names=CONTRIBUTION_NAMES),
                   usage_note='Metric fields are separate; do not sum graph views, cache with input, or reasoning with output.',
                   glyphs=[dict(component_id=r['component_id'],response_id=r['response_id'],
                                role=r['role'],contribution_label=r['contribution_label'],
                                version_region=r['version_region'],visual=r['visual']) for r in allocations],
                   regions=regions)
    (args.out/'graph_overlay.json').write_text(json.dumps(overlay,indent=2,allow_nan=False)+'\n')
    manifest = dict(inputs={str(p):digest(p) for p in inputs},
        responses=len(responses),components=len(components),
        responses_with_any_usage=sum(any((r.get('usage') or {}).get(m) is not None for m in METRICS) for r in responses),
        method='equal emitted-candidate shares; missing stays null; mixed-region sensitivity exported',
        actual_new_agent_runs=0, status='exported; inspect usage coverage and source accounting before empirical claims')
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='inputs'},indent=2))


if __name__=='__main__':
    main()
