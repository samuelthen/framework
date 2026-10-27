"""Audit live-study coverage, actual usage and paired descriptive differences."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import statistics
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'worktrace'))
from worktrace.operational import category

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def main():
    for version,rawname in [('live_pilot','live_utility'),('live_v2','live_utility_v2')]:
        folder=OUT/version;raw=ROOT/'raw'/rawname
        records=[]
        for p in sorted((folder/'episodes').glob('*.json')):
            row=json.loads(p.read_text());episode=raw/'episodes'/row['episode_id']
            trajectory=episode/'trajectory.json';commands=[];tool_time=0;tool_count=0
            if trajectory.exists():
                data=json.loads(trajectory.read_text())
                for message in data.get('messages',[]):
                    for call in message.get('tool_calls') or []:
                        try:command=json.loads(call['function']['arguments']).get('command','')
                        except (ValueError,KeyError):continue
                        commands.append(command)
                row['continuation_operational_calls']=dict(Counter(category(c) for c in commands))
            logs=episode/'api/usage.jsonl'
            usage=[json.loads(s) for s in logs.read_text().splitlines()] if logs.exists() else []
            row['returned_models']=sorted({r.get('returned_model') for r in usage if r.get('returned_model')})
            row['api_seconds']=sum(r['seconds'] for r in usage)
            row['reasoning_tokens']=sum((r.get('usage',{}).get('completion_tokens_details') or {}).get('reasoning_tokens',0) for r in usage if r.get('usage'))
            cached=[(r.get('usage') or {}).get('prompt_tokens_details',{}).get('cached_tokens') for r in usage]
            row['cached_input_tokens']=sum(cached) if cached and all(v is not None for v in cached) else None
            row['grading_available']=row.get('scoped_quality') in {'scoped_pass','scoped_fail','source_build_failure'}
            row['fixture_grading_available']=row.get('fixture_complete_quality') in {'scoped_pass','scoped_fail','source_build_failure'}
            row['finalized']=row.get('agent_exit')=='Submitted'
            records.append(row)
        groups=[]
        for arm in ['fresh','cache','bypass']:
            a=[r for r in records if r['arm']==arm];valid=[r for r in a if r['status']=='completed' and r['grading_available']]
            groups.append(dict(arm=arm,planned_episodes=6,observed=len(a),protocol_and_grade_complete=len(valid),
                scoped_pass=sum(r.get('scoped_quality')=='scoped_pass' for r in valid),
                fixture_pass=sum(r.get('fixture_complete_quality')=='scoped_pass' for r in valid) if any(r.get('fixture_grading_available') for r in valid) else None,
                finalized=sum(r['finalized'] for r in valid),
                mean_input_tokens=statistics.mean(r['input_tokens'] for r in valid) if valid else None,
                mean_output_tokens=statistics.mean(r['output_tokens'] for r in valid) if valid else None,
                mean_api_seconds=statistics.mean(r['api_seconds'] for r in valid) if valid else None,
                mean_initial_check_seconds=statistics.mean(r['initial_check_seconds'] for r in valid) if valid else None,
                mean_total_wall_seconds=statistics.mean(r['total_wall_seconds'] for r in valid) if valid else None,
                statuses=dict(Counter(r['status'] for r in a))))
        lookup={(r['case'],r['replicate'],r['arm']):r for r in records};paired=[]
        for other in ['cache','bypass']:
            for case in ['pilot03','confirm00','confirm03']:
                for rep in [0,1]:
                    a=lookup.get((case,rep,'fresh'));b=lookup.get((case,rep,other))
                    if not a or not b or any(r['status']!='completed' or not r['grading_available'] for r in [a,b]):continue
                    paired.append(dict(case=case,replicate=rep,comparison='fresh_minus_'+other,
                        scoped_success_difference=int(a['scoped_quality']=='scoped_pass')-int(b['scoped_quality']=='scoped_pass'),
                        fixture_success_difference=int(a.get('fixture_complete_quality')=='scoped_pass')-int(b.get('fixture_complete_quality')=='scoped_pass'),
                        input_token_difference=a['input_tokens']-b['input_tokens'],output_token_difference=a['output_tokens']-b['output_tokens'],
                        initial_check_seconds_difference=a['initial_check_seconds']-b['initial_check_seconds']))
        report=dict(version=version,planned=18,observed=len(records),episodes=records,arm_summary=groups,paired=paired,
            independent_tasks=3,decodes_per_arm_per_task=2,
            interpretation='Diagnostic selected-snapshot study. Repeated decodes are not independent tasks. Quality equality here is not a non-inferiority result. API cache reuse and timing may depend on schedule.',
            model_usage_known=sum(r.get('usage_complete',False) and r.get('api_attempts',0)>0 for r in records),
            actual_api_attempts=sum(r.get('api_attempts',0) for r in records),
            total_reported_input_tokens=sum(r.get('input_tokens') or 0 for r in records),total_reported_output_tokens=sum(r.get('output_tokens') or 0 for r in records))
        same_patch={}
        for case in sorted({r['case'] for r in records}):
            known=[r['final_patch_sha256'] for r in records if r['case']==case and r.get('final_patch_sha256')]
            same_patch[case]=dict(available=len(known),unique_patches=len(set(known)))
        report['patch_identity_by_case']=same_patch
        (folder/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
        print(version,len(records),'episodes',report['actual_api_attempts'],'API attempts')
        for g in groups:print(g)


if __name__=='__main__':main()
