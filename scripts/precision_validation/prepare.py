"""Freeze component units and blinded full evidence. Never execute trajectory commands."""
import json
import sys
import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/one_day_precision'))
from packets import load_runs
from worktrace.parse import shell
import pandas as pd

OUT = ROOT / 'results/precision_validation_20261026'
OLD = ROOT / 'results/one_day_precision_20261026'


def components(command):
    # Pipelines are one observation-producing work component. Quoted scripts,
    # substitutions and heredoc bodies remain intact. Directory setup is context.
    # bash -n parses stdin without executing any command, expansion or script.
    syntax = subprocess.run(['bash', '-n'], input=command, text=True,
                            capture_output=True, timeout=5)
    if syntax.returncode:
        return [{'command': command, 'directory_context': [],
                 'syntax_status': 'invalid_shell_opaque_attempt', 'syntax_diagnostic': syntax.stderr}]
    parts = shell.split_chain(command, split_pipelines=False)
    # A control construct is a single conditional work unit; `then`, `fi`,
    # loop bodies and other branches are never independently counted commands.
    grouped, block, depth = [], [], 0
    for part in parts:
        head = part.lstrip()
        if re.match(r'^(if|for|while|until|case|select)\b', head):
            depth += 1
        if depth:
            block.append(part)
            if re.match(r'^(fi|done|esac)\b', head):
                depth -= 1
                if not depth:
                    grouped.append('; '.join(block))
                    block = []
        else:
            grouped.append(part)
    if block:
        # Unsupported nesting is opaque, rather than pretending inner syntax
        # keywords are independently performed actions.
        return [{'command': command, 'directory_context': [], 'syntax_status': 'opaque_control_flow'}]
    context, out = [], []
    for part in grouped:
        toks = shell._tokens(part)
        if toks and toks[0] == 'cd':
            context.append(part)
            continue
        out.append({'command': part, 'directory_context': list(context)})
    return out or [{'command': command, 'directory_context': []}]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = pd.read_csv(OLD / 'packets/blinding_key.csv')
    key = key[key.order.between(3, 10)]
    runs = load_runs(key.run_id)
    records = []
    for order, group in key.groupby('order'):
        evidence = []
        for k in group.sort_values('label').itertuples():
            run, ops, patch = runs[k.run_id]
            for idx, op in enumerate(ops):
                cs = components(op['command'] or '')
                for ci, comp in enumerate(cs):
                    records.append({'order': int(order), 'blinded_label': k.label,
                                    'action_index': idx, 'component_index': ci,
                                    'component_id': f'{order:02d}:{k.label}{idx:03d}.c{ci}',
                                    'parent_op_id': f'{order:02d}:{k.label}{idx:03d}', **comp,
                                    'output_attribution': 'shared call output; reviewer must establish component attribution',
                                    'execution_status': 'review_required'})
            visible = []
            for idx, op in enumerate(ops):
                visible.append({'action_index': idx, 'command': op['command'],
                                'output': op['agent_output'] if op.get('agent_saw_truncated') else op['output'],
                                'exit_code': op['exit_code'], 'agent_saw_truncated': op.get('agent_saw_truncated', False),
                                'missing_result': op.get('missing_result', False)})
            evidence.append({'blinded_label': k.label, 'actions': visible, 'final_patch': patch})
        (OUT / f'evidence_{order:02d}.json').write_text(json.dumps(evidence, indent=2))
    (OUT / 'components.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records))
    print(f'{len(records)} components in {len(key)} runs; full evidence frozen')


if __name__ == '__main__':
    main()
