"""Reproduce the additive full-run v2 review of Luna task 03.

Judgments are authored in the overlay, not inferred by this script. All 30
emitted components of the run are retained for the eight response budgets.
The prior fixed 20-case study and all other runs remain unchanged.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('MPLCONFIGDIR','/tmp/worktrace-luna03-mpl')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'worktrace'))
from worktrace.contributions import apply_reviews, contribution_score
from worktrace.resources import allocate_usage, assert_conservation, ROLE_MARKERS, CONTRIBUTION_COLORS, METRICS


def read(path):return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
def write(path, rows):path.write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in rows))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def csvout(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'results/luna_task03_v2_20261027')
    args=p.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    old=ROOT/'results/framework_one_hour_run_20261027_0230'
    original=ROOT/'results/precision_validation_20261026/reconciled_component_annotations.jsonl'
    source_components=old/'reviewed/resources/components_with_responses.jsonl'
    source_ledger=old/'reviewed/resources/response_usage.jsonl'
    mapping={c['component_id']:c for c in read(source_components)}
    assert sum(c['contribution_label']=='non_direct' for c in mapping.values()
               if int(c['order'])==3 and c['blinded_label']=='Y')==8
    source=[c for c in read(original) if int(c['order'])==3 and c['blinded_label']=='Y']
    assert len(source)==30
    for c in source:
        for key in ['run_id','response_id','native_op_id']:c[key]=mapping[c['component_id']][key]
    reviewpath=out/'contribution_review_completed.jsonl';reviews=read(reviewpath)
    assert len(reviews)==30 and {r['component_id'] for r in reviews}=={c['component_id'] for c in source}
    assert all(r['assessment_status']=='reviewed' and r['reviewer_type']=='model' for r in reviews)
    components=apply_reviews(source,reviews)
    assert all(c['contribution_label']!='non_direct' and c['contribution_review_status']=='reviewed' for c in components)
    rid=components[0]['run_id'];responses=[r for r in read(source_ledger) if r['run_id']==rid]
    assert len(responses)==8
    allocations=allocate_usage(responses,components);assert_conservation(responses,allocations)
    oldalloc={r['component_id']:r for r in read(old/'reviewed/resources/component_allocations.jsonl') if r['component_id']}
    assert all(a['usage']==oldalloc[a['component_id']]['usage'] and a['allocation_weight']==oldalloc[a['component_id']]['allocation_weight'] for a in allocations)
    write(out/'components.jsonl',components);write(out/'response_usage.jsonl',responses);write(out/'component_allocations.jsonl',allocations)
    byusage={a['component_id']:a for a in allocations}
    identity={r['component_id']:r for r in csv.DictReader((old/'reviewed/component_identity_join.csv').open())}
    full=contribution_score(components)
    assert [full[k] for k in ['direct','indirect','no_demonstrated','uncertain']]==[10,0,10,10]
    assert len({c['response_id'] for c in components if c['action_index'] in [1,2,3]})==1
    strict=contribution_score([c for c in components if c['execution_status']=='executed'])
    roles=[dict(role=role,**contribution_score([c for c in components if c['role']==role])) for role in ['exploration','edit','verification','administration']]
    csvout(out/'role_precision.csv',roles)
    usage=[];seen=set()
    for c in components:
        a=byusage[c['component_id']]
        usage.append(dict(component_id=c['component_id'],role=c['role'],execution_status=c['execution_status'],
            archived_contribution=c['archived_contribution_label'],contribution=c['contribution_label'],
            reason=c['contribution_review']['reason'],review_origin=c['contribution_review']['review_origin'],
            response_id=a['response_id'],input_tokens=a['usage']['input_tokens'],cached_input_tokens=a['usage']['cached_input_tokens'],
            output_tokens=a['usage']['output_tokens'],cost_usd=a['usage']['cost_usd'],allocation_method=a['allocation_method'],
            allocation_weight=a['allocation_weight'],target_history='unknown',
            command_recurrence='exact_repeat' if c['command'] in seen else 'new_command',
            property_checked=c['contribution_review'].get('property_checked'),
            relevant_state_changed=c['contribution_review'].get('relevant_state_changed'),
            earlier_check_ids=json.dumps(c['contribution_review'].get('earlier_check_ids',[])),
            evidence=c['contribution_review']['evidence']))
        seen.add(c['command'])
    csvout(out/'component_table.csv',usage)
    totals={metric:sum(r['usage'][metric] for r in responses) if all(r['usage'][metric] is not None for r in responses) else None for metric in METRICS}
    summary=dict(run_id=rid,components=30,native_calls=len({c['native_op_id'] for c in components}),responses=8,
        reviewed=30,prior_reviews_carried_forward=5,new_reviews=25,legacy_cases_resolved=8,
        category_counts={label:sum(c['contribution_label']==label for c in components)
                         for label in ['direct','indirect','no_demonstrated','uncertain']},
        full_precision=full,confirmed_executed_only=strict,roles=roles,usage=totals,
        legacy_unsplit_remaining=0,reviewer='Codex (model identifier unavailable)',human_validation=False,
        checkpoint_outcome='UNTESTED',allocation_changed=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    fig,ax=plt.subplots(figsize=(13,5.5),facecolor='#FCFCFA')
    x=list(range(1,31));y=[int(identity[c['component_id']]['inferred_state_after_native_call']) for c in components]
    ax.plot(x,y,color='#BAC3C9',lw=1,zorder=1)
    for i,state,c in zip(x,y,components):
        ax.scatter(i,state,s=65,marker=ROLE_MARKERS[c['role']],color=CONTRIBUTION_COLORS[c['contribution_label']],zorder=3)
    for cid in ['03:Y001.c0','03:Y004.c0','03:Y005.c0','03:Y007.c0','03:Y008.c0']:
        i=next(i for i,c in enumerate(components) if c['component_id']==cid)
        ax.annotate(cid,(x[i],y[i]),xytext=(0,28 if cid!='03:Y008.c0' else 55),textcoords='offset points',ha='center',fontsize=8,arrowprops=dict(arrowstyle='-',color='#84919A'))
    ax.set(xlabel='Candidate component order',ylabel='Inferred state AFTER parent call',xticks=range(1,31),xlim=(.2,30.8),ylim=(-.25,1.65),yticks=[0,1],yticklabels=['V0','V1'])
    ax.grid(axis='y',color='#E3E7E9')
    ax.set_title('Luna task 03 — all 30 components reviewed under v2\n10 direct / 0 indirect / 10 no demonstrated / 10 uncertain; no legacy unsplit',loc='left',fontsize=13)
    roles_handles=[Line2D([],[],marker=ROLE_MARKERS[r],color='#43515B',ls='None',label=r.title()) for r in ['exploration','edit','verification','administration']]
    color_handles=[Line2D([],[],marker='o',color=CONTRIBUTION_COLORS[l],ls='None',label=n) for l,n in [('direct','Direct'),('no_demonstrated','No demonstrated'),('uncertain','Uncertain')]]
    fig.legend(handles=roles_handles,loc='lower left',bbox_to_anchor=(.07,.13),ncol=4,frameon=False)
    fig.legend(handles=color_handles,loc='lower left',bbox_to_anchor=(.07,.07),ncol=3,frameon=False)
    fig.text(.08,.03,'Model review; independent benchmarks UNTESTED. Internal compound-call states unresolved. Token shares: component_table.csv.',fontsize=9)
    fig.subplots_adjust(bottom=.30,top=.78,left=.08,right=.98)
    fig.savefig(out/'trajectory.png',dpi=150);plt.close(fig)
    lines=['# Luna task 03: complete four-label contribution review','',
        '**All 30 components now have v2 labels; legacy unsplit = 0.** Five prior v2 judgments are carried forward and 25 are newly reviewed, including all eight remaining legacy cases. '
        'The original 20-case/four-run study and its labels are untouched. Action roles and execution-status tags are retained from the prior annotation; this completion reviews contribution labels. '
        'This is retrospective, unblinded model review by Codex (model identifier unavailable), not human validation.','',
        '| Category | Count |','| --- | ---: |',*[f'| {name} | {full[key]} |' for name,key in [('Direct','direct'),('Indirect','indirect'),('No demonstrated contribution','no_demonstrated'),('Uncertain','uncertain'),('Legacy unsplit','legacy_non_direct')]],'',
        f"Direct precision: **{full['lower']:.1%}–{full['upper']:.1%}**, using all 30 candidates under the archived execution convention. "
        f"The {strict['included']} confirmed-executed components give **{strict['lower']:.1%}–{strict['upper']:.1%}** as a separate execution sensitivity. "
        'Eight components have uncertain execution; two invoked tests have uncertain outcomes. Label bounds are not confidence intervals.','',
        '| Role | N | D | I | Z | U | Direct bounds |','| --- | ---: | ---: | ---: | ---: | ---: | --- |',
        *[f"| {r['role']} | {r['included']} | {r['direct']} | {r['indirect']} | {r['no_demonstrated']} | {r['uncertain']} | {r['lower']:.1%}–{r['upper']:.1%} |" for r in roles],'',
        'No indirect example is supported in this run. In particular, Y001–Y003 were emitted together: their chronological execution alone cannot prove one result guided generation of the next call. '
        'A later direct dependency must be demonstrated before assigning indirect. Uncertain results are not forced into the non-contributing category.','',
        'Y007.c0 changes from legacy non_direct to direct: it creates the specifically required submission artifact, which Y008 then inspects. '
        'Separators, the unused dependency inventory, repeated header support and an unsupported extra whitespace check receive no_demonstrated. '
        'Y005/Y006 timeouts provide no established test pass, so the retry is uncertain rather than proven repeated-support over-verification.','',
        f"Resources are unchanged: **{totals['input_tokens']:,} input / {totals['cached_input_tokens']:,} cached input / {totals['output_tokens']:,} output tokens**, "
        f"harness-recorded response cost **${totals['cost_usd']:.8f}** across eight responses. Cache is included in input. "
        'Component shares remain explicitly allocated estimates when a response generates several components. No raw run total was distributed to fill missing usage.','',
        ('![Complete Luna task 03 with recorded response-cost bands](response_cost_bands/luna_task_03_response_costs.png)'
         if (out/'response_cost_bands/luna_task_03_response_costs.png').exists()
         else '![Complete Luna task 03 trajectory](trajectory.png)'),'',
        '## Annotation implementation','',
        '1. Decompose native calls into meaningful work components, retaining parent action, generating response, order and execution uncertainty. Do not credit a compound call as a whole.','2. Read task requirements, the actual agent-visible observations, subsequent performed work and final patch. The final patch is evidence, not an exact-template reference; unchanged source and alternative valid fixes can contribute. Hidden/elided output receives no credit.','3. Assign one contribution label independently of action role: direct establishes relevant facts/changes/checks; indirect needs an observed decision/dependency to later performed direct work; no_demonstrated means no supported contribution in available evidence; uncertain records a specific missing result/state/link.','4. Save model identity, evidence, requirement links, command SHA256, reason, property/state/prior-check details and any indirect-support IDs in an additive overlay. Original labels remain archived_contribution_label. Five existing reviews retain their original provenance.','5. worktrace.contributions.apply_reviews checks IDs, command hashes, nonempty provenance/evidence and label vocabulary. For indirect links it enforces same run, later order, direct label and not known unexecuted. These are structural checks; the reviewer must still establish actual performance and a semantic dependency.','6. contribution_score excludes known unexecuted candidates and returns D/N to (D+U)/N. Indirect and no_demonstrated get no direct credit. Uncertain execution remains explicit, with a confirmed-execution sensitivity. Empty roles are undefined.','7. worktrace.resources.allocate_usage divides each recorded response budget across all emitted components from that response; no component is dropped for being unhelpful or unexecuted. It preserves separate input/cache/output/USD, missing values, no-tool expenditure and conservation. This script asserts every component allocation equals the previous ledger exactly.','8. Code-state placement is inferred at parent-call boundaries. Contribution, execution, token allocation and independent benchmark outcomes remain separate. No PASS or post-pass savings is inferred from these labels.','',
        'The complete evidence and original/reviewed labels are in [component_table.csv](component_table.csv), with machine-readable reviews in [contribution_review_completed.jsonl](contribution_review_completed.jsonl). '
        'Task requirements, original prompt delivery rules and final patches are preserved in the [prior context](../framework_one_hour_run_20261027_0230/task_context.md). '
        'Focused annotation/resource regression results are in [checks.txt](checks.txt).','']
    (out/'RESULTS.md').write_text('\n'.join(lines).rstrip()+'\n')
    paths=[original,source_components,source_ledger,reviewpath]
    manifest=dict(scope='User-requested full Luna task 03 review; does not change prior 20-case scope',
        components=30,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},
        code_sha256=sha(Path(__file__)),legacy_unsplit_remaining=0,
        output_hashes={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                       if p.is_file() and p != out/'manifest.json'})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
