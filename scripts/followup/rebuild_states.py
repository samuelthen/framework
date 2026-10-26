"""Rebuild 16 pilot graphs in a separate process/output namespace."""
import json
import subprocess
import sys
import pandas as pd
from followup_common import ROOT,BASE,OUT,dump


def main():
    code='''import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[2])/'scripts/precision_validation'))
import compare_states
compare_states.OUT=Path(sys.argv[1])
compare_states.main()
'''
    result=subprocess.run([sys.executable,'-c',code,str(OUT),str(ROOT)],text=True,capture_output=True,check=True)
    (OUT/'state_rebuild.log').write_text(result.stdout+result.stderr)
    def read(path):return {r['run_id']:r for r in (json.loads(s) for s in path.read_text().splitlines())}
    previous=read(BASE/'corrected_version_graphs.jsonl');current=read(OUT/'corrected_version_graphs.jsonl')
    rows=[]
    for rid,g in current.items():
        old=previous[rid]
        rows.append(dict(run_id=rid,model=g['model'],versions_8da1f1a=old['n_versions'],versions_now=g['n_versions'],
                         final_root_8da1f1a=old['final']==0,final_root_now=g['final']==0,
                         uncertain_versions_8da1f1a=sum(n['uncertain'] for n in old['nodes']),
                         uncertain_versions_now=sum(n['uncertain'] for n in g['nodes'])))
    pd.DataFrame(rows).to_csv(OUT/'restore_scope_graph_delta.csv',index=False)
    dump(OUT/'restore_scope_status.json',dict(status='repaired and regression-covered',pilot_graphs=len(rows),
        graphs_with_version_count_change=sum(r['versions_8da1f1a']!=r['versions_now'] for r in rows),
        limits='Scope proof now requires initial complete tracked listing and clean baseline; missing evidence preserves uncertainty. Not a complete filesystem snapshot reconstruction.'))


if __name__=='__main__':main()
