"""End-to-end accounting checks through the public exporter CLI.

Fixtures are authored synthetic data, not scientific trajectory results.
"""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def export(tmp_path, responses, components):
    response_path = tmp_path / 'responses.jsonl'
    component_path = tmp_path / 'components.jsonl'
    for path, rows in [(response_path, responses), (component_path, components)]:
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    out = tmp_path / 'export'
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/followup/component_resources.py'),
         '--responses', str(response_path), '--components', str(component_path), '--out', str(out)],
        capture_output=True, text=True, timeout=30)
    return result, out


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_cli_conserves_shared_unassigned_and_unexecuted_response_usage(tmp_path):
    responses = [dict(response_id=f'r:t{i}', run_id='r', generation_version='V0',
                      usage=dict(input_tokens=800, cached_input_tokens=500, output_tokens=n))
                 for i, n in enumerate([10, 100, 70, 20])]
    components = [
        dict(component_id='a', response_id='r:t1', role='exploration',
             contribution_label='direct', version_region='V0'),
        dict(component_id='b', response_id='r:t1', role='edit',
             contribution_label='uncertain', version_region='V0->V1'),
        dict(component_id='c', response_id='r:t2', role='verification',
             contribution_label='direct', version_region='V1'),
        dict(component_id='d', response_id='r:t3', role='verification',
             contribution_label='non_direct', version_region='V1', execution_status='not_executed'),
    ]
    result, out = export(tmp_path, responses, components)
    assert result.returncode == 0, result.stderr
    allocated = rows(out / 'component_allocations.jsonl')
    assert sum(r['usage']['output_tokens'] for r in allocated) == 200
    assert sum(r['usage']['input_tokens'] for r in allocated) == 3200
    assert sum(r['usage']['cached_input_tokens'] for r in allocated) == 2000
    assert next(r for r in allocated if r['component_id'] is None)['usage']['output_tokens'] == 10
    assert next(r for r in allocated if r['component_id'] == 'd')['usage']['output_tokens'] == 20
    regions = rows(out / 'region_totals.jsonl')
    for view in ['role', 'version', 'role_version', 'target', 'contribution']:
        for method in ['equal_component_allocation', 'mixed_response_bucket']:
            group = [r for r in regions if r['view'] == view and r['region_method'] == method]
            assert sum(r['output_tokens']['known_total'] for r in group) == pytest.approx(200)
    precision = rows(out / 'contribution_expenditure_bounds.jsonl')[0]['output_tokens']
    assert precision['lower'] == pytest.approx(.6)
    assert precision['upper'] == pytest.approx(.9)
    assert json.loads((out / 'manifest.json').read_text())['actual_new_agent_runs'] == 0


def test_cli_missing_usage_remains_unknown_in_summaries_and_graph(tmp_path):
    responses = [dict(response_id='r:t0', run_id='r', usage={})]
    components = [dict(component_id='a', response_id='r:t0', role='verification')]
    result, out = export(tmp_path, responses, components)
    assert result.returncode == 0, result.stderr
    overlay = json.loads((out / 'graph_overlay.json').read_text())
    assert overlay['glyphs'][0]['visual']['size_value'] is None
    for region in rows(out / 'region_totals.jsonl'):
        assert region['output_tokens']['known_total'] is None
        assert region['output_tokens']['mean_allocated_per_component'] is None
    bound = rows(out / 'contribution_expenditure_bounds.jsonl')[0]['output_tokens']
    assert bound['lower'] is None and bound['status'] == 'missing_usage'


def test_cli_duplicate_response_fails_before_creating_results(tmp_path):
    response = dict(response_id='r:t0', run_id='r', usage=dict(output_tokens=10))
    result, out = export(tmp_path, [response, response], [])
    assert result.returncode != 0
    assert 'Duplicate response_id' in result.stderr
    assert not out.exists()


def test_cli_four_labels_do_not_inflate_direct_credit_or_collapse_legacy(tmp_path):
    labels = ['direct', 'indirect', 'no_demonstrated', 'uncertain', 'non_direct']
    responses = [dict(response_id='r:t0', run_id='r', usage=dict(output_tokens=50))]
    components = [dict(component_id=f'c{i}', response_id='r:t0', role='verification', contribution_label=label)
                  for i, label in enumerate(labels)]
    result, out = export(tmp_path, responses, components)
    assert result.returncode == 0, result.stderr
    allocations = rows(out / 'component_allocations.jsonl')
    assert {r['contribution_label'] for r in allocations} == set(labels)
    assert sum(r['usage']['output_tokens'] for r in allocations) == 50
    bounds = rows(out / 'contribution_expenditure_bounds.jsonl')[0]['output_tokens']
    assert bounds['lower'] == .2 and bounds['upper'] == .4
    assert len({r['visual']['contribution_color'] for r in allocations}) == 5
