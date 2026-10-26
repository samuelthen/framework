"""Finish the fixed two-task smoke study from local sources; no task execution.

Requires a quickcheck output under RUN/reviewed and the current-session review
at RUN/contribution_review_completed.jsonl. Does not create semantic judgments,
fetch data, launch containers, or modify archived results.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'worktrace'))
from worktrace.checkpoints import summarize_checkpoints
from worktrace.contributions import contribution_score
from worktrace.resources import assert_conservation, METRICS
from worktrace.loaders.jetbrains import load_row


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write(path, rows):
    path.write_text(''.join(json.dumps(row, allow_nan=False) + '\n' for row in rows))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def textsha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csvout(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def decoded(value):
    try: return json.loads(value)
    except (ValueError, TypeError): return value


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |',
            *['| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows]]


def bounds(row):
    return 'undefined' if row['included'] == 0 else f"{row['lower']:.1%}–{row['upper']:.1%}"


def display_usage(value):
    if value is None: return 'unavailable'
    return f'{int(value):,}' if value == int(value) else f'{value:,.2f}'


def load_sources(sample):
    import pyarrow.parquet as pq
    rows, paths = {}, []
    for model in ['gemini_3_7_flash', 'luna']:
        path = ROOT / f'raw/jetbrains/{model}-run1.parquet'; paths.append(path)
        tasks = [s['task_id'] for s in sample if s['run_id'].startswith(f'jb:{model}:')]
        for row in pq.read_table(path, filters=[('instance_id', 'in', tasks)]).to_pylist():
            rid = f"jb:{row['model']}:{row['instance_id']}:r{int(row['run'])}"
            if rid in {s['run_id'] for s in sample}: rows[rid] = row
    refpath = ROOT / 'raw/swebenchpro/v1.parquet'; paths.append(refpath)
    refs = {r['instance_id']: r for r in pq.read_table(refpath,
        filters=[('instance_id', 'in', sorted({s['task_id'] for s in sample}))]).to_pylist()}
    assert set(rows) == {s['run_id'] for s in sample} and len(refs) == 2
    return rows, refs, paths


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--started-at', required=True, help='ISO UTC start of user task, not subprocess start')
    args = p.parse_args(); out = args.run_dir; current = out / 'reviewed'
    started = dt.datetime.fromisoformat(args.started_at)
    if started.tzinfo is None: raise ValueError('start needs timezone')
    sample = list(csv.DictReader((current / 'sample.csv').open()))
    components = read(current / 'components.jsonl')
    reviews = read(out / 'contribution_review_completed.jsonl')
    assert len(sample) == 4 and len({s['task_id'] for s in sample}) == 2
    assert {int(s['order']) for s in sample} == {3, 4} and len(components) == 175
    assert len(reviews) == 20 and all(r['assessment_status'] == 'reviewed' for r in reviews)
    assert set(r['component_id'] for r in reviews) == set(r['component_id'] for r in read(out / 'contribution_review_template.jsonl'))
    assert sum(c['contribution_review_status'] == 'reviewed' for c in components) == 20
    assert collections.Counter(r['contribution_label'] for r in reviews) == {
        'direct': 7, 'indirect': 1, 'no_demonstrated': 11, 'uncertain': 1}
    archived = {r['component_id']: r for r in read(ROOT / 'results/precision_validation_20261026/reconciled_component_annotations.jsonl')}
    assert all(c['archived_contribution_label'] == archived[c['component_id']]['contribution_label']
               and c['command'] == archived[c['component_id']]['command'] for c in components)
    identity = {r['component_id']: r for r in csv.DictReader((current / 'component_identity_join.csv').open())}
    responses = read(current / 'resources/response_usage.jsonl')
    allocations = read(current / 'resources/component_allocations.jsonl')
    reconcile = read(current / 'resources/run_usage_reconciliation.jsonl')
    assert len(responses) == 104
    assert_conservation(responses, allocations)
    assert len({r['response_id'] for r in responses}) == 104
    token_reconcile = [r for r in reconcile if r['metric'] in METRICS[:3]]
    assert len(token_reconcile) == 12 and all(r['status'] == 'matches' for r in token_reconcile)
    raw, refs, source_paths = load_sources(sample)
    row_hashes, ops = [], {}
    context = ['# Complete task and submitted-patch context', '',
        'Selected source evidence only; no trajectory commands have been executed. '
        'Reference patches are one route, not mandatory implementations.', '']
    coverage = []
    for s in sample:
        rid = s['run_id']; row = raw[rid]; _, operations = load_row(row); ops[rid] = operations
        rs = [r for r in responses if r['run_id'] == rid]
        ms = json.loads(row['messages']); src_responses = [m for m in ms if m.get('object') == 'response']
        assert len(src_responses) == len(rs) == row['api_calls']
        assert all(r['usage']['cached_input_tokens'] <= r['usage']['input_tokens'] for r in rs)
        assert all(m['usage']['total_tokens'] == m['usage']['input_tokens'] + m['usage']['output_tokens'] for m in src_responses)
        row_hashes.append(dict(run_id=rid, task_record_sha256=row['task_record_sha256'],
            messages_sha256=textsha(row['messages']), submission_sha256=textsha(row['submission']),
            model_name=row['model_name'], api_calls=row['api_calls'], cost_source=row['cost_source'],
            archived_resolved=bool(row['resolved']), source_error_responses=sum(bool(m.get('error')) for m in src_responses)))
        coverage.append(dict(order=s['order'], model=s['model'], run_id=rid,
            components=sum(identity[c['component_id']]['run_id'] == rid for c in components),
            native_calls=len(operations), responses=len(rs),
            input_responses=sum(r['usage']['input_tokens'] is not None for r in rs),
            cache_responses=sum(r['usage']['cached_input_tokens'] is not None for r in rs),
            output_responses=sum(r['usage']['output_tokens'] is not None for r in rs),
            cost_responses=sum(r['usage']['cost_usd'] is not None for r in rs),
            no_tool_responses=sum(r['tool_call_count'] == 0 for r in rs),
            missing_provider_response_ids=sum(r['source_response_id'] is None for r in rs),
            input_tokens=row['input_tokens'], cached_input_tokens=row['cached_input_tokens'],
            output_tokens=row['output_tokens'], run_cost_usd=row['cost_usd'], cost_source=row['cost_source']))
        if s['model'] == 'gemini-3.7-flash':
            ref = refs[s['task_id']]
            context += [f"## Task {int(s['order']):02d}", '', f"Instance: {s['task_id']}; base: {ref['base_commit']}", '',
                '### Problem', '', decoded(ref['problem_statement']), '', '### Requirements', '', decoded(ref['requirements']), '',
                '### Interface', '', decoded(ref['interface']), '', '### Reference patch (one route)', '',
                '```diff', ref['patch'], '```', '']
        context += [f"### Task {int(s['order']):02d} {s['model']} final submitted patch", '',
            f"Source messages hash: {textsha(row['messages'])}; patch hash: {textsha(row['submission'])}", '',
            '```diff', row['submission'], '```', '']
    context += ['## Submission requirement H2', '',
        'Both actual task prompts require: create patch.txt, inspect it in a separate tool call and confirm only intended source changes with standard headers, then submit in another call. '
        'This requirement distinguishes the first saved-artifact inspection from a repeated live-worktree diff.', '',
        '## Reference conflicts and alternative fixes', '',
        '- Task 03 R1/R2: classify wrapped cancellation/deadline errors correctly; R3: auth must not mask them; R4: preserve unrelated error/success behavior. '
        'The reference removes status forwarding and changes server wiring. These exact edits are not mandatory: the model patches retain status forwarding and use other context checks. No intermediate or final correctness is inferred from matching a patch.',
        '- Task 04 R1: add typed pool fields; R2: map optional pool keys; R3: absent update key must yield false; R4: default/deprecated fixtures equal Default and preserve unrelated values. '
        'The prose/default-preservation language, accepted reference and existing configured-case test conflict with explicit false-on-absence wording. '
        'Gemini retains true; Luna changes Default to false and observes an old configured-case failure. The archived resolved flag does not resolve that conflict. '
        'Reference MaxIdleConn=2, command-side pool setters, JSON tag changes and YAML additions are not imposed as extra loader requirements in this review.', '']
    (out / 'task_context.md').write_text('\n'.join(context) + '\n')
    write(out / 'source_records.jsonl', row_hashes)
    csvout(out / 'resource_coverage.csv', coverage)

    review_byid = {r['component_id']: r for r in reviews}
    evidence = ['# Current-session review evidence', '',
        'All 20 judgments are unblinded model reviews by Codex (model identifier unavailable), not human validation. '
        'Full requirements/reference/final patches are in [task_context.md](task_context.md). '
        'The raw files are referenced by hashes; excerpts here are bounded. Parent outputs can contain several components and do not automatically credit each one.', '']
    evidence_records = []
    for c in components:
        cid = c['component_id']
        if cid not in review_byid: continue
        review = review_byid[cid]; rid = identity[cid]['run_id']; op = ops[rid][c['action_index']]
        result = op.get('agent_output', op['output'])
        excerpt = result if len(result) <= 4200 else result[:3000] + '\n[excerpt shortened here; raw agent-visible observation hash recorded]\n' + result[-1000:]
        record = dict(component_id=cid, native_op_id=op['op_id'], response_id=op['response_id'],
            raw_messages_sha256=textsha(raw[rid]['messages']), agent_visible_output_sha256=textsha(result),
            raw_output_sha256=textsha(op['output']), final_patch_sha256=textsha(raw[rid]['submission']),
            archived_label=c['archived_contribution_label'], reviewed_label=c['contribution_label'],
            evidence=review['evidence'], requirement_links=review['requirement_links'],
            supporting_component_ids=review['supporting_component_ids'])
        evidence_records.append(record)
        evidence += [f'## {cid}', '', f"Original: {c['archived_contribution_label']}; reviewed: **{c['contribution_label']}**; role: {c['role']}.", '',
            f"Native action: `{op['op_id']}`; response: `{op['response_id']}`; visible-output SHA256: `{textsha(result)}`.", '',
            '```bash', c['command'], '```', '', review['evidence'], '',
            '### Actual parent-call observation excerpt', '', '```text', excerpt, '```', '']
    (out / 'review_evidence.md').write_text('\n'.join(evidence) + '\n')
    write(out / 'review_evidence_index.jsonl', evidence_records)

    byallocation = {r['component_id']: r for r in allocations if r['component_id']}
    ledger = {r['response_id']: r for r in responses}
    seen_commands = collections.defaultdict(set); usage_rows = []
    for c in sorted(components, key=lambda c: (c['order'], c['blinded_label'], c['action_index'], c['component_index'])):
        a = byallocation[c['component_id']]; response = ledger[a['response_id']]; rid = a['run_id']
        recurrence = 'exact_repeat' if c['command'] in seen_commands[rid] else 'new_command'
        seen_commands[rid].add(c['command'])
        usage_rows.append(dict(component_id=c['component_id'], run_id=rid, response_id=a['response_id'],
            native_op_id=ops[rid][c['action_index']]['op_id'], role=c['role'],
            archived_contribution=c['archived_contribution_label'], contribution=c['contribution_label'],
            review_status=c['contribution_review_status'], execution_status=c['execution_status'],
            target_history='unknown', command_recurrence=recurrence,
            input_tokens=a['usage']['input_tokens'], cached_input_tokens=a['usage']['cached_input_tokens'],
            output_tokens=a['usage']['output_tokens'], cost_usd=a['usage']['cost_usd'],
            attribution_method=a['allocation_method'], allocation_weight=a['allocation_weight'],
            response_component_count=a['response_component_count'], cost_provenance=response['cost_provenance'],
            inferred_state_after_parent_call=identity[c['component_id']]['inferred_state_after_native_call'],
            checkpoint_outcome='UNTESTED', evidence_ref=f"review_evidence.md#{c['component_id'].lower().replace(':','').replace('.','')}" if c['component_id'] in review_byid else 'archived source labels; not reviewed here'))
    csvout(out / 'component_usage.csv', usage_rows)

    full, subset, strict, inventory = [], [], [], []
    for s in sample:
        group = [c for c in components if identity[c['component_id']]['run_id'] == s['run_id']]
        common = dict(order=s['order'], model=s['model'], run_id=s['run_id'])
        full.append(dict(**common, **contribution_score(group)))
        subset.append(dict(**common, **contribution_score([c for c in group if c['contribution_review_status'] == 'reviewed'])))
        strict.append(dict(**common, **contribution_score([c for c in group if c['execution_status'] == 'executed'])))
        counts = collections.Counter(c['contribution_label'] for c in group)
        inventory.append(dict(**common, candidates=len(group), **{k: counts[k] for k in ['direct','indirect','no_demonstrated','uncertain','non_direct']}))
    csvout(out / 'full_run_category_counts.csv', full)
    csvout(out / 'reviewed_subset_counts.csv', subset)
    csvout(out / 'confirmed_execution_sensitivity.csv', strict)
    csvout(out / 'candidate_category_counts.csv', inventory)

    environment = json.loads((out / 'checkpoint_environment.json').read_text())
    assert environment['actual_evaluations'] == 0 and environment['status'] == 'unavailable'
    checkpoints = []
    for s in sample:
        if int(s['order']) != 3: continue
        for priority, version in enumerate(['final_submitted', 'initial', 'first_recoverable_edit_different_from_final']):
            checkpoints.append(dict(run_id=s['run_id'], task_id=s['task_id'], version_id=version,
                occurrence_index={'initial':0,'first_recoverable_edit_different_from_final':1,'final_submitted':2}[version],
                priority=priority+1, after_component_id=None, snapshot_sha256=None, snapshot_complete=False,
                reconstruction_evidence=['submitted patch available' if version=='final_submitted' else 'trajectory text available; no complete pinned repository snapshot'],
                environment_digest=None, evaluator_protocol_sha256=None, evaluation_kind='final_benchmark',
                status='not_evaluated', evaluation_executed=False, exit_code=None, test_report=None, log_sha256=None,
                duration_seconds=0, reason=environment['reason'],
                boundary_status='unknown: complete snapshot and component-internal timing not established'))
    write(out / 'checkpoint_evaluations.jsonl', checkpoints)
    checkpoint_summary = summarize_checkpoints(checkpoints)
    (out / 'checkpoint_summary.json').write_text(json.dumps(checkpoint_summary, indent=2) + '\n')

    report = ['# Fixed two-task contribution and resource smoke study', '',
        'This run recovered actual response tokens and completed the fixed 20-case model review. '
        'Checkpoint evaluation is **unavailable**, so the empirical pipeline is partial and post-pass spending remains unknown. '
        'This is a development smoke study, not human validation or a model ranking.', '',
        '## Fixed sample and resources', '',
        'Frozen evaluation orders 03/04, Gemini/Luna run 1: **175 candidates, 109 native calls, 104 stored generating responses**. '
        'No sample expansion, additional paid annotator, live agent run, dataset download or task-image build occurred.', '',
        *table(['Task','Model','Candidates','Calls','Responses','Input','Cached input','Output','Run USD (source)'],
            [[r['order'], r['model'], r['components'], r['native_calls'], r['responses'], f"{r['input_tokens']:,}",
              f"{r['cached_input_tokens']:,}", f"{r['output_tokens']:,}", f"{r['run_cost_usd']:.8f} ({r['cost_source']})"] for r in coverage]), '',
        '**All 12 input/cache/output reconciliations match exactly** (four runs × three fields; difference zero). '
        'Each of 104/104 responses and 175/175 candidates has these three token fields. Cached input is a reported subset of input; '
        'raw total_tokens equals input + output for every response. Do not add cache to input or reasoning details to output. '
        'Raw cache-write details remain in the ledger without being silently folded into cached input.', '',
        'There are 0 stored no-tool responses, 0 stored error responses, and stored response counts equal api_calls in each run. '
        'All 104 provider response IDs are absent. Canonical IDs use run + stored response order and map every native call; '
        'the available traces cannot exclude unrecorded provider retries. Empty/missing future usage would stay null, never be inferred from run totals.', '',
        'Luna has **20/20 harness-recorded per-response extra.cost values** that sum to its two run totals. '
        'These are recorded harness costs, not independently verified invoices. Gemini has zero placeholders in extra.cost while '
        'run cost_source is trajectory_tokens_litellm_public_map and run totals are nonzero; Gemini response/component USD stays null. '
        'No run cost was spread over responses. See [reconciliation](reviewed/resources/run_usage_reconciliation.jsonl) and '
        '[resource coverage](resource_coverage.csv).', '',
        'Every response budget is conserved across **all** emitted candidates, including known unexecuted ones. '
        'Shared response values use 1/k equal-share **allocated estimates**; singleton values are response-associated, not measured causal reasoning cost. '
        'Here 98/175 candidates use shared-response estimates and 77/175 have singleton response association. '
        'No-tool expenditure would remain unassigned. Separate input/cache/output/USD, allocation methods, source IDs and review status are in '
        '[component_usage.csv](component_usage.csv); role/contribution and whole-response mixed sensitivities are in '
        '[region_totals.jsonl](reviewed/resources/region_totals.jsonl). Target history is explicitly unknown; command recurrence means an identical earlier emitted command in that run and does not determine contribution.', '',
        '## Bounded contribution review', '',
        '**20/20 prepared cases reviewed** (11.4% of all candidates; 11.6% of the 172 precision-included candidates). '
        'The current Codex session inspected complete task requirements, actual prompts, relevant full agent-visible observations/later trajectory and all four final patches. '
        'Reviewer: **Codex (model identifier unavailable), model, retrospective and unblinded**. No independent or human validation is claimed. '
        'The original source labels are unchanged and retained in archived_contribution_label; the completed review is an additive overlay.', '',
        'D=direct, I=indirect, Z=no demonstrated contribution, U=uncertain, L=unreviewed legacy non_direct. '
        'The enriched packet cannot estimate population category prevalence or independent annotation accuracy.', '',
        '### Reviewed subset only', '',
        *table(['Task','Model','N','D','I','Z','U','Direct bounds'],
            [[r['order'],r['model'],r['included'],r['direct'],r['indirect'],r['no_demonstrated'],r['uncertain'],bounds(r)] for r in subset]), '',
        'Reviewed totals: **D=7, I=1, Z=11, U=1**. Direct bounds on this enriched subset are 35.0–40.0%, '
        'a feasibility description rather than a population estimate. Four direct controls remain direct; '
        'one uncertain control becomes direct and three become Z; twelve legacy cases become D=2/I=1/Z=8/U=1.', '',
        '### Partially reviewed full runs', '',
        *table(['Task','Model','N','D','I','Z','U','L','Reviewed','Direct bounds'],
            [[r['order'],r['model'],r['included'],r['direct'],r['indirect'],r['no_demonstrated'],r['uncertain'],r['legacy_non_direct'],r['reviewed'],bounds(r)] for r in full]), '',
        'All-candidate counts (175): **D=61/I=1/Z=11/U=41/L=61**. Precision excludes 3 known unexecuted candidates, '
        'leaving 172 with **D=61/I=1/Z=11/U=41/L=58**. Of these, 19 have uncertain execution and remain included under the archived convention; '
        '[confirmed-execution sensitivity](confirmed_execution_sensitivity.csv) separately reports only the 153 confirmed executed components. '
        'Label bounds are D/N to (D+U)/N; I and Z get no direct credit. L stays unsplit and is excluded from the possible-direct numerator '
        'conditional on retaining its archived non-direct judgment. Bounds are not confidence intervals and do not cover systematic label, role or execution error.', '',
        '### Exploration and verification: partial full-run bounds', '']
    role_rows = list(csv.DictReader((current / 'role_precision_by_run.csv').open()))
    report += table(['Task','Model','Role','N','D','I','Z','U','L','Reviewed','Direct bounds'],
        [[r['order'],r['model'],r['role'],r['included'],r['direct'],r['indirect'],r['no_demonstrated'],r['uncertain'],r['legacy_non_direct'],r['reviewed'],
          f"{float(r['lower']):.1%}–{float(r['upper']):.1%}" if r['lower'] else 'undefined']
         for r in role_rows if r['role'] in {'exploration','verification'}])
    report += ['', 'Role-specific results on only reviewed cases are saved separately in '
        '[reviewed_subset_by_run.csv](reviewed/reviewed_subset_by_run.csv), including undefined empty-role denominators. '
        'Roles outside this review remain archived model judgments. Verification includes required saved-artifact '
        'integrity checks under H2; these bounds are not test-only behavioral precision.', '',
        '## Evidence-linked examples', '',
        'All 20 original/reviewed judgments, assessed observations and exact source hashes appear in '
        '[review_evidence.md](review_evidence.md) and the [overlay](contribution_review_completed.jsonl). '
        'Complete requirements and final/reference patches are in [task_context.md](task_context.md).', '']
    for cid in ['03:X011.c0','04:X003.c0','03:Y008.c0','04:Y012.c0','04:X013.c0','03:X020.c0','04:Y006.c1']:
        c = next(c for c in components if c['component_id']==cid); r=review_byid[cid]; a=byallocation[cid]
        report += [f"### {cid}: {c['archived_contribution_label']} → {r['contribution_label']}", '',
            f"`{c['command']}`", '', r['evidence'], '',
            f"Input/cache/output = {display_usage(a['usage']['input_tokens'])} / {display_usage(a['usage']['cached_input_tokens'])} / {display_usage(a['usage']['output_tokens'])}; "
            f"USD={'unavailable' if a['usage']['cost_usd'] is None else format(a['usage']['cost_usd'], '.8f')}; "
            f"{a['allocation_method']} (weight {a['allocation_weight']:.6g}; displayed shares rounded, full values in CSV).", '']
    report += ['The first-artifact inspections challenge the earlier repeated-support interpretation: unchanged source does not mean the saved submission artifact was already inspected. '
        'Conversely, no demonstrated task contribution in a baseline check does not establish repetition. The environment diagnostic is uncertain rather than automatically labeled waste. '
        'Only the prepared cases were re-reviewed; the remaining legacy checks cannot support a new repeated-support rate.', '',
        '## Checkpoints and post-pass spending', '',
        'Task 03 only: six priority slots (final, initial, first recoverable edited state different from final for each run); '
        '**0 actual evaluations attempted, 0 PASS, 0 semantic FAIL**. Docker was reachable, but none of the 46 installed image tags matches the pinned Flipt task; '
        'there is no configured final-protocol adapter or complete pinned task checkout. Setup stopped without image builds/downloads or host execution of trajectory commands. '
        'See [environment evidence](checkpoint_environment.json), [six unevaluated slots](checkpoint_evaluations.jsonl), '
        'and [checkpoint summary](checkpoint_summary.json). All snapshot/protocol/environment hashes remain null because no exact evaluated snapshot exists.', '',
        'The six slots are not evaluations or reconstructed versions. Their component boundaries remain unknown. '
        'Maximum allowed executions was six with 120 seconds each and two concurrent containers; zero were launched. '
        'Archived final resolved=True remains a separate historical field, not an independently established PASS. '
        '**Earliest evaluated passing version and all post-pass input/cache/output/cost are unavailable.** '
        'No safe savings, stopping policy or intermediate correctness is inferred. Unknown no-tool timing and response-crossing boundaries would need explicit mixed/allocated sensitivity if evaluation became available.', '',
        '## Trajectory figures', '',
        'Each pair uses fixed-size markers: circle exploration, diamond edit, square verification, triangle administration. '
        'Green D, blue I, orange Z, gray U; beige is explicitly **unreviewed legacy unsplit**, a review status rather than a fifth v2 contribution category. '
        'States are inferred AFTER parent native calls; compound-call internal states are unresolved. Gray bands mark uncertain inferred states. '
        'All independent checkpoint outcomes are UNTESTED. Token triplets and evidence links are provided in the component table rather than marker size.', '',
        '![Task 03 paired trajectories](reviewed/task_03_progression.png)', '',
        '![Task 04 paired trajectories](reviewed/task_04_progression.png)', '',
        '## Stage status and checks', '',
        *table(['Stage','Status','Evidence / limitation'], [
            ['Fixed identity join / token conservation','real-data tested','175 candidates / 109 calls / 104 responses; exact token reconciliation'],
            ['20-case v2 overlay','real-data tested','Current-session model judgments; evidence/provenance and dependency schema checks, not semantic/human accuracy'],
            ['Resource costs','real-data tested, partial','Luna recorded response cost; Gemini missing response cost; shares allocated'],
            ['Trajectory figures','real-data tested','Actual actions and joined usage; inferred parent-call states'],
            ['Missing/no-tool/shared/mixed accounting, zero-role bounds','synthetic-only tested for absent cases','Empirical subset has no no-tool/missing token responses; existing authored tests cover these cases'],
            ['Checkpoint outcome gate / pass→fail / recovery','synthetic-only tested','Authored fixtures validate bookkeeping; no empirical outcomes'],
            ['Exact reconstruction / final benchmark / post-pass spending','unavailable','Task image, pinned complete checkout and final-protocol adapter absent']]), '',
        'Recorded test results: [tests.txt](tests.txt); original audit probes: [audit_checks.txt](audit_checks.txt); '
        'restore-scope probes: [restore_scope_checks.txt](restore_scope_checks.txt). '
        'Synthetic fixtures are code checks and never appear as task outcomes.', '',
        'The bounded pipeline successfully joins real response expenditure to all components and supports auditable four-label review. '
        'The strongest observation is accounting-level: response token sums reconcile exactly, while the evidence review distinguishes '
        'a supported indirect navigation step, a first submission-artifact check, and an unresolved environment diagnostic that the old binary label merged. '
        'Final quality/reference conflicts and the lack of checkpoint evaluation prevent model ranking or post-pass waste claims. '
        'The next necessary test is to supply the pinned task-03 image and final benchmark adapter, verify exact final reconstruction first, '
        'then evaluate the fixed initial/intermediate slots under the same protocol; independent review remains necessary for semantic validation.', '']
    finished = dt.datetime.now(dt.timezone.utc)
    deadline = started + dt.timedelta(minutes=60); cutoff = started + dt.timedelta(minutes=43)
    report += [f"Started {started.isoformat()}; benchmark cutoff {cutoff.isoformat()}; report deadline {deadline.isoformat()}. "
        f"Report generated {finished.isoformat()} ({(finished-started).total_seconds()/60:.1f} minutes elapsed). "
        f"Benchmark setup closed at {environment['checked_at_utc']}, before cutoff. See manifest for sources and commands.", '']
    (out / 'RESULTS.md').write_text('\n'.join(report).rstrip() + '\n')
    manifest = dict(started_at_utc=started.isoformat(), benchmark_cutoff_utc=cutoff.isoformat(), deadline_utc=deadline.isoformat(),
        report_finished_at_utc=finished.isoformat(), elapsed_seconds=(finished-started).total_seconds(),
        deadline_met=finished<=deadline, pulled_main_commit='0d630fe', tasks=2,runs=4,components=175,native_calls=109,responses=104,
        reviewed_cases=20,reviewer_type='model',reviewer_name='Codex (model identifier unavailable)',human_validation=False,
        review_context_window_started_at_utc='2026-10-26T18:33:20+00:00',
        review_overlay_completed_at_utc=max(r['reviewed_at_utc'] for r in reviews),
        actual_checkpoint_evaluations=0,max_checkpoint_evaluations=6,evaluation_seconds_limit=120,max_concurrent_containers=2,
        benchmark_work_closed_at_utc=environment['checked_at_utc'],complete_empirical_pipeline=False,
        actual_new_paid_annotation_calls=0,actual_new_agent_runs=0,source_labels_changed=False,
        sample_ids=sample,
        source_hashes={str(path.relative_to(ROOT)):sha(path) for path in source_paths},
        original_source_hashes=json.loads((current/'manifest.json').read_text())['source_hashes'],
        commands=[
            'git pull --ff-only origin main',
            '.venv/bin/python scripts/followup/framework_quickcheck.py --jetbrains-shard raw/jetbrains/gemini_3_7_flash-run1.parquet --jetbrains-shard raw/jetbrains/luna-run1.parquet --out '+str(out),
            '.venv/bin/python scripts/followup/framework_quickcheck.py --contribution-review '+str(out/'contribution_review_completed.jsonl')+' --jetbrains-shard raw/jetbrains/gemini_3_7_flash-run1.parquet --jetbrains-shard raw/jetbrains/luna-run1.parquet --out '+str(current),
            'docker image ls --format {{.Repository}}:{{.Tag}} {{.ID}} (read-only; no task launch)',
            'PYTHONPATH=worktrace .venv/bin/python -m pytest -q worktrace/tests scripts/one_day_precision/test_one_day.py scripts/precision_validation/test_validation.py scripts/followup/test_followup.py',
            '.venv/bin/python audit/reproduce_reliability.py', '.venv/bin/python audit/probe_restore_scope.py',
            '.venv/bin/python scripts/followup/one_hour_results.py --run-dir '+str(out)+' --started-at '+args.started_at],
        allocation_method='equal shares across all emitted candidates; shared components are estimates; missing USD remains null',
        code_hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),ROOT/'worktrace/worktrace/checkpoints.py',ROOT/'worktrace/worktrace/loaders/jetbrains.py',ROOT/'scripts/followup/framework_quickcheck.py']})
    manifest['output_hashes'] = {str(path.relative_to(out)):sha(path) for path in sorted(out.rglob('*'))
        if path.is_file() and path.name!='manifest.json'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ['elapsed_seconds','deadline_met','components','reviewed_cases','actual_checkpoint_evaluations','complete_empirical_pipeline']},indent=2))


if __name__=='__main__': main()
