"""Illustrative WorkTrace graph; synthetic numbers, not experimental results."""
from pathlib import Path
import json
import os
import sys

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/worktrace-example-mpl')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'worktrace'))
from worktrace.resources import allocate_usage, region_totals, ROLE_MARKERS, CONTRIBUTION_COLORS

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

OUT = ROOT/'output/figures'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    responses = [dict(response_id=f'example:R{i}',run_id='illustrative_only',usage=dict(output_tokens=t))
                 for i,t in enumerate([600,900,240,60,120,80],start=1)]
    specs = [('Read parser.py',1,'exploration','direct','V0'),
             ('Read parser tests',1,'exploration','direct','V0'),
             ('Implement the fix',2,'edit','direct','V0 -> V1'),
             ('Check repaired behavior',3,'verification','direct','V1'),
             ('Repeat the same check',4,'verification','non_direct','V1'),
             ('Re-read unchanged code',5,'exploration','non_direct','V1'),
             ('Check another edge case',6,'verification','uncertain','V1')]
    components = [dict(component_id=f'C{i}',response_id=f'example:R{r}',role=role,
                       contribution_label=label,version_region=version,title=title)
                  for i,(title,r,role,label,version) in enumerate(specs,start=1)]
    allocations = allocate_usage(responses,components)
    totals = region_totals(allocations,('version_region',))
    assert sum(r['output_tokens']['known_total'] for r in totals)==2000
    byid = {r['component_id']:r for r in allocations}
    fig,ax=plt.subplots(figsize=(14,8.2))
    fig.patch.set_facecolor('#FCFCFA');ax.set_facecolor('#FCFCFA')
    ax.set(xlim=(0,14),ylim=(0,8.2));ax.axis('off')
    ink='#17252D';muted='#53616B';line='#C4CCD1'
    ax.text(.25,7.9,'WorkTrace: code versions, contribution, and token expenditure',fontsize=18,fontweight='bold',color=ink)
    ax.text(.25,7.53,'ILLUSTRATIVE DATA  |  Output tokens only  |  No task results or real token costs are shown',fontsize=11,color=muted)

    def region(x,w,title,summary):
        ax.add_patch(FancyBboxPatch((x,1.4),w,5.8,boxstyle='round,pad=0.08,rounding_size=0.12',
                                   facecolor='#F2F5F6',edgecolor=line,lw=1.2,linestyle=(0,(4,3))))
        ax.text(x+.16,6.83,title,fontsize=13,fontweight='bold',color=ink)
        ax.text(x+.16,1.73,summary,fontsize=12,fontweight='bold',color=ink)
    region(.3,3.6,'Initial-version region','600 tokens  /  2 components')
    region(4.4,3.4,'Edit-transition region','900 tokens  /  1 component')
    region(8.3,5.4,'Repaired-version region','500 tokens  /  4 components')
    for x,text in [(2.1,'V0'),(10.95,'V1')]:
        ax.add_patch(Circle((x,6.02),.43,facecolor='white',edgecolor=ink,lw=2,zorder=4))
        ax.text(x,6.02,text,ha='center',va='center',fontsize=17,fontweight='bold',color=ink,zorder=5)
    ax.add_patch(FancyArrowPatch((2.55,6.02),(10.5,6.02),arrowstyle='-|>',mutation_scale=18,
                               lw=2,color=muted,zorder=3))
    ax.text(6.1,6.34,'edit changes the implementation',ha='center',fontsize=10,color=muted)

    def card(cid,x,y,w=3.13,h=.7):
        a=byid[cid];title=specs[int(cid[1:])-1][0]
        role=a['role'];color=CONTRIBUTION_COLORS[a['contribution_label']]
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06,rounding_size=0.08',
            facecolor='white',edgecolor=line,lw=1,zorder=5))
        ax.scatter(x+.06,y+h*.5,s=100,marker=ROLE_MARKERS[role],color=color,zorder=6)
        ax.text(x+.23,y+h*.64,f'{cid}  {title}',fontsize=10.5,fontweight='bold',color=ink,zorder=7)
        value=a['usage']['output_tokens'];r=a['response_id'].split(':')[-1]
        note=f'{value:,.0f} output tokens'
        note+=' (allocated)' if a['allocation_method']=='equal_share_response_allocation' else ' (response-associated)'
        if cid == 'C3':
            ax.text(x+.23,y+h*.29,f'{r}  |  {value:,.0f} output tokens',fontsize=9,color=muted,zorder=7)
            ax.text(x+.23,y+h*.08,'(response-associated)',fontsize=9,color=muted,zorder=7)
        else:
            ax.text(x+.23,y+h*.22,f'{r}  |  {note}',fontsize=9,color=muted,zorder=7)
    card('C1',.55,4.38)
    card('C2',.55,3.18)
    card('C3',4.57,4.30,w=3.06,h=.85)
    for cid,y in [('C4',4.90),('C5',3.97),('C6',3.04),('C7',2.11)]:card(cid,8.57,y,w=4.82)

    # Checks/reads loop back to the same version; edits alone connect versions.
    for y in [4.73,3.53]:
        ax.add_patch(FancyArrowPatch((.51,y),(1.78,5.84),connectionstyle='arc3,rad=-.38',
            arrowstyle='-|>',mutation_scale=10,color=muted,lw=1.2,alpha=.75,zorder=2))
    for cid,y in [('C4',5.25),('C5',4.32),('C6',3.39),('C7',2.46)]:
        ax.add_patch(FancyArrowPatch((13.44,y),(11.35,5.94),connectionstyle='arc3,rad=.28',
            arrowstyle='-|>',mutation_scale=10,color=muted,lw=1.1,alpha=.7,zorder=2))
    ax.text(.58,2.65,'R1 generated C1 + C2 together:',fontsize=10,color=muted)
    ax.text(.58,2.33,'600 / 2 = 300 tokens each.',fontsize=10,color=muted)
    ax.text(4.62,3.77,'900 tokens on the edit transition;',fontsize=10,color=muted)
    ax.text(4.62,3.45,'not a second charge to V1.',fontsize=10,color=muted)
    ax.text(.35,.98,'Shape:',fontsize=10,fontweight='bold',color=ink)
    x=1.55
    for role,label in [('exploration','Exploration'),('edit','Edit'),('verification','Verification')]:
        ax.scatter(x+.14,1.02,s=45,marker=ROLE_MARKERS[role],color=muted);ax.text(x+.38,.98,label,fontsize=10,color=ink);x+=1.9
    ax.text(7.25,.98,'Color:',fontsize=10,fontweight='bold',color=ink)
    x=8.05
    for label,text in [('direct','Direct'),('non_direct','Non-direct'),('uncertain','Uncertain')]:
        ax.plot([x,x+.22],[1.02,1.02],lw=3,color=CONTRIBUTION_COLORS[label]);ax.text(x+.32,.98,text,fontsize=10,color=ink);x+=1.65
    ax.text(.35,.52,'Whole trajectory: 2,000 output tokens / 7 components = 285.7 tokens per component.',fontsize=12,fontweight='bold',color=ink)
    ax.text(.35,.17,'Region totals include each response once. Component shares are an attribution assumption; they do not measure internal reasoning.',fontsize=10,color=muted)
    fig.subplots_adjust(left=.015,right=.99,bottom=.02,top=.99)
    for ext in ['png','pdf','svg']:
        path = OUT/f'worktrace_resource_example.{ext}'
        fig.savefig(path,dpi=150,facecolor=fig.get_facecolor())
        if ext == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
    plt.close(fig)
    data=dict(status='illustrative only; synthetic usage, not measured experiment',responses=responses,
              components=components,allocations=allocations,version_regions=totals)
    (OUT/'worktrace_resource_example.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Illustrative graph saved: output/figures/worktrace_resource_example.png (plus PDF/SVG and source JSON)')


if __name__=='__main__':main()
