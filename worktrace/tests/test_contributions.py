from copy import deepcopy

import pytest

from worktrace.contributions import apply_reviews, command_sha, contribution_score, review_sample


def component(cid, position, label='non_direct', role='exploration', trajectory='X'):
    return dict(component_id=cid, order=3, blinded_label=trajectory,
                action_index=position, component_index=0, command=f'read {cid}', role=role,
                contribution_label=label, execution_status='executed')


def review(c, label, links=None):
    return dict(component_id=c['component_id'], source_command_sha256=command_sha(c),
                assessment_status='reviewed', contribution_label=label,
                supporting_component_ids=links or [], reviewer_type='model',
                reviewer_name='test fixture, not real annotation', evidence='Authored fixture evidence')


def test_pending_review_does_not_turn_legacy_into_zero_contribution():
    source = [component('a', 0), component('b', 1, 'direct'), component('c', 2, 'uncertain')]
    saved = deepcopy(source)
    pending = review_sample(source)
    result = apply_reviews(source, pending)
    assert source == saved
    assert result[0]['contribution_label'] == 'non_direct'
    score = contribution_score(result)
    assert score['legacy_non_direct'] == 1 and score['no_demonstrated'] == 0
    assert score['lower'] == pytest.approx(1/3) and score['upper'] == pytest.approx(2/3)


def test_review_keeps_indirect_none_and_uncertain_separate_with_original_labels():
    source = [component('a', 0), component('b', 1, 'direct'),
              component('c', 2, 'uncertain'), component('d', 3)]
    result = apply_reviews(source, [review(source[0], 'indirect', ['b']),
                                    review(source[3], 'no_demonstrated')])
    assert result[0]['archived_contribution_label'] == 'non_direct'
    score = contribution_score(result)
    assert [score[k] for k in ['direct', 'indirect', 'no_demonstrated', 'uncertain']] == [1, 1, 1, 1]
    assert score['reviewed'] == 2 and score['legacy_non_direct'] == 0
    assert (score['lower'], score['upper']) == (.25, .5)


def test_review_requires_matching_source_identity_and_provenance():
    source = [component('a', 0)]
    valid = review(source[0], 'no_demonstrated')
    for field, value in [('source_command_sha256', 'wrong'), ('evidence', ''),
                         ('reviewer_type', 'unknown'), ('contribution_label', 'non_direct')]:
        bad = dict(valid, **{field: value})
        with pytest.raises(ValueError): apply_reviews(source, [bad])
    with pytest.raises(ValueError, match='Duplicate or unknown'):
        apply_reviews(source, [valid, valid])


def test_indirect_needs_later_performed_direct_work_in_same_trajectory():
    source = [component('a', 1), component('earlier', 0, 'direct'),
              component('other', 2, 'direct', trajectory='Y'), component('none', 3, 'no_demonstrated')]
    for links in [[], ['missing'], ['earlier'], ['other'], ['none']]:
        with pytest.raises(ValueError): apply_reviews(source, [review(source[0], 'indirect', links)])


def test_review_sample_is_bounded_and_does_not_select_unexecuted_candidates():
    source = [component('a', 0), component('b', 1, role='verification'),
              component('c', 2), component('d', 3, 'direct'), component('e', 4, 'uncertain')]
    skipped = dict(component('not-run', -1), execution_status='not_executed')
    sample = review_sample([skipped, *source])
    assert len(sample) == 5 and {r['component_id'] for r in sample} == {c['component_id'] for c in source}


def test_empty_role_precision_is_undefined_not_zero():
    score = contribution_score([])
    assert score['included'] == 0
    assert score['lower'] is None and score['upper'] is None
