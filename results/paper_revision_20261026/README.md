# Additional analyses for the paper revision

These are new analyses of saved measurements, not new agent experiments. Run `paper/worktrace-draft/analyze_saved_data.py` to reproduce them. The script never executes commands taken from traces. It never calls an annotator.

The script uses 5,000 task-bootstrap samples with seed 20261026. Paired contrasts retain task correspondence. Intervals are exploratory 95% percentile intervals, without multiple-comparison adjustment. They do not account for parser or label error.

## Main results

| Analysis | Result |
| --- | --- |
| Verification-gap contrast, Gemini minus Luna | +2.58 checks [2.30, 2.84] with support files excluded |
| Same contrast under all-write rule | +1.80 [1.54, 2.05] |
| Same contrast under known-write rule | +2.21 [1.94, 2.48] |
| Revisit-rate contrast, OpenHands minus mini-swe-agent | +14.73 percentage points [14.26, 15.19] |
| Revisit-rate contrast, SWE-agent minus mini-swe-agent | +11.81 percentage points [11.37, 12.25] |
| Different-command share after removing first final-version checks | 89.0% [87.5, 90.5] |

## Definitions and samples

**Verification gap:** final-version check count minus the mean check count on other inferred versions. The initial repository state is excluded from those other versions. Eligible runs have at least two inferred versions and do not end at the initial state.

`version_common_sample.csv` and `version_paired_differences.csv` use the same 892 task–repeat pairs across all three models and all three version rules. This gives 892 runs per model from 418 tasks. A repeat index matches positions in the saved sampling design; it does not imply shared model randomness. The selection depends on observed trajectories. These comparisons do not estimate an unconditional causal effect.

`version_gaps.csv`, `version_by_outcome.csv`, and `version_by_count.csv` use all eligible runs in each stated group. Their samples differ from the fixed common subset. Keep these populations distinct.

**Target revisit rate:** operations with an earlier same-target candidate, divided by all operations in a run. Harness summaries average these per-run rates. They differ from the older pooled operation summaries. `harness_paired_differences.csv` pairs the same 2,000 tasks. `harness_by_source.csv` repeats that comparison separately within the two source datasets.

**Outlier:** one task contains 164 repeated probe executions, of which 163 count as exact repeats. Sensitivity analysis excludes that task from all three harnesses. The revisit contrasts remain +14.76 and +11.85 points.

**Later final-version checks:** the saved Gemini reconciliation includes 6,699 checks. Removing the first check from every nonempty run leaves 4,964 checks. These split exactly into new commands, same command with different output, and identical reruns. The reported shares pool checks and resample tasks. They do not measure test coverage.

## Limits

The analyses strengthen the descriptive comparisons under the tested measurement choices. They do not repair the audited state-tracking errors, validate contribution labels, recover test scope, or demonstrate that any work can be removed safely. The three version rules also share implementation risks. Results from the current data remain exploratory.

`manifest.json` records package versions and input hashes. The analysis script asserts sample sizes, complete pairing, and the final-check count identity.

## Restored patch-size benchmark

`harness_patch_size_profiles.csv` restores the four-bin benchmark with the current per-run rate definitions. The task bins follow the saved procedure: rank per-task reference-patch line counts with stable tie breaking, then form four equal bins. Every bin has 500 matched tasks per harness. The model row of the restored figure comes from `results/v2/benchmark/table2_difficulty.csv`, using only the `gold_patch_lines` rows.

These profiles report descriptive means, without new uncertainty intervals. They should be described as patch-size profiles rather than direct measurements of reasoning difficulty.
