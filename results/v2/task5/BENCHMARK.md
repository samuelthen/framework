# Task 5: Open-SWE-Traces v1.2 cross-harness benchmark (Section 3, facts only, no LLM)

**Stopped here for your review before any Qwen labeling.**

## Data and sample
- **Dataset:** `nvidia/Open-SWE-Traces` v1.2 at revision `a85dc97`. Agent Qwen3.8-27B (thinking, xhigh) under OpenHands, SWE-agent and mini-swe-agent; tasks from SWE-rebench-V2 and Scale-SWE.
- **Sample** (`sample.csv`, `scripts/v2_openswe_sample.py`):
  - The population is the 21,662 instance_ids that all three harnesses attempted, after dropping mini-SWE runs with unknown `resolved`.
  - 2,000 ids drawn with seed 0; one run per harness per id, drawn with the same seed where mini-SWE has several.
  - Result: **6,000 runs**.
- **Download** (`scripts/openswe_download.py`):
  - Each shard is a single 2,500-row row group, so rows cannot be read selectively.
  - The sample touches all 70 shards of the three harnesses (20.7 GB).
  - All 70 were verified against the Hub's LFS sha256.
- **Adapters** (`worktrace/loaders/openswe.py`): all three harnesses are stored as chat messages. Tool replies carry no call id and are paired with calls by position.
  - **OpenHands:** `execute_bash`, `str_replace_editor`, `think`, `finish`. The exit code is parsed from `[The command completed with exit code N.]`.
  - **SWE-agent:** `bash`, `str_replace_editor`, `submit`. Outputs carry no exit code (stays unknown). The first `submit` returns the harness's review checklist.
  - **mini-swe-agent:** `bash` tool calls with JSON replies `{returncode, output}`. Long outputs are stored only as head and tail (`elided_chars`), i.e. what the agent saw.
- **Automated audit** (by a third model, Claude) of 10 runs per harness, seed 0 (`audit_10_per_harness.csv`, `v2_task5.py audit`):
  - Each event log was rebuilt from its raw parquet row.
  - Raw calls equal ops for 30 of 30 runs, every reply is paired, commands and outputs match, and turns match.
  - The only unreplied call per run is the final submit.
  - **0 problems.**
  - Spot check: SWE-agent's `revert` ops are real `git stash`/`restore`/`checkout --` commands, often a stash to test the original code.
- **Across all 6,000 runs:** 1 lost result (SWE-agent).

## Table 1: by harness, same model (`table1_by_harness.csv`; task-clustered 95% CIs)
| | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| Resolve rate | 57.1% [54.9, 59.2] | 51.0% [49.0, 53.1] | 54.5% [52.5, 56.6] |
| Turns | 42.9 | 59.0 | 67.5 |
| Tool calls | 51.8 [50.5, 53.0] | 66.2 [64.8, 67.6] | 67.5 [66.0, 68.9] |
| Assistant output, k chars | 111 | 149 | 258 |
| Final context, k chars | 177 | 243 | 358 |
| **Exact-repeat rate (run mean)** | **0.20% [0.14, 0.28]** | **0.18% [0.16, 0.21]** | **0.20% [0.17, 0.23]** |
| Exact-repeat rate (pooled) | 0.32% [0.14, 0.66]* | 0.20% [0.18, 0.23] | 0.24% [0.21, 0.27] |
| Same-object revisit | 19.3% [18.9, 19.7] | 33.5% [33.0, 33.9] | 30.9% [30.4, 31.3] |
| Runs with ≥1 exact repeat | 7.3% [6.2, 8.5] | 11.1% [9.8, 12.5] | 12.3% [10.9, 13.8] |

- \* One mini-SWE run (`siliconcompiler_lambdapdk_pr114`) runs the same `python -c` command 163 times out of 235 ops. Without it, mini-SWE's pooled rate is 0.17%.
- **Tokens:** the dataset has no token counts, so character counts are given instead.
- **Turns vs tool calls:** OpenHands can issue several tool calls in one turn (up to 5), so its turns are fewer than its tool calls.

**Op kinds (% of ops):**

| | read | search | edit | revert | run | probe | submit | other |
|---|---|---|---|---|---|---|---|---|
| mini-swe-agent | 30.5 | 21.3 | 12.0 | 1.5 | 28.8 | 2.7 | 1.9 | 1.4 |
| OpenHands | 23.8 | 19.7 | 23.4 | 1.4 | 25.8 | 2.4 | 1.5 | 1.9 |
| SWE-agent | 26.8 | 18.6 | 18.4 | 2.6 | 25.0 | 4.4 | 3.0 | 1.3 |

## Table 2: by gold-patch size (four equal task bins, same tasks in every harness; `table2_gold_patch_bins.csv`)
| Bin (gold lines) | Resolve | Tool calls | Exact-repeat (pooled) | Same-object revisit | Runs with ≥1 exact repeat |
|---|---|---|---|---|---|
| Q1 easiest (0–12) | 65.0% | 53.4 | 0.20% [0.16, 0.24] | 26.8% | 7.9% |
| Q2 (12–33) | 63.3% | 55.1 | 0.42% [0.20, 0.86]* | 28.1% | 10.7% |
| Q3 (33–77) | 49.4% | 63.0 | 0.20% [0.17, 0.24] | 28.5% | 10.4% |
| Q4 hardest (77–6,814) | 39.1% | 75.8 | 0.20% [0.17, 0.24] | 30.2% | 11.9% |

\* Q2 contains the siliconcompiler run above. The per-harness rows are in the CSV and show the same pattern in each harness.

## What this shows
1. **With the model fixed, the harness barely changes exact repetition.** The run-mean exact-repeat rate is 0.18–0.20% in all three harnesses, with overlapping CIs.
   - The planned sentence "[harness] shows the highest repeat rate" has no clear winner.
   - SWE-agent and OpenHands have slightly more runs with any exact repeat: 11–12% vs 7%.
2. **The harness changes cost and revisits.**
   - OpenHands and SWE-agent make about 30% more tool calls than mini-swe-agent.
   - They revisit the same object much more often (31–34% vs 19%).
   - SWE-agent writes about 2.3× the assistant text of mini-swe-agent.
   - Part of the revisit gap is mechanical: `str_replace_editor view` re-opens a file by path, where mini-swe-agent uses `sed -n` ranges or `grep`.
   - The extra cost does not buy resolve rate: mini-swe-agent resolves the most (57% vs 51–55%).
3. **"Repetition grows with difficulty" is again not supported.**
   - From the easiest to the hardest bin, tool calls rise 1.42× and resolve rate falls 65% → 39%.
   - The exact-repeat rate is flat at 0.20%.
   - Only same-object revisits rise slightly (26.8% → 30.2%), the same picture as on JetBrains.
4. **Qwen3.8-27B does not repeat more than the frontier models.**
   - Its exact-repeat rate (about 0.2%) sits between the GPT models (about 0.03%) and Gemini (2.2%).
   - Its same-object revisit rate is higher (19–34% vs 9–21%).
   - The plan's expectation of "longer runs with more repeated work" holds for length, but not for exact repeats.
5. **Rare stuck loops exist.** One run repeats a command 163 times. Such runs are worth reporting as an Error-Loop-like case, but they are too rare to move the averages.

## Before labeling Qwen (your call)
- **Labeling volume (counted):**
  - The 6,000 runs have 370,992 ops, of which **109,114 have a repeat candidate**: mini-SWE 20,289 (19.6%), SWE-agent 43,279 (32.1%), OpenHands 45,546 (34.4%).
  - At the current rate of about 0.3–0.5 labels/s, labeling them all would take **3–4 days** on the shared key, after Gemini finishes.
  - A sample of 500 of the 2,000 tasks × 3 harnesses would be about 27k matched ops, about 1 day.
- **Skip rule:** Qwen has no pilot labels, so the per-model ≥98% rule cannot be checked yet. A small pilot (e.g. 20 tasks × 3 harnesses, all ops) would establish it first.
