"""Prepare identical-context derived-state-aware/withheld inputs, never label.

Withheld means no computed state features, not that a reviewer cannot infer
state changes from the same preserved command history.
"""
import pandas as pd
from followup_common import ROOT,BASE,OUT,jsonl,dump,lines


def main():
    key=pd.read_csv(ROOT/'results/one_day_precision_20261026/packets/blinding_key.csv')
    runs={(int(r.order),r.label):r.run_id for r in key.itertuples()}
    facts=jsonl(OUT/'corrected_facts.jsonl')
    lookup={(r['run_id'],r['action_index']):r for r in facts}
    opids={r['op_id']:(r['run_id'],r['action_index']) for r in facts}
    cases=jsonl(OUT/'expert_blind/cases.jsonl')
    rows=[]
    for case in cases:
        rid=runs[(case['order'],case['blinded_label'])]
        f=lookup[(rid,case['action_index'])]
        feature={k:f[k] for k in ('kind','object','write','written_paths','state')}
        feature['basis']='rule-computed heuristic, not a verified content snapshot'
        feature['prior_candidate_facts']=[dict(earlier_action=opids[oid][1],**v) for oid,v in f['cand_facts'].items() if oid in opids]
        common=dict(case_id=case['case_id'],order=case['order'],blinded_label=case['blinded_label'],
                    component_index=case['component_index'],action_index=case['action_index'],command=case['command'],
                    context_file='expert_blind/'+case['full_trajectory_file'],
                    reference_file=f"expert_blind/reference_{case['order']:02d}.md",
                    requirement_source='expert_blind/requirement_reviews.jsonl; accepted human reference required',
                    previous_contribution_labels=None)
        rows.append(dict(**common,arm='derived_state_aware',derived_state_features=feature))
        rows.append(dict(**common,arm='derived_state_withheld',derived_state_features=None))
    lines(OUT/'paired_ablation_inputs.jsonl',rows)
    dump(OUT/'ablation_status.json',dict(status='inputs_prepared; no model annotations or expert accuracy run',
        paired_cases=len(cases),arms=['derived_state_aware','derived_state_withheld'],
        controls='same issue/reference, raw command history, final submitted patch, candidate unit, model/prompt settings; separate blinded sessions',
        limitation='Raw edits/order remain visible in both arms; this tests explicit derived-state augmentation, not complete inability to infer state.',
        required_next='Freeze expert references, run both arms with same annotator/settings in isolated sessions, compare paired errors/abstentions against human reference.'))


if __name__=='__main__':main()
