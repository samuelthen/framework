"""Measured evidence-cache overhead on real artifacts and scoped Go checks.

Perturbations are deliberately authored tests over reconstructed real inputs.
Tool replay timings do not establish LLM cost savings or causal decision value.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'worktrace'))
from worktrace.evidence_cache import EvidenceCache,EvidenceContext
from container_checks import run,IMAGE

OUT=ROOT/'results/utility_audit_20261028'


def sha(data):return hashlib.sha256(data).hexdigest()


def stable_result(output):
    events=[]
    for line in output.decode().splitlines():
        try: record=json.loads(line)
        except ValueError: continue
        if record.get('Action') in {'pass','fail','skip'}:
            events.append({k:record.get(k) for k in ['Package','Test','Action']})
    return sorted(events,key=lambda r:json.dumps(r,sort_keys=True))


def main():
    folder=OUT/'round_6';folder.mkdir(parents=True,exist_ok=True)
    artifact=ROOT/'raw/utility_replay/task03/patch.txt'
    row=json.loads((ROOT/'raw/utility_selected/03_luna.json').read_text())
    artifact.write_text(row['submission'])
    expected=artifact.with_name('expected.patch');expected.write_text(row['submission'])
    def context():
        return EvidenceContext('exact-saved-artifact-check','sha256:literal-equality-v1',
            'saved-artifact-matches-intended-diff',str(artifact.parent),platform.python_version(),
            (('patch.txt',sha(artifact.read_bytes())),('expected.patch',sha(expected.read_bytes()))),
            'delivery-integrity',True,True,True)
    def checker():
        current=artifact.read_bytes();intended=expected.read_bytes()
        return dict(matches=current==intended,contains_unified_headers=b'--- a/' in current and b'+++ b/' in current)
    cache=EvidenceCache();c=context();original=checker()
    assert cache.store(c,original,status='completed',observation_complete=True,provenance='reconstructed submitted patch; exact equality scope only')
    observations=[]
    observations.append(dict(case='unchanged real artifact',cache_hit=cache.lookup(context()) is not None,expected_hit=True))
    before=artifact.read_bytes();artifact.write_bytes(before+b'\n# invalid extra content\n')
    observations.append(dict(case='authored artifact mutation',cache_hit=cache.lookup(context()) is not None,expected_hit=False))
    artifact.write_bytes(before)
    irrelevant=artifact.with_name('unrelated_notes.txt');irrelevant.write_text('authored irrelevant edit')
    observations.append(dict(case='authored irrelevant file addition',cache_hit=cache.lookup(context()) is not None,expected_hit=True))
    for field,value in [('environment_digest','changed-runtime'),('checker_digest','changed-checker'),('goal_context','behavior-only'),('cwd','/different')]:
        observations.append(dict(case=f'authored {field} change',cache_hit=cache.lookup(replace(context(),**{field:value})) is not None,expected_hit=False))
    assert all(o['cache_hit']==o['expected_hit'] for o in observations)
    fresh_times=[];cached_times=[]
    for i in range(1000):
        # Alternate ordering to avoid making one path systematically colder.
        for cached in ([False,True] if i%2==0 else [True,False]):
            started=time.perf_counter_ns()
            value=cache.lookup(context())['result'] if cached else checker()
            elapsed=time.perf_counter_ns()-started
            assert value==original
            (cached_times if cached else fresh_times).append(elapsed/1e6)
    small=dict(workload='exact artifact-equality/header check on real submitted patch',
        iterations=1000,measurement='warm in-process wall time; cache includes file hashing, key construction, lookup and result decoding',
        fresh_median_ms=statistics.median(fresh_times),reuse_median_ms=statistics.median(cached_times),
        net_median_saved_ms=statistics.median(fresh_times)-statistics.median(cached_times),
        perturbations=observations,semantic_scope='artifact bytes only, not task behavior')
    (folder/'artifact_cache.json').write_text(json.dumps(small,indent=2)+'\n')
    print('Artifact experiment',json.dumps(small),flush=True)

    # Actual Go package reruns on a fixed reconstructed snapshot, with build
    # cache left enabled. This is an explicit -count=1 checker, not a model run.
    root=ROOT/'raw/utility_replay/task03/eval_submitted'
    command=['go','test','-mod=readonly','-count=1','-json','-run','^TestErrorUnaryInterceptor$','./internal/server/middleware/grpc']
    def go_context():
        dependencies=tuple((str(p.relative_to(root)),sha(p.read_bytes())) for p in sorted(root.rglob('*')) if p.is_file())
        return EvidenceContext(' '.join(command),sha(json.dumps(command).encode()),
             'selected-patched-context-error-test', '/work',IMAGE+';CGO_ENABLED=0;network=none;fixed-reviewed-test',
             dependencies,'scoped-reproduction',True,True,True)
    go_cache=EvidenceCache();go_runs=[];cached_lookup=[];results=[]
    for i in range(3):
        record,output,error=run(f'task03_cache_fresh_{i}',3,'eval_submitted',command,limit=120)
        parsed=stable_result(output)
        assert record['exit_code']==0 and parsed
        go_runs.append(record);results.append(parsed)
    assert all(result==results[0] for result in results)
    gc=go_context()
    assert go_cache.store(gc,results[0],status='completed',observation_complete=True,
                          provenance='three identical scoped test outcome sets; historical logs and timings retained separately')
    for i in range(100):
        started=time.perf_counter();answer=go_cache.lookup(go_context());elapsed=time.perf_counter()-started
        assert answer['result']==results[0];cached_lookup.append(elapsed)
    fresh_median=statistics.median(r['seconds'] for r in go_runs)
    cached_median=statistics.median(cached_lookup)
    go=dict(workload='fixed Go patched-test outcome summary; observed stable in three fresh executions',
        fresh_runs=go_runs,cache_samples=100,scope_files=len(gc.dependency_digests),
        fresh_median_seconds=fresh_median,reuse_median_seconds=cached_median,
        net_median_tool_time_saved_seconds=fresh_median-cached_median,
        output_equivalence='Package/Test/Action outcomes only; timestamps/durations intentionally excluded; cached result explicitly marked reused',
        compiled_build_cache='enabled in both paths; test result cache bypassed by the original explicit count=1 checker',
        scope_assessment='controlled selected package/test and container; empirical stability is not proof of universal determinism',
        original_trace_cache_hit_claim=False,actual_llm_savings_measured=False,
        remaining_cost='No model generation, future context, network transfer or production storage cost measured; do not report this as end-to-end savings')
    (folder/'go_check_cache.json').write_text(json.dumps(go,indent=2)+'\n')
    print('Go experiment',json.dumps(go),flush=True)


if __name__=='__main__':main()
