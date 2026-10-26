"""Report completed follow-up work separately from experiments awaiting inputs."""
import importlib.metadata
import json
import platform
import re
from pathlib import Path
import pandas as pd
from followup_common import ROOT,BASE,OUT,dump,jsonl,sha


def main():
    roles=pd.read_csv(OUT/'role_precision_summary.csv')
    ver=pd.read_csv(OUT/'verification_reason_counts.csv')
    restore=json.loads((OUT/'restore_scope_status.json').read_text())
    expert=json.loads((OUT/'expert_validation_status.json').read_text())
    packet=json.loads((OUT/'expert_packet_status.json').read_text())
    design=json.loads((OUT/'confirmation_design.json').read_text())
    accuracy_text=('Accuracy is not computed.' if expert.get('accuracy') is None else
                   f"Accuracy on supplied non-abstaining assessable enriched cases is {100*expert['accuracy']:.1f}%; inspect coverage before interpretation.")
    tests=re.search(r'(\d+) passed',(OUT/'test_results.txt').read_text()).group(1)
    text=['# Follow-up work: restore scope, adjudication and experiment preparation','',
        'The two restore cases are repaired and regression-covered. The disagreement review and repeated-support '
        'screen are complete as model-coded analyses. The four scientific experiments are **not all completed**: '
        'human reference judgments and configured target execution backends are still missing. No accuracy, '
        'confirmed system ranking, property-saturation result or live cost reduction is invented for these gaps.','',
        '## Completed repairs','',
        '- `git checkout .` cannot erase untracked or staged changes in the graph. Restores now require initial '
        'complete tracked-path evidence and a clean baseline; absent evidence keeps state uncertain.',
        '- Index/HEAD mutations invalidate restore assumptions. Known-write sensitivity graphs also preserve that '
        'uncertainty. `final_is_initial` explicitly distinguishes root identity from an uncertain placeholder node.',
        '- Regression checks include real Git repositories created in temporary directories. Only test-authored '
        'commands are executed there; no dataset trajectory commands are executed.',
        f'- **{tests} project/study/follow-up tests pass**, plus the seven original audit probes and three restore-scope '
        'probes (the third is a supported positive restore control).',
        f'- Rebuilt {restore["pilot_graphs"]} pilot graphs separately; '
        f'{restore["graphs_with_version_count_change"]} version counts change relative to 8da1f1a. '
        'See `restore_scope_graph_delta.csv`. Historical results/labels are preserved, not silently regenerated.','',
        '## Consequential disagreements and expert validation','',
        '- Ranked every disputed component by its potential equal-task bound-width effect, with separate '
        'exploration and verification priority queues. Fixed-denominator weights are review priorities, not '
        'estimates of changes when execution/role denominators change.',
        '- Inspected the 12 highest-impact assessable label disagreements against visible outputs and earlier reads. '
        '`model_review_decisions.json` records proposed judgments and trace citations. These are model-coded '
        'adjudication proposals and do not replace the independent reference.',
        '- The review distinguishes location-only searches, formatting without demonstrated repair, unchanged '
        'rereads, useful baseline characterization and documentation-scope uncertainty. Seeing a line in the '
        'final patch is insufficient by itself.',
        f'- Prepared a blinded {packet["cases"]}-case expert packet: up to two available high-impact disagreements plus two random agreement '
        'controls per task, with full anonymous tool histories/final patches and raw task references. '
        'Task 09 has no contribution-label disagreements, so its two missing disagreement slots are not invented. '
        'Separate blank forms support independent requirement review and all 769 component judgments.',
        f'- Current accepted human requirement tasks: {len(expert["approved_requirement_tasks"])}; valid human '
        f'case judgments: **{expert["valid_judgments"]}**. {accuracy_text} '
        f'The {packet["cases"]}-case sample is enriched and cannot establish population accuracy.',
        '- Prepared paired derived-state-aware/withheld annotation inputs with identical raw context. '
        'Withholding computed state features does not prevent a reviewer from inferring state from edits. '
        'Neither ablation has been labeled/scored against a human reference yet. Controlled synthetic challenges '
        'also cover equivalent call packaging, residual opaque granularity, alternative valid fixes and '
        'verification before/after relevant edits; these are fixtures, not additional empirical results.','',
        '## Equal-run exploration and verification precision','',
        'These reproduce the archived two-pass labels and the existing role-reconciliation convention. Bounds '
        'are annotation bounds, not confidence intervals. Complete paired tasks are equally weighted; pooled '
        'shares are in separate columns. Non-verification role disputes still inherit B in the historical '
        'reconciliation, which is an additional limitation of exploration estimates.','',
        '| Model | Exploration | Verification |','|---|---:|---:|']
    for model in ['gemini-3.7-flash','gpt-5.6-luna']:
        r=roles[(roles.version=='cross_review')&(roles.model==model)].set_index('role')
        a,b=r.loc['exploration'],r.loc['verification']
        text.append(f'| {model} | {100*a.run_mean_lower:.1f}–{100*a.run_mean_upper:.1f}% | '
                    f'{100*b.run_mean_lower:.1f}–{100*b.run_mean_upper:.1f}% |')
    text+=['','## Isolated verification diagnoses','',
        'One contribution enum is retained: `direct / non_direct / uncertain`. Reason categories are explanatory '
        'fields, not replacement labels. Counts below are a conservative **model-coded screen**, not an expert '
        'measure of over-verification. Shared parent-output environment cues may mix component causes.','',
        '| Model | Supported repeated-support screen | Other non-direct categories | Uncertain verification |',
        '|---|---:|---:|---:|']
    for model,g in ver.groupby('model'):
        strict=int(g[g.reason_category=='supported_repeated_support'].components.sum())
        other=int(g[(g.contribution_label=='non_direct')&(g.reason_category!='supported_repeated_support')].components.sum())
        unknown=int(g[g.contribution_label=='uncertain'].components.sum())
        text.append(f'| {model} | {strict} | {other} | {unknown} |')
    text+=['',
        'A supported repeat requires non_direct reconciliation, both reviewers calling repeated support on unchanged '
        'relevant state, a common earlier check judged direct by both, and no environment cue. Environment/setup '
        'failure candidates, unrelated checks, other non-direct work and unconfirmed repeats stay separate in '
        '`verification_reason_audit.csv`. No passing/different command automatically earns direct credit.',
        'The normalized-property/state review form and coverage-curve computation are implemented. No property '
        'saturation curve is reported yet: zero normalized expert scope records are approved. A flat curve would '
        'not by itself prove non-contribution, because justified confidence can be direct.','',
        '## Confirmation panels frozen','',
        '| Panel | Shared non-development tasks | Joint-success eligible | Initial samples |','|---|---:|---:|---|']
    for p in design['panels']:
        text.append(f'| {p["panel"]} | {p["shared_tasks"]} | {p["joint_success_eligible"]} | 30 all-attempt + 30 joint-success tasks |')
    text+=['',
        'The attempt samples do not condition on outcome. The semantic samples explicitly condition on joint '
        'success; they are different target populations and must not be combined as an unconditional success '
        'estimate. Original calibration/evaluation tasks are excluded. Reference-patch-size quartiles provide '
        'the independent demand proxy. These are fresh to contribution-pilot annotation, not unseen by all '
        'older aggregate/novelty analyses.',
        '`confirmation_saved_effort.csv` and `confirmation_paired_effort.csv` report archived success/interaction '
        'effort and paired task intervals only. They are not new semantic confirmation or new benchmark episodes. '
        'Contribution labels/reference validation are pending. Thirty tasks is a starting workload, not a power '
        'guarantee; freeze any expansion/stopping method before confirmation decisions.','',
        '## Self-loop control prototype','',
        'Implemented unrestricted, simple check-count-cap and property/state-aware controllers. The intervention '
        'is **suppress a dedicated check while continuing the agent**, not terminate the run. Mixed calls are '
        'ineligible for automatic partial suppression. The state-aware API accepts no final patch or future '
        'contribution labels, requires a complete assessed runtime content snapshot, and permits work when '
        'property/state/determinism is unknown. New properties and relevant edits reset the loop criterion.',
        'Thresholds k=1,2,3 have logic regression tests, not live utility results. No threshold/cap is selected. '
        'Docker is available (29.8.1), but selected-task adapters and target Gemini/Luna/Qwen backends are not '
        'configured. The existing annotation proxy is not treated as evidence of those target systems. '
        'No live episodes or new paid API jobs were run; cost/success/non-inferiority are unmeasured.',
        'The full four-experiment protocol is in `experiment_protocol.json`. Experiments 1–3 support the '
        'framework/behavior story only after their human/annotation gates pass. Experiment 4 is the separate '
        'actionability test; no safe stopping claim follows from this screen. Failed-run recall remains deferred.','',
        '## Reproduce and supply the missing inputs','',
        '```bash','bash scripts/followup/run_all.sh','```','',
        'No download, model call or live task execution is hidden in this command. Filled expert forms are '
        'preserved. Start with `expert_blind/README.md`, requirement_reviews.jsonl and judgments.jsonl. '
        'To execute the later live study, provide target-system/harness configuration and task environments '
        'after expert calibration. Original results remain under `precision_validation_20261026/`.','']
    (OUT/'RESULTS.md').write_text('\n'.join(text))
    dump(OUT/'status.json',{
        'restore_cases':'repaired; regression-covered',
        'disagreement_review':'12 model-coded proposals; independent expert forms prepared',
        'experiment_1':'pending human reference and actual ablation outputs',
        'experiment_2':'samples frozen; archived effort computed; semantic confirmation pending',
        'experiment_3':'repeat/failure screen computed; normalized expert property/state curves pending',
        'experiment_4':'prefix-only prototype tested; target runtime/configuration and live cost/success experiments pending',
        'human_accuracy_computed':expert.get('accuracy') is not None,'new_live_episodes':0,'threshold_selected':None,
        'failed_run_recall':'deferred'})
    old=json.loads((BASE/'manifest.json').read_text())
    verification={}
    for name,expected in old['output_sha256'].items():
        path=BASE/name
        verification[name]='match' if path.exists() and sha(path)==expected else 'missing_or_changed'
    dump(OUT/'original_output_integrity.json',verification)
    assert all(v=='match' for v in verification.values()),'Original results modified'
    inputs=list((ROOT/'scripts/followup').glob('*.py'))+[ROOT/'scripts/followup/run_all.sh']
    inputs += [ROOT/p for p in ['worktrace/worktrace/versions.py','worktrace/worktrace/parse/shell.py',
        'worktrace/tests/test_restore_scope.py','audit/probe_restore_scope.py','data/runs.parquet',
        'results/v2/task5/runs_benchmark.parquet','raw/jetbrains/gemini_3_7_flash-run1.parquet',
        'raw/jetbrains/luna-run1.parquet','worktrace/tests/test_versions.py',
        'paper/worktrace-draft/PROGRESS_AND_NEXT_STEPS.md',
        'results/one_day_precision_20261026/packets/blinding_key.csv',
        'results/one_day_precision_20261026/sample_manifest.csv']]
    inputs += [p for p in BASE.iterdir() if p.is_file()]
    inputs += [OUT/'model_review_decisions.json',OUT/'experiment_protocol.json',OUT/'runtime_inventory.json']
    dump(OUT/'manifest.json',dict(python=platform.python_version(),
        packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','pyarrow','pytest']},
        inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs if p.exists()},
        outputs={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ('manifest.json','run.log')},
        original_output_hashes_verified=len(verification),reproduce='bash scripts/followup/run_all.sh'))
    print('Wrote follow-up report/status/manifest; original output hashes unchanged')


if __name__=='__main__':main()
