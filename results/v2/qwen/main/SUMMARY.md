# Qwen main run: 500 tasks × 3 harnesses (Open-SWE-Traces v1.2, Qwen3.8-27B)

## Setup
- **Sample:** 500 of the 2,000 benchmark tasks (seed 0). Each task has one run per harness, so the comparisons are paired on task.
- **Labels:** primary annotator (deepseek-v4.1-flash), prompt v1, current facts (`labeling_log.csv`).
  - Every matched op is LLM-labelled: 26,963 labels, 40 label errors, kept as uncertain.
  - Unmatched ops are rule-labelled `distinct`, since all harnesses passed the ≥98% rule on the pilot.
- **Code:** `worktrace/scripts/v2_qwen.py` (labeling) and `v2_qwen_analyze.py` (`build`, `report`, `agree`, `version_move`).
- **CIs:** task-clustered 95%. Harness differences use a task-paired bootstrap.
- **Validation:** all labels come from LLM annotators. Nothing is human-validated.

| | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| ops | 25,653 | 32,991 | 33,097 |
| matched (LLM-labelled) | 4,934 | 11,442 | 10,587 |

## 1. Do higher revisit rates mean more non-distinct work? (`1_headline*.csv`)
**Among revisits** (relation `revisits` or `reproduces`):

| | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| n | 4,283 | 9,705 | 9,256 |
| distinct | 90.3% | 95.2% | 91.0% |
| **non-distinct** | **9.6% [8.6, 10.5]** | **4.6% [4.1, 5.1]** | **8.9% [8.1, 9.7]** |
| uncertain | 0.1% | 0.2% | 0.2% |

**Among exact repeats:**

| | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| n | 47 | 71 | 69 |
| non-distinct | 47% | 61% | 42% |
| uncertain | 28% | 14% | 19% |

Exact repeats are few, and the CIs are wide (±15 points).

**As a share of all work:**

| | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| revisits, % of ops | 16.7% | 29.4% | 28.0% |
| **non-distinct revisits, % of ops** | **1.60% [1.43, 1.77]** | **1.36% [1.22, 1.52]** | **2.48% [2.27, 2.71]** |
| non-distinct revisits per run | 0.82 | 0.90 | 1.64 |

Paired on task, against mini-swe-agent:

| | revisit share of ops | non-distinct revisit share of ops |
|---|---|---|
| OpenHands | +12.7 pts [11.8, 13.6] | **−0.23 pts [−0.45, −0.03]** |
| SWE-agent | +11.3 pts [10.4, 12.1] | **+0.88 pts [0.60, 1.15]** |

**Answer:**
- **The higher revisit rates mostly mean more *informative* revisits, not more non-distinct work.**
- **OpenHands** revisits 12.7 points more of its ops than mini-swe-agent, yet has slightly *less* non-distinct work. Its extra revisits are almost all judged distinct.
- **SWE-agent** has a small real excess: 0.9 points of ops, about 0.8 extra non-distinct ops per run.
  - About half of that comes from its post-submit segment (§3). Before the first submit its share is 2.12% against mini's 1.60%.
- **Caveat:** the annotators disagree on Qwen more than on JetBrains (§6), so these small non-distinct differences are less robust than the revisit differences.

## 2. Where does the revisit gap come from? (`2_read_style.csv`)
**Revisits by op kind, % of all ops:**

| kind | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| **edit** (same file edited again) | 3.8 | **15.5** | **10.8** |
| run | 2.8 | 7.1 | 4.7 |
| read | 9.3 | 5.9 | 8.4 |
| other kinds | 0.9 | 0.9 | 4.2 (incl. 1.5 second submits) |

**Read revisits by read style** (% of all ops; non-distinct share among those revisits):

| read style | mini-swe-agent | OpenHands | SWE-agent |
|---|---|---|---|
| range read (`sed -n`, `head`/`tail`, `view` with `view_range`) | 7.6% (12.2% nd) | 4.6% (4.9% nd) | 6.9% (11.5% nd) |
| whole-file view (`cat`, `view` without range) | 0.5% (10.3% nd) | 0.5% (4.5% nd) | 0.7% (16.1% nd) |
| grep / search | 1.3% (11.7% nd) | 1.0% (11.1% nd) | 1.1% (22.1% nd) |

- **The revisit gap is a tool artifact, but of *edit* granularity, not read granularity.**
  - `str_replace_editor` makes one change per call. Every further edit to a file counts as a revisit of that object.
  - mini-swe-agent writes several changes per command (heredocs, `sed -i`, scripts).
  - Edit revisits alone account for about 9–12 of the 11–13-point gap. Read revisits are *not* higher for OpenHands or SWE-agent.
- **This corrects the guess in `task5/BENCHMARK.md`** that `view` re-opens drive the gap.
- **Non-distinct revisits are mostly re-reads of ranges.** Their non-distinct share is similar across read styles within a harness. OpenHands is lowest in every style.

## 3. SWE-agent after the first submit (`3_swe_agent_post_submit.csv`)
- **Every run continues:** all 500 SWE-agent runs have ops after the first `submit`, because the harness's first submit returns a review checklist.
- **Size:** 1,942 ops, 5.9% of all SWE-agent ops; 3.9 per run on average, median 3.
- **What they are:** runs 28%, the second submit 26%, reverts 16% (removing repro scripts, as the checklist asks), probes 13%, edits 11%.

| | pre-submit | post-submit |
|---|---|---|
| ops | 31,155 | 1,942 |
| matched share | 30.1% | 61.8% |
| non-distinct, share of all ops | 2.2% | **8.4% [7.0, 9.8]** |
| non-distinct, share of matched ops | 7.3% | **13.6% [11.4, 15.9]** |

- **The post-submit segment is about 4× as dense in non-distinct work as the rest of the run.** It is mostly re-running the same tests and re-checking the diff after the checklist.
- **It is a harness-induced, bounded cost:** a few ops per run, but present in every run.

## 4. Return-after-k and the Error Loop, per harness (`4_*.csv`)
**Return-after-k** (logistic GEE, task clusters, adjusted for position and run length):

| | returns | non-distinct by k = 1 / 2–3 / ≥4 | OR k ≥ 4 vs k = 1 | events per parameter |
|---|---|---|---|---|
| mini-swe-agent | 3,278 | 10.5% / 10.3% / 9.1% | 1.06 [0.78, 1.43] | 79 |
| OpenHands | 7,376 | 3.3% / 4.1% / 5.0% | 1.48 [1.07, 2.05] | 82 |
| SWE-agent | 6,924 | 7.8% / 9.1% / 8.9% | 1.16 [0.92, 1.46] | 151 |

- **For Qwen, the k effect is weak or absent:** an OR of 1.5 only for OpenHands, against 2.65 for Gemini.
- **Reading:** the more other objects Qwen visits before returning, the more it re-does work only under OpenHands, and only mildly.
- **Position runs the other way from Gemini:** later returns are *more* often non-distinct under OpenHands and SWE-agent (OR about 2).

**Error Loop** (3+ consecutive ops with the same error):

| | runs with a loop | loops | mean length | `error_loop` signature: non-distinct |
|---|---|---|---|---|
| mini-swe-agent | 4.4% | 22 | 3.2 | 0% of 48 |
| OpenHands | 6.6% | 34 | 3.1 | 0% of 72 |
| SWE-agent | 5.6% | 28 | 3.1 | 3% of 60 |

- **Error loops are more common than on JetBrains (about 1%) but short.** Their ops are almost never judged non-distinct, because the agent changes something between the errors.
- **SWE-agent caveat:** it records no exit codes, so its loops are detected from error lines only.

## 5. View B for Qwen (`5_viewb*.csv`; variant (b), support files from the submitted patch)
| | versions per run | runs with a backtrack | backtracks via `git stash`/`checkout`/`restore` | runs with another backtrack | verify runs on final version | final share of all verifies |
|---|---|---|---|---|---|---|
| mini-swe-agent | 6.4 | 37.2% | 96% | 1.8% | 2.59 | 29% |
| OpenHands | 14.2 | 44.8% | 98% | 1.0% | 1.32 | 14% |
| SWE-agent | 11.5 | 36.0% | 98% | 1.0% | 2.52 | 20% |

- **Versions per run track edit calls almost one to one** (0.9–1.0 versions per edit call). The version counts reflect each harness's edit granularity, not more iteration.
- **The apparent backtracks are almost all `git stash && <test>; git stash pop`:** the agent tests the *original* code to confirm a failure, then restores its changes.
  - Real backtracks occur in 1–2% of runs, in line with JetBrains (≤3.7%).
  - View B should treat a stash-and-pop within one command as a probe of the root, not as a move. Flagged for the next View B revision; not changed here.
- **Qwen spreads its verification over the whole run** (final version 14–29% of verifies), unlike Gemini's late, final-version-heavy verification (55%).
- **`version_move` (prompt v2.1, primary annotator)** on 300 random changes, 100 per harness, seed 0 (`5_version_move.csv`; 0 label errors):

  | | correct | branch_out | support | sidetrack |
  |---|---|---|---|---|
  | mini-swe-agent | 35% | **2%** | 62% | 1% |
  | OpenHands | 28% | **0%** | 71% | 1% |
  | SWE-agent | 52% | **0%** | 45% | 3% |

  - **Branch-outs are as rare as on JetBrains** (0–2% vs 0.6%), so runs are linear here too.
  - **`support` is much more common** (45–71% vs 17% on JetBrains). Qwen writes many repro and scratch scripts, and the sample is drawn from variant (a), where every write is a change.

## 6. Second annotator (GLM-5.3-flash) on 1,000 random matched ops (`agree_model2.csv`, `annotator_range.csv`)
| field | agreement | κ |
|---|---|---|
| contribution | 93.4% | **0.45** |
| relation | 74.7% | 0.29 |
| candidate-redundant | 97.9% | 0.31 |

**Contribution, rows primary, columns GLM:**

| | distinct | non-distinct | uncertain |
|---|---|---|---|
| distinct | 905 | 20 | 8 |
| non-distinct | 34 | 27 | 1 |
| uncertain | 2 | 1 | 2 |

**Candidate-redundancy rate, primary vs GLM** (share of ops, implied from the sample):

| | primary | GLM |
|---|---|---|
| mini-swe-agent | 0.22% | 0.55% |
| OpenHands | 0.00% | 0.42% |
| SWE-agent | 0.55% | 0.94% |

- **Agreement on Qwen is much weaker than on JetBrains** (κ 0.45 vs 0.70).
  - The two annotators agree that non-distinct work is rare (6% and 5% of matched ops).
  - But they often pick *different* ops as non-distinct.
- **The candidate-redundancy rate is therefore reported as a range across annotators:** 0–0.9% of ops, at most about 1% in every harness.
- **The harness ordering is the same under both annotators:** SWE-agent highest, OpenHands and mini-swe-agent lower.
