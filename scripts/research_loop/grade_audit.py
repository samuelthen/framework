"""Regrade saved candidates in two explicit contexts without model calls.

The exact context applies only the dataset's test patch. The fixture-complete
sensitivity adds reference testdata assets to every candidate equally. Neither
context is claimed to reproduce the original benchmark harness.
"""
import json
from pathlib import Path
import shutil
import live_pilot as live

ROOT=live.ROOT
OUT=ROOT/'results/research_loop_20261028/grading_audit'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cases={c['id']:c for c in json.loads((ROOT/'raw/live_utility_v2/cases.json').read_text())}
    oracles=json.loads((ROOT/'raw/live_utility_v2/private_oracles.json').read_text())
    rows=[]
    candidates=[(c,'initial',None) for c in cases]
    for folder in sorted((ROOT/'raw/live_utility/episodes').glob('*')):
        if (folder/'final.patch').exists():
            case=folder.name.split('_x-test-')[0]
            candidates.append((case,folder.name,folder/'final.patch'))
    for name,identifier,patchfile in candidates:
        case=cases[name];oracle=oracles[name]
        target=ROOT/'raw/grading_audit'/identifier
        target.parent.mkdir(parents=True,exist_ok=True)
        live.clone_tree(Path(case['source']) if patchfile is None else Path(case['base']),target)
        try:
            prep=live.patch(target,patchfile.read_text()) if patchfile else {'exit_code':0}
            test=live.patch(target,oracle['test_patch']) if prep['exit_code']==0 else None
            if test is None or test['exit_code']:
                rows.append(dict(case=name,candidate=identifier,status='preparation_failed'));continue
            command=['go','test','-mod=readonly','-count=1','-json','-run','^('+'|'.join(oracle['test_names'])+')$',*['./'+p for p in oracle['packages']]]
            for context in ['exact_test_patch','fixture_complete']:
                if context=='fixture_complete' and not oracle.get('fixture_patch'):continue
                if context=='fixture_complete':
                    applied=live.patch(target,oracle['fixture_patch'])
                    if applied['exit_code']:raise RuntimeError('Fixture sensitivity patch failed')
                result=live.check(target,ROOT/'raw/utility_replay/go_buildcache',case['image'],command)
                live.write(ROOT/'raw/grading_audit_logs'/identifier/(context+'.json'),result)
                rows.append(dict(case=name,candidate=identifier,context=context,status=result['status'],quality=result['canonical']['quality'],
                    seconds=result['seconds'],tests=result['canonical']['test_outcomes']))
        finally:shutil.rmtree(target)
        live.write(OUT/'outcomes.json',rows)
        print(identifier,[(r['context'],r['quality']) for r in rows if r['candidate']==identifier],flush=True)
    live.write(OUT/'outcomes.json',rows)


if __name__=='__main__':main()
