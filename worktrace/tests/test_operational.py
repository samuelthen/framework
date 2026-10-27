"""Guard against treating textual mentions and opaque scripts as checks."""
import pytest
from worktrace.operational import category, result_screen


@pytest.mark.parametrize('command,expected',[
    ('go test ./config/...','verification'),('python -m pytest tests/test_a.py','verification'),
    ("rg 'pytest' README.md",'exploration'),("echo 'pytest tests'",'administration'),
    ('cd /app && go test ./...','verification'),('cat a.py && go test ./...','mixed_call'),
    ('git diff --stat','artifact_inspection'),('python opaque.py','opaque_execution'),
    ("python -c \"from pathlib import Path; Path('x').write_text('a')\"",'edit'),
    ('npm install','opaque_execution'),('git restore -- a.py','edit')])
def test_operational_categories(command,expected): assert category(command)==expected


def test_result_screen_preserves_unavailable_and_empty_results():
    assert result_screen({'missing_result':True})=='missing_result'
    assert result_screen({'exit_code':-1,'output':'partial'})=='timeout_or_interrupted'
    assert result_screen({'exit_code':0,'output':''})=='empty_observation'
    assert result_screen({'exit_code':0,'output':'ok','agent_saw_truncated':True})=='truncated_observation'


def test_printed_checker_text_is_not_executed_verification():
    assert category('python -c "print(\'go test ./...\')"') != 'verification'
