# Qwen pilot (Open-SWE-Traces v1.2, Qwen3.8-27B): skip-rule check and uncertain share

**Stopped here for review before the 500-task main run.**

## Setup
- **Runs:** 20 of the 2,000 sampled tasks (seed 0) × 3 harnesses = 60 runs, 4,018 ops (`pilot_runs.csv`).
- **Labeling:** every op labelled with prompt v1 by the primary annotator (x-test-2, served as deepseek-v4.1-flash-1017), current facts.
  - 7 label errors (0.2%), kept as `uncertain`.
- **Code and outputs:** `worktrace/scripts/v2_qwen.py pilot` and `pilot_report`. Labels in `data/labels/qwen_pilot.jsonl`, table in `pilot_summary.csv`.
- **CIs:** task-clustered 95%.

All labels come from an LLM annotator. Nothing here is human-validated.

## Results
| | mini-swe-agent | OpenHands | SWE-agent | all |
|---|---|---|---|---|
| ops (matched / unmatched) | 1,141 (255 / 886) | 1,389 (465 / 924) | 1,488 (534 / 954) | 4,018 (1,254 / 2,764) |
| **unmatched ops labelled distinct** | **99.7% [99.3, 100]** | **99.4% [98.9, 99.8]** | **99.7% [99.3, 100]** | 99.6% [99.3, 99.8] |
| passes the ≥98% skip rule | yes | yes | yes | |
| **uncertain, matched ops** | **1.2% [0.0, 3.4]** | **0.6% [0.0, 1.2]** | **1.5% [0.3, 2.6]** | 1.1% [0.5, 1.8] |
| uncertain, all ops | 0.5% | 0.6% | 0.7% | 0.6% |
| non-distinct, matched ops | 5.1% [2.7, 7.7] | 5.2% [2.8, 7.8] | 9.7% [6.9, 13.3] | 7.1% [5.5, 9.0] |
| label errors | 1 | 3 | 3 | 7 |

- **Skip rule:** all three harnesses pass, and even the lower CI bounds stay above 98%.
  - The main run can therefore skip unmatched ops in every harness. They get a rule label (`distinct`, `rule_skip`), as for Gemini and Terra.
  - None of the 2,764 unmatched ops is labelled non-distinct. The 12 that are not distinct are `uncertain`, 5 of them label errors.
- **Uncertain share:** about 1% of matched ops, well under the B.10 criterion 3 limit of 20%.
- **Non-distinct share of matched ops (first look, n = 20 tasks):** 5–10% here vs 22.7% on the JetBrains pilot.
  - On matched ops, Qwen's revisits are mostly judged informative.
  - SWE-agent is about twice OpenHands and mini-swe-agent, but the CIs are wide.
  - The headline analysis (revisits by harness, paired on task) belongs to the main run.

## Main-run cost (with the skip rule)
- **Volume:** matched ops only. In the full 2,000-task benchmark 29% of ops are matched, so 500 tasks × 3 harnesses ≈ 27k labels.
- **Time:** about 1 day at the current rate, run after Gemini's last shard to avoid sharing the key.
