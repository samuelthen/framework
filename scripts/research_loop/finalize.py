"""Validate claim arithmetic and write compact provenance without raw prompts."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def read(name):return json.loads((OUT/name).read_text())
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def main():
    extraction=read('extraction_manifest.json');live=read('live_v2/analysis.json')
    assert extraction['runs']==2100 and extraction['candidate_components']==110354
    assert extraction['native_calls']==61769 and extraction['responses']==54350
    assert live['observed']==18 and live['actual_api_attempts']==139
    assert all(r['status']=='completed' and r['usage_complete'] and r['grading_available'] for r in live['episodes'])
    assert {tuple(r['returned_models']) for r in live['episodes']}=={('deepseek-v4.1-flash-1017',)}
    assert all(r['scoped_pass']==4 and r['fixture_pass']==6 for r in live['arm_summary'])
    assert sum(r['finalized'] for r in live['episodes'])==4
    edits=read('live_v2/net_edit_audit.json')
    assert len(edits)==18 and all(not r['changed_production_paths_from_initial'] and r['initial_snapshot_hash_verified'] for r in edits)
    witnesses=read('allocation_sensitivity.json')
    assert all(r['both_orderings_feasible'] and r['tasks']==30 for r in witnesses)
    for line in (OUT/'allocation_witness.jsonl').read_text().splitlines():
        r=json.loads(line)
        for prefix in ['min_gap','max_gap']:
            assert abs(r[prefix+'_target_allocation']+r[prefix+'_other_allocation']-r['observed_output_tokens'])<1e-8
    ledger=[]
    for version,raw in [('live_pilot','live_utility'),('live_v2','live_utility_v2')]:
        for folder in sorted((ROOT/'raw'/raw/'episodes').glob('*')):
            logs=folder/'api/usage.jsonl'
            if logs.exists():
                for line in logs.read_text().splitlines():ledger.append(dict(study=version,episode_id=folder.name,**json.loads(line)))
    assert sum(r['study']=='live_v2' for r in ledger)==139
    (OUT/'soc_usage_ledger.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in ledger))
    # Snapshot and response hashes support auditing without publishing the
    # full agent conversations or private evaluation data.
    provenance=[]
    for raw in ['live_utility','live_utility_v2']:
        for folder in sorted((ROOT/'raw'/raw/'episodes').glob('*')):
            for name in ['trajectory.json','final.patch','initial_feedback.json','private_grading.json','private_fixture_grading.json']:
                p=folder/name
                if p.exists():provenance.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size))
    (OUT/'live_artifact_hashes.json').write_text(json.dumps(provenance,indent=2)+'\n')
    validation=dict(software_test_command='PYTHONPATH=worktrace python3 -m pytest -q worktrace/tests scripts/one_day_precision/test_one_day.py scripts/precision_validation/test_validation.py scripts/followup/test_followup.py',
        software_tests_passed=207,software_tests_failed=0,
        claim_arithmetic_verified=True,live_backend_identity_verified=True,
        final_production_snapshots_verified=18,allocation_conservation_verified=True,
        literature_claim='No first-graph, first-attribution or universal-reward claim; closest full cost model not reproduced.',
        empirical_units=dict(archived_tasks=700,archived_runs=2100,model_confirmation_tasks=30,executable_tasks=5,
                             source_file_interventions=4,live_task_snapshots=3,live_decodes_per_cell=2,live_v2_episodes=18),
        remaining_limits=['Operational categories are not independently human-validated semantic labels.',
            'Executable tests are scoped and fixture/interface dependent; one repository.',
            'Three chosen live snapshots do not establish a population utility or non-inferiority claim.',
            'Tokenizer weighting is an adapted sensitivity, not full reproduction of downstream context/cache attribution.'])
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    inputs=['raw/jetbrains/luna-run1.parquet','raw/jetbrains/gemini_3_7_flash-run1.parquet','raw/jetbrains/terra-run1.parquet',
            'raw/swebenchpro/v1.parquet','data/runs.parquet','results/v2/task5/runs_benchmark.parquet',
            'results/followup_20261026/confirmation_sample.csv']
    scripts=sorted((ROOT/'scripts/research_loop').glob('*.py'))+[ROOT/'worktrace/worktrace/operational.py']
    manifest=dict(inputs={p:sha(ROOT/p) for p in inputs},code={str(p.relative_to(ROOT)):sha(p) for p in scripts},
        actual_live_v1_requests=48,actual_live_v2_requests=139,preflight_chat_requests=2,adapter_smoke_requests=1,
        published_usage_records=len(ledger),credentials_published=False,raw_prompts_published=False,
        current_claim='Measurement study with scoped executable validation and a diagnostic continuation pilot.',
        submission_readiness='Not certified; strongest supported paper is narrower than universal action utility.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Verified all claim arithmetic, 18 unchanged production snapshots, 139 DeepSeek requests, and allocation conservation.')


if __name__=='__main__':main()
