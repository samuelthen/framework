"""Constructive allocation sensitivity using fixed observed response totals.

These are feasible accounting witnesses, never reconstructed token ground truth.
All results are conditional on the frozen operational component categories.
"""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def main():
    responses=[json.loads(s) for s in (OUT/'responses.jsonl').read_text().splitlines()]
    runs={r['run_id']:r for r in (json.loads(s) for s in (OUT/'runs.jsonl').read_text().splitlines())}
    selected=[r for r in responses if r['split']=='confirmation' and r['model'] in {'gemini_3_7_flash','luna'}]
    summary=[];witness=[]
    for role in ['exploration','edit','verification']:
        byrun=defaultdict(lambda:defaultdict(float))
        for r in selected:
            amount=r['usage']['output_tokens']
            if amount is None:continue
            categories=r['component_categories'];n=sum(categories.values());target=categories.get(role,0)
            lower=amount if n and target==n else 0.0
            upper=amount if target else 0.0
            equal=amount*target/n if n else 0.0
            assert 0<=lower<=equal+1e-8<=upper+1e-8<=amount+1e-8
            # Opposite extremal assignments use different but equally feasible
            # divisions of the same observed response total, never extra tokens.
            minimum=lower if r['model']=='gemini_3_7_flash' else upper
            maximum=upper if r['model']=='gemini_3_7_flash' else lower
            witness.append(dict(role=role,response_id=r['response_id'],run_id=r['run_id'],
                observed_output_tokens=amount,min_gap_target_allocation=minimum,max_gap_target_allocation=maximum,
                min_gap_other_allocation=amount-minimum,max_gap_other_allocation=amount-maximum,
                source_categories=categories))
            for name,value in [('lower',lower),('upper',upper),('equal',equal)]:byrun[r['run_id']][name]+=value
        bytask=defaultdict(dict)
        for rid,amounts in byrun.items():
            run=runs[rid];total=run['recorded_run_usage']['output_tokens'];known=run['stored_response_usage']['output_tokens']
            if total is None or known is None or total<known-1e-8:continue
            bytask[run['task_id']][run['model']]=dict(lower=amounts['lower']/total,
                upper=(amounts['upper']+total-known)/total,equal=amounts['equal']/known)
        differences=[]
        for task,models in bytask.items():
            if len(models)!=2:continue
            a=models['gemini_3_7_flash'];b=models['luna']
            differences.append(dict(task_id=task,minimum=a['lower']-b['upper'],maximum=a['upper']-b['lower'],
                equal_stored_response_share=a['equal']-b['equal']))
        summary.append(dict(role=role,tasks=len(differences),minimum_mean_difference=float(np.mean([r['minimum'] for r in differences])),
            maximum_mean_difference=float(np.mean([r['maximum'] for r in differences])),
            equal_stored_response_mean=float(np.mean([r['equal_stored_response_share'] for r in differences])),
            both_orderings_feasible=bool(np.mean([r['minimum'] for r in differences])<0<np.mean([r['maximum'] for r in differences])),
            interpretation='Full-run extremal bounds include positive unlocalized residual. Equal estimate uses stored-response denominator; neither is causal reasoning attribution.',
            per_task=differences))
    (OUT/'allocation_witness.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in witness))
    (OUT/'allocation_sensitivity.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('All witnesses conserve observed output; feasible accounting can reverse all three operational role rankings.')


if __name__=='__main__':main()
