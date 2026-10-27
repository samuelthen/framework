"""Authored isolated checks on exact reconstructed Go files.

Never executes shell commands from a trajectory. Evaluation is scoped package
testing in a declared Go image, not the original SWE-bench Pro harness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/utility_audit_20261028'
IMAGE = 'golang@sha256:e47f121850f4e276b2b210c56df3fda9191278dd84a3a442bfe0b09934462a8f'


def run(label, task, version, command, *, network=False, limit=180):
    work = ROOT / f'raw/utility_replay/task{task:02d}/{version}'
    container_name = f'worktrace-utility-{label.replace("_", "-")}-{time.time_ns()}'
    base = ['docker', 'run', '--rm', '--name', container_name, '--cpus=2', '--memory=2g', '--pids-limit=256',
            '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--mount', f'type=bind,src={work},dst=/source,readonly',
            '--tmpfs', '/work:rw,size=256m',
            '--mount', f'type=bind,src={ROOT}/raw/utility_replay/go_modcache,dst=/go/pkg/mod',
            '--mount', f'type=bind,src={ROOT}/raw/utility_replay/go_buildcache,dst=/gocache',
            '-e', 'GOCACHE=/gocache', '-e', 'CGO_ENABLED=0', '-e', 'GOTOOLCHAIN=local',
            '-w', '/work']
    if not network: base += ['--network=none']
    # Workspaces may write derived go.work.sum/build metadata. Writes go only
    # to disposable tmpfs, never back into the reconstructed source snapshot.
    base += [IMAGE, 'sh', '-c', 'cp -a /source/. /work/ && exec "$@"', 'utility-check', *command]
    started = time.perf_counter()
    try:
        result = subprocess.run(base, capture_output=True, timeout=limit)
        code, output, error, status = result.returncode, result.stdout, result.stderr, 'completed'
    except subprocess.TimeoutExpired as exc:
        # Limit client and daemon lifetime; the named task process is not left running.
        code, output, error, status = None, exc.stdout or b'', exc.stderr or b'', 'timeout'
        subprocess.run(['docker','rm','-f',container_name], capture_output=True, timeout=15)
    elapsed = time.perf_counter() - started
    folder = OUT/'container_logs'; folder.mkdir(parents=True, exist_ok=True)
    (folder/f'{label}.stdout.txt').write_bytes(output)
    (folder/f'{label}.stderr.txt').write_bytes(error)
    record = dict(label=label, task_order=task, snapshot=version, command=command,
                  environment=IMAGE, network_enabled=network, seconds=elapsed, exit_code=code,
                  source_mount_readonly=True, disposable_work_copy=True,
                  status=status, stdout_sha256=hashlib.sha256(output).hexdigest(),
                  stderr_sha256=hashlib.sha256(error).hexdigest(),
                  interpretation='scoped deterministic reproduction, not original benchmark certification')
    return record, output, error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['format', 'modules', 'tests', 'requirements'])
    parser.add_argument('--task', type=int, choices=[3,4])
    args = parser.parse_args()
    tasks = [args.task] if args.task else [3,4]
    records = []
    for task in tasks:
        if args.phase == 'format':
            files = ['internal/server/auth/middleware.go', 'internal/server/middleware/grpc/middleware.go'] if task == 3 else ['config/config.go']
            for name in files:
                label = f'task{task:02d}_format_{name.replace("/", "_")}'
                record, output, error = run(label, task, 'before_formatter', ['gofmt', name], limit=30)
                pre = (ROOT/f'raw/utility_replay/task{task:02d}/before_formatter'/name).read_bytes()
                submitted = (ROOT/f'raw/utility_replay/task{task:02d}/submitted'/name).read_bytes()
                record.update(source_file=name, bytes_before=len(pre), bytes_after=len(output),
                              formatter_changes_bytes=pre != output if record['exit_code']==0 else None,
                              formatted_output_matches_submitted=output == submitted if record['exit_code']==0 else None,
                              before_sha256=hashlib.sha256(pre).hexdigest())
                records.append(record)
        elif args.phase == 'modules':
            record, _, _ = run(f'task{task:02d}_modules', task, 'base', ['go','mod','download'], network=True, limit=240)
            records.append(record)
        elif args.phase == 'requirements':
            if task != 4: raise ValueError('Requirement diagnostic is scoped to task 04')
            import shutil
            for version in ['base','before_formatter','submitted','reference']:
                original = ROOT/f'raw/utility_replay/task04/{version}'
                target = original.with_name(f'probe_{version}')
                if target.exists(): shutil.rmtree(target)
                shutil.copytree(original,target)
                shutil.copy2(ROOT/'scripts/utility_audit/requirement_probe.go',target/'utility_requirement_probe.go')
                record, output, _ = run(f'task04_probe_{version}',task,f'probe_{version}',
                    ['go','run','-mod=readonly','utility_requirement_probe.go'],limit=120)
                if record['exit_code']==0: record['properties']=json.loads(output)
                record['probe_sha256']=hashlib.sha256((target/'utility_requirement_probe.go').read_bytes()).hexdigest()
                records.append(record)
        else:
            package = './internal/server/middleware/grpc' if task == 3 else './config'
            pattern = '^TestErrorUnaryInterceptor$' if task == 3 else '^Test(Load|ServeHTTP|Validate|Scheme)$'
            for version in ['eval_base', 'eval_before_formatter', 'eval_submitted', 'eval_reference']:
                label = f'task{task:02d}_{version}'
                record, _, _ = run(label, task, version,
                    ['go','test','-mod=readonly','-count=1','-json','-run',pattern,package], limit=240)
                records.append(record)
        (OUT/f'{args.phase}_task{task:02d}.json').write_text(json.dumps([r for r in records if r['task_order']==task],indent=2)+'\n')
    print(json.dumps(records,indent=2))


if __name__ == '__main__': main()
