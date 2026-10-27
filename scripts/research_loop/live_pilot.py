"""Matched Soc snapshot continuations: fresh public check, warm reuse, bypass.

Agents see public issue text, production candidate and public-check summaries.
Independent evaluator patches and grading logs are never mounted in their
containers. This is an off-policy snapshot pilot, not a rerun of Luna/Gemini.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import time
import uuid
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('MSWEA_GLOBAL_CONFIG_DIR',str(ROOT/'raw/live_utility/mini-config'))
os.environ.setdefault('MSWEA_SILENT_STARTUP','1')
sys.path.insert(0,str(ROOT/'scripts/utility_audit'))
sys.path.insert(0,str(ROOT/'worktrace'))
from reconstruct import tree_manifest
from executable_panel import patch,scoped_quality
from soc_client import Client,AgentModel,Budget,load_env

RAW=ROOT/'raw/live_utility';OUT=ROOT/'results/research_loop_20261028/live_pilot'
IMAGE_TAG='worktrace/utility-agent:20261028'
FINISH='echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'


def run(args,**kwargs):
    r=subprocess.run(args,text=True,capture_output=True,timeout=kwargs.pop('timeout',120),**kwargs)
    if r.returncode:raise RuntimeError('Trusted setup command failed: '+r.stderr[-1000:])
    return r.stdout


def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def digest(root):return hashlib.sha256(json.dumps(tree_manifest(root),sort_keys=True).encode()).hexdigest()


def clone_tree(source,target):
    """Private copy-on-write snapshots on macOS; never hard-link mutable caches."""
    if sys.platform=='darwin':
        run(['/bin/cp','-cR',str(source),str(target)])
    else:shutil.copytree(source,target)


def check(source,cache,image,command,timeout=120):
    """Disposable work copy; public and grading callers use separate caches."""
    cache.mkdir(parents=True,exist_ok=True)
    name='wt-public-check-'+uuid.uuid4().hex[:12]
    args=['docker','run','--rm','--name',name,'--network=none','--cpus=2','--memory=2g','--pids-limit=256','--cap-drop=ALL','--security-opt=no-new-privileges',
        '--mount',f'type=bind,src={source},dst=/source,readonly','--tmpfs','/work:rw,size=256m',
        '--mount',f'type=bind,src={ROOT}/raw/utility_replay/go_modcache,dst=/go/pkg/mod,readonly',
        '--mount',f'type=bind,src={cache},dst=/gocache','-e','GOCACHE=/gocache','-e','CGO_ENABLED=0','-e','GOPROXY=off','-e','GOTOOLCHAIN=local','-w','/work',
        image,'bash','-c','cp -a /source/. /work/ && exec "$@"','public-check',*command]
    start=time.monotonic()
    try:r=subprocess.run(args,capture_output=True,timeout=timeout);code,stdout,stderr,status=r.returncode,r.stdout,r.stderr,'completed'
    except subprocess.TimeoutExpired as e:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
        code,stdout,stderr,status=None,e.stdout or b'',e.stderr or b'','timeout'
    events=[]
    for line in stdout.decode(errors='replace').splitlines():
        try:e=json.loads(line)
        except ValueError:continue
        if e.get('Action') in {'pass','fail','skip'} and e.get('Test'):
            events.append({k:e[k] for k in ['Package','Test','Action']})
    events.sort(key=lambda e:json.dumps(e,sort_keys=True))
    quality=scoped_quality(code,status,stdout,stderr,events)
    canonical=dict(exit_code=code,quality=quality,test_outcomes=events)
    return dict(canonical=canonical,status=status,seconds=time.monotonic()-start,stdout=stdout.decode(errors='replace'),stderr=stderr.decode(errors='replace'))


def prepare():
    RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'plan.json').exists() and (RAW/'cases.json').exists():
        previous=json.loads((OUT/'plan.json').read_text())
        if previous.get('schedule'):
            for c in json.loads((RAW/'cases.json').read_text()):
                if digest(Path(c['source']))!=c['source_sha256']:raise RuntimeError('Frozen candidate changed')
            print('Existing nonempty live plan retained; use a new output root for a new study.');return
    refs={r['instance_id']:r for r in pq.read_table(ROOT/'raw/swebenchpro/v1.parquet').to_pylist()}
    selected=[('pilot03','instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0',ROOT/'raw/utility_replay/task03/base',['./internal/server/auth','./internal/server/middleware/grpc']),
              ('confirm00','instance_flipt-io__flipt-29d3f9db40c83434d0e3cc082af8baec64c391a9',ROOT/'raw/research_executable/case_00/base',['./internal/telemetry']),
              ('confirm03','instance_flipt-io__flipt-abaa5953795afb9c621605bb18cb32ac48b4508c',ROOT/'raw/research_executable/case_03/base',['./internal/config'])]
    rows={r['instance_id']:r for r in pq.read_table(ROOT/'raw/jetbrains/luna-run1.parquet',columns=['instance_id','submission','resolved']).to_pylist()}
    image=json.loads(run(['docker','image','inspect',IMAGE_TAG]))[0]['Id']
    cases=[]
    for name,task,base,packages in selected:
        target=RAW/'prefixes'/name/'source'
        if not target.exists():
            shutil.copytree(base,target)
            applied=patch(target,rows[task]['submission'])
            if applied['exit_code']:raise RuntimeError('Candidate preparation failed')
        case=dict(id=name,task_id=task,base=str(base),source=str(target),image=image,
            source_sha256=digest(target),public_command=['go','test','-mod=readonly','-count=1','-json',*packages],
            problem_statement=refs[task]['problem_statement'],requirements=refs[task]['requirements'],
            original_recorded_resolved=rows[task]['resolved'])
        cache=RAW/'prefixes'/name/'public_build_cache'
        checks=[check(target,cache,image,case['public_command']) for _ in range(2)]
        write(RAW/'prefixes'/name/'public_checks.json',checks)
        if not all(c['status']=='completed' and c['canonical']['test_outcomes'] and c['canonical']['quality'] in {'scoped_pass','scoped_fail'} for c in checks):
            case['cache_eligible']=False
        else:case['cache_eligible']=checks[0]['canonical']==checks[1]['canonical']
        case['cache_scope']='Canonical public test-outcome summary; full source snapshot, fixed image, read-only module cache, discarded filesystem side effects. Two-run stability is not universal determinism.'
        case['cache_fill_seconds']=sum(c['seconds'] for c in checks)
        cases.append(case);print('Prepared',name,'public',checks[-1]['canonical']['quality'],'cache eligible',case['cache_eligible'],flush=True)
    # The private oracle stays in host-only raw storage, never case prompts.
    write(RAW/'private_oracles.json',{c['id']:dict(test_patch=refs[c['task_id']]['test_patch'],test_names=json.loads(refs[c['task_id']]['selected_test_files_to_run']),
        packages=sorted({str(Path(s[6:]).parent) for s in refs[c['task_id']]['test_patch'].splitlines() if s.startswith('+++ b/') and s.endswith('_test.go')})) for c in cases})
    write(RAW/'cases.json',cases)
    schedule=[dict(case=c['id'],model=m,arm=a,replicate=r) for c in cases if c['cache_eligible'] for m in ['x-test-2'] for a in ['fresh','cache','bypass'] for r in range(2)]
    random.Random(20261028).shuffle(schedule)
    plan=dict(design='Diagnostic snapshot-continuation pilot; same source snapshot and task within each comparison.',cases=[{k:v for k,v in c.items() if k not in {'problem_statement','requirements','base','source'}} for c in cases],
        schedule=schedule,max_model_calls_per_episode=4,max_output_tokens_per_call=3072,requested_reasoning_effort='low',
        max_api_attempts=80,max_accounted_tokens=1_000_000,workers=2,
        model_selection='User selected DeepSeek before continuation episodes; archived three-model comparisons remain separate.',
        measurement='Fresh check time, cache hash/lookup time, continuation API/tool usage and independent selected-check outcome.',
        selection='Three contrasting archived candidate snapshots selected after offline outcomes; not a random population sample.',
        cache_overhead='Cache-fill executions are setup costs, retained separately; arm comparison is conditional on an eligible warm cache.',
        interpretation='New Soc policies continuing fixed candidates, not causal estimates for the archived Luna or Gemini policy; no population non-inferiority claim.')
    path=OUT/'plan.json'
    if path.exists() and json.loads(path.read_text())!=plan:
        previous=json.loads(path.read_text())
        if previous['schedule'] or (OUT/'episodes').exists():raise RuntimeError('Frozen live plan changed')
        write(OUT/'plan_preflight_unavailable.json',previous)
    write(path,plan)


def allowed_source(path):
    p=Path(path)
    return not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts and p.suffix in {'.go','.ts','.tsx','.js','.jsx'} and not p.name.endswith(('_test.go','.test.ts','.test.tsx','.spec.ts','.test.js')) and not {'test','tests','testdata'}&set(p.parts)


def episode(job,cases,oracles,env,budget):
    from minisweagent.environments.docker import DockerEnvironment
    from minisweagent.agents.default import DefaultAgent
    identifier=f"{job['case']}_{job['model']}_{job['arm']}_r{job['replicate']}"
    folder=RAW/'episodes'/identifier;summary=OUT/'episodes'/f'{identifier}.json'
    if summary.exists():return json.loads(summary.read_text())
    folder.mkdir(parents=True,exist_ok=True);case=cases[job['case']]
    record=dict(job,episode_id=identifier,source_sha256=case['source_sha256'],cost_usd=None,status='started')
    environment=None;work=folder/'work';cache=folder/'agent_build_cache'
    start=time.monotonic()
    try:
        if shutil.disk_usage(ROOT).free<3*1024**3:raise RuntimeError('Disk reserve reached')
        clone_tree(RAW/'prefixes'/case['id']/'public_build_cache',cache)
        clone_tree(Path(case['base']),work)
        if job['arm']=='fresh':
            observation=check(Path(case['source']),cache,case['image'],case['public_command'])
            if observation['status']!='completed':raise RuntimeError('Public checker unavailable')
            feedback=dict(public_check=observation['canonical'],reused=False);record['initial_check_seconds']=observation['seconds']
        elif job['arm']=='cache':
            tick=time.monotonic()
            if digest(Path(case['source']))!=case['source_sha256']:raise RuntimeError('Cache source changed')
            observed=json.loads((RAW/'prefixes'/case['id']/'public_checks.json').read_text())[-1]
            feedback=dict(public_check=observed['canonical'],reused=True);record['initial_check_seconds']=time.monotonic()-tick
        else:feedback=dict(public_check=None,decision='Initial optional public check bypassed; you may inspect and check further.');record['initial_check_seconds']=0.0
        write(folder/'initial_feedback.json',feedback)
        logger=logging.getLogger(identifier);logger.setLevel(logging.ERROR)
        environment=DockerEnvironment(logger=logger,image=case['image'],cwd='/work',timeout=90,interpreter=['bash','-c'],
            run_args=['--rm','--network','none','--memory','2g','--cpus','2','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges',
                '--mount',f'type=bind,src={work},dst=/work','--mount',f'type=bind,src={cache},dst=/agentcache',
                '--mount',f'type=bind,src={ROOT}/raw/utility_replay/go_modcache,dst=/go/pkg/mod,readonly'],
            container_timeout='15m',env={'GOCACHE':'/agentcache','CGO_ENABLED':'0','GOPROXY':'off','GOTOOLCHAIN':'local','PAGER':'cat'})
        def trusted(command):
            value=environment.execute({'command':command})
            if value['returncode']:raise RuntimeError('Trusted workspace preparation failed')
            return value['output']
        trusted('git init -q && git config user.email experiment@local && git config user.name WorkTrace && git add -A && git commit -qm base')
        # Use the original public submission rather than exposing evaluator tests.
        source_files=tree_manifest(Path(case['source']));base_files=tree_manifest(Path(case['base']))
        for relative in sorted(set(source_files)|set(base_files)):
            if source_files.get(relative)==base_files.get(relative):continue
            target=work/relative;origin=Path(case['source'])/relative
            if origin.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin,target)
            elif target.exists():target.unlink()
        client=Client(env,job['model'],folder/'api',budget)
        system='You are a coding agent in an offline Linux repository at /work. A production candidate is already applied. Continue working on the issue, or finalize it. Use the bash tool in every response. Modify production source only; do not modify existing tests, dependency files or .git, and do not fetch history. When finished, issue the standalone command: '+FINISH
        steps=case.get('continuation_steps',4)
        orientation=''
        if case.get('show_candidate_diff'):
            current=trusted('git diff --no-ext-diff HEAD')
            orientation='\nCurrent candidate diff (already applied):\n'+current[:30000]+'\nInspect this candidate against the requirements; prioritize any concrete correction, or finish if it is sufficient. Avoid spending the entire budget locating files already shown here.\n'
        task=case['problem_statement']+'\nRequirements:\n'+case['requirements']+orientation+'\nInitial optional public verification feedback:\n'+json.dumps(feedback)+f'\nYou have at most {steps} model calls. Use the existing repository source and tests; no independent grading information is available.'
        agent=DefaultAgent(AgentModel(client),environment,system_template=system,instance_template='{{task}}',step_limit=steps,wall_time_limit_seconds=case.get('wall_seconds',240),cost_limit=0,output_path=folder/'trajectory.json')
        try:status=agent.run(task)
        except Exception as error:status={'exit_status':'error','error_type':type(error).__name__}
        agent.save(folder/'trajectory.json');record['agent_exit']=status.get('exit_status');record['model_calls']=agent.n_calls
        record['protocol_valid']=status.get('exit_status') not in {'error',None,'RepeatedFormatError'}
        trusted('git add -N -- .')
        files=trusted('git diff --name-only').splitlines();allowed=[p for p in files if allowed_source(p)]
        final_patch=trusted('git diff --no-ext-diff --binary HEAD -- '+' '.join(shlex.quote(p) for p in allowed)) if allowed else ''
        (folder/'final.patch').write_text(final_patch);record['final_patch_sha256']=hashlib.sha256(final_patch.encode()).hexdigest()
        grade=folder/'grading_source';clone_tree(Path(case['base']),grade)
        applied=patch(grade,final_patch) if final_patch else dict(exit_code=0)
        oracle=oracles[case['id']]
        hidden=patch(grade,oracle['test_patch']) if applied['exit_code']==0 else None
        if applied['exit_code'] or hidden is None or hidden['exit_code']:raise RuntimeError('Final grading patch preparation failed')
        command=['go','test','-mod=readonly','-count=1','-json','-run','^('+'|'.join(oracle['test_names'])+')$',*['./'+p for p in oracle['packages']]]
        result=check(grade,ROOT/'raw/utility_replay/go_buildcache',case['image'],command)
        write(folder/'private_grading.json',result)
        record.update(status='completed' if record['protocol_valid'] else 'agent_or_adapter_failure',scoped_quality=result['canonical']['quality'],grading_seconds=result['seconds'])
        if oracle.get('fixture_patch'):
            fixed=patch(grade,oracle['fixture_patch'])
            if fixed['exit_code']:raise RuntimeError('Fixture-complete grading preparation failed')
            secondary=check(grade,ROOT/'raw/utility_replay/go_buildcache',case['image'],command)
            write(folder/'private_fixture_grading.json',secondary)
            record['fixture_complete_quality']=secondary['canonical']['quality']
            record['fixture_grading_seconds']=secondary['seconds']
        else:record['fixture_complete_quality']=record['scoped_quality']
    except Exception as error:record.update(status='infrastructure_or_adapter_error',error_type=type(error).__name__,error=str(error)[:150])
    finally:
        if environment and environment.container_id:
            subprocess.run(['docker','rm','-f',environment.container_id],capture_output=True,timeout=15);environment.container_id=None
        record['total_wall_seconds']=time.monotonic()-start
        for name in ['work','agent_build_cache','grading_source']:
            target=folder/name
            if target.exists():shutil.rmtree(target)
        usage=[]
        if (folder/'api/usage.jsonl').exists():usage=[json.loads(s) for s in (folder/'api/usage.jsonl').read_text().splitlines()]
        record['api_attempts']=len(usage);record['usage_complete']=all(u.get('usage') is not None for u in usage)
        record['input_tokens']=sum((u.get('usage') or {}).get('prompt_tokens',0) for u in usage) if record['usage_complete'] else None
        record['output_tokens']=sum((u.get('usage') or {}).get('completion_tokens',0) for u in usage) if record['usage_complete'] else None
        write(summary,record)
    return record


def execute(env_file):
    logging.getLogger('agent').setLevel(logging.ERROR)
    plan=json.loads((OUT/'plan.json').read_text());cases={c['id']:c for c in json.loads((RAW/'cases.json').read_text())};oracles=json.loads((RAW/'private_oracles.json').read_text())
    budget=Budget(plan['max_api_attempts'],plan['max_accounted_tokens']);env=load_env(env_file)
    with ThreadPoolExecutor(max_workers=plan['workers']) as pool:
        futures=[pool.submit(episode,job,cases,oracles,env,budget) for job in plan['schedule']]
        for future in as_completed(futures):
            r=future.result();print(r['episode_id'],r['status'],r.get('scoped_quality'),'calls',r.get('api_attempts'),flush=True)
            write(OUT/'progress.json',dict(planned=len(plan['schedule']),finished=len(list((OUT/'episodes').glob('*.json'))),api_attempts=budget.requests,
                accounted_tokens_for_limit=budget.tokens,unknown_usage_attempts=budget.unknown_usage_attempts))


def smoke(env_file):
    from minisweagent.environments.docker import DockerEnvironment
    from minisweagent.agents.default import DefaultAgent
    logging.getLogger('agent').setLevel(logging.ERROR)
    folder=RAW/'adapter_smoke';folder.mkdir(parents=True,exist_ok=True)
    env=load_env(env_file);client=Client(env,'x-test-2',folder/'api',Budget(4,30000))
    environment=DockerEnvironment(image=IMAGE_TAG,cwd='/work',timeout=15,interpreter=['bash','-c'],
        run_args=['--rm','--network','none','--memory','512m','--cpus','1','--pids-limit','128','--cap-drop','ALL','--security-opt','no-new-privileges'],container_timeout='3m')
    try:
        agent=DefaultAgent(AgentModel(client),environment,
            system_template='You are testing an experimental tool adapter. Do not read or change files. Call the bash tool exactly once with the command: '+FINISH,
            instance_template='Complete the adapter check.',step_limit=2,wall_time_limit_seconds=90,cost_limit=0,output_path=folder/'trajectory.json')
        result=agent.run('');result['model_calls']=agent.n_calls
        write(OUT/'adapter_smoke.json',result);print(json.dumps(result),flush=True)
    finally:
        subprocess.run(['docker','rm','-f',environment.container_id],capture_output=True,timeout=15);environment.container_id=None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','smoke','execute']);parser.add_argument('--env-file');args=parser.parse_args()
    prepare() if args.phase=='prepare' else smoke(args.env_file) if args.phase=='smoke' else execute(args.env_file)
