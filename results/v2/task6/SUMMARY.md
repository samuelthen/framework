# Task 6: scale labeling — all Gemini runs, 10% Luna/Terra samples

**Labels:**
- **Annotator and prompt:** the primary annotator (x-test-2, served as deepseek-v4.1-flash-1017), prompt v1, current facts.
- **Skip rule** (per model): the skip rule applies to Gemini and Terra, so their unmatched ops carry a rule label (`distinct`, `rule_skip`). Luna fails the rule, so all of its ops are LLM-labelled.
- **Log:** `labeling_log.csv`.

All labels come from an LLM annotator. Nothing is human-validated, and the GLM second annotator was run only on the pilot, not at scale.

**Code:** `worktrace/scripts/v2_task6.py` (labeling) and `v2_task6_analyze.py` (`build`, `report`). All CIs are task-clustered 95%.

| | Gemini | Luna | Terra |
|---|---|---|---|
| scope | all runs | 10% task sample | 10% task sample |
| runs / tasks | 2,100 / 700 | 204 / 68 | 204 / 68 |
| ops / matched ops | 111,570 / 25,348 | 3,895 / 486 | 4,132 / 444 |
| LLM labels / label errors | 25,348 / 9 | 3,895 / 3 (all on unmatched ops) | 444 / 0 |

## 1. B.7 measures (`measures.csv`)
| | Gemini | Luna | Terra |
|---|---|---|---|
| non-distinct share of matched ops | **23.0% [22.1, 23.9]** | 8.0% [4.8, 11.5] | 6.8% [4.1, 9.6] |
| uncertain share of matched ops | 0.8% | 0.4% | 0.2% |
| **candidate-redundancy rate (run mean), lo – hi** | **1.32% – 1.66%** | 0.48% | 0.16% |
| exact-repeat rate (run mean) | 2.22% | 0.00% | 0.04% |
| tail ops after the last distinct op, per run (hi) | 0.00 [0.00, 0.01] | 0.00 | 0.00 |
| runs with any tail (hi) | 0.4% | 0.5% | 0% |
| late non-distinct rate, lo – hi | 3.7% – 4.3% | 0.3% – 1.1% | 0.3% |

- **The pilot's picture holds at scale.**
  - About a quarter of Gemini's matched ops are non-distinct, matching the pilot's 22.7% for all models.
  - Candidate-redundant work is 1.3–1.7% of a Gemini run.
  - Essentially no run has a low-contribution tail (0.4% of runs), so Test Looper is again not supported.
- **The rate is a single-annotator range.**
  - At scale, the candidate-redundancy range covers only uncertain handling; it has no second annotator.
  - On the pilot, the range across both annotators was barely wider than the primary's own (Task 4).
- **The scale estimate is lower than the pilot's.**
  - Gemini 1.3–1.7% here vs 1.9–2.4% in the pilot (16 runs, CI [1.0, 3.0]). The scale CIs are about 10× narrower.
  - Luna (0.5% vs 1.4%) and Terra (0.2% vs 0%) are close to the pilot. Their samples are small, so the CIs are wide.

## 2. Signatures vs exact repeats (`signatures_ci.csv`, Gemini all runs)
| signature | matches | non-distinct | exact-repeat share | difference, pts |
|---|---|---|---|---|
| `reread_unchanged_same_output` | 994 | 97.8% | 82.3% | **+15.5 [+12.7, +18.6]** |
| `return_any` | 16,532 | 26.7% | 14.1% | **+12.6 [+11.5, +13.6]** |
| `self_repeat` | 8,180 | 13.2% | 2.2% | **+11.0 [+10.0, +12.1]** |
| `error_loop` | 62 | 11.3% | 0% | +11.3 [+1.8, +22.9] |
| `edit_test_identical_test` | 68 | 95.6% | 91.2% | +4.4 [−2.8, +12.7] |
| `new_to_new` (control) | 70,574 | 0.4% | 0% | +0.4 |

- **B.10 criterion 4 now holds with real n.** Three fact-defined signatures sit more than 10 points from the exact-repeat share, with CIs that exclude 10:
  - `reread_unchanged`: n = 994, vs 11 in the pilot.
  - `return_any`: n = 16,532.
  - `self_repeat`: n = 8,180.
- **The pilot's +75 points for `reread_unchanged` was a small-n artefact.**
  - At scale, most such re-reads are also exact repeats (82%), so the gap is +15.5 points.
  - The signature still finds non-distinct re-reads that exact-repeat counting misses: re-reading the same unchanged content with a different command.
  - **Caveat, as in v1:** this signature's facts (same output, object unwritten) are shown to the annotator, so its high non-distinct share is partly by construction.
- **Not evidence:** `informative_then_redundant`, `return_distinct` and `return_non_distinct` are defined by the labels themselves (non-distinct 100% or 0% by construction), so they are omitted here. They are in the CSV.

## 3. Return-after-k, re-run on all Gemini runs (`return_after_k_*.csv`)
- **Model:** logistic GEE (exchangeable, task clusters) and a task-clustered logit, `non_distinct ~ k_bin + relative position + log(run length)`.
- **Data:** every `return_any` match (object view); the 180 `uncertain` are dropped.

**Events per parameter:**

| fit | returns used | non-distinct (events) | parameters | **events per parameter** | task clusters |
|---|---|---|---|---|---|
| Gemini, all runs | 16,352 | 4,405 | 4 | **1,101** | 700 |
| pooled with Luna/Terra samples (+ model term) | 16,973 | 4,428 | 6 | 738 | 700 |
| *pilot (Task 3), for comparison* | | *32* | *6* | *≈5* | *17* |

**Odds ratios, Gemini, all runs** (GEE; the logit agrees to within 0.2 everywhere):

| term | OR [95% CI] |
|---|---|
| k = 2–3 vs k = 1 | 1.47 [1.27, 1.72] |
| **k ≥ 4 vs k = 1** | **2.65 [2.32, 3.03]** |
| relative position (0 → 1) | 0.17 [0.14, 0.21] |
| log run length | 1.39 [1.20, 1.61] |

**Raw non-distinct share by k** (Gemini): k = 1: 15.8%; k = 2–3: 19.6%; k ≥ 4: 31.1%.

- **The return-after-k effect is confirmed and is now well powered**, at about 1,100 events per parameter vs about 5 in the pilot.
- **Shape:** it is monotone in k, and it survives adjustment for position and run length.
- **Size:** the effect is much smaller than the pilot suggested (OR 2.7, not 14–33).
- **Reading:** the more other objects an agent visits before coming back, the more likely the return re-does work it already had.
- **Position:** later returns are *less* often non-distinct (OR 0.17 from start to end of a run). This fits verification and refinement at the end, not waste.
- **Luna and Terra:** they have too few non-distinct returns (8 and 15) to estimate a k effect of their own. In the pooled fit they enter only as lower intercepts (OR 0.12 and 0.21 vs Gemini).
