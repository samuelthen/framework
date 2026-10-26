# WorkTrace: progress (interim, 2026-10-25)

**26 October update:** [Eight-pair contribution validation](results/precision_validation_20261026/RESULTS.md)
now includes corrected component units, two blinded model-coded passes, reviewer
disagreements, verification precision and baseline comparisons. The original
precision ranking is sensitive to call packaging. Seven audit probes now pass;
16 pilot default graphs were rebuilt separately. Historical summaries below
remain pre-repair results, and human validation is still pending.

**Start here for an overall assessment: [`OVERVIEW.md`](OVERVIEW.md). To rebuild graphs or results on another machine: [`REPRODUCE.md`](REPRODUCE.md).**

The v1 pilot results are in `RESULTS.md` and are unchanged; v2 work is under `results/v2/`. All labels come from LLM annotators, and all checks are automated audits by a third model (Claude). **Nothing is human-validated;** B.10 criteria 1–2 are replaced by proxies (`results/v2/B10_STATUS.md`).

## Done
| Item | Main result | File |
|---|---|---|
| Task 2: relabel after fact fixes | Non-distinct share of matched ops 22.7% [16.7, 29.6]; uncertain 2.2% | `results/v2/task2/SUMMARY.md` |
| View B: code-version graph | Gemini 4.8 versions per run, Luna/Terra 2.6; backtracks ≤3.7% of runs; verification concentrates on the final version (Gemini 3.2 runs vs 0.7 on each earlier version) | `results/v2/viewb/SUMMARY.md` |
| View B vs the tail measure (Gemini) | The final-version verify runs are 92% *different* commands (broader suites, other tests, checks, builds) and only 1.9% identical reruns, which is why the tail measure finds no non-distinct tail | `results/v2/reconcile/SUMMARY.md` |
| prompt_v2.1 `version_move` | 177 pilot changes: 80% correct, 0.6% branch_out, 17% support, 3% sidetrack. Runs are linear refinement (Late-Landing-like) | `results/v2/prompt_v2/V2_1_RESULTS.md` |
| Error Loop | About 1% of runs | `results/v2/error_loop/SUMMARY.md` |
| Task 3: return-after-k confounds | The k effect survives adjustment for length, position and model, but only about 5 events per parameter | `results/v2/task3/SUMMARY.md` |
| Task 6: scale labeling (all Gemini, 10% Luna/Terra) | Gemini non-distinct share of matched ops 23.0%. Candidate-redundancy 1.3–1.7%; tail ≈ 0. Return-after-k confirmed: OR 2.65 [2.32, 3.03] for k ≥ 4 at about 1,100 events per parameter. `reread_unchanged` +15.5 pts [12.7, 18.6] (n = 994) | `results/v2/task6/SUMMARY.md` |
| Task 4: proxy validation | Primary vs GLM κ = 0.70 (candidate-redundant κ = 0.83); self-consistency κ ≈ 0.9; candidate-redundancy rate 1.1–1.2% across both annotators and uncertain handling; CodeTraceBench: WorkTrace P 3.5% / R 27.5% vs exact repeat P 5.6% / R 33.3% (a different construct) | `results/v2/task4/SUMMARY.md` |

## Running
- **Task 5** (Open-SWE-Traces v1.2, Qwen3.8-27B, 2,000 shared tasks): benchmark accepted 2026-10-25 (`results/v2/task5/BENCHMARK.md`).
  - Run-mean exact-repeat rate 0.18–0.20% in every harness. Pooled rates are given with and without the stuck-loop case study.
- **Qwen pilot** (20 tasks × 3 harnesses, all 4,018 ops labelled, `results/v2/qwen/pilot/SUMMARY.md`):
  - Unmatched ops are distinct 99.4–99.7% of the time, so every harness passes the 98% skip rule.
  - Uncertain is 0.6–1.5% of matched ops; non-distinct is 5–10% of matched ops.
  - **Waiting for review before the 500-task main run.**
- **Qwen main run** (500 tasks × 3 harnesses, matched ops only) and then GLM on 1,000 matched ops: in progress (`results/v2/qwen_main.log`).

## Repository layout
- **Code:** `worktrace/` (package, scripts, tests, `config.yaml`).
- **Outputs:** results in `results/`, figures in `figures/`, LLM labels in `data/labels/`.
- **Not included:** raw datasets, trajectory event logs, API caches and credentials.
