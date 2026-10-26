"""Measurement regressions: packaging, opaque syntax, uncertainty and state."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/precision_validation'))
from prepare import components
from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph
from analyze import score, project_native, validate_review
from compare_reviewers import reconcile
import pytest


def test_quote_and_heredoc_bodies_do_not_inflate_denominator():
    command = 'cd /app && python -c "print(1); print(2)"; cat > a.py <<\'PY\'\nprint(3); print(4)\nPY\npytest'
    c = components(command)
    assert len(c) == 3
    assert c[0]['directory_context'] == ['cd /app']
    assert c[-1]['command'] == 'pytest'


def test_pipeline_and_control_flow_are_meaningful_units():
    c = components('cat a.py | head -10; if grep foo a.py; then echo yes; else echo no; fi; pytest')
    assert len(c) == 3
    assert c[0]['command'] == 'cat a.py | head -10'
    assert c[1]['command'].startswith('if ') and c[1]['command'].endswith('fi')


def test_invalid_attempt_is_not_fictitious_performed_commands():
    assert len(components('python -c "broken\nprint(1); print(2)')) == 1


def test_command_substitution_does_not_swallow_following_command():
    assert len(components('echo $(cat a.py); pytest')) == 2


def records(cmds):
    return extract_facts([dict(op_id=f'op{i}', turn_id=f't{i}', command=c, output=o, exit_code=e)
                          for i, (c, o, e) in enumerate(cmds)])


def test_known_path_and_unknown_additional_effects_both_survive():
    r = records([('cat A.py', 'A' * 30, 0), ('cat B.py', 'B' * 30, 0),
                 ('echo x > A.py && python opaque.py', '', 0), ('cat A.py', 'A' * 30, 0), ('cat B.py', 'B' * 30, 0)])
    assert r[2]['write'] == 'unknown' and 'A.py' in r[2]['written_paths']
    assert r[3]['cand_facts']['op0']['object_written_since'] == 'yes'
    assert r[4]['cand_facts']['op1']['object_written_since'] == 'unknown'


def test_path_like_branch_does_not_prove_restoration():
    r = records([('sed -i s/x/y/ a.py', '', 0), ('git checkout release.py', '', 0)])
    g = build_version_graph(dict(run_id='r', task_id='t', model='m'), r)
    assert g['final'] != 0 and r[-1]['write'] == 'unknown'


def test_stash_restores_dirty_paths_for_subsequent_partial_restore():
    r = records([('sed -i s/x/y/ a.py', '', 0), ('sed -i s/x/y/ b.py', '', 0),
                 ('git stash', 'saved', 0), ('git stash pop', '', 0), ('git checkout -- a.py', '', 0)])
    g = build_version_graph(dict(run_id='r', task_id='t', model='m'), r)
    assert g['final'] != 0  # b.py remains dirty


def test_verification_uses_same_precision_and_keeps_uncertainty():
    s = score([{'role': 'verification', 'contribution_label': x}
               for x in ['direct', 'non_direct', 'uncertain']])
    assert s['N'] == 3 and s['D'] == 1 and s['ND'] == 1 and s['U'] == 1
    assert s['P_lower'] == pytest.approx(1/3) and s['P_upper'] == pytest.approx(2/3)


def test_known_skipped_branches_do_not_inflate_performed_denominator():
    s = score([{'contribution_label': 'direct', 'execution_status': 'executed'},
               {'contribution_label': 'non_direct', 'execution_status': 'not_executed'},
               {'contribution_label': 'uncertain', 'execution_status': 'uncertain'}])
    assert s['N'] == 2 and s['P_lower'] == .5 and s['P_upper'] == 1


def test_strongest_call_projection_does_not_copy_credit_to_components():
    rows = [{'contribution_label': 'direct'}, {'contribution_label': 'non_direct'},
            {'contribution_label': 'uncertain'}]
    assert project_native(rows) == 'direct'
    assert score(rows)['P_lower'] == pytest.approx(1/3)


def test_missing_component_cannot_silently_improve_precision():
    inventory = [{'blinded_label': 'X', 'action_index': 0, 'component_index': i} for i in (0,1)]
    with pytest.raises(AssertionError, match='incomplete components'):
        validate_review({'requirements': [], 'components': []}, inventory)


def review(label='direct', execution='executed', role='edit', reqs=None):
    return {'contribution_label': label, 'execution_status': execution, 'role': role,
            'requirement_ids': ['R1'] if reqs is None else reqs, 'reason': 'supported_edit',
            'evidence': 'specific edit/output and retained patch', 'uncertainty_reason': None}


def test_disagreement_widens_uncertainty_instead_of_majority_vote():
    r = reconcile(review(), review(label='non_direct'))
    assert r['contribution_label'] == 'uncertain'
    assert score([r])['P_lower'] == 0 and score([r])['P_upper'] == 1


def test_unexecuted_exclusion_requires_both_reviewers():
    a = review(label='non_direct', execution='not_executed')
    assert score([reconcile(a, a)])['N'] == 0
    r = reconcile(a, review(label='non_direct'))
    assert r['execution_status'] == 'uncertain' and score([r])['N'] == 1


def test_verification_membership_disagreement_cannot_earn_certain_credit():
    r = reconcile(review(role='verification'), review(role='exploration'))
    assert r['role'] == 'verification' and r['contribution_label'] == 'uncertain'


def test_direct_agreement_needs_shared_requirement_scope():
    r = reconcile(review(reqs=['R1']), review(reqs=['R2']))
    assert r['contribution_label'] == 'uncertain'
