"""Regression probes for the reliability audit, 2026-10-25.

Run: python3 audit/reproduce_reliability.py
These assert the desired semantics. They failed on the historical audited
implementation; the current repairs are documented in
results/precision_validation_20261026/RESULTS.md.
They use synthetic trajectory records; they execute no trajectory commands or APIs.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worktrace"))

from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph

PASS = "===== 3 passed in 0.12s =====\n" + "x" * 30
READ = "old content\n" * 5
RUN = dict(run_id="r", task_id="t", model="m", resolved=True)


def ops(commands):
    return extract_facts([
        dict(op_id=f"op{i}", turn_id=f"r:t{i}", command=c, output=o, exit_code=e)
        for i, (c, o, e) in enumerate(commands)
    ])


class ReliabilityChecks(unittest.TestCase):
    def test_status_listing_cannot_prove_equal_contents(self):
        records = ops([
            ("git status --short", " M a.py\n", 0),
            ("pytest", PASS, 0),
            ("python fix.py", "done", 0),
            ("git status --short", " M a.py\n", 0),
            ("pytest", PASS, 0),
        ])
        self.assertNotEqual(records[-1]["cand_facts"]["op1"]["any_code_written_since"], "no")

    def test_branch_switch_invalidates_code_state(self):
        records = ops([
            ("pytest", PASS, 0),
            ("git checkout other_branch", "Switched to branch other_branch", 0),
            ("pytest", PASS, 0),
        ])
        self.assertNotEqual(records[-1]["cand_facts"]["op0"]["any_code_written_since"], "no")

    def test_known_write_does_not_hide_unknown_write(self):
        records = ops([
            ("cat B.py", READ, 0),
            ("echo x > A.py && python fix.py", "", 0),
            ("cat B.py", READ, 0),
        ])
        self.assertEqual(records[-1]["cand_facts"]["op0"]["object_written_since"], "unknown")

    def test_multi_file_edit_tracks_every_path(self):
        records = ops([
            ("cat A.py", READ, 0),
            ("sed -i 's/x/y/' A.py B.py", "", 0),
            ("cat A.py", READ, 0),
        ])
        self.assertIn("A.py", records[1]["written_paths"])

    def test_failed_revert_does_not_restore_root(self):
        graph = build_version_graph(RUN, ops([
            ("sed -i 's/x/y/' a.py", "", 0),
            ("git checkout .", "error: permission denied", 1),
        ]))
        self.assertNotEqual(graph["final"], 0)

    def test_partial_revert_preserves_unknown_dirty_state(self):
        graph = build_version_graph(RUN, ops([
            ("python fix.py", "", 0),
            ("sed -i 's/x/y/' a.py", "", 0),
            ("git checkout -- a.py", "", 0),
        ]))
        self.assertNotEqual(graph["final"], 0)

    def test_identical_truncated_diff_cannot_merge_versions(self):
        clipped = "diff --git a/a.py b/a.py\n[Output truncated]"
        graph = build_version_graph(RUN, ops([
            ("sed -i 's/x/y/' a.py", "", 0),
            ("git diff", clipped, 0),
            ("sed -i 's/y/z/' a.py", "", 0),
            ("git diff", clipped, 0),
        ]))
        self.assertEqual(graph["n_versions"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
