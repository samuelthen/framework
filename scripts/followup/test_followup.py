import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from policy import Request,PropertyStatePolicy,CheckCountCap
from verification_audit import classify
from property_curves import accumulate
from expert_gate import accepted_requirements,accuracy_bounds


def req(prop='empty_input',digest='hash1',**kwargs):
    return Request(prop,digest,scope_complete=True,deterministic=True,state_basis='content_snapshot',**kwargs)


def establish(p,r):
    assert p.decide(r).allow
    p.observe(r,completed=True,passed=True,property_assessed=True)


def test_first_check_allowed_and_first_established_repeat_suppressed():
    p=PropertyStatePolicy(1);r=req();establish(p,r)
    assert not p.decide(r).allow


def test_new_property_and_relevant_edit_reset_streak():
    p=PropertyStatePolicy(2);a=req();establish(p,a);establish(p,a)
    assert not p.decide(a).allow
    assert p.decide(req('unicode')).allow
    assert p.decide(a).allow
    p.on_edit(['empty_input'])
    assert p.decide(a).allow


def test_unknown_state_or_heuristic_version_never_suppresses():
    p=PropertyStatePolicy(1);establish(p,req())
    assert p.decide(Request('empty_input','hash1',True,True,True,'inferred_version_graph')).allow
    assert p.decide(Request('empty_input',None)).allow


def test_new_content_and_incomplete_result_allow_more_checks():
    p=PropertyStatePolicy(1);r=req();establish(p,r)
    assert p.decide(req(digest='newhash')).allow
    p.observe(r,completed=False,passed=False,property_assessed=False)
    assert p.decide(r).allow


def test_mixed_call_is_not_partially_suppressed():
    p=PropertyStatePolicy(1);establish(p,req())
    assert p.decide(req(dedicated_verification=False)).allow


def test_passing_without_known_property_is_not_established_support():
    p=PropertyStatePolicy(1);r=req()
    p.observe(r,completed=True,passed=True,property_assessed=False)
    assert p.decide(r).allow


def test_future_fields_are_not_accepted_by_prefix_api():
    with pytest.raises(TypeError):Request('p','hash',final_patch='future')


def test_simple_cap_can_block_new_property_while_state_policy_allows():
    p=PropertyStatePolicy(1);cap=CheckCountCap(1);r=req();establish(p,r);cap.observe(r)
    assert not cap.decide(req('other')).allow
    assert p.decide(req('other')).allow


def test_environment_failure_cannot_be_a_supported_repeat():
    r=dict(verification_gain='repeated_support',relevant_state_changed='unchanged',earlier_check_ids=['old'],reason='repeated_support')
    old=dict(contribution_label='direct')
    category,env,_=classify(r,r,'non_direct','ModuleNotFoundError: No module named x',{'old':(old,old)})
    assert env and category!='supported_repeated_support'


def test_missing_state_and_prior_support_prevent_repeat_confirmation():
    r=dict(verification_gain='repeated_support',relevant_state_changed='uncertain',earlier_check_ids=[],reason='repeat')
    assert classify(r,r,'non_direct','1 passed',{})[0]=='repeated_support_needs_property_state_review'


def test_distinct_property_curve_resets_by_assessed_state_and_keeps_confidence_direct():
    rows=[]
    for i,(state,label,props) in enumerate([('A','direct',['p']),('A','direct',['p']),
                                          ('A','direct',['q']),('B','direct',['p']),('B','uncertain',['q'])]):
        rows.append(dict(order=3,blinded_label='X',component_id=str(i),relevant_state_id=state,
                         contribution_label=label,normalized_property_ids=props))
    out=accumulate(rows)
    assert [r['cumulative_distinct_supported_properties'] for r in out]==[1,1,2,1,1]
    assert out[1]['contribution_label']=='direct'  # flat does not mean non_direct


def test_machine_or_empty_reference_cannot_pass_human_gate():
    assert not accepted_requirements({'annotator_type':'model','annotator_name':'Codex',
                                     'review_status':'accepted','requirements':['R1']})
    assert not accepted_requirements({'annotator_type':'human','annotator_name':'Reviewer',
                                     'review_status':'accepted','requirements':[]})


def test_missing_expert_labels_produce_no_accuracy_not_zero_accuracy():
    r=accuracy_bounds([],[])
    assert r['accuracy_lower'] is None and r['prediction_coverage'] is None


def test_abstention_bounds_keep_assessable_reference_denominator():
    r=accuracy_bounds(['direct','non_direct','uncertain'],['direct','uncertain','direct'])
    assert r['assessable_reference_cases']==2 and r['reference_uncertain_cases']==1
    assert r['accuracy_lower']==.5 and r['accuracy_upper']==1


def test_equivalent_call_packaging_has_same_shell_component_inventory():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'precision_validation'))
    from prepare import components
    together=[r['command'] for r in components('cat A.py && pytest test_a.py')]
    separate=[r['command'] for cmd in ['cat A.py','pytest test_a.py'] for r in components(cmd)]
    assert together==separate


def test_alternative_mean_repairs_share_required_behavior():
    def a(xs):return sum(xs)/len(xs) if xs else 0
    def b(xs):
        if len(xs)==0:return 0
        return sum(xs)/len(xs)
    for values,expected in [([],0),([3],3),([2,4],3),([-2,2],0)]:
        assert a(values)==b(values)==expected


def test_frozen_expert_case_count_matches_forms_and_metadata():
    import json
    from followup_common import OUT,jsonl
    status=json.loads((OUT/'expert_packet_status.json').read_text())
    assert len(jsonl(OUT/'expert_blind/cases.jsonl'))==status['cases']
    assert len(jsonl(OUT/'expert_blind/judgments.jsonl'))==status['cases']
