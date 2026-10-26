"""Tests for the one-day study's scoring, matching and coverage logic (not mirrors of the implementation).

usage: python -m pytest -q scripts/one_day_precision/test_one_day.py"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from matched_effort import _cell, compare  # noqa: E402
from score import score_run, validate  # noqa: E402


def _ann(labels):
    return pd.DataFrame({"contribution_label": labels})


def test_denominator_counts_every_action_including_errors_and_submission():
    # 10 actions: 3 direct, 2 uncertain, 5 non-direct (errors, submission ...): N must be 10, not 5 or 8
    s = score_run(_ann(["direct"] * 3 + ["uncertain"] * 2 + ["non_direct"] * 5))
    assert s["N"] == 10 and s["D"] == 3 and s["U"] == 2


def test_uncertain_widens_bounds_and_is_never_dropped():
    s = score_run(_ann(["direct", "uncertain", "uncertain", "non_direct"]))
    assert s["P_lower"] == pytest.approx(0.25)
    assert s["P_upper"] == pytest.approx(0.75)
    assert s["uncertain_share"] == pytest.approx(0.5)
    # dropping U would give 1/2 = 0.5, which lies inside the bounds but is not what we report
    assert s["P_lower"] < 0.5 < s["P_upper"]


def test_all_uncertain_run_has_full_width_bounds():
    s = score_run(_ann(["uncertain"] * 4))
    assert (s["P_lower"], s["P_upper"]) == (0.0, 1.0)


def test_empty_run_gives_undefined_scores_not_zero():
    s = score_run(_ann([]))
    assert s["N"] == 0 and np.isnan(s["P_lower"]) and np.isnan(s["P_upper"])


def test_validate_rejects_missing_actions_and_reasonless_non_direct():
    ok = [{"action_index": 0, "contribution_label": "direct", "role": "edit", "non_direct_reason": None},
          {"action_index": 1, "contribution_label": "non_direct", "role": "exploration", "non_direct_reason": "unused_context"}]
    validate(ok, 2)
    with pytest.raises(AssertionError):
        validate(ok, 3)  # an action without a label must not silently shrink N
    bad = [dict(ok[0]), dict(ok[1], non_direct_reason=None)]
    with pytest.raises(AssertionError):
        validate(bad, 2)


def test_outcome_cells_and_unknown_kept_separate():
    assert _cell(True, True) == "both_success"
    assert _cell(True, False) == "first_only_success"
    assert _cell(False, True) == "second_only_success"
    assert _cell(False, False) == "both_failure"
    assert _cell(None, True) == "unknown_outcome"
    assert _cell(float("nan"), False) == "unknown_outcome"


def test_matched_comparison_pairs_on_task_and_reports_zero_denominators():
    W = pd.DataFrame({"task_id": ["a", "b", "c", "d"],
                      "resolved_x": [True, True, False, None], "resolved_y": [True, False, False, True],
                      "n_ops_x": [10, 20, 5, 7], "n_ops_y": [5, 0, 5, 7]})
    eff, dif = compare(W, "x", "y", "p", "x vs y", "v")
    D = pd.DataFrame(dif).set_index("cell")
    assert D.loc["both_success", "n_tasks"] == 1
    assert D.loc["both_success", "mean_diff_first_minus_second"] == 5
    assert D.loc["first_only_success", "zero_denominator_tasks"] == 1  # task b: y used 0 actions
    assert D.loc["unknown_outcome", "n_tasks"] == 1                     # task d is not dropped into a cell
    assert D.loc["all_shared_tasks", "n_tasks"] == 4


def test_terminal_coverage_counts_only_achieved_requirements():
    from pilot_analysis import coverage_bounds
    # an edited-then-lost requirement is 'not_achieved' at the endpoint and must not count;
    # uncertain requirements widen only the upper bound
    lo, hi, H, U, K = coverage_bounds(["not_achieved", "achieved", "uncertain"])
    assert (H, U, K) == (1, 1, 3)
    assert lo == pytest.approx(1 / 3) and hi == pytest.approx(2 / 3)
    with pytest.raises(AssertionError):
        coverage_bounds(["mentioned"])  # inspecting/mentioning a requirement is not a status
    assert np.isnan(coverage_bounds([])[0])
