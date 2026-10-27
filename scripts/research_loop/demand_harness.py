"""Demand-stratified model contrasts and an arithmetic cross-harness control.

Cross-harness source tables are previously exposed secondary evidence. Their
kind counts are not canonical work units, causal effects, tokens or utility.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from analyze import ci

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def main():
    flat=pd.read_csv(OUT/'flat_runs.csv')
    sizes=flat[flat.split.eq('discovery')].groupby('task_id').gold_lines.first().dropna()
    cuts=np.quantile(sizes,[.25,.5,.75])
    rows=[]
    for split in ['discovery','confirmation']:
        d=flat[flat.split.eq(split)].copy()
        d['demand_bin']=d.gold_lines.map(lambda s:'unknown' if pd.isna(s) else 'Q'+str(1+sum(s>c for c in cuts)))
        for bin,g in d.groupby('demand_bin'):
            for model,x in g.groupby('model'):
                for metric in ['native_calls','candidate_components','non_admin_candidates','output_tokens','input_tokens']:
                    rows.append(dict(split=split,bin=bin,model=model,metric=metric,**ci(x[metric].dropna())))
    pd.DataFrame(rows).to_csv(OUT/'demand_summary.csv',index=False)
    plan=json.loads((OUT/'analysis_plan.json').read_text())
    data=pd.read_parquet(ROOT/'results/v2/task5/runs_benchmark.parquet')
    data['harness']=data.harness.replace({'OpenHands':'openhands','SWE-agent':'swe-agent'})
    results=[]
    for split,d in [('frozen_confirmation',data[data.task_id.isin(plan['harness_confirmation_tasks'])]),('previously_analyzed_all',data)]:
        for comparison in ['openhands','swe-agent']:
            a=d[d.harness.eq(comparison)].set_index('task_id');b=d[d.harness.eq('mini-swe-agent')].set_index('task_id')
            ids=sorted(set(a.index)&set(b.index))
            for kind in ['n_ops','kind_edit','kind_read','kind_search','kind_run','kind_probe','kind_revert','kind_submit','kind_other']:
                diffs=a.loc[ids,kind].to_numpy()-b.loc[ids,kind].to_numpy()
                results.append(dict(split=split,comparison=comparison,reference='mini-swe-agent',metric=kind,**ci(diffs)))
            total_diff=(a.loc[ids,'n_ops']-b.loc[ids,'n_ops']).mean()
            edit_diff=(a.loc[ids,'kind_edit']-b.loc[ids,'kind_edit']).mean()
            print(split,comparison,'call gap',total_diff,'edit call gap',edit_diff,'fraction',edit_diff/total_diff if total_diff else None)
    pd.DataFrame(results).to_csv(OUT/'harness_kind_contrasts.csv',index=False)
    (OUT/'demand_harness_manifest.json').write_text(json.dumps(dict(
        reference_patch_line_cuts=cuts.tolist(),cut_estimation='discovery tasks only; not a validated human-difficulty scale',
        harness_token_usage='unavailable; do not convert text characters or action counts into tokens',
        harness_scope='same recorded Qwen model, distinct archived harness configurations; no randomized causal attribution',
        source_exposure='cross-harness tables and facts were previously analyzed; frozen confirmation is new arithmetic decomposition only'),indent=2)+'\n')


if __name__=='__main__':main()
