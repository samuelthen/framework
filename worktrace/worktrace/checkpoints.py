"""Evidence-gated checkpoint summaries; this module never executes a task.

Inferred state IDs and archived success do not establish benchmark outcomes.
Schema validation does not independently verify a report's contents or snapshots.
"""
import re

STATUSES = {'pass', 'fail', 'timeout', 'infrastructure_error',
            'unreconstructable', 'not_evaluated'}


def validate_checkpoint(record):
    if record.get('status') not in STATUSES:
        raise ValueError('Unsupported checkpoint status')
    if record['status'] in {'pass', 'fail'}:
        hashes = ['snapshot_sha256', 'evaluator_protocol_sha256', 'log_sha256']
        if (record.get('evaluation_executed') is not True
                or record.get('snapshot_complete') is not True
                or record.get('evaluation_kind') != 'final_benchmark'
                or not record.get('environment_digest')
                or not record.get('test_report')
                or not record.get('reconstruction_evidence')
                or any(not re.fullmatch('[0-9a-f]{64}', record.get(k) or '') for k in hashes)):
            raise ValueError('A semantic outcome requires exact snapshot and final-benchmark evidence')
        if record['status'] == 'pass' and record.get('exit_code') != 0:
            raise ValueError('PASS requires a successful evaluator result')
    return record


def summarize_checkpoints(records):
    """Summarize sparse observations without propagating validity across edits.

    Repeated content can share an evaluation only with explicit snapshot and
    environment/protocol identity. Occurrences remain separate in the ledger.
    This does not infer resource timing or claim that later work was redundant.
    """
    for record in records:
        validate_checkpoint(record)
    runs = {}
    for record in records:
        runs.setdefault(record['run_id'], []).append(record)
    summaries = []
    for rid, group in sorted(runs.items()):
        ordered = sorted(group, key=lambda r: r['occurrence_index'])
        passing = [r for r in ordered if r['status'] == 'pass']
        first = passing[0] if passing else None
        later_failures = [r['version_id'] for r in ordered if first is not None
                          and r['occurrence_index'] > first['occurrence_index'] and r['status'] == 'fail']
        summaries.append(dict(run_id=rid, candidate_checkpoints=len(group),
            evaluations_executed=sum(bool(r.get('evaluation_executed')) for r in group),
            semantic_outcomes=sum(r['status'] in {'pass', 'fail'} for r in group),
            earliest_evaluated_passing_version=first['version_id'] if first else None,
            later_evaluated_failures=later_failures,
            unevaluated=sum(r['status'] not in {'pass', 'fail'} for r in group),
            post_pass_expenditure=None,
            post_pass_status='requires response/boundary timing join' if first else 'unavailable: no evaluated passing snapshot'))
    return summaries
