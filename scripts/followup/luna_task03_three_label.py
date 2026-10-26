"""Reproduce a separate, user-requested three-label direct-effort annotation.

Indirect here is broad assessed non-direct effort, not v2's demonstrated-guidance
label. Authored judgments live in annotations.jsonl; this script validates them,
scores direct effort and preserves existing response budgets. No new annotation
API, benchmark or trajectory command execution takes place.
"""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'worktrace'))
from worktrace.resources import allocate_usage, assert_conservation

SCHEME='direct_effort_three_label_v1'
LABELS=('direct','indirect','uncertain')


def read(path):return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,rows):path.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows))
def csvout(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def score(rows):
    performed=[r for r in rows if r['execution_status']!='not_executed']
    counts=collections.Counter(r['contribution_label'] for r in performed)
    n=len(performed)
    return dict(included=n,**{l:counts[l] for l in ['direct','indirect','uncertain']},
        lower=counts['direct']/n if n else None,
        upper=(counts['direct']+counts['uncertain'])/n if n else None)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'results/luna_task03_three_label_20261027')
    p.add_argument('--draw',action='store_true')
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    prior=ROOT/'results/luna_task03_v2_20261027'
    source=read(prior/'components.jsonl');reviews=read(out/'annotations.jsonl')
    indexed={r['component_id']:r for r in reviews}
    assert len(source)==len(reviews)==len(indexed)==30
    assert set(indexed)=={r['component_id'] for r in source}
    components=[]
    for c in source:
        r=indexed[c['component_id']]
        assert r['annotation_scheme']==SCHEME and r['contribution_label'] in LABELS
        assert r['source_command_sha256']==hashlib.sha256(c['command'].encode()).hexdigest()
        assert r['assessment_status']=='reviewed' and r['reviewer_type']=='model' and r['reviewer_name'] and r['evidence'] and r['assessment']
        assert r['prior_four_label']==c['contribution_label']
        assert r['direct_effort_credit']==(r['contribution_label']=='direct')
        components.append(dict(c,prior_four_label=c['contribution_label'],annotation_scheme=SCHEME,
            contribution_label=r['contribution_label'],contribution_review=r,reason=r['reason'],
            evidence=r['assessment']+' '+r['evidence'],review_provenance='current-session three-label reinterpretation; broad indirect'))
    responses=read(prior/'response_usage.jsonl')
    allocations=allocate_usage(responses,components);assert_conservation(responses,allocations)
    old={a['component_id']:a for a in read(prior/'component_allocations.jsonl')}
    assert all(a['usage']==old[a['component_id']]['usage'] and a['allocation_weight']==old[a['component_id']]['allocation_weight'] for a in allocations)
    byusage={a['component_id']:a for a in allocations}
    write(out/'components.jsonl',components);write(out/'component_allocations.jsonl',allocations)
    rows=[]
    for c in components:
        a=byusage[c['component_id']];r=indexed[c['component_id']]
        rows.append(dict(component_id=c['component_id'],role=c['role'],execution_status=c['execution_status'],
            prior_four_label=c['prior_four_label'],contribution=c['contribution_label'],reason=r['reason'],
            direct_effort_credit=r['direct_effort_credit'],input_tokens=a['usage']['input_tokens'],
            cached_input_tokens=a['usage']['cached_input_tokens'],output_tokens=a['usage']['output_tokens'],
            cost_usd=a['usage']['cost_usd'],allocation_method=a['allocation_method'],assessment=r['assessment'],evidence=r['evidence']))
    csvout(out/'component_table.csv',rows)
    full=score(components);strict=score([c for c in components if c['execution_status']=='executed'])
    roles=[dict(role=role,**score([c for c in components if c['role']==role])) for role in ['exploration','edit','verification','administration']]
    csvout(out/'role_precision.csv',roles)
    resource_rows=[]
    for metric in ['input_tokens','cached_input_tokens','output_tokens','cost_usd']:
        complete=all(a['usage'][metric] is not None for a in allocations)
        totals={label:math.fsum(a['usage'][metric] for a in allocations if a['contribution_label']==label and a['usage'][metric] is not None) for label in LABELS}
        total=math.fsum(totals.values()) if complete else None
        resource_rows.append(dict(metric=metric,**totals,total=total,complete=complete,
            direct_lower=totals['direct']/total if total else None,
            direct_upper=(totals['direct']+totals['uncertain'])/total if total else None,
            attribution='allocated response shares; not measured per-component reasoning'))
    csvout(out/'direct_effort_resources.csv',resource_rows)
    summary=dict(annotation_scheme=SCHEME,components=30,full=full,confirmed_executed_only=strict,roles=roles,
        direct_credit_only=True,indirect_semantics='broad assessed non-direct effort, including navigation/support/overhead; not proven causal guidance',
        legacy_unsplit=0,no_demonstrated_category=False,human_validation=False,allocation_changed=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if args.draw:
        subprocess.run([sys.executable,str(ROOT/'scripts/followup/draw_response_cost_bands.py'),
            '--reviewed-components',str(out/'components.jsonl'),'--task-order','3','--contribution-view','detailed',
            '--contribution-caption','THREE-LABEL VIEW: indirect = assessed non-direct effort, including navigation/support/overhead; only direct receives contributing-effort credit.',
            '--out',str(out/'response_cost_bands')],check=True,capture_output=True,text=True)
    report=['# Luna task 03: three-label direct-effort annotation','',
        '**30 components reviewed: 10 direct, 10 indirect, 10 uncertain.** No no_demonstrated or legacy-unsplit category appears in this view. '
        'This is a separate user-requested interpretation, not an independent validation study. The prior four-label outputs remain unchanged.','',
        '## Definition','',
        '- **Direct:** establishes a requirement-bearing observation, implements relevant source/delivery work, or verifies a supported repair/preservation/delivery property. Receives direct contributing-effort credit.',
        '- **Indirect:** assessed effort without established direct contribution, including navigation, context gathering, formatting, repeated checking and operational scaffolding. Receives no direct-effort credit. This broader bucket does **not** imply proven causal guidance or useful marginal gain.',
        '- **Uncertain:** execution, observed result or contribution cannot reliably be established. Retained as uncertainty rather than forced into indirect.','',
        'The ten former no_demonstrated judgments fall into this broader indirect bucket after reassessment; the direct and uncertain sets remain unchanged. '
        'Negative search results can be indirect, or direct when they themselves establish a missing required behavior. Chronological proximity alone does not prove guidance.','',
        f"Direct component precision: **{full['lower']:.1%}–{full['upper']:.1%}** (D/N to (D+U)/N). "
        f"There are {strict['included']} confirmed-executed components: **{strict['lower']:.1%}–{strict['upper']:.1%}** as a separate sensitivity. "
        'Eight components have uncertain execution and two invoked tests lack results. Roles and execution statuses retain their prior provenance.','',
        '| Role | N | Direct | Indirect | Uncertain | Direct bounds |','| --- | ---: | ---: | ---: | ---: | --- |',
        *[f"| {r['role']} | {r['included']} | {r['direct']} | {r['indirect']} | {r['uncertain']} | {r['lower']:.1%}–{r['upper']:.1%} |" for r in roles],'',
        '## Concrete decisions','',
        '- The broad file listing Y000.c1 and dependency inventory Y002.c0 are indirect orientation/context effort.',
        '- Formatting Y004.c1, repeated header checks Y008.c2/c3, and display separators are indirect support/overhead in this version. They do not receive direct credit.',
        '- Y007.c0 creates the required saved patch and Y008.c0 first inspects that artifact: direct delivery contribution.',
        '- Y005/Y006 tests time out without results: uncertain, not automatically indirect or proven over-verification.','',
        '## Evidence and accounting','',
        'Current-session reviewer: **Codex (model identifier unavailable)**. This is unblinded model review using the actual trace, complete requirements and final patch; it is not human validation. '
        'The [30 authored annotations](annotations.jsonl) record source command hashes, reasons, assessments, evidence and provenance. '
        '[component_table.csv](component_table.csv) supplies every component, old/new labels and separate input/cache/output/USD. '
        '[direct_effort_resources.csv](direct_effort_resources.csv) reports allocation-dependent direct resource bounds separately from component precision. '
        'All eight response budgets and all component shares are unchanged; cache is included in input. No benchmark PASS or post-pass savings is inferred.','',
        '![Three-label Luna task 03 response-cost bands](response_cost_bands/luna_task_03_response_costs.png)','',
        'The three-label scheme has its own identifier and validator. It does not use the strict four-label indirect-link validator: broad indirect does not require a later-direct dependency. '
        'Only the annotation categories differ; the 30-component decomposition and prior action roles are preserved, including administrative scaffolding. '
        'This result does not resolve whether those scaffolding units should be combined in a future measurement version.']
    (out/'RESULTS.md').write_text('\n'.join(report).rstrip()+'\n')
    manifest=dict(annotation_scheme=SCHEME,inputs={str(p.relative_to(ROOT)):sha(p) for p in [prior/'components.jsonl',prior/'response_usage.jsonl',out/'annotations.jsonl']},
        code_sha256=sha(Path(__file__)),output_hashes={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'manifest.json'})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
