"""Authored fixtures test bookkeeping, never empirical benchmark results."""
import pytest

from worktrace.checkpoints import summarize_checkpoints, validate_checkpoint


def checkpoint(i, status, snapshot=None):
    return dict(run_id='synthetic', occurrence_index=i, version_id=f'V{i}',
        status=status, evaluation_executed=status in {'pass', 'fail', 'timeout'},
        snapshot_sha256=snapshot or str(i) * 64, snapshot_complete=True,
        evaluation_kind='final_benchmark', environment_digest='sha256:fixture',
        evaluator_protocol_sha256='a' * 64, log_sha256='b' * 64,
        test_report='synthetic-fixture.json', reconstruction_evidence=['authored fixture'], exit_code=0)


def test_unknown_initial_and_no_passing_state_have_no_post_pass_spending():
    row, = summarize_checkpoints([checkpoint(0, 'not_evaluated'), checkpoint(1, 'fail'), checkpoint(2, 'timeout')])
    assert row['earliest_evaluated_passing_version'] is None
    assert row['post_pass_expenditure'] is None
    assert row['unevaluated'] == 2


def test_sparse_pass_fail_recovery_preserves_occurrences_and_does_not_infer_earliest_pass():
    rows = [checkpoint(0, 'not_evaluated'), checkpoint(1, 'pass'), checkpoint(2, 'fail'),
            checkpoint(3, 'pass'), checkpoint(4, 'pass', snapshot='1' * 64)]
    row, = summarize_checkpoints(rows)
    assert row['earliest_evaluated_passing_version'] == 'V1'
    assert row['later_evaluated_failures'] == ['V2']
    assert row['candidate_checkpoints'] == 5
    assert row['post_pass_expenditure'] is None


@pytest.mark.parametrize('field,value', [('evaluation_executed', False), ('snapshot_complete', False),
    ('snapshot_sha256', None), ('evaluator_protocol_sha256', None),
    ('environment_digest', None), ('test_report', None), ('log_sha256', None),
    ('evaluation_kind', 'agent_selected_test'), ('exit_code', 1)])
def test_pass_cannot_come_from_inferred_or_narrow_check(field, value):
    record = checkpoint(1, 'pass'); record[field] = value
    with pytest.raises(ValueError): validate_checkpoint(record)
