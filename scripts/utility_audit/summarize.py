"""Summarize saved execution evidence; does not launch new checks or annotators."""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/utility_audit_20261028'


def read(name): return json.loads((OUT/name).read_text())
def lines(name): return [json.loads(s) for s in (OUT/name).read_text().splitlines() if s.strip()]
def write(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def test_outcome(record):
    stdout=(OUT/f"container_logs/{record['label']}.stdout.txt").read_text()
    stderr=(OUT/f"container_logs/{record['label']}.stderr.txt").read_text()
    events=[]
    for line in stdout.splitlines():
        try: e=json.loads(line)
        except ValueError: continue
        if e.get('Test') and e.get('Action') in ['pass','fail','skip']:
            events.append(dict(test=e['Test'],outcome=e['Action']))
    build_fail='[build failed]' in stdout or ('undefined:' in stderr or 'unknown field' in stderr)
    return dict(task=record['task_order'],snapshot=record['snapshot'],
        outcome='build_failure' if build_fail else 'pass' if record['exit_code']==0 else 'fail',
        test_events=events,scope=record['command'],label=record['label'])


def main():
    checks=[test_outcome(r) for task in [3,4] for r in read(f'tests_task{task:02d}.json')]
    formats=read('format_task03.json')+read('format_task04.json')
    write('round_4/summary.json',dict(round=4,
        critique='Command labels and whole-call versions hide intermediate edit states and byte-level no-ops.',
        improvement='Reconstruct edit boundaries; independently execute scoped checks; record byte effect and behavior separately.',
        reconstructed_luna_tasks=2,patched_test_executions=len(checks),formatter_file_checks=len(formats),
        formatter_files_changing_bytes=sum(r['formatter_changes_bytes'] for r in formats),
        first_scoped_pass_task03='before_formatter',actual_final_benchmark_evaluations=0,
        checks=checks,formatter_results=formats))
    probes=read('requirements_task04.json')
    write('round_5/summary.json',dict(round=5,
        critique='One test pass/fail or a reference diff is not a universal definition of correct progress.',
        improvement='Specify requirement/property context and report conflicts and preservation separately.',
        authored_probe_executions=4,properties_per_snapshot=5,reference_conflict='absent_flag_false',
        scope='five authored diagnostics on task 04; not five independent benchmark tasks',
        probes=probes,agent_continuations=0,causal_action_utilities_measured=0))
    small=read('round_6/artifact_cache.json');large=read('round_6/go_check_cache.json')
    write('round_6/summary.json',dict(round=6,
        critique='A valid repeat does not imply a useful cache: dependency validation and lookup have overhead.',
        improvement='Compare fresh and reuse paths including hashing and decoding, under explicit scope.',
        artifact_net_median_saved_ms=small['net_median_saved_ms'],
        go_net_median_tool_time_saved_seconds=large['net_median_tool_time_saved_seconds'],
        actual_llm_savings_measured=False,original_trace_cache_hits_certified=0,
        fresh_go_runs=3,cache_lookup_samples=100,cheap_path_iterations=1000,
        limitations=['Three stable test outcome sets do not prove determinism.',
                    'Fixed external module/build caches are controlled assumptions, not fully hashed dependencies.',
                    'Fresh Go command explicitly bypasses Go test-result cache with count=1; build cache remains enabled.',
                    'No agent continuation, model generation, downstream context cost or production storage measured.']))
    reconciled=lines('resources_16runs/run_usage_reconciliation.jsonl')
    metrics=['input_tokens','cached_input_tokens','output_tokens']
    runids=sorted({r['run_id'] for r in reconciled})
    rows=[]
    for rid in runids:
        fields={r['metric']:r for r in reconciled if r['run_id']==rid}
        residuals={m:fields[m]['recorded_run_total']-fields[m]['known_response_sum'] for m in metrics}
        rows.append(dict(run_id=rid,model=rid.split(':')[1],
            all_token_metrics_reconcile=all(fields[m]['status']=='matches' for m in metrics),
            unlocalized_token_residual=residuals,
            stored_response_coverage={m:fields[m]['known_response_sum']/fields[m]['recorded_run_total'] for m in metrics},
            cost_status=fields['cost_usd']['status'],
            interpretation='Residual is a run/ledger discrepancy; cause and per-action attribution are unknown.'))
    write('round_7/records.json',rows)
    write('round_7/summary.json',dict(round=7,
        critique='Conserving the stored response ledger does not establish agreement with total recorded run expenditure.',
        improvement='Reconcile each metric; show unlocalized residual separately; restrict percentages to their named denominator.',
        runs=len(rows),runs_with_all_three_token_metrics_matching=sum(r['all_token_metrics_reconcile'] for r in rows),
        mismatching_runs=sum(not r['all_token_metrics_reconcile'] for r in rows),
        metric_status_counts=dict(Counter(r['status'] for r in reconciled)),
        luna_cost_runs_matching=sum(r['cost_status']=='matches' and r['model']=='luna' for r in rows),
        gemini_response_cost_runs_incomplete=sum(r['cost_status']=='response_usage_incomplete' and r['model']=='gemini_3_7_flash' for r in rows)))
    # Preserve real response-associated tokens, but never silently relabel them as
    # full run cost or per-component causal reasoning expenditure.
    regions=lines('resources_16runs/region_totals.jsonl'); role_rows=[]
    for rid in runids:
        rs=[r for r in regions if r['run_id']==rid and r['view']=='role' and r['region_method']=='equal_component_allocation']
        for r in rs:
            row=dict(run_id=rid,role=r['role'],method='equal emitted-component allocation',metrics={})
            for m in [*metrics,'cost_usd']:
                vals=[s[m]['known_total'] for s in rs]
                total=sum(vals) if all(v is not None for v in vals) else None
                row['metrics'][m]=dict(allocated_amount=r[m]['known_total'],
                    fraction_of_stored_response_total=r[m]['known_total']/total if total else None,
                    denominator='stored response usage; see round_7 residuals for relation to full run')
            role_rows.append(row)
    write('round_7/role_expenditure.json',role_rows)
    write('summary.json',dict(iterations=7,downloaded_trajectory_shards=2,
        selected_tasks=8,selected_runs=16,native_calls=449,candidate_components=769,
        reconstructed_tasks=2,model_calls=0,agent_continuations=0,
        actual_final_benchmark_evaluations=0,
        rounds=[read(f'round_{i}/summary.json') for i in range(1,8)]))
    print('Saved seven iteration summaries and the scoped execution matrix.')


if __name__=='__main__': main()
