"""Independent scoped checks on every Flipt task in the frozen attempt panel.

Selection is fixed before local execution; include failures and incompatible
environments in the coverage report. Recorded agent commands are never run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/utility_audit'))
from prepare_inputs import extract_archive
from container_checks import IMAGE
IMAGE_124='golang@sha256:2d40d4fc278dad38be0777d5e2a88a2c6dee51b0b29c97a764fc6c6a11ca893c'

OUT=ROOT/'results/research_loop_20261028/executable_panel'
RAW=ROOT/'raw/research_executable'


def scoped_quality(code,status,stdout,stderr,events):
    """Fail closed on infrastructure; distinguish test and source-build failure."""
    text=(stdout+stderr).decode(errors='replace')
    if status!='completed' or any(s in text for s in ['signal: killed','no space left on device','module lookup disabled by GOPROXY=off','missing go.sum entry','updates to go.mod needed','requires go >=']):return None
    if code==0:return 'scoped_pass'
    if any(e.get('Action')=='fail' for e in events):return 'scoped_fail'
    if re.search(r'undefined[: ]|has no field or method|unknown field|cannot use |not enough arguments|too many arguments|does not implement|imported and not used|declared and not used',text):return 'source_build_failure'
    return 'build_or_setup_unresolved'


def patch(target,text):
    for line in text.splitlines():
        if line.startswith(('--- ','+++ ')):
            path=line[4:].split('\t')[0]
            if path=='/dev/null':continue
            path=path[2:] if path.startswith(('a/','b/')) else path
            p=Path(path)
            if p.is_absolute() or '..' in p.parts or '.git' in p.parts:raise ValueError('Unsafe patch path')
    r=subprocess.run(['patch','--batch','--fuzz=0','--forward','-p1','-d',str(target)],input=text,text=True,capture_output=True)
    return dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)


def prepare():
    OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
    plan=json.loads((OUT.parent/'analysis_plan.json').read_text())
    tasks=sorted(t for t in plan['model_confirmation_tasks'] if 'instance_flipt-io__flipt-' in t)
    refs={r['instance_id']:r for r in pq.read_table(ROOT/'raw/swebenchpro/v1.parquet').to_pylist() if r['instance_id'] in tasks}
    submissions={}
    for model in ['luna','gemini_3_7_flash']:
        rows=pq.read_table(ROOT/f'raw/jetbrains/{model}-run1.parquet',columns=['instance_id','submission','resolved']).to_pylist()
        submissions[model]={r['instance_id']:r for r in rows if r['instance_id'] in tasks}
    records=[]
    for i,task in enumerate(tasks):
        ref=refs[task];folder=RAW/f'case_{i:02d}';folder.mkdir(exist_ok=True)
        archive=folder/'base.tar.gz'
        if not archive.exists():
            with urllib.request.urlopen(f"https://codeload.github.com/{ref['repo']}/tar.gz/{ref['base_commit']}",timeout=60) as source,archive.open('wb') as dest:shutil.copyfileobj(source,dest)
        if not (folder/'base').exists():extract_archive(archive,folder/'base')
        gomod=(folder/'base/go.mod').read_text()
        packages=sorted({str(Path(s[6:]).parent) for s in ref['test_patch'].splitlines() if s.startswith('+++ b/') and s.endswith('_test.go')})
        names=json.loads(ref['selected_test_files_to_run'])
        if any(not re.fullmatch(r'Test\w+',n) for n in names):raise ValueError('Unexpected selected-test identifier')
        versions=[]
        for name in ['base','luna','gemini_3_7_flash','reference']:
            target=folder/f'eval_{name}'
            if target.exists():shutil.rmtree(target)
            shutil.copytree(folder/'base',target)
            submitted=None if name=='base' else ref['patch'] if name=='reference' else submissions[name][task]['submission']
            applied=patch(target,submitted) if submitted else None
            testing=patch(target,ref['test_patch']) if applied is None or applied['exit_code']==0 else None
            versions.append(dict(version=name,patch=applied,test_patch=testing,
                recorded_resolved=submissions[name][task]['resolved'] if name in submissions else None,
                preparation_ok=(applied is None or applied['exit_code']==0) and testing is not None and testing['exit_code']==0))
        records.append(dict(case=i,task_id=task,base_commit=ref['base_commit'],archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            go_version=re.search(r'(?m)^go (\S+)',gomod).group(1),packages=packages,test_names=names,versions=versions,
            checker='fixed selected evaluator test names in packages changed by independent test patch',source='frozen all-attempt panel; all five matching repository tasks retained'))
        print('Prepared',i,task,'Go',records[-1]['go_version'],flush=True)
    (OUT/'preparation.json').write_text(json.dumps(records,indent=2)+'\n')


def execute(modules=False,cases=None,output_name=None):
    if cases is None:cases=json.loads((OUT/'preparation.json').read_text())
    output_name=output_name or ('module_preparation.json' if modules else 'execution.json')
    records=[]
    (OUT/'logs').mkdir(exist_ok=True)
    for case in cases:
        version_tuple=tuple(int(s) for s in case['go_version'].split('.')[:2])
        for snapshot in case['versions']:
            image=IMAGE if version_tuple<=(1,20) else IMAGE_124
            record=dict(case=case['case'],task_id=case['task_id'],version=snapshot['version'],image=image)
            if modules and snapshot['version'] not in {'reference','base'}:continue
            if shutil.disk_usage(ROOT).free<3*1024**3:
                record.update(status='disk_reserve_limit',quality=None);records.append(record);continue
            if not snapshot['preparation_ok'] or version_tuple>(1,24):
                record.update(status='patch_preparation_unavailable' if not snapshot['preparation_ok'] else 'go_version_incompatible',quality=None)
                records.append(record);continue
            work=RAW/f"case_{case['case']:02d}/eval_{snapshot['version']}"
            name=f"worktrace-panel-{case['case']}-{snapshot['version'].replace('_','-')}-{time.time_ns()}"
            command=['go','test','-mod=readonly','-count=1','-json','-run','^('+'|'.join(case['test_names'])+')$',*['./'+p for p in case['packages']]]
            if modules:command=['go','list','-mod=readonly','-deps','-test',*['./'+p for p in case['packages']]]
            args=['docker','run','--rm','--name',name,'--cpus=2','--memory=2g','--pids-limit=256','--cap-drop=ALL','--security-opt=no-new-privileges','--network=none',
                '--mount',f'type=bind,src={work},dst=/source,readonly','--tmpfs','/work:rw,size=256m',
                '--mount',f'type=bind,src={ROOT}/raw/utility_replay/go_modcache,dst=/go/pkg/mod',
                '--mount',f'type=bind,src={ROOT}/raw/utility_replay/go_buildcache,dst=/gocache',
                '-e','GOCACHE=/gocache','-e','CGO_ENABLED=0','-e','GOPROXY=off','-e','GOTOOLCHAIN=local','-w','/work',
                image,'sh','-c','cp -a /source/. /work/ && exec "$@"','panel-check',*command]
            if modules:
                args.remove('--network=none');args[args.index('GOPROXY=off')]='GOPROXY=https://proxy.golang.org,direct'
            start=time.monotonic()
            try:
                r=subprocess.run(args,capture_output=True,timeout=240 if modules else 120);code=r.returncode;stdout=r.stdout;stderr=r.stderr;status='completed'
            except subprocess.TimeoutExpired as e:
                subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
                code=None;stdout=e.stdout or b'';stderr=e.stderr or b'';status='timeout'
            stem=f"case_{case['case']:02d}_{snapshot['version']}"
            if modules:stem+='_modules'
            (OUT/f'logs/{stem}.stdout.txt').write_bytes(stdout);(OUT/f'logs/{stem}.stderr.txt').write_bytes(stderr)
            combined=(stdout+stderr).decode(errors='replace')
            blocked=any(s in combined for s in ['module lookup disabled by GOPROXY=off','missing go.sum entry','updates to go.mod needed','requires go >='])
            events=[]
            for line in stdout.decode(errors='replace').splitlines():
                try:e=json.loads(line)
                except ValueError:continue
                if e.get('Test') and e.get('Action') in ['pass','fail','skip']:events.append({k:e[k] for k in ['Test','Action']})
            record.update(status='dependency_unavailable' if blocked else status,exit_code=code,seconds=time.monotonic()-start,command=command,
                quality=None if modules or blocked else scoped_quality(code,status,stdout,stderr,events),
                phase='module_preparation' if modules else 'independent_scoped_test',
                events=events,stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest())
            records.append(record);print(stem,record['status'],record['quality'],flush=True)
            (OUT/output_name).write_text(json.dumps(records,indent=2)+'\n')
    (OUT/output_name).write_text(json.dumps(records,indent=2)+'\n')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','modules','execute']);a=parser.parse_args()
    prepare() if a.phase=='prepare' else execute(modules=a.phase=='modules')
