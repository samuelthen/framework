"""Revised, independently versioned continuation pilot after failed setup audit."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys
import pyarrow.parquet as pq
import live_pilot as live

ROOT=live.ROOT
OLDRAW=ROOT/'raw/live_utility'
live.RAW=ROOT/'raw/live_utility_v2'
live.OUT=ROOT/'results/research_loop_20261028/live_v2'


def prepare():
    live.RAW.mkdir(parents=True,exist_ok=True);live.OUT.mkdir(parents=True,exist_ok=True)
    if (live.OUT/'plan.json').exists():
        print('Frozen v2 plan retained.');return
    cases=json.loads((OLDRAW/'cases.json').read_text())
    oracles=json.loads((OLDRAW/'private_oracles.json').read_text())
    refs={r['instance_id']:r for r in pq.read_table(ROOT/'raw/swebenchpro/v1.parquet').to_pylist()}
    for case in cases:
        folder=live.RAW/'prefixes'/case['id'];folder.mkdir(parents=True,exist_ok=True)
        live.clone_tree(OLDRAW/'prefixes'/case['id']/'public_build_cache',folder/'public_build_cache')
        shutil.copy2(OLDRAW/'prefixes'/case['id']/'public_checks.json',folder/'public_checks.json')
        case.update(continuation_steps=8,wall_seconds=360,show_candidate_diff=True)
        blocks=[]
        for block in refs[case['task_id']]['patch'].split('diff --git ')[1:]:
            path=next((s[6:] for s in block.splitlines() if s.startswith('+++ b/')),'')
            if '/testdata/' in '/'+path:
                blocks.append('diff --git '+block)
        oracles[case['id']]['fixture_patch']=''.join(blocks)
    live.write(live.RAW/'cases.json',cases);live.write(live.RAW/'private_oracles.json',oracles)
    schedule=[dict(case=c['id'],model='x-test-2',arm=a,replicate=r) for c in cases for a in ['fresh','cache','bypass'] for r in range(2)]
    random.Random(20261029).shuffle(schedule)
    live.write(live.OUT/'plan.json',dict(version=2,selection='Same three snapshots as v1; no outcome-dependent case replacement.',
        source='Authorized Soc service; x-test-2 preflight identifies deepseek-v4.1-flash-1017.',
        changes_from_v1=['Eight equal-budget calls and visible candidate diff to reduce reorientation.',
            'Copy-on-write private caches; same source and cache snapshots in all arms.',
            'Primary exact dataset test-patch context and secondary fixture-complete context; fixtures are host-only.',
            'Infrastructure failures remain missing, never model failures.'],
        max_model_calls_per_episode=8,max_output_tokens_per_call=3072,requested_reasoning_effort='low',
        max_api_attempts=160,max_accounted_tokens=3_000_000,workers=2,schedule=schedule,
        independence='Two decodes per cell on three chosen tasks are diagnostic replicates, not 18 independent tasks.',
        cache_scope='Canonical public outcomes on a fixed snapshot; lookup includes source hashing; eligibility assessed in v1 preflight.',
        endpoint_cost='User describes Soc as free; billing not independently measured, monetary cost stays null.',
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/research_loop/live_pilot.py',ROOT/'scripts/research_loop/soc_client.py']}))
    print('Frozen 18 v2 episodes; exact and fixture-complete grading contexts retained.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','execute']);parser.add_argument('--env-file');args=parser.parse_args()
    prepare() if args.phase=='prepare' else live.execute(args.env_file)
