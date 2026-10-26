"""Prioritize consequential disagreements; prepare label-blind expert forms.

No semantic ground truth is generated. Expert forms are never overwritten.
"""
import json
import shutil
import numpy as np
import pandas as pd
from followup_common import ROOT,BASE,OUT,SEED,jsonl,dump,lines


def main():
    a=jsonl(BASE/'reconciled_component_annotations.jsonl')
    b={r['component_id']:r for r in jsonl(BASE/'component_annotations.jsonl')}
    c={r['component_id']:r for r in jsonl(BASE/'reviewer_c_component_annotations.jsonl')}
    n={};role_n={}
    for r in a:
        k=(r['order'],r['blinded_label'])
        n[k]=n.get(k,0)+(r['execution_status']!='not_executed')
        rk=(*k,r['role'])
        role_n[rk]=role_n.get(rk,0)+(r['execution_status']!='not_executed')
    rows=[]
    for r in a:
        x,y=b[r['component_id']],c[r['component_id']]
        disagree=x['contribution_label']!=y['contribution_label']
        assessable=(x['execution_status']==y['execution_status']=='executed' and
                    {x['contribution_label'],y['contribution_label']}=={'direct','non_direct'})
        rows.append(dict(component_id=r['component_id'],order=r['order'],blinded_label=r['blinded_label'],
            action_index=r['action_index'],component_index=r['component_index'],
            label_disagreement=disagree,role_disagreement=x['role']!=y['role'],
            execution_disagreement=x['execution_status']!=y['execution_status'],
            expert_assessable_disagreement=assessable,
            fixed_denominator_mean_bound_width=1/(8*n[(r['order'],r['blinded_label'])]),
            exploration_fixed_denominator_priority=(1/(8*max(1,role_n.get((r['order'],r['blinded_label'],'exploration'),0))))
                if 'exploration' in (x['role'],y['role']) else 0,
            verification_fixed_denominator_priority=(1/(8*max(1,role_n.get((r['order'],r['blinded_label'],'verification'),0))))
                if 'verification' in (x['role'],y['role']) else 0,
            b_label=x['contribution_label'],c_label=y['contribution_label'],b_role=x['role'],c_role=y['role'],
            b_requirements=x['requirement_ids'],c_requirements=y['requirement_ids'],
            b_evidence=x['evidence'],c_evidence=y['evidence'],command=r['command']))
    D=pd.DataFrame(rows)
    D=D.sort_values(['expert_assessable_disagreement','fixed_denominator_mean_bound_width','component_id'],ascending=[False,False,True])
    D.to_csv(OUT/'disagreement_priority.csv',index=False)
    candidates=D[D.label_disagreement|D.role_disagreement|D.execution_disagreement]
    candidates.to_csv(OUT/'all_disagreements_with_impact.csv',index=False)
    candidates.sort_values('verification_fixed_denominator_priority',ascending=False).to_csv(
        OUT/'verification_disagreement_priority.csv',index=False)
    candidates.sort_values('exploration_fixed_denominator_priority',ascending=False).to_csv(
        OUT/'exploration_disagreement_priority.csv',index=False)
    # Two assessable/high-impact disputes and two random agreements per task.
    # This enriched feasibility sample cannot establish population accuracy.
    rng=np.random.default_rng(SEED);selected=[]
    for order in range(3,11):
        g=D[D.order==order]
        dis=g[g.label_disagreement].head(2)
        controls=g[~(g.label_disagreement|g.role_disagreement|g.execution_disagreement)]
        controls=controls.iloc[rng.permutation(len(controls))[:2]]
        selected += [dict(r,selection='impact_disagreement') for r in dis.to_dict('records')]
        selected += [dict(r,selection='random_agreement_control') for r in controls.to_dict('records')]
    selected=[selected[i] for i in rng.permutation(len(selected))]
    expert=OUT/'expert_blind';expert.mkdir(exist_ok=True)
    form=[];private=[];packets=[]
    for i,s in enumerate(selected,1):
        cid=s['component_id'];r=next(x for x in a if x['component_id']==cid)
        case=f'case_{i:03d}';private.append(dict(case_id=case,**s))
        ev=json.loads((BASE/f"evidence_{r['order']:02d}.json").read_text())
        trajectory=next(x for x in ev if x['blinded_label']==r['blinded_label'])
        packets.append(dict(case_id=case,order=r['order'],blinded_label=r['blinded_label'],
                            action_index=r['action_index'],component_index=r['component_index'],
                            command=r['command'],directory_context=r.get('directory_context',[]),
                            parent_action=trajectory['actions'][r['action_index']],
                            full_trajectory_file=f"evidence_{r['order']:02d}.json"))
        form.append(dict(case_id=case,contribution_label=None,role=None,reason=None,requirement_ids=[],
                         evidence=None,execution_status=None,property_checked=None,earlier_check_ids=[],
                         relevant_state_changed=None,annotator_type=None,annotator_name=None,
                         uncertainty_reason=None,reference_review_status=None))
    lines(expert/'cases.jsonl',packets)
    if not (expert/'judgments.jsonl').exists():lines(expert/'judgments.jsonl',form)
    private=pd.DataFrame(private)
    if (OUT/'expert_private_key.csv').exists():
        previous=pd.read_csv(OUT/'expert_private_key.csv')
        assert previous[['case_id','component_id']].equals(private[['case_id','component_id']]),'Frozen expert cases changed'
    private.to_csv(OUT/'expert_private_key.csv',index=False)
    allform=[dict(component_id=r['component_id'],contribution_label=None,role=None,evidence=None,
                  requirement_ids=[],annotator_type=None,annotator_name=None) for r in a]
    if not (expert/'all_component_judgments.jsonl').exists():lines(expert/'all_component_judgments.jsonl',allform)
    references=[]
    src=ROOT/'results/one_day_precision_20261026/packets'
    for order in range(3,11):
        shutil.copyfile(BASE/f'evidence_{order:02d}.json',expert/f'evidence_{order:02d}.json')
        text=next(src.glob(f'{order:02d}_*.md')).read_text().split('## Run X:')[0]
        (expert/f'reference_{order:02d}.md').write_text(text)
        references.append(dict(order=order,requirements=[],conflicts=[],alternatives=[],preservation=[],
                               review_status=None,annotator_type=None,annotator_name=None))
    if not (expert/'requirement_reviews.jsonl').exists():lines(expert/'requirement_reviews.jsonl',references)
    (expert/'README.md').write_text(f'''# Independent expert packet

Review each task reference independently before contribution judgments. The
reference patch is one route, not an exact command or line prescription. Separate
repair from already-present behavior; retain conflicting requirements as uncertain.

Cases contain raw anonymous commands/agent-visible results and the final patch.
No prior contribution labels, candidate matches, computed states or model key are
included. Do not open files outside this directory until the independent pass is
saved. Run style/length can weaken identity blinding.

Use direct / non_direct / uncertain for every role. Passing/new/different is not
automatic direct credit. Cite concrete content, requirement and downstream support.
Unknown output/execution/attribution is uncertain. For verification record property,
earlier checks and relevant state; explain repeated support versus environment
failure or unrelated checking. Native output is shared; do not credit a whole
compound call because one component contributes.

Fill judgments.jsonl ({len(selected)} enriched cases) and requirement_reviews.jsonl. The
optional all_component_judgments.jsonl supports complete review of all 769 units.
State your actual annotator type/name; machine judgments are not human validation.
The enriched packet is a feasibility/reference audit, not a representative accuracy
sample. No blanks are treated as negative labels. Forms are preserved on reruns.
''')
    dump(OUT/'expert_packet_status.json',dict(cases=len(selected),tasks=8,full_components=len(a),
        status='prepared; awaiting independent expert judgments',
        priority_measure='absolute change in equal-task mean bound width at fixed component denominator; execution/role changes require separate sensitivity',
        target_cases=32,
        selection='up to 2 available high-impact label disagreements + 2 random agreements per task; seeded and label-blind packet',
        tasks_without_label_disagreements=[o for o in range(3,11) if not D[(D.order==o)&D.label_disagreement].shape[0]]))


if __name__=='__main__':main()
