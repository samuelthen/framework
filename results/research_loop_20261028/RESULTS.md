# Research-loop results — 28 October 2026

The study now has two substantive measurement findings, executable property validation, and a complete controlled DeepSeek pilot. It has **not** established a universal redundancy score or safe suppression policy. The paper's strongest current story is how measurements change model comparisons and which cost claims remain unresolved.

## Evidence added

| Evidence | Completed scope | Main result |
|---|---|---|
| Archived model analysis | 2,100 runs; 700 tasks × three configurations | 61,769 native calls, 110,354 candidate components, 54,350 stored responses |
| Frozen model confirmation | 30 matched all-attempt tasks | Gemini/Luna call ratio 3.21 becomes 1.20 for candidates; reported output ratio remains 11.28 |
| Third-model extension | Terra on the same tasks | Call ratio to Luna 1.16; candidate ratio 1.06, with interval including one |
| Attribution sensitivity | Exact response totals; full-run residuals retained | Both category-share orderings are feasible for exploration, edit and explicit verification |
| Cross-harness decomposition | Existing 6,000-run Qwen table; frozen 30-task subset | OpenHands' 6.7-call gap includes 5.67 edit calls; this does not prove redundant edits |
| Independent scoped checks | All five Flipt tasks in the frozen panel; four snapshots each | Reference 5/5; archived agent patches 3/10 in exact context; build and test failures separated |
| File interventions | Four leave-one-source-file-out checks | Three file groups necessary for the checker; one has no detected loss under it |
| Revised DeepSeek study | 18/18 completed; three snapshots × three arms × two decodes | Same production patch per snapshot in every arm; local cache time saving, no observed quality difference |

## Finding 1: the counting unit changes the model comparison

On the frozen 30 tasks, Gemini averages **54.83 native calls** versus Luna's **17.10**. Their ratio is **3.21 [2.82, 3.59]**. Decomposition gives **60.07 versus 50.10 candidate components**, a ratio of **1.20 [1.04, 1.37]**. Nine task-level orderings reverse. These are requested work components, not independently proven executed actions.

Reported output tokens still differ by **11.28 [9.62, 13.05]**. Removing administrative candidates does not erase the component gap. Joint-success and repository sensitivities preserve the main counting-unit result. This supports a concrete explanation for part of the apparent call-effort gap: different packaging of work. It does not establish equal compute or equal usefulness.

## Finding 2: response telemetry does not identify role-level cost rankings

For exploration, an equal split suggests Gemini has a larger output-expenditure share. However, feasible accounting that preserves the same observed response totals gives a mean full-run difference of **−5.6 to +46.4 percentage points**. Edit spans **−30.9 to +23.8**, and explicit verification **−15.2 to +8.8**.

These are allocation bounds conditional on the operational categories, not sampling confidence intervals. `allocation_witness.jsonl` constructs opposite assignments while conserving each response. It does not reconstruct actual reasoning tokens. Only **1,843/2,100** runs reconcile all three token fields; unlocalized residuals remain visible.

A concrete baseline sensitivity strengthens the result: weighting components by their available command-token length reverses the edit-share comparison, from **Gemini − Luna = +4.8 points under equal splitting to −19.0 points**. Both allocate the same recorded totals. Available reasoning text is also unequal: 0/396 Luna responses, 1,641/1,641 Gemini responses, and 0/387 Terra responses expose it. Retokenized available text is therefore a coverage-dependent baseline, not a substitute for reported usage. See `text_baseline_summary.json`.

## DeepSeek intervention pilot

The Soc alias `x-test-2` returned model ID `deepseek-v4.1-flash-1017`. The user selected DeepSeek before continuation episodes. The revised study uses the same snapshots as the first pilot, a visible candidate diff, eight equal-budget calls, and copy-on-write private work/cache snapshots.

| Arm | Initial public-check time, mean | Input tokens, mean | Output tokens, mean | Exact scoped pass | Fixture-complete pass |
|---|---:|---:|---:|---:|---:|
| Fresh | 2.152 s | 83,712 | 2,258 | 4/6 | 6/6 |
| Cache | 0.057 s | 73,068 | 1,821 | 4/6 | 6/6 |
| Bypass | 0 s | 65,017 | 2,206 | 4/6 | 6/6 |

There are **139 requests with complete returned usage**: **1,330,779 input tokens and 37,712 output tokens**. Cached input and reported reasoning remain separate details. Monetary cost is unknown, even though the user describes Soc access as free.

Only four episodes submit; the others reach the call limit. All final production patches are identical within a snapshot. This does not demonstrate a quality gain from any arm. It also cannot prove equivalence across tasks. Token means are descriptive over three chosen snapshots, with schedule/server-cache effects. The initial cache fill and public compiled-cache setup costs are excluded from the warm-cache arm difference and retained separately. The fresh command bypasses Go test-result caching with `-count=1`; build caching stays enabled.

## What the failed loop taught us

The first four-call pilot is fully retained: 18 scheduled cells, 48 API attempts, six disk-reserve blocks, one additional grading gap, and no balanced valid outcome comparison. These are protocol defects, not agent failures. The revised pilot closes those execution gaps.

The grading audit also found that the readonly task's updated test requires a fixture absent from the candidate checkout. Exact grading fails; supplying reference testdata equally to candidates passes. Both contexts remain reported. A test's dependence on omitted setup must not be presented as universal evidence that a repair is wrong.

## Remaining scientific gap

The broad “measure utility of every exploration and verification action” claim is still not supported. The evidence now supports a narrower measurement paper. The token-weighted sensitivity compares a concrete attribution assumption, but it does not reproduce the closest cost study's full downstream charging model. Broader executable repositories and a careful closest-method comparison remain necessary for a confident submission-readiness judgment. No additional label or equation closes those empirical gaps.

The user chose executable validation instead of human review. We therefore make property-level claims where execution is available and retain semantic uncertainty elsewhere. Archived model-coded labels are not converted into accuracy ground truth.

## Review artifacts

- [Full paper draft](../../paper/worktrace-draft/WORKTRACE_MEASUREMENT_PAPER_20261028.md)
- [Measurement figure](figures/measurement_findings.png) and [DeepSeek figure](figures/deepseek_pilot.png)
- [Frozen plan](analysis_plan.json), [amendments](analysis_amendments.md), and [research log](RESEARCH_LOG.md)
- [DeepSeek v2 plan](live_v2/plan.json), [analysis](live_v2/analysis.json), and [grading sensitivity](grading_audit/outcomes.json)
- [Reproduction instructions](REPRODUCE.md)

Software validation: **207 tests pass**, and the claim audit verifies the live backend identity, all 18 final production snapshots, frozen sample arithmetic and attribution conservation. These regression checks are not additional benchmark tasks.
