"""Leave-one-source-file-out tests of passing submitted patches.

This measures a patch-file group's necessity under a fixed checker. It does not
estimate the utility of reading a file, an individual edit call, or a continuation.
"""
import json
from pathlib import Path
import shutil
import executable_panel as panel


def main():
    cases=json.loads((panel.OUT/'preparation.json').read_text())
    outcomes=json.loads((panel.OUT/'execution.json').read_text())
    passing={(r['case'],r['version']) for r in outcomes if r.get('quality')=='scoped_pass' and r['version'] in {'luna','gemini_3_7_flash'}}
    selected=[];links=[]
    for case in cases:
        folder=panel.RAW/f"case_{case['case']:02d}"
        versions=[]
        for model in ['luna','gemini_3_7_flash']:
            if (case['case'],model) not in passing:continue
            full=folder/f'eval_{model}';base=folder/'base'
            paths=[]
            for p in full.rglob('*.go'):
                relative=p.relative_to(full)
                if p.name.endswith('_test.go'):continue
                old=base/relative
                if not old.exists() or old.read_bytes()!=p.read_bytes():paths.append(relative)
            for index,relative in enumerate(sorted(paths)):
                name=f'ablate_{model}_{index:02d}'
                target=folder/f'eval_{name}'
                if target.exists():shutil.rmtree(target)
                shutil.copytree(full,target)
                old=base/relative;changed=target/relative
                if old.exists():shutil.copy2(old,changed)
                else:changed.unlink()
                versions.append(dict(version=name,preparation_ok=True))
                links.append(dict(case=case['case'],task_id=case['task_id'],model=model,version=name,
                    removed_source_file=str(relative),full_scoped_outcome='scoped_pass',
                    intervention='Restore this source file to base; leave independent evaluator tests and other patch files unchanged.',
                    attribution_unit='all submitted changes to one source file; not a single agent action'))
        if versions:selected.append(dict(case,versions=versions))
    (panel.OUT/'ablation_plan.json').write_text(json.dumps(links,indent=2)+'\n')
    results=panel.execute(cases=selected,output_name='ablation_execution.json')
    lookup={(r['case'],r['version']):r for r in results}
    for link in links:
        r=lookup[(link['case'],link['version'])];q=r.get('quality')
        link['ablated_scoped_outcome']=q
        link['tested_marginal_effect']='necessary_for_this_checker' if q=='scoped_fail' else 'necessary_for_suite_build' if q=='source_build_failure' else 'no_loss_detected_under_this_checker' if q=='scoped_pass' else 'unresolved'
        link['causal_action_utility']=None
    (panel.OUT/'ablation_summary.json').write_text(json.dumps(links,indent=2)+'\n')
    print('Completed',len(links),'patch-file ablations.')


if __name__=='__main__':main()
