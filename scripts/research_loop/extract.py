"""Extract response-associated operational expenditure from all pinned local runs.

No semantic contribution labels, model calls, or trajectory execution. Native
call categories and edit barriers are observable proxies with explicit limits.
"""
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'worktrace'))
from worktrace.loaders.jetbrains import load_row,load_response_usage
from worktrace.operational import category,result_screen
from worktrace.resources import METRICS
sys.path.insert(0,str(ROOT/'scripts/precision_validation'))
from prepare import components as decompose

OUT=ROOT/'results/research_loop_20261028'
ROLES=['exploration','edit','verification','artifact_inspection','administration','opaque_execution','mixed_call','mixed_response','no_tool']


def main():
    plan=json.loads((OUT/'analysis_plan.json').read_text())
    confirm=set(plan['model_confirmation_tasks'])
    frozen=list(csv.DictReader((ROOT/'results/followup_20261026/confirmation_sample.csv').open()))
    semantic={r['task_id'] for r in frozen if r['panel']=='cross_model' and r['purpose']=='joint_success_semantic_panel'}
    old=list(csv.DictReader((ROOT/'results/one_day_precision_20261026/sample_manifest.csv').open()))
    development={r['task_id'] for r in old if r['split'] in {'calibration','evaluation'}}
    # Task demand comes from the independent reference patch, not trajectory cost.
    runrefs={r['run_id']:r for r in pq.read_table(ROOT/'data/runs.parquet').to_pylist()}
    runs=[];responses=[];pairs=[];validation=[];started=time.monotonic()
    for model in ['luna','gemini_3_7_flash','terra']:
        shard=ROOT/f'raw/jetbrains/{model}-run1.parquet'
        for batch in pq.ParquetFile(shard).iter_batches(batch_size=2):
            for source in batch.to_pylist():
                run,ops=load_row(source);rid=run['run_id'];task=run['task_id']
                group='confirmation' if task in confirm else 'semantic_confirmation' if task in semantic else 'legacy_development' if task in development else 'discovery'
                categories={op['op_id']:category(op['command']) for op in ops}
                candidates={op['op_id']:[dict(c,category=category(c['command'])) for c in decompose(op['command'])] for op in ops}
                rc=Counter(categories.values());by_response=defaultdict(list)
                for op in ops:by_response[op['response_id']].append(op)
                usage=load_response_usage(source);classified=[]
                for response in usage:
                    cs=[c['category'] for op in by_response[response['response_id']] for c in candidates[op['op_id']]]
                    label=cs[0] if cs and len(set(cs))==1 else 'mixed_response' if cs else 'no_tool'
                    classified.append(dict(run_id=rid,task_id=task,model=model,split=group,
                        response_id=response['response_id'],category=label,component_categories=dict(Counter(cs)),
                        usage=response['usage']))
                responses.extend(classified)
                known={m:math.fsum(r['usage'][m] for r in classified if r['usage'][m] is not None) if any(r['usage'][m] is not None for r in classified) else None for m in METRICS}
                record=dict(run_id=rid,task_id=task,model=model,split=group,resolved=run['resolved'],
                    native_calls=len(ops),responses=len(classified),gold_lines=runrefs.get(rid,{}).get('gold_lines'),
                    native_category_counts=dict(rc),candidate_component_counts=dict(Counter(c['category'] for cs in candidates.values() for c in cs)),
                    candidate_components=sum(len(cs) for cs in candidates.values()),
                    responses_with_usage={m:sum(r['usage'][m] is not None for r in classified) for m in METRICS},
                    recorded_run_usage={m:run.get(m) for m in METRICS},stored_response_usage=known,
                    usage_residual={m:run[m]-known[m] if run.get(m) is not None and known[m] is not None else None for m in METRICS},
                    operational_expenditure={})
                for role in ROLES:
                    value={}
                    for metric in METRICS:
                        total=known[metric]
                        if total is None or total==0:
                            value[metric]=dict(associated=None,equal_candidate_allocated=None,possible=None);continue
                        associated=allocated=possible=0.0
                        for r in classified:
                            amount=r['usage'][metric]
                            if amount is None:continue
                            calls=r['component_categories'];n=sum(calls.values())
                            if r['category']==role:associated+=amount
                            if n:allocated+=amount*calls.get(role,0)/n
                            elif role=='no_tool':allocated+=amount
                            if role in calls or r['category']==role:possible+=amount
                        value[metric]=dict(associated=associated/total,equal_candidate_allocated=allocated/total,possible=possible/total)
                    record['operational_expenditure'][role]=value
                seen={};barrier=0
                for index,op in enumerate(ops):
                    role=categories[op['op_id']];command=op['command'].strip()
                    if role=='verification':
                        previous=seen.get(command)
                        if previous:
                            oldindex,oldop,oldbarrier=previous
                            pairs.append(dict(run_id=rid,task_id=task,model=model,split=group,
                                earlier_index=oldindex,current_index=index,
                                command_sha256=hashlib.sha256(command.encode()).hexdigest(),
                                command_excerpt=command[:240],prior_status=result_screen(oldop),current_status=result_screen(op),
                                intervening_edit_or_opaque_call=barrier!=oldbarrier,
                                state_equality_certified=False,prior_output_attribution='native call only'))
                        seen[command]=(index,op,barrier)
                    if role in {'edit','mixed_call','opaque_execution'}:barrier+=1
                record['exact_verification_repeat_pairs']=sum(p['run_id']==rid for p in pairs)
                runs.append(record)
                # A reproducible validation inventory for later blind intent review.
                if group=='confirmation':
                    for i,op in enumerate(ops):
                        validation.append(dict(run_id=rid,task_id=task,op_id=op['op_id'],action_index=i,
                            operational_category=categories[op['op_id']],command=op['command'],components=candidates[op['op_id']],
                            result_screen=result_screen(op),raw_output_sha256=hashlib.sha256((op.get('output') or '').encode()).hexdigest()))
                if len(runs)%100==0:print(f'{len(runs)} runs extracted in {time.monotonic()-started:.1f}s',flush=True)
    for name,rows in [('runs',runs),('responses',responses),('verification_pairs',pairs),('validation_inventory',validation)]:
        (OUT/f'{name}.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows))
    (OUT/'extraction_manifest.json').write_text(json.dumps(dict(runs=len(runs),responses=len(responses),
        native_calls=sum(r['native_calls'] for r in runs),candidate_components=sum(r['candidate_components'] for r in runs),repeat_pairs=len(pairs),
        operational_categories=ROLES,analysis_plan_sha256=hashlib.sha256((OUT/'analysis_plan.json').read_bytes()).hexdigest(),
        semantic_contribution_labels_produced=0,causal_utilities_measured=0,
        interpretation='Operational command-category expenditure; response associations/bounds are not semantic usefulness.',
        seconds=time.monotonic()-started),indent=2)+'\n')
    print('Extraction complete.',len(runs),'runs',len(responses),'responses',flush=True)


if __name__=='__main__':main()
