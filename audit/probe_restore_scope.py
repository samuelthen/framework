"""Restore-scope regressions. Synthetic records only; no trajectory execution.

The Mac-local probe mentioned in the user's review was not in this checkout.
These reproduce the two described cases and a positive scope control.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worktrace'))
from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph


def graph(commands):
    ops = [dict(op_id=f'op{i}', turn_id=f't{i}', command=c, output=o, exit_code=e)
           for i, (c,o,e) in enumerate(commands)]
    return build_version_graph(dict(run_id='r',task_id='t',model='synthetic'), extract_facts(ops))


BASE = [('git status --porcelain','',0), ('git ls-files','tracked.py\n',0)]


class RestoreScopeChecks(unittest.TestCase):
    def test_untracked_creation_survives_worktree_checkout(self):
        g=graph(BASE+[('echo new > untracked.py','',0), ('git checkout .','',0)])
        self.assertNotEqual(g['final'],0)
        self.assertTrue(g['nodes'][g['final']]['uncertain'])

    def test_staged_edit_survives_worktree_checkout(self):
        g=graph(BASE+[('sed -i s/old/new/ tracked.py','',0), ('git add tracked.py','',0), ('git checkout .','',0)])
        self.assertNotEqual(g['final'],0)

    def test_supported_tracked_unstaged_restore(self):
        g=graph(BASE+[('sed -i s/old/new/ tracked.py','',0), ('git checkout .','',0)])
        self.assertEqual(g['final'],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
