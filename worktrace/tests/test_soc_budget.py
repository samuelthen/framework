"""No API calls: failed requests must reserve resources and remain unknown."""
import importlib.util
from pathlib import Path
import pytest

SOURCE=Path(__file__).resolve().parents[2]/'scripts/research_loop/soc_client.py'
spec=importlib.util.spec_from_file_location('study_soc_client',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_parallel_reservations_cannot_overrun_fixed_allowance():
    budget=module.Budget(3,10000);payload={'max_tokens':1000,'messages':[]}
    first=budget.reserve(payload)
    with pytest.raises(RuntimeError):budget.reserve(payload)
    budget.settle({'total_tokens':100},first)
    second=budget.reserve(payload);budget.settle(None,second)
    assert budget.unknown_usage_attempts==1 and budget.pending==0
    assert budget.tokens==100+second


def test_unknown_usage_never_becomes_zero():
    budget=module.Budget(1,10000);allowance=budget.reserve({'max_tokens':100})
    budget.settle({'total_tokens':None},allowance)
    assert budget.tokens==allowance
    with pytest.raises(RuntimeError):budget.reserve({'max_tokens':100})
