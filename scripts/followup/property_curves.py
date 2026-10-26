"""Distinct-property curves only from reviewed normalized scope records.

A flat curve does not imply non-contribution: justified confidence can be direct
without adding a new property. Unknown scope is reported, not filled from commands.
"""
from collections import defaultdict
import pandas as pd
from followup_common import OUT,jsonl,dump


def accumulate(records):
    seen=defaultdict(set);counts=defaultdict(int);out=[]
    for r in records:
        key=(r['order'],r['blinded_label'],r['relevant_state_id'])
        counts[key]+=1
        properties=set(r['normalized_property_ids']) if r['contribution_label']=='direct' else set()
        new=properties-seen[key];seen[key]|=properties
        out.append(dict(order=r['order'],blinded_label=r['blinded_label'],relevant_state_id=r['relevant_state_id'],
                        component_id=r['component_id'],checks_in_state=counts[key],new_properties=len(new),
                        cumulative_distinct_supported_properties=len(seen[key]),contribution_label=r['contribution_label']))
    return out


def main():
    reviewed=jsonl(OUT/'verification_property_review.jsonl')
    index={r['component_id']:r for r in pd.read_csv(OUT/'verification_reason_audit.csv').to_dict('records')}
    approved=[];excluded=[]
    for r in reviewed:
        if (r.get('assessment_status')!='approved' or r.get('reviewer_type')!='human' or
            not r.get('reviewer_name') or not r.get('relevant_state_id') or not r.get('evidence') or
            r.get('contribution_label') not in ('direct','non_direct','uncertain')):
            excluded.append(r['component_id']);continue
        original=index[r['component_id']]
        approved.append(dict(r,order=int(original['order']),blinded_label=original['blinded_label']))
    # Input file order follows actual candidate chronology generated in the audit.
    if approved:
        pd.DataFrame(accumulate(approved)).to_csv(OUT/'property_coverage_curves.csv',index=False)
    else:
        pd.DataFrame(columns=['order','blinded_label','relevant_state_id','component_id','checks_in_state',
                              'new_properties','cumulative_distinct_supported_properties','contribution_label']).to_csv(
            OUT/'property_coverage_curves.csv',index=False)
    dump(OUT/'coverage_curve_status.json',dict(status='computed_on_reviewed_scope' if approved else 'pending_normalized_expert_property_state_review',
        reviewed_checks=len(approved),unassessable_or_unfilled_checks=len(excluded),excluded_component_ids=excluded,
        note='No command-string/property-text novelty proxy substituted for distinct supported properties. Flat coverage alone is not over-verification.'))


if __name__=='__main__':main()
