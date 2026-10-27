"""Reconstruct the two Luna edit/formatter boundaries without executing traces.

Only constant pathlib read/write and string.replace expressions are interpreted.
Unified diffs are applied with exact context matching. Unknown syntax fails closed.
"""
import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/utility_audit_20261028'


def hash_bytes(data): return hashlib.sha256(data).hexdigest()


def safe_path(root, name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Unsafe path')
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()): raise ValueError('Unsafe resolved path')
    return target


def apply_patch(root, text):
    """Strict ordinary text modification hunks only, sufficient for these patches."""
    blocks = text.split('diff --git ')[1:]
    changed = []
    for block in blocks:
        lines = block.splitlines(keepends=True)
        normalized = []
        for line in lines:
            if line.startswith('\\ No newline at end of file'):
                if not normalized: raise ValueError('Orphan no-newline marker')
                normalized[-1] = normalized[-1].removesuffix('\n')
            else: normalized.append(line)
        lines = normalized
        old = next(s[6:].rstrip('\n') for s in lines if s.startswith('--- a/'))
        new = next(s[6:].rstrip('\n') for s in lines if s.startswith('+++ b/'))
        if old != new: raise ValueError('Renames/new files not supported in this scoped reconstruction')
        path = safe_path(root, old)
        before = path.read_text().splitlines(keepends=True); result = []; cursor = 0; i = 0
        while i < len(lines):
            line = lines[i]
            if not line.startswith('@@ '): i += 1; continue
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if not match: raise ValueError('Malformed hunk')
            start = int(match[1]) - 1
            if start < cursor: raise ValueError('Overlapping hunks')
            result.extend(before[cursor:start]); cursor = start; i += 1
            old_count = new_count = 0
            while i < len(lines) and not lines[i].startswith('@@ '):
                item = lines[i]; i += 1
                if not item or item[0] not in ' +-': continue
                if item[0] in ' -':
                    if cursor >= len(before) or before[cursor] != item[1:]:
                        raise ValueError(f'Patch context mismatch: {old}:{cursor+1}')
                    cursor += 1; old_count += 1
                if item[0] in ' +': result.append(item[1:]); new_count += 1
            if old_count != int(match[2] or 1) or new_count != int(match[4] or 1):
                raise ValueError('Hunk counts mismatch')
        result.extend(before[cursor:]); path.write_text(''.join(result)); changed.append(old)
    if not changed: raise ValueError('No modified file blocks')
    return changed


def interpret_replacements(root, code):
    env = {}; changed = []
    def expr(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, type(None))): return node.value
        if isinstance(node, ast.Name): return env[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Path':
            if len(node.args) != 1 or node.keywords: raise ValueError('Unexpected Path arguments')
            return safe_path(root, expr(node.args[0]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            obj = expr(node.func.value); name = node.func.attr
            args = [expr(a) for a in node.args]
            if node.keywords: raise ValueError('Unexpected keyword')
            if isinstance(obj, Path) and name == 'read_text' and not args: return obj.read_text()
            if isinstance(obj, Path) and name == 'write_text' and len(args) == 1:
                before = obj.read_bytes(); obj.write_text(args[0]); changed.append(dict(path=str(obj.relative_to(root)),
                    before_sha256=hash_bytes(before), after_sha256=hash_bytes(obj.read_bytes())))
                return len(args[0])
            if isinstance(obj, str) and name == 'replace' and len(args) == 2: return obj.replace(*args)
        raise ValueError(f'Unsupported expression: {ast.dump(node)[:120]}')
    for node in ast.parse(code).body:
        if isinstance(node, ast.ImportFrom) and node.module == 'pathlib': continue
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            env[node.targets[0].id] = expr(node.value)
        elif isinstance(node, ast.Expr): expr(node.value)
        elif (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
              and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.NotIn)
              and len(node.test.comparators) == 1 and not node.orelse
              and len(node.body) == 1 and isinstance(node.body[0], ast.Raise)):
            if expr(node.test.left) not in expr(node.test.comparators[0]): raise ValueError('Edit guard failed')
        else: raise ValueError(f'Unsupported statement: {type(node).__name__}')
    return changed


def tree_manifest(root):
    return {str(p.relative_to(root)): hash_bytes(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    components = {r['component_id']: r for r in (json.loads(s) for s in
        (ROOT / 'results/precision_validation_20261026/reconciled_component_annotations.jsonl').read_text().splitlines())}
    import pyarrow.parquet as pq
    refs = {r['instance_id']: r for r in pq.read_table(ROOT / 'raw/swebenchpro/v1.parquet').to_pylist()}
    records = []
    for order, action in [(3, 4), (4, 6)]:
        path = ROOT / f'raw/utility_replay/task{order:02d}'
        row = json.loads((ROOT / f'raw/utility_selected/{order:02d}_luna.json').read_text())
        base = path / 'base'; pre = path / 'before_formatter'; final = path / 'submitted'; oracle = path / 'reference'
        for target in [pre, final, oracle]:
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(base, target)
        command = components[f'{order:02d}:Y{action:03d}.c0']['command']
        match = re.search(r"<<'PY'\n(.*)\nPY$", command, re.S)
        if not match: raise ValueError('Scoped Python body missing')
        changes = interpret_replacements(pre, match[1])
        final_files = apply_patch(final, row['submission'])
        reference_files = apply_patch(oracle, refs[row['instance_id']]['patch'])
        # Fixed independent evaluator patch; not supplied by the studied agent.
        for version in ['base', 'before_formatter', 'submitted', 'reference']:
            evaluation = path / f'eval_{version}'
            if evaluation.exists(): shutil.rmtree(evaluation)
            shutil.copytree(path / version, evaluation)
            apply_patch(evaluation, refs[row['instance_id']]['test_patch'])
        record = dict(task_order=order, base_commit=refs[row['instance_id']]['base_commit'],
            editing_component=f'{order:02d}:Y{action:03d}.c0', formatting_component=f'{order:02d}:Y{action:03d}.c1',
            interpreter='restricted literal Path/read/write/string.replace; no trajectory process execution',
            writes=changes, submitted_modified_files=final_files, reference_modified_files=reference_files,
            pre_formatter_vs_submitted={file:dict(before_formatter_sha256=hash_bytes((pre/file).read_bytes()),
                                                  submitted_sha256=hash_bytes((final/file).read_bytes()),
                                                  identical=(pre/file).read_bytes() == (final/file).read_bytes()) for file in final_files},
            tree_hashes={version: hash_bytes(json.dumps(tree_manifest(path/version), sort_keys=True).encode())
                         for version in ['base', 'before_formatter', 'submitted', 'reference']},
            evaluation_status='snapshots reconstructed; no final-benchmark outcome asserted')
        records.append(record)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'reconstruction.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__': main()
