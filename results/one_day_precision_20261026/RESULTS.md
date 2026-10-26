# One-day study: contribution precision in successful runs and outcome-matched effort

**Status:** route A, completed as a **model-coded feasibility pilot** plus a full saved-data analysis.
- **Labels:** made by one model annotator (Claude, single pass) and preliminary. Nothing here is human-validated.
- **Outcomes:** the dataset's recorded `resolved` field; no task tests were executed.
- **Readiness:** this is not evidence for a publication-ready claim.

## Question
Among successful runs on the same task under the same harness, how much of the performed work directly supports the accepted solution, and does that share differ between systems?

## Inputs actually used
- **JetBrains SWE-bench Pro trajectories,** pinned revision `a5ec6ad…`:
  - repeat 1 of Gemini 3.7 Flash and GPT-5.6 Luna under mini-swe-agent;
  - all 6,300 run records for the effort analysis.
- **SWE-bench Pro reference data,** revision `2d52cb3…`: issue text, requirements text, interface text, reference patch and fail-to-pass test ids.
  - 83 of 700 tasks have no reference row; 23 runs have an empty final patch (`availability.csv`).
- **Open-SWE-Traces v1.2 Task 5 sample** (Qwen3.8-27B; 2,000 tasks × 3 harnesses, one run each), used for the harness panel.
- **Local environment:** the repository at `/home/user/framework` with `.venv` (Python 3.12). Local substitutes for the brief's paths are recorded in `run.log`.

**Route decision (A):** full commands, outputs, final patches and accepted reference evidence are available locally. No task environment is available, so code state is read from the trace rather than executed.

## 1. Outcome-matched effort (saved data; 5,000 task-bootstrap replicates, seed 20261026)
Unit: recorded tool actions per run.

**Gemini 3.7 Flash vs GPT-5.6 Luna** (mini-swe-agent, repeat 1, 700 shared tasks):

| outcome cell | tasks | Gemini mean / median | Luna mean / median | paired mean diff [95% CI] | ratio of means [95% CI] |
|---|---|---|---|---|---|
| both succeed | 334 | 48.3 / 46 | 16.1 / 15 | **+32.2 [30.4, 33.9]** | **3.00 [2.90, 3.10]** |
| only Gemini succeeds | 88 | 56.1 / 52.5 | 18.1 / 18 | +37.9 [34.5, 41.5] | 3.10 |
| only Luna succeeds | 26 | 44.7 / 41.5 | 19.0 / 19 | +25.7 [17.0, 35.2] | 2.36 |
| both fail | 252 | 56.4 / 53 | 19.2 / 18 | +37.2 [34.9, 39.7] | 2.94 |

- **Repeats and aggregation:** the both-succeed difference is stable across repeat 2 (+32.7), repeat 3 (+32.2) and the task-level aggregate over successful repeats (+33.5, 387 tasks).
- **Model calls:** with the dataset's `api_calls` count, the ratio is 3.9–4.1.
- **Distribution:** Gemini uses more actions on 100% of both-succeed tasks. No zero denominators.

**Harness panel** (Qwen3.8-27B fixed; one run per harness per task):

| comparison | both succeed: tasks | paired mean diff [95% CI] | ratio of means | both fail: tasks | paired mean diff |
|---|---|---|---|---|---|
| mini-swe-agent − OpenHands (primary) | 940 | −12.6 [−13.8, −11.5] | 0.78 | 779 | −14.9 |
| mini-swe-agent − SWE-agent (secondary) | 1,005 | −13.3 [−14.6, −12.1] | 0.77 | 774 | −17.4 |

- **Source strata:** the gap holds in both. For mini − OpenHands on both-succeed tasks: Scale-SWE −9.9, SWE-rebench-V2 −17.8.
- **Packaging caveat:** the harnesses package calls differently (one editor change per call in OpenHands/SWE-agent), so these are differences in recorded interaction, not in productive work.

**Reading:** these numbers measure effort conditional on common success. They say nothing yet about redundancy or precision.

## 2. Contribution-precision pilot (model-coded)
**Sample:**
- **Population:** 306 of the 334 both-succeed tasks have usable context. The other 28 lack a reference row or a final patch.
- **Selection:** frozen in seeded random order (seed 20261026).
- **Split:** 3 calibration task pairs, then **8 evaluation task pairs (16 runs, 449 actions)**, all completed in order. No task was skipped or replaced.

**Labels:**
- **Coverage:** every executed action is labelled `direct`, `non_direct` (with a reason) or `uncertain`, with evidence spans and links to requirements and later actions (`action_annotations.jsonl`).
- **Requirements:** frozen per task as behaviours with permissible alternatives (`requirements.jsonl`).
- **Guide:** v1 was frozen after calibration (`annotation_guide.md`).

**Results, evaluation pairs** (`scores_by_run.csv`, `pilot_pairs.csv`, `pilot_summary.csv`):

| | Gemini 3.7 Flash | GPT-5.6 Luna |
|---|---|---|
| actions per run (mean) | 41.6 | 14.5 |
| direct actions per run (mean) | 12.6 | 6.6 |
| precision lower bound D/N, mean (median) | **0.30** (0.30) | **0.46** (0.50) |
| precision upper bound (D+U)/N, mean (median) | **0.33** (0.33) | **0.50** (0.50) |
| uncertain share, mean | 0.03 | 0.04 |
| precision excluding the submission action, lower–upper (mean) | 0.31–0.34 | 0.51–0.55 |

**Paired comparison (Gemini − Luna):**
- **Mean differences:** −0.16 on the lower bound and −0.17 on the upper bound.
- **Sampling uncertainty:** a task-bootstrap 95% interval for the mean lower-bound difference is [−0.25, −0.08]. This is illustrative at n = 8, and separate from the label bounds.
- **Per pair:**
  - In **7 of 8 pairs** Luna's precision is higher under every resolution of the uncertain labels.
  - In 1 pair (task 10) the order depends on the uncertain labels: lower bounds 0.33 vs 0.33.
  - Two-sided exact sign test on 7/8: p = 0.07.

**Where Gemini's extra actions go** (summed over the 8 pairs, `pilot_decomposition.csv`, `fig_effort_decomposition`):
- **Totals:** Gemini performs 217 more actions (333 vs 116).

| category | share of the extra actions |
|---|---|
| direct work | **22%** (101 vs 53 direct actions) |
| repeated support (re-reading or re-inspecting unchanged content) | 22% |
| unused context (relevant-area reads no surviving change relies on) | 20% |
| superseded checks (mostly pre-change baseline test runs) | 13% |
| administration (status, patch handling, tool setup) | 12% |
| negative detours | 5% |
| the rest | 6% |

- **By role:** Gemini performs more direct *verification* (35 vs 15 actions) and more direct exploration (48 vs 26). It also performs far more non-direct exploration (117 vs 18).

**Counterexamples and limits inside the pilot:**
- **Task 10:** equal lower bounds; Gemini's upper bound is higher (0.39 vs 0.33).
- **Task 3:** Luna's run never obtained a test result (two cut-off runs, U = 2), giving the widest interval in the set, [0.30, 0.50].
- **Task 8:** Gemini spent 9 actions trying to run GUI tests without a display. All failed for environment reasons; they are labelled superseded checks and administration.

**Failed-run extension (gate passed for one run only):**
- **Eligible run:** the only failure among repeats 1–3 on the 8 evaluation tasks is Gemini repeat 2 on task 10.
- **Reading:** a static reading of its final patch against the frozen requirements gives terminal `reference_requirement_coverage` **4/5 = 0.80**, or 2/3 counting repair requirements only.
  - It handles the per-server ignore-inactive setting but never removes the pointer indirection in `searchCache` (R1), consistent with the fail-to-pass `TestSearchCache` signature.
- **Not computed:** peak coverage and Q_failure. This is a case, not an estimate (`failed_run_coverage.csv`).

## What the pilot establishes and what it does not
**Feasible:** with full traces and a reference, every action of a successful run can be linked to concrete requirements or classified as non-direct with a reason. Unresolved labels are rare (3–4% of actions).

**Suggestive, not established:**
- **Higher precision for Luna.** On the same tasks, Luna's successful runs spend a larger share of actions on direct solution work (about 0.46–0.50 vs 0.30–0.33).
- **Effort alone overstates the gap.** It shows a 3× gap. The labels show Gemini also performs about 1.9× as many *direct* actions, especially more distinct verification. Only about 22% of its extra effort is direct work.

**Not established:**
- **Not a population difference.** n = 8 tasks, one annotator, and selection on joint success.
- **Not packaging-free.** Luna bundles several commands into 75% of its actions vs 14% for Gemini, and compound actions are credited by their strongest component. Part of the precision gap may come from packaging (`diagnostics.md` §3).
- **No causal claims:** nothing about necessity, or about what could be safely removed.

## Limitations
- **Annotators:** a single model annotator with no second reviewer, and no human labels.
- **Blinding:** weak, because run length reveals the model.
- **Outcomes and states:** outcomes are dataset-recorded, and code states are read statically, not executed.
- **Requirements:** made by the same annotator from the dataset's own requirement text and reference patch. Two tasks have reference/requirement conflicts (`diagnostics.md` §4).
- **Packets:** the original packets showed raw rather than agent-visible output for truncated observations; corrected in judging from task 05 (`diagnostics.md` §2).
- **State tracking:** the seven WorkTrace state-tracking probes still fail. No inferred-state result is used here.

## Next experiment
1. **Re-annotation:** a second, independent annotator (preferably human) re-labels the 8 evaluation pairs blind, using the frozen guide. Report agreement and adjudicated scores.
2. **Bundling sensitivity:** split compound actions into command segments where outputs can be separated, or restrict the comparison to single-command actions.
3. **Scale-up:** extend to the 295 reserve both-succeed tasks in frozen order, and add the harness panel (Qwen, mini-swe-agent vs OpenHands) on matched successful tasks.
4. **Failures:** run the failed-run extension on tasks with several failures, with executed tests in task containers, to measure terminal and peak coverage.

## Manuscript-ready paragraph (preliminary)
> On 334 SWE-bench Pro tasks that both solved under the same harness, Gemini 3.7 Flash used 3.0 times as many tool actions as GPT-5.6 Luna (48.3 vs 16.1 per task; paired difference +32.2, 95% CI 30.4–33.9). In a model-coded feasibility pilot of 8 randomly ordered task pairs (449 actions), each action was linked to explicit solution requirements or labelled non-direct. The share of actions directly supporting the accepted solution was 0.30–0.33 for Gemini and 0.46–0.50 for Luna, with bounds covering unresolved labels. Luna's share was higher under every label resolution in 7 of 8 pairs. Only about one fifth of Gemini's additional actions were direct; most were repeated inspections, unused context reads, superseded checks and administration. These pilot labels come from a single model annotator. They have not been validated by humans, and the per-action comparison is sensitive to differences in how the systems bundle commands.

## Files
**Data:**
- `availability.csv`, `sample_manifest.csv`
- `requirements.jsonl`, `action_annotations.jsonl`
- `scores_by_run.csv`, `pilot_pairs.csv`, `pilot_summary.csv`, `pilot_paired.json`, `pilot_decomposition.csv`, `pilot_direct_by_role.csv`
- `matched_effort.csv`, `matched_differences.csv`
- `failed_run_coverage.csv`, `failed_run_coverage_summary.json`
- `examples.json`, `bundling.csv`

**Figures** (`.pdf` and `.png`): `fig_matched_effort`, `fig_precision_bounds`, `fig_effort_decomposition`, `fig_trajectory_example`. The trajectory example is the median-gap pair, task 6, chosen by the rule declared in `examples.json`.

**Review material:** `packets/` (blinded, full), `packets_compact/`, `packets/blinding_key.csv`, `annotation_guide.md`.

**Process:** `diagnostics.md`, `run.log`, `manifest.json`, `status.json`.

**Reproduce:** `bash scripts/one_day_precision/run_all.sh`. No API, no downloads; writes only this folder.
