"""Three successive critiques of utility proxies on recovered real traces.

Only saved evidence is inspected. These are screens, not causal utility labels
or proofs that repeated verification may be suppressed.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'worktrace'))
from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph

OUT = ROOT/'results/utility_audit_20261028'


def read(path): return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def output_status(op):
    raw, visible = op.get('output') or '', op.get('agent_output') or ''
    if 'timed out' in visible.lower() or op.get('exit_code') == -1: return 'timeout_or_interrupted'
    if op.get('missing_result'): return 'missing_result'
    if not raw.strip(): return 'empty_observation'
    if re.search(r'(?m)^--- FAIL:|^FAIL\s|\[build failed\]', raw): return 'observed_test_or_build_failure'
    if re.search(r'(?m)^PASS$|^ok\s+\S+\s+(?:\d|\(cached\))', raw): return 'observed_test_success'
    if op.get('exit_code') not in (0, None): return 'nonzero_other_observation'
    return 'other_observation'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round', type=int, choices=[1,2,3], required=True)
    args = parser.parse_args()
    folder = OUT/f'round_{args.round}'; folder.mkdir(parents=True, exist_ok=True)
    components = read(ROOT/'results/precision_validation_20261026/reconciled_component_annotations.jsonl')
    operations = read(ROOT/'raw/utility_selected/operations.jsonl')
    runs = {r['run_id']: r for r in read(ROOT/'raw/utility_selected/runs.jsonl')}
    opindex = {(r['order'],r['blinded_label'],r['action_index']):r for r in operations}
    included = [c for c in components if c['execution_status']!='not_executed']
    summary = dict(round=args.round, runs=len(runs), native_calls=len(operations), candidates=len(components),
                   precision_included=len(included), source='pinned raw trajectories and archived model-coded annotations')
    rows = []
    if args.round == 1:
        counts = Counter(c['contribution_label'] for c in included)
        summary.update(critique='Directness is a descriptive annotation, not action utility. Binary or broad indirect labels merge unknown future benefit and diagnostic/operational work.',
                       label_counts=dict(counts), label_bounds=[counts['direct']/len(included),
                          (counts['direct']+counts['uncertain'])/len(included)],
                       actual_counterfactual_utility_measured=False,
                       improvement='Retain descriptive labels; introduce result/evidence validity before utility scoring.')
        for c in included:
            rows.append(dict(component_id=c['component_id'],role=c['role'],label=c['contribution_label'],
                             causal_utility=None,utility_status='not identifiable from label alone'))
    elif args.round == 2:
        parent_components = Counter((c['order'],c['blinded_label'],c['action_index']) for c in components)
        for c in components:
            if c['role']!='verification': continue
            key=(c['order'],c['blinded_label'],c['action_index']);op=opindex[key]
            rows.append(dict(component_id=c['component_id'],execution_status=c['execution_status'],
                command=c['command'],parent_action_index=c['action_index'],
                parent_result_status=output_status(op),shared_parent_output=parent_components[key]>1,
                parent_exit_code=op['exit_code'],raw_observation_chars=len(op.get('output') or ''),
                agent_visible_chars=len(op.get('agent_output') or ''),
                agent_saw_truncated=op.get('agent_saw_truncated',False),
                utility_status='result validity and observation scope needed before scoring'))
        summary.update(critique='A requested check is not necessarily a completed result; parent success and shared output cannot establish individual-component outcomes.',
            parent_status_counts=dict(Counter(r['parent_result_status'] for r in rows)),
            verification_components=len(rows),shared_parent_outputs=sum(r['shared_parent_output'] for r in rows),
            improvement='Track executed/result/visible-evidence status separately; a timeout is not cached test success or zero utility.')
    else:
        graphs={}; byrun=defaultdict(list)
        for op in operations:byrun[op['run_id']].append(op)
        for rid, ops in byrun.items():
            ops.sort(key=lambda r:r['action_index']);extract_facts(ops);graphs[rid]=build_version_graph(runs[rid],ops)
        seen=defaultdict(dict)
        for c in sorted(components,key=lambda c:(c['order'],c['blinded_label'],c['action_index'],c['component_index'])):
            key=(c['order'],c['blinded_label']);cmd=c['command'].strip();op=opindex[(*key,c['action_index'])]
            prior=seen[key].get(cmd)
            if prior and c['role']=='verification':
                oldop=opindex[(*key,prior['action_index'])];g=graphs[op['run_id']]
                oldstate=g['op_version'][prior['action_index']];state=g['op_version'][c['action_index']]
                rows.append(dict(component_id=c['component_id'],earlier_component_id=prior['component_id'],command=cmd,
                    earlier_result_status=output_status(oldop),current_result_status=output_status(op),
                    earlier_inferred_state=oldstate,current_inferred_state=state,
                    same_inferred_state=oldstate==state,
                    earlier_visible_truncated=oldop.get('agent_saw_truncated',False),
                    complete_dependency_snapshot_available=False,cache_reuse_certified=False))
            seen[key][cmd]=c
        summary.update(critique='Exact repeated commands can test changed implementations or recover missing evidence; even identical inferred graph states do not prove complete dependency equality.',
            exact_repeat_verification_pairs=len(rows),same_inferred_state_pairs=sum(r['same_inferred_state'] for r in rows),
            changed_inferred_state_pairs=sum(not r['same_inferred_state'] for r in rows),
            pairs_with_prior_timeout_or_missing=sum(r['earlier_result_status'] in {'timeout_or_interrupted','missing_result','empty_observation'} for r in rows),
            certified_cache_hits=0,
            improvement='Separate command recurrence, execution-state identity, prior observation completeness and task-property scope; conservatively require a certificate for reuse.')
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (folder/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
