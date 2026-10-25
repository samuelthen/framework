# WorkTrace: all results so far, and is it promising? (interim, 2026-10-25)

Scope:
- **Data:**
  - 6,300 JetBrains SWE-bench Pro runs (3 models × 700 tasks × 3 runs), facts only.
  - A 50-run pilot with every operation LLM-labelled.
  - Proxy validation: a second annotator, self-consistency, and CodeTraceBench.
  - Open-SWE-Traces v1.2: 6,000 Qwen3.8-27B runs (2,000 tasks × 3 harnesses), facts only, plus a 60-run labelled pilot.
- **Still to come:** the Qwen 500-task main labeling run (awaiting go) and the last of the full Gemini labeling (Task 6, run 3 of 3).
- **Validation status:** nothing is human-validated. Labels come from LLM annotators, and all checks are automated audits by a third model (Claude).

## Short verdict
- **The method works.** Facts, labels, graphs and signatures are reproducible, and model–model agreement is decent.
- **But the paper as planned ("much repeated work is redundant, and patterns explain it") is not supported so far.**
  - Redundant work is rare in this data.
  - What repetition there is is mostly *useful* verification and refinement.
- **The most promising story is the reverse claim:**
  - Repeat counts overstate waste, because most repetition is purposeful.
  - Agents converge by linear refinement and then verify the final code with a widening set of checks.
  - WorkTrace is the tool that can show this. A counting tool cannot.
- **Two results could still change the picture:**
  - the Open-SWE harness comparison, where a weaker model and different harnesses may waste more;
  - human labels (B.8).

## 1. How much repetition is there? (Section 3, facts only)
| Model | Resolve | Tool calls per run | Exact-repeat rate | Same-object revisit |
|---|---|---|---|---|
| Gemini 3.7 Flash | 60.0% | 53.1 | 2.21% [2.08, 2.35] | 21.0% |
| GPT-5.6 Luna | 50.0% | 17.6 | 0.02% | 11.1% |
| GPT-5.6 Terra | 54.2% | 19.0 | 0.05% | 9.4% |

- **Exact repeats are rare.** They are essentially absent for the GPT models.
- **The planned "repetition grows with difficulty" claim is not supported.** From the easiest to the hardest bin, the exact-repeat rate is flat (0.70% → 0.75%) while tool calls rise 1.38×.
- **Open-SWE (Qwen3.8-27B, same 2,000 tasks in each harness; `results/v2/task5/BENCHMARK.md`):**

  | Harness | Resolve | Tool calls | Exact-repeat (run mean) | Same-object revisit |
  |---|---|---|---|---|
  | mini-swe-agent | 57.1% | 51.8 | 0.20% | 19.3% |
  | OpenHands | 51.0% | 66.2 | 0.18% | 33.5% |
  | SWE-agent | 54.5% | 67.5 | 0.20% | 30.9% |

  - With the model fixed, the harness barely changes exact repetition. It does change cost and revisits.
  - Exact repetition is again flat with difficulty.
  - One stuck-loop run (164 identical probes, all with empty output) is a case study, not a pattern.
  - **Promising?** ✗ for a "lots of waste" headline.

## 2. How much repeated work is redundant? (pilot, LLM labels)
- **Matched ops** (ops with a repeat candidate): 22.7% [16.7, 29.6] are judged non-distinct.
- **Across all ops** that falls to 3.6%.
- **Candidate-redundancy rate** (non-distinct and reproducing earlier work, as a share of all ops), as a range across both annotators and both ways of counting `uncertain`:

| Model | Range |
|---|---|
| Gemini | 1.9% – 2.4% |
| Luna | 1.4% |
| Terra | 0.0% |
| All | 1.1% – 1.2% |

- **No low-contribution tail:** 0 ops after the last distinct op in every Gemini pilot run.
- **Annotator robustness is good:** the range barely moves between annotators.
- **Qwen pilot** (20 tasks × 3 harnesses, all ops labelled; `results/v2/qwen/pilot/SUMMARY.md`):
  - Non-distinct share of matched ops: 5–10%, against 22.7% in the JetBrains pilot.
  - Unmatched ops are distinct 99.4–99.7% of the time, so the skip rule passes in every harness.
- **Promising?** ✓ the measure is robust. ✗ there is little redundancy to explain.

## 3. Does WorkTrace see something exact repeats miss? (signatures)
- **`reread_unchanged`** (re-reading a file that has not changed since): 75 points more non-distinct than the exact-repeat rate [+17, +95].
- **`self_repeat`:** +13 points.
- **`return_any`:** +7 points; the CI includes 0.
- **Promising?** ✓ This is the clearest sign that structure adds information beyond counting. But n is small: 11 matches for `reread_unchanged`.

## 4. What do runs look like structurally? (View B code-version graph, all 6,300 runs)
- **Mostly linear refinement.**
  - Gemini 4.8 code versions per run, Luna and Terra 2.6.
  - Backtracks occur in ≤3.7% of runs.
  - The LLM `version_move` label calls 0.6% of changes `branch_out`; 80% are `correct` and 17% `support` (scratch and repro files).
- **Gemini verifies late and broadly:**
  - 3.2 verify runs on the final version vs 0.7 on each earlier version.
  - 55% of all its verifies land on the final version.
  - 92% of those final verifies are *different* commands (broader suites, other tests, check scripts, lint, builds).
  - Only 1.9% are identical reruns.
- **Resolve rate falls with more versions:** 72% for 1 version, 45–58% for 5–8.
- **Error Loop** (3+ consecutive ops with the same error): about 1% of runs.
- **Promising?** ✓ A clean, TRACE-style picture (Late-Landing-like) with a clear message: the extra work at the end is verification, not waste.

## 5. Return-after-k (Task 3)
- **Model:** logistic GEE, `non_distinct ~ k + position + log length + model`.
- **The k effect survives adjustment** (OR 14–33 vs k = 1) but with very wide CIs.
- **It appears only in long runs and mostly for Gemini.**
- **Power is thin:** about 5 events per parameter. This will be re-run on all Gemini runs once labelling finishes.
- **Promising?** ? Direction only for now.

## 6. Are the labels trustworthy? (proxies; human labels pending)
- **Second annotator (GLM-5.3-flash), matched ops:** κ = 0.70 on contribution, 0.83 on candidate redundancy.
- **Self-consistency (T = 0.7, 3 samples):** κ ≈ 0.88–0.90.
- **CodeTraceBench** (human "unuseful" labels): WorkTrace P 3.5% / R 27.5% vs exact repeat P 5.6% / R 33.3%.
  - Not better than the baseline.
  - Its labels mostly mark planning repeats and empty actions, a different construct. Only 32 of its 69 labelled steps are repeats at all.
- **Promising?** ✓ the labels are stable. ? external validity is unshown, and human validation is still pending.

## What would make it promising for the original framing
1. **Open-SWE shows a harness with clearly more redundant work** under the same model.
   - Exact repeats show no such harness.
   - In the pilot, SWE-agent's non-distinct share is about twice the others', but n is small. The 500-task run decides it.
2. **Human labels agree** with the LLM labels (B.8 sample ready in `annotation/pilot.csv`).
3. **The full Gemini set makes the return-after-k and `reread_unchanged` effects robust** (Task 6, in progress).

If (1) fails, the stronger paper is a measurement paper: "repetition ≠ waste".
- **Claim:** recent agents waste little.
- **Evidence:**
  - their repetition is refinement and verification;
  - counting tools mislabel it.
- **Caveat:** the interventions (Section 5.3) would then have little to remove.

## Where to look
| Topic | File |
|---|---|
| v1 pilot | `RESULTS.md` |
| v2 relabel | `results/v2/task2/SUMMARY.md` |
| View B | `results/v2/viewb/SUMMARY.md`, figures `figures/v2/viewb_patterns_*_support.png` |
| Verify classes | `results/v2/reconcile/SUMMARY.md` |
| version_move | `results/v2/prompt_v2/V2_1_RESULTS.md` |
| Return-after-k | `results/v2/task3/SUMMARY.md` |
| Validation proxies | `results/v2/task4/SUMMARY.md`, `results/v2/B10_STATUS.md` |
| Open-SWE choice | `results/v2/task5/RECOMMENDATION.md` |
| Open-SWE benchmark | `results/v2/task5/BENCHMARK.md` |
| Qwen pilot | `results/v2/qwen/pilot/SUMMARY.md` |
