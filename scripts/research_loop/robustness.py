"""Replication, outcome/repository sensitivity and full-run attribution bounds."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from analyze import ci
from executable_panel import scoped_quality

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def ratio(a,b):
    a=np.array(a,dtype=float);b=np.array(b,dtype=float)
    valid=np.isfinite(a)&np.isfinite(b);a=a[valid];b=b[valid]
    if not len(a) or b.mean()==0:return dict(n=len(a),estimate=None,lo=None,hi=None)
    ix=np.random.default_rng(20261028).integers(0,len(a),size=(5000,len(a)))
    draws=a[ix].mean(axis=1)/b[ix].mean(axis=1)
    return dict(n=len(a),estimate=float(a.mean()/b.mean()),lo=float(np.quantile(draws,.025)),hi=float(np.quantile(draws,.975)))


def main():
    rows=[json.loads(s) for s in (OUT/'runs.jsonl').read_text().splitlines()]
    refs=pd.read_parquet(ROOT/'raw/swebenchpro/v1.parquet',columns=['instance_id','repo']).set_index('instance_id').repo.to_dict()
    tables={m:{r['task_id']:r for r in rows if r['model']==m} for m in ['luna','gemini_3_7_flash','terra']}
    findings=[];repo_sensitivity=[]
    for split in ['confirmation','discovery']:
        for first in ['gemini_3_7_flash','terra']:
            shared=sorted(t for t in set(tables[first])&set(tables['luna']) if tables[first][t]['split']==split)
            for scope in ['all_attempts','joint_success']:
                tasks=[t for t in shared if scope=='all_attempts' or tables[first][t]['resolved'] is True and tables['luna'][t]['resolved'] is True]
                a=[tables[first][t] for t in tasks];b=[tables['luna'][t] for t in tasks]
                item=dict(split=split,scope=scope,first=first,second='luna',tasks=len(tasks),ratios={},reversals={})
                for metric in ['native_calls','candidate_components','output_tokens']:
                    va=[r['recorded_run_usage']['output_tokens'] if metric=='output_tokens' else r[metric] for r in a]
                    vb=[r['recorded_run_usage']['output_tokens'] if metric=='output_tokens' else r[metric] for r in b]
                    item['ratios'][metric]=ratio([np.nan if v is None else v for v in va],[np.nan if v is None else v for v in vb])
                native=np.array([x['native_calls']-y['native_calls'] for x,y in zip(a,b)])
                component=np.array([x['candidate_components']-y['candidate_components'] for x,y in zip(a,b)])
                output=np.array([np.nan if x['recorded_run_usage']['output_tokens'] is None or y['recorded_run_usage']['output_tokens'] is None else x['recorded_run_usage']['output_tokens']-y['recorded_run_usage']['output_tokens'] for x,y in zip(a,b)])
                for name,x,y in [('native_vs_candidate',native,component),('candidate_vs_output',component,output)]:
                    valid=np.isfinite(x)&np.isfinite(y);values=(x[valid]*y[valid]<0).astype(float)
                    item['reversals'][name]=dict(reversals=int(values.sum()),ties=int(((x[valid]==0)|(y[valid]==0)).sum()),**ci(values))
                item['recorded_success_difference']=ci([float(x['resolved'])-float(y['resolved']) for x,y in zip(a,b) if x['resolved'] is not None and y['resolved'] is not None])
                findings.append(item)
                if scope=='all_attempts':
                    for repo in sorted({refs.get(t,'unknown') for t in tasks}):
                        ids=[t for t in tasks if refs.get(t,'unknown')!=repo]
                        if not ids:continue
                        v={}
                        for metric in ['native_calls','candidate_components']:
                            v[metric]=sum(tables[first][t][metric] for t in ids)/sum(tables['luna'][t][metric] for t in ids)
                        repo_sensitivity.append(dict(split=split,first=first,left_out_repo=repo,tasks=len(ids),**v))
    (OUT/'robustness_summary.json').write_text(json.dumps(findings,indent=2)+'\n')
    pd.DataFrame(repo_sensitivity).to_csv(OUT/'leave_one_repo_out.csv',index=False)
    bounds=[];tasks=sorted(t for t,r in tables['luna'].items() if r['split']=='confirmation')
    for role in ['exploration','edit','verification','administration']:
        for metric in ['input_tokens','output_tokens']:
            low=[];high=[];unknown=0
            for task in tasks:
                pair=[]
                for model in ['gemini_3_7_flash','luna']:
                    r=tables[model][task];total=r['recorded_run_usage'][metric];known=r['stored_response_usage'][metric]
                    if total in (None,0) or known is None or known>total+1e-8:pair=[];break
                    shares=r['operational_expenditure'][role][metric]
                    residual=total-known
                    pair.append((shares['associated']*known/total,(shares['possible']*known+residual)/total))
                if len(pair)!=2:unknown+=1;continue
                low.append(pair[0][0]-pair[1][1]);high.append(pair[0][1]-pair[1][0])
            bounds.append(dict(role=role,metric=metric,first='gemini_3_7_flash',second='luna',lower=ci(low),upper=ci(high),unavailable_pairs=unknown,
                denominator='recorded run total; all positive unlocalized residual may belong to any operational category',
                interpretation='Partial identification over arbitrary within-response allocations; not a causal token attribution.'))
    (OUT/'full_run_share_bounds.json').write_text(json.dumps(bounds,indent=2)+'\n')
    # Reclassify saved compiler diagnostics, preserving the original execution log.
    folder=OUT/'executable_panel';records=json.loads((folder/'execution.json').read_text())
    for r in records:
        if 'exit_code' not in r:continue
        stem=f"case_{r['case']:02d}_{r['version']}"
        r['quality']=scoped_quality(r['exit_code'],r['status'],(folder/f'logs/{stem}.stdout.txt').read_bytes(),(folder/f'logs/{stem}.stderr.txt').read_bytes(),r.get('events',[]))
    (folder/'quality_classified.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Primary confirmation',findings[0])
    print('Third-model confirmation extension',findings[2])


if __name__=='__main__':main()
