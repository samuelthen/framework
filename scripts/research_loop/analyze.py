"""Task-paired descriptive comparisons and partial-identification sensitivities."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'
SEED=20261028


def read(name):return [json.loads(s) for s in (OUT/name).read_text().splitlines() if s.strip()]
def ci(values):
    a=np.array([x for x in values if x is not None and np.isfinite(x)],dtype=float)
    if not len(a):return dict(n=0,mean=None,lo=None,hi=None)
    samples=np.random.default_rng(SEED).choice(a,size=(5000,len(a)),replace=True).mean(axis=1)
    return dict(n=len(a),mean=float(a.mean()),lo=float(np.quantile(samples,.025)),hi=float(np.quantile(samples,.975)))


def main():
    runs=read('runs.jsonl');pairs=read('verification_pairs.jsonl')
    for r in runs:
        n=r['native_calls'];c=r['candidate_components'];counts=r['candidate_component_counts']
        r['components_per_native_call']=c/n if n else None
        r['non_admin_candidates']=c-counts.get('administration',0)
        for metric in ['input_tokens','cached_input_tokens','output_tokens','cost_usd']:
            r[metric]=r['recorded_run_usage'][metric]
        for role in ['exploration','edit','verification','opaque_execution','mixed_call','administration']:
            r[f'{role}_native_share']=r['native_category_counts'].get(role,0)/n if n else None
            r[f'{role}_candidate_share']=counts.get(role,0)/c if c else None
        r['token_reconciles']=all(r['usage_residual'][m] is not None and abs(r['usage_residual'][m])<1e-6 for m in ['input_tokens','cached_input_tokens','output_tokens'])
    summary=[];contrasts=[];bounds=[];details=[]
    for split in ['discovery','confirmation','semantic_confirmation','legacy_development','all']:
        selected=[r for r in runs if split=='all' or r['split']==split]
        models={m:{r['task_id']:r for r in selected if r['model']==m} for m in ['gemini_3_7_flash','luna']}
        shared=sorted(set(models['gemini_3_7_flash'])&set(models['luna']))
        for scope in ['all_attempts','joint_success']:
            tasks=[t for t in shared if scope=='all_attempts' or all(models[m][t]['resolved'] is True for m in models)]
            for model,bytask in models.items():
                rs=[bytask[t] for t in tasks]
                metrics=['native_calls','candidate_components','non_admin_candidates','components_per_native_call',
                         'input_tokens','cached_input_tokens','output_tokens','cost_usd',
                         'exploration_candidate_share','verification_candidate_share','opaque_execution_candidate_share','mixed_call_candidate_share']
                for metric in metrics:
                    summary.append(dict(split=split,scope=scope,model=model,metric=metric,**ci([r[metric] for r in rs])))
            for metric in ['native_calls','candidate_components','non_admin_candidates','components_per_native_call','input_tokens','output_tokens']:
                differences=[models['gemini_3_7_flash'][t][metric]-models['luna'][t][metric] for t in tasks
                             if models['gemini_3_7_flash'][t][metric] is not None and models['luna'][t][metric] is not None]
                contrasts.append(dict(split=split,scope=scope,metric=metric,first='gemini_3_7_flash',second='luna',**ci(differences)))
            for role in ['exploration','edit','verification','opaque_execution','administration']:
                for metric in ['input_tokens','output_tokens']:
                    lo=[];hi=[];equal=[];call=[]
                    for task in tasks:
                        a=models['gemini_3_7_flash'][task];b=models['luna'][task]
                        x=a['operational_expenditure'][role][metric];y=b['operational_expenditure'][role][metric]
                        if any(v is None for v in [x['associated'],x['possible'],y['associated'],y['possible']]):continue
                        lo.append(x['associated']-y['possible']);hi.append(x['possible']-y['associated'])
                        equal.append(x['equal_candidate_allocated']-y['equal_candidate_allocated'])
                        call.append(a['candidate_component_counts'].get(role,0)/a['candidate_components']-b['candidate_component_counts'].get(role,0)/b['candidate_components'])
                    low=ci(lo);high=ci(hi)
                    bounds.append(dict(split=split,scope=scope,role=role,metric=metric,
                        lower_bound=low,upper_bound=high,equal_candidate_allocation_difference=ci(equal),candidate_share_difference=ci(call),
                        interpretation='Shares of stored response usage; descriptive association only; all-or-none bounds within mixed responses.'))
            for task in tasks:
                a=models['gemini_3_7_flash'][task];b=models['luna'][task]
                details.append(dict(split=split,scope=scope,task_id=task,
                    native_ratio=a['native_calls']/b['native_calls'] if b['native_calls'] else None,
                    candidate_ratio=a['candidate_components']/b['candidate_components'] if b['candidate_components'] else None,
                    token_output_ratio=a['output_tokens']/b['output_tokens'] if a['output_tokens'] is not None and b['output_tokens'] else None,gold_lines=a['gold_lines'],
                    native_difference=a['native_calls']-b['native_calls'],candidate_difference=a['candidate_components']-b['candidate_components']))
    retry=[]
    for split in ['discovery','confirmation','semantic_confirmation','all']:
        for model in ['luna','gemini_3_7_flash']:
            ps=[p for p in pairs if p['model']==model and (split=='all' or p['split']==split)]
            retry.append(dict(split=split,model=model,pairs=len(ps),runs=len({p['run_id'] for p in ps}),
                pairs_crossing_edit_or_opaque=sum(p['intervening_edit_or_opaque_call'] for p in ps),
                prior_status_counts=dict(Counter(p['prior_status'] for p in ps)),
                state_equality_certified=0,interpretation='Literal dedicated-check repeats only; no implicit/script verification or dependency identity claim.'))
    pd.DataFrame(summary).to_csv(OUT/'model_summary.csv',index=False)
    pd.DataFrame(contrasts).to_csv(OUT/'paired_contrasts.csv',index=False)
    pd.DataFrame(details).to_csv(OUT/'paired_details.csv',index=False)
    (OUT/'cost_share_bounds.json').write_text(json.dumps(bounds,indent=2)+'\n')
    (OUT/'repeat_diagnoses.json').write_text(json.dumps(retry,indent=2)+'\n')
    pd.DataFrame([{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in runs]).to_csv(OUT/'flat_runs.csv',index=False)
    reconciliation=dict(runs=len(runs),all_three_token_metrics_match=sum(r['token_reconciles'] for r in runs),
        per_model={m:dict(runs=sum(r['model']==m for r in runs),matching=sum(r['model']==m and r['token_reconciles'] for r in runs)) for m in sorted({r['model'] for r in runs})})
    (OUT/'reconciliation_summary.json').write_text(json.dumps(reconciliation,indent=2)+'\n')
    print(pd.DataFrame(summary).query("split=='confirmation' and scope=='all_attempts' and metric in ['native_calls','candidate_components','non_admin_candidates','components_per_native_call','output_tokens']").to_string(index=False))
    print('Reconciliation',reconciliation)


if __name__=='__main__':main()
