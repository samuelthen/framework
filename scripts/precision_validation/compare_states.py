"""Rebuild facts and default version graphs for only the 16 evaluation runs.

Keeps all historical outputs intact; no trajectory commands are executed.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/one_day_precision'))
from packets import load_runs
from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph

OUT = ROOT / 'results/precision_validation_20261026'
OLD = ROOT / 'results/one_day_precision_20261026'


def main():
    key = pd.read_csv(OLD / 'packets/blinding_key.csv')
    key = key[key.order.between(3, 10)]
    source = load_runs(key.run_id)
    previous = pd.read_parquet(ROOT / 'data/ops_compact.parquet')
    previous = previous[previous.run_id.isin(key.run_id)].set_index(['run_id', 'op_index'])
    graph_old = {}
    for line in (ROOT / 'data/version_graphs_v2.jsonl').open():
        g = json.loads(line)
        if g['run_id'] in source:
            graph_old[g['run_id']] = g
    facts, changed, graph_rows, graphs = [], [], [], []
    for rid, (run, ops, _) in source.items():
        extract_facts(ops)
        graph = build_version_graph(run, ops)
        graphs.append(graph)
        old = graph_old[rid]
        graph_rows.append({'run_id': rid, 'model': run['model'],
                           'old_versions': old['n_versions'], 'new_versions': graph['n_versions'],
                           'old_backtracks': sum(e['label'] == 'backtrack' for e in old['edges']),
                           'new_backtracks': sum(e['label'] == 'backtrack' for e in graph['edges']),
                           'new_uncertain_versions': sum(n['uncertain'] for n in graph['nodes']),
                           'note': 'Default all-write graph, same saved runs; inferred versions, not independently verified snapshots.'})
        for o in ops:
            p = previous.loc[(rid, o['op_index'])]
            facts.append({'run_id': rid, 'action_index': o['op_index'], 'op_id': o['op_id'],
                          'kind': o['kind'], 'object': o['object'], 'write': o['write'],
                          'written_paths': o['written_paths'], 'state': o['state'],
                          'has_cand_object': o['cand_object'] is not None,
                          'exact_repeat': o['exact_repeat'], 'cand_facts': o['cand_facts']})
            fields = {'kind': p.kind, 'object': p.object, 'write': p.write,
                      'exact_repeat': bool(p.exact_repeat), 'n_parts': int(p.n_parts),
                      'has_cand_object': bool(p.has_cand_object)}
            new = {'kind': o['kind'], 'object': o['object'], 'write': o['write'],
                   'exact_repeat': o['exact_repeat'], 'n_parts': len(o['parts']),
                   'has_cand_object': o['cand_object'] is not None}
            for field, old_value in fields.items():
                if old_value != new[field]:
                    changed.append({'run_id': rid, 'action_index': o['op_index'], 'field': field,
                                    'old': old_value, 'new': new[field]})
    (OUT / 'corrected_facts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in facts))
    (OUT / 'corrected_version_graphs.jsonl').write_text(''.join(json.dumps(g) + '\n' for g in graphs))
    pd.DataFrame(changed, columns=['run_id','action_index','field','old','new']).to_csv(OUT / 'fact_changes.csv', index=False)
    pd.DataFrame(graph_rows).to_csv(OUT / 'version_changes.csv', index=False)
    print(f'Rebuilt {len(graphs)} pilot graphs and {len(facts)} facts; {len(changed)} changed compact fields')


if __name__ == '__main__':
    main()
