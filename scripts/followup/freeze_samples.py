"""Freeze fresh archived-task panels before new contribution labels.

Separate random all-attempt samples from outcome-conditional semantic samples.
No new benchmark run, annotation API or download occurs here.
"""
import numpy as np
import pandas as pd
from followup_common import ROOT,OUT,SEED,dump,sha


def sample_tasks(tasks,n,seed):
    tasks=sorted(set(tasks))
    return list(np.random.default_rng(seed).permutation(tasks)[:n])


def panel(data,systems,panel,excluded,seed):
    data=data[~data.task_id.isin(excluded)].copy()
    assert not data.duplicated(['task_id','system']).any()
    groups=data.groupby('task_id')
    shared=groups.system.nunique()
    shared=set(shared[shared==len(systems)].index)
    data=data[data.task_id.isin(shared)]
    success=data.groupby('task_id').resolved.apply(lambda s: bool(s.notna().all() and s.astype(bool).all()))
    eligible=list(success[success].index)
    assert len(shared)>=30 and len(eligible)>=30,'Insufficient tasks for frozen 30-task panels'
    rows=[]
    for purpose,ids in [('attempt_panel',sample_tasks(shared,30,seed)),
                        ('joint_success_semantic_panel',sample_tasks(eligible,30,seed+1))]:
        for order,task in enumerate(ids):
            for r in data[data.task_id==task].to_dict('records'):
                rows.append(dict(panel=panel,purpose=purpose,selection_order=order,**r))
    # Independent task demand: reference patch size, not observed agent success.
    size=data.groupby('task_id').gold_lines.median().dropna().sort_index()
    bins=pd.qcut(size.rank(method='first'),4,labels=['Q1','Q2','Q3','Q4']).astype(str).to_dict()
    for r in rows:r['patch_size_bin']=bins.get(r['task_id'],'unknown')
    selected=pd.DataFrame(rows)
    summary=[]
    for purpose,g in selected.groupby('purpose'):
        for system,s in g.groupby('system'):
            known=s[s.resolved.notna()]
            summary.append(dict(panel=panel,purpose=purpose,system=system,tasks=len(s),
                known_outcomes=len(known),resolved=int(known.resolved.astype(bool).sum()),
                success_rate=float(known.resolved.astype(bool).mean()) if len(known) else None,
                mean_native_calls=float(s.n_ops.mean()),median_native_calls=float(s.n_ops.median()),
                cost_observed=int(s.cost_usd.notna().sum()) if 'cost_usd' in s else 0,
                mean_cost_usd=float(s.cost_usd.mean()) if 'cost_usd' in s and s.cost_usd.notna().any() else None))
    return selected,summary,dict(panel=panel,systems=systems,shared_tasks=len(shared),
                                joint_success_eligible=len(eligible),excluded_development_tasks=len(excluded),
                                outcome_selection='Semantic sample conditions on all compared systems succeeding; attempt sample does not.',
                                seed=seed,semantic_seed=seed+1)


def main():
    old=pd.read_csv(ROOT/'results/one_day_precision_20261026/sample_manifest.csv')
    excluded=set(old[old.split.isin(['calibration','evaluation'])].task_id)
    jb=pd.read_parquet(ROOT/'data/runs.parquet')
    jb=jb[(jb.run_index==1)&jb.model.isin(['gemini-3.7-flash','gpt-5.6-luna'])].copy()
    jb['system']=jb.model
    qw=pd.read_parquet(ROOT/'results/v2/task5/runs_benchmark.parquet').copy();qw['system']=qw.harness
    results=[];summaries=[];design=[]
    for data,systems,name,seed in [(jb,['gemini-3.7-flash','gpt-5.6-luna'],'cross_model',SEED+100),
        (qw,['mini-swe-agent','openhands','swe-agent'],'cross_harness',SEED+200)]:
        # Normalize recorded identifiers explicitly, never guess missing systems.
        data['system']=data.system.replace({'OpenHands':'openhands','SWE-agent':'swe-agent'})
        assert set(systems)<=set(data.system)
        frame,summary,meta=panel(data,systems,name,excluded,seed)
        results.append(frame);summaries+=summary;design.append(meta)
    S=pd.concat(results,ignore_index=True)
    path=OUT/'confirmation_sample.csv'
    if path.exists():
        previous=pd.read_csv(path)
        assert previous[['panel','purpose','task_id','run_id']].equals(S[['panel','purpose','task_id','run_id']]),'Frozen sample changed'
    else:S.to_csv(path,index=False)
    pd.DataFrame(summaries).to_csv(OUT/'confirmation_saved_effort.csv',index=False)
    contrasts=[]
    for (name,purpose),g in S.groupby(['panel','purpose']):
        pivot=g.pivot(index='task_id',columns='system',values='n_ops')
        reference='gemini-3.7-flash' if name=='cross_model' else 'mini-swe-agent'
        for other in pivot.columns:
            if other==reference:continue
            diff=(pivot[reference]-pivot[other]).dropna().values
            samples=np.random.default_rng(SEED).choice(diff,size=(5000,len(diff)),replace=True).mean(axis=1)
            lo,hi=np.percentile(samples,[2.5,97.5])
            contrasts.append(dict(panel=name,purpose=purpose,first=reference,second=other,tasks=len(diff),
                                  mean_native_call_difference=float(diff.mean()),ci95_lo=float(lo),ci95_hi=float(hi),
                                  interpretation='archived interaction counts; not contribution or equal work'))
    pd.DataFrame(contrasts).to_csv(OUT/'confirmation_paired_effort.csv',index=False)
    dump(OUT/'confirmation_design.json',dict(seed=SEED,panels=design,
        exposure='Held out from the contribution pilot, not previously unseen by all saved aggregate/novelty analyses.',
        sample_sha256=sha(path),stage='frozen; contribution labels and expert reference pending',
        sample_size='30 starting tasks per panel/purpose; not a power guarantee',
        expansion_rule='After expert calibration, estimate task-level variance and predeclare an interval-width target before adding tasks; no winner-dependent stopping.',
        scope='Saved trajectories only. Actual execution/cost comparison needs separately configured harness/model backends.'))


if __name__=='__main__':main()
