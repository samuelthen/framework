"""Reconstruction must reject trace execution and mismatched patch context."""
import importlib.util
from pathlib import Path
import pytest

SOURCE = Path(__file__).resolve().parents[2]/'scripts/utility_audit/reconstruct.py'
spec = importlib.util.spec_from_file_location('utility_reconstruct', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_literal_edit_preserves_exact_bytes(tmp_path):
    (tmp_path/'code.go').write_text('old\n')
    changes=module.interpret_replacements(tmp_path,
        "from pathlib import Path\np=Path('code.go')\ns=p.read_text()\np.write_text(s.replace('old','new'))")
    assert (tmp_path/'code.go').read_text() == 'new\n'
    assert changes[0]['before_sha256'] != changes[0]['after_sha256']


@pytest.mark.parametrize('code', ["__import__('os').system('true')", "Path('../escape').write_text('x')",
                                  "Path('/absolute').read_text()"])
def test_untrusted_expressions_fail_closed(tmp_path, code):
    with pytest.raises(ValueError): module.interpret_replacements(tmp_path,code)


def test_patch_requires_exact_context(tmp_path):
    path=tmp_path/'code.go';path.write_text('old\n')
    patch='diff --git a/code.go b/code.go\n--- a/code.go\n+++ b/code.go\n@@ -1 +1 @@\n-wrong\n+new\n'
    with pytest.raises(ValueError,match='context mismatch'): module.apply_patch(tmp_path,patch)
    assert path.read_text() == 'old\n'
