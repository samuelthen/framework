"""Equal-run role precision, with pooled shares clearly separated."""
import pandas as pd
from followup_common import BASE,OUT,jsonl,dump


def score(rows):
    a=[r for r in rows if r['execution_status']!='not_executed']
    n=len(a);d=sum(r['contribution_label']=='direct' for r in a);u=sum(r['contribution_label']=='uncertain' for r in a)
    return dict(N=n,D=d,U=u,ND=n-d-u,lower=d/n if n else None,upper=(d+u)/n if n else None)


def main():
    key=pd.read_csv(BASE.parent/'one_day_precision_20261026/packets/blinding_key.csv')
    key={(int(r.order),r.label):r for r in key.itertuples()}
    out=[]
    for prefix,version in [('', 'B'),('reviewer_c_','C'),('reconciled_','cross_review')]:
        a=pd.DataFrame(jsonl(BASE/f'{prefix}component_annotations.jsonl'))
        for (order,lab),g in a.groupby(['order','blinded_label']):
            k=key[(int(order),lab)]
            for role in ['exploration','edit','verification','administration']:
                out.append(dict(version=version,order=int(order),blinded_label=lab,model=k.model,role=role,
                                **score(g[g.role==role].to_dict('records'))))
    R=pd.DataFrame(out);R.to_csv(OUT/'role_precision_by_run.csv',index=False)
    summary=[];pairs=[]
    for (version,role),g in R.groupby(['version','role']):
        eligible=g[g.N>0].groupby('order').model.nunique()
        selected=g[g.order.isin(eligible[eligible==2].index)]
        for model,m in selected.groupby('model'):
            n=int(m.N.sum());d=int(m.D.sum());u=int(m.U.sum())
            summary.append(dict(version=version,role=role,model=model,paired_tasks=len(m),N=n,D=d,U=u,
                                run_mean_lower=m.lower.mean(),run_mean_upper=m.upper.mean(),
                                pooled_lower=d/n if n else None,pooled_upper=(d+u)/n if n else None))
        for order,t in selected.groupby('order'):
            x=t.set_index('model');a=x.loc['gemini-3.7-flash'];b=x.loc['gpt-5.6-luna']
            pairs.append(dict(version=version,role=role,order=int(order),diff_min=a.lower-b.upper,diff_max=a.upper-b.lower))
    pd.DataFrame(summary).to_csv(OUT/'role_precision_summary.csv',index=False)
    pd.DataFrame(pairs).to_csv(OUT/'role_precision_pairs.csv',index=False)
    dump(OUT/'role_precision_notes.json',{'primary':'per-run precision followed by equal-task means, complete paired roles only',
        'source':'archived 8da1f1a model-coded labels; no relabeling',
        'role_uncertainty_limit':'Archived reconciliation unions disputed verification roles, but prefers B for other role disputes. Exploration values reproduce that convention; they are not fully role-invariant.'})


if __name__=='__main__':main()
