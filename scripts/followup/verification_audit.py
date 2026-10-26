"""Separate repeated-support evidence from environment/unrelated checks.

Tags explain existing labels; they never substitute for the contribution label.
No distinct-property coverage is inferred from command-string novelty.
"""
import json
import re
import pandas as pd
from followup_common import BASE,OUT,jsonl,dump,lines

ENV=re.compile(r'command not found|no module named|modulenotfounderror|cannot find module|unable to (?:connect|open display)|could not connect to display|no tests (?:ran|collected)|collected 0 items|bad substitution|connection refused|cannot run \*_test.go',re.I)


def classify(x,y,label,output,prior):
    environment=bool(ENV.search(output))
    previous=set(x.get('earlier_check_ids',[]))&set(y.get('earlier_check_ids',[]))
    established=[p for p in previous if p in prior and
                 prior[p][0]['contribution_label']==prior[p][1]['contribution_label']=='direct']
    repeat=(x.get('verification_gain')==y.get('verification_gain')=='repeated_support')
    unchanged=(x.get('relevant_state_changed')==y.get('relevant_state_changed')=='unchanged')
    reason=' '.join(str(r.get('reason','')) for r in (x,y))
    if label=='direct':category='contributing_verification'
    elif label=='uncertain':category='uncertain_contribution'
    elif environment:category='environment_or_setup_failure_candidate'
    elif repeat and unchanged and established:category='supported_repeated_support'
    elif repeat:category='repeated_support_needs_property_state_review'
    elif re.search(r'unrelated|ratings|nonbehavioral',reason,re.I):category='unrelated_or_nonbehavioral_check'
    else:category='other_non_direct'
    return category,environment,established


def main():
    a=jsonl(BASE/'reconciled_component_annotations.jsonl')
    b={r['component_id']:r for r in jsonl(BASE/'component_annotations.jsonl')}
    c={r['component_id']:r for r in jsonl(BASE/'reviewer_c_component_annotations.jsonl')}
    prior={k:(b[k],c[k]) for k in b}
    evidence={o:json.loads((BASE/f'evidence_{o:02d}.json').read_text()) for o in range(3,11)}
    key=pd.read_csv(BASE.parent/'one_day_precision_20261026/packets/blinding_key.csv')
    key={(int(r.order),r.label):r.model for r in key.itertuples()}
    rows=[];properties=[]
    for r in a:
        if r['role']!='verification' or r['execution_status']=='not_executed':continue
        x,y=b[r['component_id']],c[r['component_id']]
        run=next(z for z in evidence[r['order']] if z['blinded_label']==r['blinded_label'])
        op=run['actions'][r['action_index']]
        category,env,previous=classify(x,y,r['contribution_label'],op['output'],prior)
        rows.append(dict(component_id=r['component_id'],order=r['order'],blinded_label=r['blinded_label'],
                         model=key[(r['order'],r['blinded_label'])],contribution_label=r['contribution_label'],
                         reason_category=category,environment_cue_in_parent_output=env,
                         command=r['command'],earlier_supported_check_ids=previous,
                         b_property=x.get('property_checked'),c_property=y.get('property_checked'),
                         b_state=x.get('relevant_state_changed'),c_state=y.get('relevant_state_changed'),
                         b_evidence=x['evidence'],c_evidence=y['evidence'],
                         execution_status=r['execution_status'],
                         diagnostic_status='model-coded evidence screen; property normalization/expert check pending'))
        properties.append(dict(component_id=r['component_id'],normalized_property_ids=[],relevant_paths=[],
                               state_basis=None,relevant_state_id=None,contribution_label=None,
                               new_supported_property=None,defect_used_in_repair=None,
                               environment_failure=None,earlier_equivalent_check_ids=[],reviewer_type=None,
                               reviewer_name=None,evidence=None,assessment_status=None))
    R=pd.DataFrame(rows);R.to_csv(OUT/'verification_reason_audit.csv',index=False)
    R.groupby(['model','contribution_label','reason_category']).size().rename('components').reset_index().to_csv(
        OUT/'verification_reason_counts.csv',index=False)
    R[R.reason_category=='supported_repeated_support'].to_csv(OUT/'repeated_support_screen.csv',index=False)
    forms=OUT/'verification_property_review.jsonl'
    if not forms.exists():lines(forms,properties)
    else:
        # Extend an untouched blank template only; never erase a reviewer's work.
        existing=jsonl(forms)
        if all(not v for r in existing for k,v in r.items() if k!='component_id'):
            lines(forms,properties)
    dump(OUT/'property_coverage_status.json',{
        'verification_candidates':len(rows),
        'supported_repeat_screen':int((R.reason_category=='supported_repeated_support').sum()),
        'property_saturation_curve':'not_identifiable_until_normalized_properties_and_relevant_states_are_reviewed',
        'command_variety_is_coverage':False,
        'strict_repeat_screen':'non_direct in reconciliation; both repeated_support; both unchanged; common earlier check direct in both; no environment cue',
        'caution':'Shared parent outputs can mix causes. Screen is a review aid, not a validated suppression target. Environment failures are never counted in the repeated-support screen.'})


if __name__=='__main__':main()
