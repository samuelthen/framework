"""Static scientific figures for the measurement study and live pilot."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/research_loop_20261028'


def main():
    fig,axes=plt.subplots(1,3,figsize=(15,4.7),layout='constrained',gridspec_kw={'width_ratios':[1.15,1,1.1]})
    data=json.loads((OUT/'robustness_summary.json').read_text())
    primary=next(r for r in data if r['split']=='confirmation' and r['scope']=='all_attempts' and r['first']=='gemini_3_7_flash')
    ax,bx,cx=axes
    keys=['native_calls','candidate_components','output_tokens'];labels=['Native calls','Candidate\ncomponents','Reported\noutput tokens']
    ratios=[primary['ratios'][k] for k in keys];x=np.arange(3)
    ax.bar(x,[r['estimate'] for r in ratios],color=['#416A98','#438A78','#B27B37'],width=.65)
    ax.errorbar(x,[r['estimate'] for r in ratios],yerr=[[r['estimate']-r['lo'] for r in ratios],[r['hi']-r['estimate'] for r in ratios]],fmt='none',ecolor='#222',capsize=4)
    for i,r in enumerate(ratios):ax.text(i,r['hi']+.35,f"{r['estimate']:.2f}×",ha='center',fontsize=11)
    ax.axhline(1,color='#555',ls='--',lw=.8);ax.set_xticks(x,labels);ax.set_ylim(0,14.7)
    ax.set_ylabel('Gemini / Luna ratio of means');ax.set_title('A. Work units change the comparison',loc='left',fontsize=12,fontweight='bold')
    ax.text(.03,.93,'30 frozen matched tasks\nTask-bootstrap 95% intervals',transform=ax.transAxes,va='top',fontsize=9)
    bounds=json.loads((OUT/'full_run_share_bounds.json').read_text())
    equal=json.loads((OUT/'cost_share_bounds.json').read_text())
    token_baseline=json.loads((OUT/'text_baseline_summary.json').read_text())['attribution_contrasts'] if (OUT/'text_baseline_summary.json').exists() else []
    roles=['exploration','edit','verification'];y=np.arange(3)
    for i,role in enumerate(roles):
        r=next(r for r in bounds if r['role']==role and r['metric']=='output_tokens')
        e=next(r for r in equal if r['role']==role and r['metric']=='output_tokens' and r['split']=='confirmation' and r['scope']=='all_attempts')
        bx.plot([r['lower']['mean']*100,r['upper']['mean']*100],[i,i],lw=8,color='#BCCCDD',solid_capstyle='round')
        bx.plot(e['equal_candidate_allocation_difference']['mean']*100,i,'D',color='#A26A29',ms=7)
        if token_baseline:
            baseline=next(r for r in token_baseline if r['role']==role)
            bx.plot(baseline['gemini_minus_luna_mean_share']*100,i,'o',color='#754898',ms=7)
    bx.axvline(0,color='#444',ls='--',lw=1);bx.set_yticks(y,['Exploration','Edit','Verification']);bx.set_xlim(-40,55);bx.set_ylim(2.6,-.6)
    bx.set_xlabel('Gemini − Luna share (percentage points)');bx.set_title('B. Role-cost rankings are unresolved',loc='left',fontsize=12,fontweight='bold')
    bx.text(.02,.03,'Band: full-run accounting bounds\nDiamond: equal split; circle: command tokens\nConditional on operational categories',transform=bx.transAxes,fontsize=8.5,va='bottom')
    manifest=json.loads((OUT/'reconciliation_summary.json').read_text());models=['luna','gemini_3_7_flash','terra']
    known=[manifest['per_model'][m]['matching'] for m in models];missing=[700-n for n in known]
    cx.barh(np.arange(3),known,color='#438A78',label='Three token totals reconcile')
    cx.barh(np.arange(3),missing,left=known,color='#C27C68',label='Mismatch / unavailable')
    for i,n in enumerate(known):cx.text(n/2,i,f'{n}/700',ha='center',va='center',color='white',fontweight='bold')
    cx.set_yticks(np.arange(3),['Luna','Gemini','Terra']);cx.invert_yaxis();cx.set_xlim(0,700);cx.set_xlabel('Archived runs')
    cx.set_title('C. Response coverage needs auditing',loc='left',fontsize=12,fontweight='bold');cx.legend(loc='lower left',bbox_to_anchor=(0,-.28),frameon=False,fontsize=8)
    for a in axes:a.spines[['top','right']].set_visible(False)
    fig.suptitle('WorkTrace: work granularity, attribution uncertainty and telemetry coverage',fontsize=15,fontweight='bold')
    folder=OUT/'figures';folder.mkdir(exist_ok=True)
    for ext in ['png','pdf']:fig.savefig(folder/f'measurement_findings.{ext}',dpi=180,facecolor='white')
    live=OUT/'live_v2/analysis.json'
    if live.exists():
        rows=json.loads(live.read_text())['arm_summary']
        fig,axes=plt.subplots(1,3,figsize=(13,4.2),layout='constrained')
        colors=['#416A98','#438A78','#B27B37'];names=['Fresh','Cache','Bypass'];x=np.arange(3)
        for ax,field,title,ylabel in [(axes[0],'mean_initial_check_seconds','Initial public-check overhead','Seconds'),(axes[1],'mean_output_tokens','Continuation generation','Mean reported output tokens')]:
            values=[r[field] or 0 for r in rows];ax.bar(x,values,color=colors);ax.set_xticks(x,names);ax.set_title(title,loc='left',fontsize=11,fontweight='bold');ax.set_ylabel(ylabel)
        ax=axes[2];w=.34
        ax.bar(x-w/2,[r['scoped_pass'] for r in rows],w,color='#416A98',label='Exact test-patch context')
        ax.bar(x+w/2,[r['fixture_pass'] for r in rows],w,color='#9BB9A9',label='Fixture-complete context')
        ax.set_xticks(x,names);ax.set_ylim(0,6.8);ax.set_ylabel('Passing episodes / six scheduled');ax.set_title('Independent scoped outcomes',loc='left',fontsize=11,fontweight='bold');ax.legend(fontsize=8,frameon=False)
        for ax in axes:ax.spines[['top','right']].set_visible(False)
        fig.suptitle('DeepSeek diagnostic pilot: three fixed snapshots, two decodes per arm',fontsize=14,fontweight='bold')
        for ext in ['png','pdf']:fig.savefig(folder/f'deepseek_pilot.{ext}',dpi=180,facecolor='white')
    print(folder)


if __name__=='__main__':main()
