"""Adversarial cache-key checks; authored fixtures, not empirical task outcomes."""
from dataclasses import replace
import pytest
from worktrace.evidence_cache import EvidenceCache, EvidenceContext, evidence_key


def context():
    return EvidenceContext('checker','verifier-v1','artifact-integrity','/work','env-v1',
        (('patch.txt','a'*64),('expected.patch','b'*64)),'delivery',True,True,True)


@pytest.mark.parametrize('field,value', [('checker_digest','v2'),('property_id','another'),
    ('cwd','/other'),('environment_digest','env-v2'),('goal_context','behavior'),
    ('dependency_digests',(('patch.txt','c'*64),('expected.patch','b'*64)))])
def test_key_invalidates_relevant_changes(field,value):
    c=context();cache=EvidenceCache()
    assert cache.store(c,{'pass':True},status='completed',observation_complete=True,provenance='fixture')
    assert cache.lookup(replace(c,**{field:value})) is None


@pytest.mark.parametrize('field', ['deterministic','scope_complete','read_only'])
def test_incomplete_or_side_effectful_scope_cannot_be_reused(field):
    assert evidence_key(replace(context(),**{field:False})) is None


def test_timeout_truncation_and_missing_provenance_are_not_cached():
    cache=EvidenceCache();c=context()
    for status,complete,provenance in [('timeout',True,'p'),('completed',False,'p'),('completed',True,'')]:
        assert not cache.store(c,{'pass':False},status=status,observation_complete=complete,provenance=provenance)
    assert cache.lookup(c) is None


def test_failed_completed_result_can_be_reused_without_turning_it_into_success():
    cache=EvidenceCache();c=context()
    result={'pass':False,'diagnostic':'invalid patch'}
    assert cache.store(c,result,status='completed',observation_complete=True,provenance='fixture')
    result['pass']=True
    first=cache.lookup(c);assert first['result']['pass'] is False
    first['result']['pass']=True
    assert cache.lookup(c)['result']['pass'] is False


def test_dependency_order_is_irrelevant_but_duplicate_names_are_rejected():
    c=context()
    assert evidence_key(c)==evidence_key(replace(c,dependency_digests=tuple(reversed(c.dependency_digests))))
    assert evidence_key(replace(c,dependency_digests=(('patch.txt','a'*64),('patch.txt','b'*64)))) is None
