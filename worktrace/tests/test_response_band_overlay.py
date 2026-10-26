"""A plot label overlay cannot silently change resource identity or omit a run."""
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[2] / 'scripts/followup/draw_response_cost_bands.py'
spec = importlib.util.spec_from_file_location('response_band_overlay', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rows():
    old = [dict(component_id='a', run_id='r', response_id='t', role='verification',
                execution_status='executed', contribution='non_direct', input_tokens='10')]
    reviewed = [dict(old[0], contribution_review_status='reviewed', contribution_label='no_demonstrated')]
    return old, reviewed


def test_review_overlay_keeps_original_input_and_all_resource_fields():
    old, reviewed = rows()
    result = module.apply_reviewed_components(old, reviewed)
    assert old[0]['contribution'] == 'non_direct'
    assert result[0]['contribution'] == 'no_demonstrated'
    assert result[0]['input_tokens'] == '10'


def test_partial_duplicate_or_changed_identity_review_is_rejected():
    old, reviewed = rows()
    with pytest.raises(ValueError): module.apply_reviewed_components(old, reviewed * 2)
    with pytest.raises(ValueError): module.apply_reviewed_components(old, [dict(reviewed[0], response_id='other')])
    with pytest.raises(ValueError): module.apply_reviewed_components([*old, dict(old[0], component_id='b')], reviewed)
    with pytest.raises(ValueError): module.apply_reviewed_components(old, [dict(reviewed[0], contribution_label='non_direct')])
