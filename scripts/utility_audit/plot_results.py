"""Publication-style descriptive figures from the saved local audit only."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/utility_audit_20261028'


def read(path):return json.loads((OUT/path).read_text())


def main():
    fig=plt.figure(figsize=(14,8.7),layout='constrained')
    grid=fig.add_gridspec(3,2,height_ratios=[1,3,1.35],width_ratios=[1.55,1])
    ax=fig.add_subplot(grid[0,0]);bx=fig.add_subplot(grid[1,0]);cx=fig.add_subplot(grid[:2,1]);tx=fig.add_subplot(grid[2,:]);tx.axis('off')
    colors=ListedColormap(['#D7DDE3','#F4B2A6','#A4D7BC'])
    versions=['Base','Before\nformatter','Submitted','Reference']
    def matrix(axis,values,labels,title):
        values=np.array(values)
        axis.imshow(values,cmap=colors,vmin=0,vmax=2,aspect='auto')
        axis.set_xticks(range(4),versions);axis.set_yticks(range(len(labels)),labels)
        axis.tick_params(length=0,labelsize=10)
        for (y,x),v in np.ndenumerate(values):
            axis.text(x,y,{0:'BUILD FAIL',1:'FAIL',2:'PASS'}[v],ha='center',va='center',fontsize=9,fontweight='bold')
        axis.set_title(title,loc='left',fontweight='bold',fontsize=12,pad=12)
        for spine in axis.spines.values():spine.set_visible(False)
        axis.set_xticks(np.arange(-.5,4,1),minor=True)
        axis.set_yticks(np.arange(-.5,len(labels),1),minor=True)
        axis.grid(which='minor',color='white',linewidth=3);axis.tick_params(which='minor',length=0)
    matrix(ax,[[1,2,2,2]],['Patched targeted test'],'A. Task 03: first scoped pass precedes formatting')
    probes=read('requirements_task04.json')
    properties=['explicit_pool_values','explicit_false_flag','absent_flag_false','default_fixture_equals_Default','deprecated_fixture_equals_Default']
    data=[[0,1,1,2]]+[[2 if r['properties'][p] else 1 for r in probes] for p in properties]
    matrix(bx,data,['Patched selected tests','Explicit pool values','Explicit false flag','Absent flag = false','Default fixture preserved','Deprecated fixture preserved'],
           'B. Task 04: test and written-requirement contexts disagree')
    small=read('round_6/artifact_cache.json');large=read('round_6/go_check_cache.json')
    fresh=[small['fresh_median_ms'],large['fresh_median_seconds']*1000]
    reuse=[small['reuse_median_ms'],large['reuse_median_seconds']*1000]
    y=np.arange(2);cx.barh(y+.17,fresh,.3,label='Fresh check',color='#4579AD');cx.barh(y-.17,reuse,.3,label='Hash + reuse',color='#D4933C')
    cx.set_yticks(y,['Patch artifact\n1,000 paired checks','Scoped Go test\n3 fresh / 100 reuse'])
    for index,(a,b) in enumerate(zip(fresh,reuse)):
        for v,shift in [(a,.17),(b,-.17)]:cx.text(v*1.15,index+shift,f'{v:.3f} ms',va='center',fontsize=10)
    cx.set_xscale('log');cx.set_xlim(.01,15000);cx.set_xlabel('Median wall time (milliseconds, log scale)')
    cx.set_title('C. Reuse overhead changes the benefit',loc='left',fontweight='bold',fontsize=12,pad=12)
    cx.legend(frameon=False,loc='lower right');cx.spines[['top','right']].set_visible(False)
    tx.text(0,1,'What these checks establish',fontsize=12,fontweight='bold',va='top')
    tx.text(0,.73,
        '• Behavior, formatting, requirement coverage and evidence reuse need separate fields.\n'
        '• Task 04’s reference fails the authored absent-flag diagnostic; do not collapse both contexts into one reward.\n'
        '• Reuse time includes hashing and lookup. Go build caching remains enabled; test-result caching is bypassed with -count=1.\n'
        '• Two reconstructed Luna cases; scoped local checks only. No original benchmark certification or LLM savings measured.',
        fontsize=10.5,linespacing=1.65,va='top')
    fig.suptitle('WorkTrace local audit: observed outcomes, context conflicts and reuse overhead',fontsize=16,fontweight='bold')
    folder=OUT/'figures';folder.mkdir(exist_ok=True)
    fig.savefig(folder/'utility_audit.png',dpi=180,facecolor='white')
    fig.savefig(folder/'utility_audit.pdf',facecolor='white')
    print(folder/'utility_audit.png')


if __name__=='__main__':main()
