"""Executable evidence must not turn dependency/resource failures into utility."""
import importlib.util
from pathlib import Path
import sys
import pytest

FOLDER=Path(__file__).resolve().parents[2]/'scripts/research_loop'
sys.path.insert(0,str(FOLDER))
sys.path.insert(0,str(FOLDER.parent/'utility_audit'))
spec=importlib.util.spec_from_file_location('executable_panel_test',FOLDER/'executable_panel.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.mark.parametrize('error',['signal: killed','no space left on device','module lookup disabled by GOPROXY=off'])
def test_infrastructure_failure_has_no_quality_score(error):
    assert module.scoped_quality(1,'completed',b'',error.encode(),[]) is None


def test_compilation_and_assertion_failure_are_separate():
    assert module.scoped_quality(1,'completed',b'',b'a.go: cfg.X undefined (type Config has no field or method X)',[])=='source_build_failure'
    assert module.scoped_quality(1,'completed',b'',b'',[{'Test':'TestA','Action':'fail'}])=='scoped_fail'
    assert module.scoped_quality(0,'completed',b'',b'',[])=='scoped_pass'
    assert module.scoped_quality(1,'completed',b'',b'unexplained runtime problem',[])=='build_or_setup_unresolved'
