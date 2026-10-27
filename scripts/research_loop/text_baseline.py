"""Available-text token attribution sensitivity on the frozen attempt panel.

Uses the closest cost study's o200k_base tokenizer choice for visible generated
text. This is a baseline adaptation, not a reproduction of its entire cost model:
prices, original provider tokenization and per-fragment future cache charges are
not established by these logs. No estimated count replaces API telemetry.
"""
from collections import defaultdict
import json
from pathlib import Path
import statistics
import pyarrow.parquet as pq
import tiktoken

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def text_content(value):
    if isinstance(value,str):return value
    if isinstance(value,list):return '\n'.join(text_content(v) for v in value)
    if isinstance(value,dict):return value.get('text') or value.get('content') or ''
    return ''


def main():
    encoding=tiktoken.get_encoding('o200k_base')
    def tokens(s):return len(encoding.encode(s,disallowed_special=()))
    inventory=[json.loads(s) for s in (OUT/'validation_inventory.jsonl').read_text().splitlines()]
    responses=[json.loads(s) for s in (OUT/'responses.jsonl').read_text().splitlines() if s.strip()]
    selected={r['response_id']:r for r in responses if r['split']=='confirmation'}
    components=defaultdict(list)
    for op in inventory:
        response_id=op['op_id'].rsplit('.',1)[0]
        components[response_id].extend(op['components'])
    rows=[]
    for rid,r in selected.items():
        cs=components[rid];weights=[tokens(c['command']) for c in cs];weight=sum(weights)
        allocations=defaultdict(float)
        if cs:
            for c,w in zip(cs,weights):allocations[c['category']]+=(w/weight if weight else 1/len(cs))
        else:allocations['no_tool']=1.0
        rows.append(dict(response_id=rid,run_id=r['run_id'],task_id=r['task_id'],model=r['model'],
            reported_output_tokens=r['usage']['output_tokens'],available_command_tokens=weight,
            token_weighted_category_shares=dict(allocations),
            interpretation='Available-command-token weighting is an allocation assumption, not semantic reasoning attribution.'))
    byrun=defaultdict(list)
    for r in rows:byrun[r['run_id']].append(r)
    summaries=[]
    for rid,rs in byrun.items():
        denominator=sum(r['reported_output_tokens'] or 0 for r in rs)
        shares={role:sum((r['reported_output_tokens'] or 0)*r['token_weighted_category_shares'].get(role,0) for r in rs)/denominator
                for role in ['exploration','edit','verification']}
        summaries.append(dict(run_id=rid,task_id=rs[0]['task_id'],model=rs[0]['model'],shares=shares))
    emission=[];tasks={r['task_id'] for r in rows}
    for model in ['luna','gemini_3_7_flash','terra']:
        for batch in pq.ParquetFile(ROOT/f'raw/jetbrains/{model}-run1.parquet').iter_batches(batch_size=2,columns=['instance_id','messages']):
            for source in batch.to_pylist():
                if source['instance_id'] not in tasks:continue
                visible=reasoning=reported=reported_reasoning=0;reasoning_responses=0;response_count=0
                for m in json.loads(source['messages']):
                    if m.get('object')!='response':continue
                    response_count+=1;usage=m.get('usage') or {}
                    reported+=usage.get('output_tokens') or 0
                    reported_reasoning+=(usage.get('output_tokens_details') or {}).get('reasoning_tokens') or 0
                    for o in m.get('output') or []:
                        if o.get('type')=='function_call':visible+=tokens(o.get('arguments') or '')
                        elif o.get('type')=='message':visible+=tokens(text_content(o.get('content')))
                        elif o.get('type')=='reasoning':
                            available=text_content(o.get('content')) or text_content(o.get('summary'))
                            reasoning+=tokens(available);reasoning_responses+=bool(available)
                emission.append(dict(model=model,task_id=source['instance_id'],responses=response_count,
                    available_visible_tokens_o200k=visible,available_reasoning_tokens_o200k=reasoning,
                    responses_with_available_reasoning_text=reasoning_responses,
                    reported_output_tokens=reported,reported_reasoning_tokens=reported_reasoning))
    contrasts=[]
    for role in ['exploration','edit','verification']:
        a={r['task_id']:r['shares'][role] for r in summaries if r['model']=='gemini_3_7_flash'}
        b={r['task_id']:r['shares'][role] for r in summaries if r['model']=='luna'}
        contrasts.append(dict(role=role,tasks=len(set(a)&set(b)),gemini_minus_luna_mean_share=statistics.mean(a[t]-b[t] for t in sorted(set(a)&set(b))),
            method='Reported response output allocated by available component-command token length; reasoning and context purpose unresolved.'))
    coverage=[]
    for model in ['luna','gemini_3_7_flash','terra']:
        rs=[r for r in emission if r['model']==model]
        coverage.append(dict(model=model,tasks=len(rs),responses=sum(r['responses'] for r in rs),
            reasoning_text_responses=sum(r['responses_with_available_reasoning_text'] for r in rs),
            reported_output=sum(r['reported_output_tokens'] for r in rs),
            retokenized_available_output=sum(r['available_visible_tokens_o200k']+r['available_reasoning_tokens_o200k'] for r in rs)))
    (OUT/'text_baseline_summary.json').write_text(json.dumps(dict(tokenizer='o200k_base',tiktoken_version=tiktoken.__version__,
        attribution_contrasts=contrasts,text_coverage=coverage,available_text_emission=emission,
        limitations=['Different provider tokenizers and hidden/serialized reasoning mean text counts need not reconcile with reported tokens.',
                     'This adaptation does not reproduce source-specific downstream context/cache charging or prices.',
                     'All response totals in the weighted allocation remain reported telemetry; text weights are sensitivity assumptions.']),indent=2)+'\n')
    (OUT/'text_baseline_allocations.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(contrasts);print(coverage)


if __name__=='__main__':main()
