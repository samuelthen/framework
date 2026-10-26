"""Evaluate only supplied, attested human judgments; empty forms produce no accuracy."""
import pandas as pd
from followup_common import OUT,BASE,jsonl,dump


def accepted_requirements(row):
    return (row.get('annotator_type')=='human' and bool(row.get('annotator_name')) and
            row.get('review_status') in ('accepted','accepted_with_explicit_uncertainty') and
            bool(row.get('requirements')))


def accuracy_bounds(reference,predictions):
    pairs=[(a,b) for a,b in zip(reference,predictions) if a!='uncertain']
    n=len(pairs);u=sum(b=='uncertain' for a,b in pairs);correct=sum(a==b for a,b in pairs)
    return dict(assessable_reference_cases=n,reference_uncertain_cases=len(reference)-n,
                prediction_abstentions=u,accuracy_lower=correct/n if n else None,
                accuracy_upper=(correct+u)/n if n else None,
                prediction_coverage=(n-u)/n if n else None)


def main():
    expert=OUT/'expert_blind'
    ref={int(r['order']):r for r in jsonl(expert/'requirement_reviews.jsonl')}
    approved={o for o,r in ref.items() if accepted_requirements(r)}
    key=pd.read_csv(OUT/'expert_private_key.csv').set_index('case_id')
    supplied=[];pending=[]
    for r in jsonl(expert/'judgments.jsonl'):
        case=r['case_id'];o=int(key.loc[case,'order'])
        if (o not in approved or r.get('annotator_type')!='human' or not r.get('annotator_name') or
            r.get('contribution_label') not in ('direct','non_direct','uncertain') or not r.get('evidence') or
            r.get('role') not in ('exploration','edit','verification','administration') or
            r.get('execution_status') not in ('executed','not_executed','uncertain')):
            pending.append(case);continue
        supplied.append(dict(r,order=o,component_id=key.loc[case,'component_id']))
    status=dict(reference_status='pending' if pending else 'supplied_human_reference',
                approved_requirement_tasks=sorted(approved),valid_judgments=len(supplied),
                pending_cases=pending,human_reference_source='self-attested human names/type in preserved input forms',
                accuracy=None,note='No empty/machine-coded rows treated as expert ground truth. Enriched cases cannot establish population accuracy.')
    if supplied:
        annotations={r['component_id']:r for r in jsonl(BASE/'reconciled_component_annotations.jsonl')}
        rows=[]
        for r in supplied:
            pred=annotations[r['component_id']]['contribution_label']
            rows.append(dict(case_id=r['case_id'],component_id=r['component_id'],human=r['contribution_label'],
                             framework=pred,assessable=r['contribution_label']!='uncertain',
                             framework_abstains=pred=='uncertain'))
        pd.DataFrame(rows).to_csv(OUT/'expert_reference_comparison.csv',index=False)
        assess=[r for r in rows if r['assessable'] and not r['framework_abstains']]
        status['accuracy']=sum(r['human']==r['framework'] for r in assess)/len(assess) if assess else None
        status['scored_nonabstaining_cases']=len(assess)
    else:
        pd.DataFrame(columns=['case_id','component_id','human','framework','assessable','framework_abstains']).to_csv(
            OUT/'expert_reference_comparison.csv',index=False)
    # Coarse parent-call features are explicit proxies on the expert component
    # units, not mechanically projected ground-truth labels. Counts alone are
    # not an action classifier and receive no invented decision threshold.
    annotations={r['component_id']:r for r in jsonl(BASE/'reconciled_component_annotations.jsonl')}
    oldkey=pd.read_csv(BASE.parent/'one_day_precision_20261026/packets/blinding_key.csv')
    run={(int(r.order),r.label):r.run_id for r in oldkey.itertuples()}
    native=pd.read_csv(BASE/'baseline_diagnoses.csv').set_index(['run_id','action_index'])
    metrics=[]
    for name,col in [('framework',None),('parent_exact_repeat','predict_exact_repeat'),
                     ('parent_target_revisit','predict_target_revisit'),
                     ('parent_novelty_non_distinct','predict_novelty_non_distinct')]:
        truth=[];pred=[]
        for r in supplied:
            truth.append(r['contribution_label'])
            if col is None:pred.append(annotations[r['component_id']]['contribution_label']);continue
            k=key.loc[r['case_id']]
            value=native.loc[(run[(int(k.order),k.blinded_label)],int(k.action_index)),col]
            pred.append('uncertain' if pd.isna(value) else ('non_direct' if str(value).lower()=='true' else 'direct'))
        metrics.append(dict(method=name,**accuracy_bounds(truth,pred),
            interpretation='enriched expert cases only; parent-call proxies have coarser granularity; no population accuracy claim'))
    pd.DataFrame(metrics).to_csv(OUT/'expert_baseline_metrics.csv',index=False)
    ablation_path=OUT/'ablation_outputs.jsonl'
    ablation_status='no annotator outputs; input specifications only'
    if ablation_path.exists() and supplied:
        outputs=jsonl(ablation_path);lookup={(r['case_id'],r['arm']):r for r in outputs}
        assert len(lookup)==len(outputs),'duplicate ablation case/arm'
        paired=[]
        for r in supplied:
            x=lookup.get((r['case_id'],'derived_state_aware'));y=lookup.get((r['case_id'],'derived_state_withheld'))
            if x is None or y is None:continue
            assert x.get('model_id') and x.get('settings_sha256')
            assert (x['model_id'],x['settings_sha256'])==(y.get('model_id'),y.get('settings_sha256')),'uncontrolled ablation settings'
            assert x['contribution_label'] in ('direct','non_direct','uncertain')
            assert y['contribution_label'] in ('direct','non_direct','uncertain')
            paired.append(dict(case_id=r['case_id'],order=r['order'],reference=r['contribution_label'],
                               aware=x['contribution_label'],withheld=y['contribution_label']))
        pd.DataFrame(paired).to_csv(OUT/'paired_ablation_reference_comparison.csv',index=False)
        ablation_status=f'{len(paired)} complete paired expert-reference cases; enriched sample'
    dump(OUT/'expert_baseline_status.json',dict(human_reference_cases=len(supplied),
        methods=[r['method'] for r in metrics],call_counts='effort only; not an action classifier',
        ablation=ablation_status,scope='reference and prediction uncertainty reported separately; never fill blank labels'))
    dump(OUT/'expert_validation_status.json',status)


if __name__=='__main__':main()
