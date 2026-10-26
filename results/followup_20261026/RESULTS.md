# Follow-up work: restore scope, adjudication and experiment preparation

The two restore cases are repaired and regression-covered. The disagreement review and repeated-support screen are complete as model-coded analyses. The four scientific experiments are **not all completed**: human reference judgments and configured target execution backends are still missing. No accuracy, confirmed system ranking, property-saturation result or live cost reduction is invented for these gaps.

## Completed repairs

- `git checkout .` cannot erase untracked or staged changes in the graph. Restores now require initial complete tracked-path evidence and a clean baseline; absent evidence keeps state uncertain.
- Index/HEAD mutations invalidate restore assumptions. Known-write sensitivity graphs also preserve that uncertainty. `final_is_initial` explicitly distinguishes root identity from an uncertain placeholder node.
- Regression checks include real Git repositories created in temporary directories. Only test-authored commands are executed there; no dataset trajectory commands are executed.
- **127 project/study/follow-up tests pass**, plus the seven original audit probes and three restore-scope probes (the third is a supported positive restore control).
- Rebuilt 16 pilot graphs separately; 2 version counts change relative to 8da1f1a. See `restore_scope_graph_delta.csv`. Historical results/labels are preserved, not silently regenerated.

## Consequential disagreements and expert validation

- Ranked every disputed component by its potential equal-task bound-width effect, with separate exploration and verification priority queues. Fixed-denominator weights are review priorities, not estimates of changes when execution/role denominators change.
- Inspected the 12 highest-impact assessable label disagreements against visible outputs and earlier reads. `model_review_decisions.json` records proposed judgments and trace citations. These are model-coded adjudication proposals and do not replace the independent reference.
- The review distinguishes location-only searches, formatting without demonstrated repair, unchanged rereads, useful baseline characterization and documentation-scope uncertainty. Seeing a line in the final patch is insufficient by itself.
- Prepared a blinded 30-case expert packet: up to two available high-impact disagreements plus two random agreement controls per task, with full anonymous tool histories/final patches and raw task references. Task 09 has no contribution-label disagreements, so its two missing disagreement slots are not invented. Separate blank forms support independent requirement review and all 769 component judgments.
- Current accepted human requirement tasks: 0; valid human case judgments: **0**. Accuracy is not computed. The 30-case sample is enriched and cannot establish population accuracy.
- Prepared paired derived-state-aware/withheld annotation inputs with identical raw context. Withholding computed state features does not prevent a reviewer from inferring state from edits. Neither ablation has been labeled/scored against a human reference yet. Controlled synthetic challenges also cover equivalent call packaging, residual opaque granularity, alternative valid fixes and verification before/after relevant edits; these are fixtures, not additional empirical results.

## Equal-run exploration and verification precision

These reproduce the archived two-pass labels and the existing role-reconciliation convention. Bounds are annotation bounds, not confidence intervals. Complete paired tasks are equally weighted; pooled shares are in separate columns. Non-verification role disputes still inherit B in the historical reconciliation, which is an additional limitation of exploration estimates.

| Model | Exploration | Verification |
|---|---:|---:|
| gemini-3.7-flash | 40.3–62.7% | 38.8–71.4% |
| gpt-5.6-luna | 61.3–72.8% | 53.9–91.5% |

## Isolated verification diagnoses

One contribution enum is retained: `direct / non_direct / uncertain`. Reason categories are explanatory fields, not replacement labels. Counts below are a conservative **model-coded screen**, not an expert measure of over-verification. Shared parent-output environment cues may mix component causes.

| Model | Supported repeated-support screen | Other non-direct categories | Uncertain verification |
|---|---:|---:|---:|
| gemini-3.7-flash | 12 | 14 | 30 |
| gpt-5.6-luna | 3 | 2 | 27 |

A supported repeat requires non_direct reconciliation, both reviewers calling repeated support on unchanged relevant state, a common earlier check judged direct by both, and no environment cue. Environment/setup failure candidates, unrelated checks, other non-direct work and unconfirmed repeats stay separate in `verification_reason_audit.csv`. No passing/different command automatically earns direct credit.
The normalized-property/state review form and coverage-curve computation are implemented. No property saturation curve is reported yet: zero normalized expert scope records are approved. A flat curve would not by itself prove non-contribution, because justified confidence can be direct.

## Confirmation panels frozen

| Panel | Shared non-development tasks | Joint-success eligible | Initial samples |
|---|---:|---:|---|
| cross_model | 689 | 323 | 30 all-attempt + 30 joint-success tasks |
| cross_harness | 2000 | 902 | 30 all-attempt + 30 joint-success tasks |

The attempt samples do not condition on outcome. The semantic samples explicitly condition on joint success; they are different target populations and must not be combined as an unconditional success estimate. Original calibration/evaluation tasks are excluded. Reference-patch-size quartiles provide the independent demand proxy. These are fresh to contribution-pilot annotation, not unseen by all older aggregate/novelty analyses.
`confirmation_saved_effort.csv` and `confirmation_paired_effort.csv` report archived success/interaction effort and paired task intervals only. They are not new semantic confirmation or new benchmark episodes. Contribution labels/reference validation are pending. Thirty tasks is a starting workload, not a power guarantee; freeze any expansion/stopping method before confirmation decisions.

## Self-loop control prototype

Implemented unrestricted, simple check-count-cap and property/state-aware controllers. The intervention is **suppress a dedicated check while continuing the agent**, not terminate the run. Mixed calls are ineligible for automatic partial suppression. The state-aware API accepts no final patch or future contribution labels, requires a complete assessed runtime content snapshot, and permits work when property/state/determinism is unknown. New properties and relevant edits reset the loop criterion.
Thresholds k=1,2,3 have logic regression tests, not live utility results. No threshold/cap is selected. Docker is available (29.8.1), but selected-task adapters and target Gemini/Luna/Qwen backends are not configured. The existing annotation proxy is not treated as evidence of those target systems. No live episodes or new paid API jobs were run; cost/success/non-inferiority are unmeasured.
The full four-experiment protocol is in `experiment_protocol.json`. Experiments 1–3 support the framework/behavior story only after their human/annotation gates pass. Experiment 4 is the separate actionability test; no safe stopping claim follows from this screen. Failed-run recall remains deferred.

## Reproduce and supply the missing inputs

```bash
bash scripts/followup/run_all.sh
```

No download, model call or live task execution is hidden in this command. Filled expert forms are preserved. Start with `expert_blind/README.md`, requirement_reviews.jsonl and judgments.jsonl. To execute the later live study, provide target-system/harness configuration and task environments after expert calibration. Original results remain under `precision_validation_20261026/`.
