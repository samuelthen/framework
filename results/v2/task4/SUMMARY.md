# Task 4: proxy validation (no human labels of our own)

Nothing in this task is human-validated by us. These are proxies for B.10 criteria 1–2; human validation is still pending (`results/v2/B10_STATUS.md`). The only human labels used are CodeTraceBench's own `unuseful` annotations, made by that dataset's authors.

## 1. Second annotator: `agreement.csv`, `confusion.md`
- **Annotators:** MODEL_2 = `x-test-1`, served as **glm-5.3-flash** (user-confirmed 2026-10-24).
  - It is a different family from the primary (deepseek-v4.1-flash), and is not Gemini, GPT or Qwen.
  - Same prompt v1, same reasoning settings, temperature 0.
- **Items** (`items.csv`): all 225 matched pilot ops plus 200 random unmatched ops (seed 0). 1 label error.
- **Comparison:** the primary's v2 labels (Task 2) against MODEL_2.

| Field | Subset | n | Agreement | κ | Macro-F1 |
|---|---|---|---|---|---|
| contribution | matched | 225 | 90.2% | **0.70** | **0.83** |
| contribution | unmatched sample | 200 | 99.0% | 0.50 | 0.75 |
| relation | matched | 225 | 84.0% | 0.50 | 0.61 |
| candidate-redundant (binary) | all | 425 | 98.4% | **0.83** | 0.91 |

**Matched contribution confusion** (rows: primary, columns: MODEL_2):

| | distinct | non_distinct | uncertain |
|---|---|---|---|
| distinct | 169 | 2 | 1 |
| non_distinct | 19 | 32 | 0 |
| uncertain | 0 | 0 | 2 |

- **MODEL_2 is more conservative about non-distinct.** On matched ops it calls 15.1% non-distinct; the primary calls 22.7%.
- **The two agree on candidate redundancy** (non-distinct *and* `reproduces`): 9.8% for MODEL_2 vs 9.3% for the primary. Their disagreements are almost all non-distinct `revisits`.
- **On the unmatched sample** both say `distinct` for ≥98.5% of ops. The low κ there is a prevalence artefact.

### Candidate-redundancy rate as a range across annotators and uncertain handling (`annotator_range.csv`)
- **Method:** pilot measure (B.7), share of a run's ops that are candidate-redundant, task-clustered CIs.
  - The MODEL_2 view replaces every matched op's label with MODEL_2's. Only matched ops can be candidate-redundant.
  - `lo` counts uncertain as not redundant; `hi` counts it as redundant.

| Model | primary lo – hi | MODEL_2 lo – hi | **range across both** |
|---|---|---|---|
| Gemini | 1.92% – 2.39% | 2.09% – 2.38% | **1.9% – 2.4%** |
| Luna | 1.36% – 1.36% | 1.36% – 1.36% | **1.4%** |
| Terra | 0.00% – 0.00% | 0.00% – 0.00% | **0.0%** |
| All | 1.08% – 1.23% | 1.13% – 1.22% | **1.1% – 1.2%** |

95% CIs per cell are in the CSV. For example, Gemini primary `lo` is [1.0, 3.0] and MODEL_2 `lo` is [1.2, 3.0].

## 2. Self-consistency: primary annotator, temperature 0.7, 3 samples, the same 425 items
Each sample is compared with the primary's temperature-0 v2 label. Each sample had 1 label error.

| Field | Subset | sample 0 κ | sample 1 κ | sample 2 κ | agreement range |
|---|---|---|---|---|---|
| contribution | matched (225) | 0.90 | 0.88 | 0.90 | 95.6–96.4% |
| relation | matched (225) | 0.70 | 0.66 | 0.70 | 90.2–92.4% |
| candidate-redundant | all (425) | 0.88 | 0.83 | 0.92 | 98.6–99.3% |

- **Stability** (`self_consistency_stability.json`): contribution is identical across the temperature-0 label and all three samples for 92.4% of matched ops and 98.5% of unmatched ops.
- **Macro-F1 caution:** for sample 2 on matched contribution, macro-F1 is 0.64 even though κ is 0.90. A class absent from one side scores F1 = 0, so κ is the better summary here.
- **Reading:** the primary annotator is more consistent with itself (κ ≈ 0.9) than with MODEL_2 (κ 0.70). Part of the cross-annotator gap is therefore a stable difference between the two models, not noise.

## 3. CodeTraceBench external check: `codetracebench/prf.csv`, `codetracebench/steps.csv`
- **Data:** `NJU-LINK/CodeTraceBench` at revision `aa213b8`, verified split, SWE-bench trajectories.
  - 489 runs, all GPT-5: 313 OpenHands, 108 SWE-agent, 68 mini-SWE-agent.
  - Human `unuseful` labels from the dataset authors.
- **Loader:** `worktrace/loaders/codetracebench.py`.
  - Our op count equals the manifest `step_count` for 484 / 489 runs (`alignment.csv`).
  - The 5 misaligned runs have no `unuseful` labels and are excluded.
  - Loader audit (automated audit by a third model, Claude) on 5 runs: ops match the raw steps one to one, and every labelled step was checked against the raw file.
- **Labeling:** the primary annotator, prompt v1, on all 5,889 ops with a repeat candidate.
  - 86 label errors (1.5%; 75 empty responses after retries), kept as `uncertain`.
  - Unmatched ops cannot be non-distinct under the v1 evidence rule.

**WorkTrace vs baselines** (484 runs, 17,317 steps, 69 `unuseful`; task-clustered 95% CIs). For WorkTrace, `lo` counts uncertain as not redundant and `hi` counts it as redundant.

| Predictor | predicted | TP | precision | recall | F1 |
|---|---|---|---|---|---|
| exact repeat (baseline) | 412 | 23 | 5.6% [3.0, 9.0] | 33.3% [22.2, 43.9] | 9.6 |
| same-object revisit (baseline) | 4,599 | 27 | 0.6% [0.3, 0.8] | 39.1% [28.3, 49.2] | 1.2 |
| WorkTrace non-distinct, lo / hi | 1,759 / 1,936 | 23 / 28 | 1.3% / 1.4% | 33.3% / 40.6% | 2.5 / 2.8 |
| **WorkTrace candidate-redundant, lo / hi** | 536 / 799 | 19 / 25 | **3.5% [1.9, 5.6] / 3.1%** | **27.5% [16.9, 38.2] / 36.2%** | **6.3 / 5.8** |

**By harness** (candidate-redundant `lo` vs exact repeat):
- **SWE-agent:** P 7.4% / R 38.3% vs exact P 7.4% / R 48.9%.
- **OpenHands:** 0 of 14 vs exact 0 of 14.
- **mini-SWE:** 1 of 8 vs exact 0 of 8.

**Reading:**
- **WorkTrace does not beat the exact-repeat baseline on CodeTraceBench.** Precision is similar (3.5% vs 5.6%, overlapping CIs), and recall is somewhat lower (27.5% vs 33.3%).
- **WorkTrace beats same-object revisit** by about 6× in precision at similar recall.
- **The comparison is weak, because CodeTraceBench's `unuseful` is a different construct.**
  - Its labels mostly mark repeated `task_tracker` plan updates, empty actions after a format error, and some test runs, not repeated reads of unchanged code.
  - Only 32 of the 69 `unuseful` steps have any repeat candidate at all; the other 37 cannot be flagged by any repeat-based measure.
  - Of the 69: both predictors find 18, only WorkTrace finds 1, only exact repeat finds 5, and neither finds 45.
- **Most WorkTrace "false positives" are true repeats.** 210 of its 517 candidate-redundant predictions outside `unuseful` are exact repeats that CodeTraceBench did not mark. They are repeated, but CodeTraceBench does not count them as unuseful.
- **Conclusion:** this check is weak evidence either way. It says nothing about whether our non-distinct label matches human judgment of *redundant* work. That still needs the B.8 human labels.
