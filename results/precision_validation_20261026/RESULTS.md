# Eight-pair contribution measurement validation

**The original model ranking is not established by this validation.** Correcting the action unit materially changes the comparison, and independent component judgments still disagree. The outputs now expose both sources of uncertainty rather than presenting a single precision ranking.

## Work completed

- Reused the same eight evaluation tasks (orders 03–10), 16 recorded-success trajectories. No larger dataset or new graph design was added.
- Corrected command counting and decomposed compound calls without spreading whole-call credit to every part.
- Reviewed requirements, alternative implementations, existing behavior to preserve, and conflicting references.
- Completed two blinded component annotation passes, B and C, on the same canonical inventory. Each pass used two Codex workers covering disjoint task groups. C used the frozen reviewed requirement sheets; neither pass saw the other contribution labels or the model key. Original Claude call labels remain preserved.
- Recomputed component/native sensitivities, contribution and verification precision, paired differences, reviewer agreement and baseline diagnoses. All roles use `direct / non_direct / uncertain`; reasons are separate.
- Fixed the seven audit regressions. **102 project/study/validation tests and all 7 audit probes pass.** Rebuilt only the 16 pilot default graphs/facts into a separate directory.

All annotation is model-coded. These are independently blinded worker passes, not independent human or independent model-family validation. No task environment or patch test suite was re-executed.

## Units and counting

| System | Native calls | Candidate components | Mean components/call | Multi-component calls |
|---|---:|---:|---:|---:|
| gemini-3.7-flash | 333 | 391 | 1.17 | 9.0% |
| gpt-5.6-luna | 116 | 378 | 3.26 | 86.2% |

The original regex counted separators inside quoted programs. The new decomposition respects quotes, heredocs and substitutions, groups pipelines/control flow, attaches directory context, and keeps malformed shell as one opaque attempted action. `bash -n` checks syntax only and does not execute commands. Inline programs/test suites can still contain several activities; these units are pragmatic, not fully packaging invariant.

Each pass covers **769 candidate components**, from 449 native calls. Reviewers separately judge execution. Conservative reconciliation excludes a candidate only when both mark it not executed: 13 excluded, 688 established executions, 68 uncertain executions. Unknown execution retains contribution uncertainty; it is not silently counted as certainly productive or omitted.

## Contribution precision

For each run, lower = D/N and upper = (D+U)/N. The table averages run bounds over the eight matched tasks. These bounds concern unresolved labels/execution, not errors in apparently certain judgments.

| Annotation version | Gemini mean bounds | Luna mean bounds |
|---|---:|---:|
| Pass B | 44.7%–53.4% | 36.2%–50.8% |
| Pass C | 38.3%–47.8% | 32.9%–47.4% |
| Conservative cross-review bounds | 34.0%–59.5% | 31.1%–54.9% |

The conservative mean paired Gemini-minus-Luna difference ranges from **-20.9 to +28.4 percentage points** under unresolved judgments. Its exploratory task-bootstrap envelope is [-23.7, +38.7] points (5,000 task resamples; seed 20261026). Eight-task sampling and annotation accuracy remain separate limitations.

Reconciliation preserves equal judgments; conflicting contribution/execution judgments become uncertain. Verification-role disagreement also becomes uncertain and is included in the candidate verification denominator. Certain direct agreement requires at least one shared requirement ID. This is a conservative sensitivity, **not semantic consensus or a gold reference**. Individual passes and every disagreement remain available.

The reconciled included labels are 233 direct, 320 non_direct and 203 uncertain.

Unit choice can be isolated within pass B, holding its component judgments fixed:

| Unit | Gemini mean bounds | Luna mean bounds | Pairs |
|---|---:|---:|---:|
| native_strongest_component_sensitivity | 47.3%–55.5% | 58.2%–72.5% | 8 |
| components | 44.7%–53.4% | 36.2%–50.8% | 8 |
| components_excluding_submission_calls | 46.8%–51.8% | 38.9%–47.5% | 8 |
| single_component_calls | 50.6%–55.8% | 40.3%–44.4% | 6 |

The native strongest-component rule favors bundling. It is retained only as a sensitivity, not used to assign component labels. The single-component analysis has only six complete pairs and 16 Luna calls, so it is selective and imprecise. Neither component counts nor precision alone establish time/token savings or the quality of an internal search heuristic.

## Reproducibility

| Comparison panel | Components | Label agreement | Cohen κ | Role agreement |
|---|---:|---:|---:|---:|
| all_candidates | 769 | 85.8% | 0.759 | 94.9% |
| executed_by_both | 688 | 84.9% | 0.715 | 94.8% |
| both_assessable_executed | 655 | 86.3% | 0.722 | 94.5% |

There are 109 contribution disagreements, 39 role disagreements and 13 execution disagreements; these categories overlap. `component_disagreements.csv` includes both requirements/evidence/reasons. No uncertainty is dropped to inflate agreement.

For historical context only, the original Claude call labels and pass B projected to native calls agree 67.9% (κ 0.446). That comparison mixes guide and unit changes and is not a clean component reproducibility estimate. The two component passes are the relevant new check, but shared model/requirement/parser biases can still survive their agreement.

## Verification precision

Verification has exactly the same contribution labels. The following table pools verification candidates; per-run means are also exported. Reasons distinguish repeated support, missing/no-result checks, unrelated properties, defects used in repair and justified additional confidence.

| Version/system | N | Direct | Non-direct | Uncertain | Precision bounds |
|---|---:|---:|---:|---:|---:|
| B: gemini-3.7-flash | 87 | 39 (44.8%) | 35 (40.2%) | 13 (14.9%) | 44.8%–59.8% |
| B: gpt-5.6-luna | 62 | 42 (67.7%) | 7 (11.3%) | 13 (21.0%) | 67.7%–88.7% |
| C: gemini-3.7-flash | 91 | 42 (46.2%) | 31 (34.1%) | 18 (19.8%) | 46.2%–65.9% |
| C: gpt-5.6-luna | 63 | 38 (60.3%) | 13 (20.6%) | 12 (19.0%) | 60.3%–79.4% |
| Cross-review: gemini-3.7-flash | 91 | 35 (38.5%) | 26 (28.6%) | 30 (33.0%) | 38.5%–71.4% |
| Cross-review: gpt-5.6-luna | 66 | 34 (51.5%) | 5 (7.6%) | 27 (40.9%) | 51.5%–92.4% |

Passing or issuing a different command never automatically establishes direct contribution. Role disputes are retained, because distinguishing task verification from administration affects this denominator. These rates do not show that suppressing checks preserves correctness; no stopping intervention was performed.

## Requirements and alternative fixes

- **03:** cancellation/deadline/auth propagation are repairs; unrelated behavior is preservation. Context fallback and pre-existing status handling require scoped evidence, not blanket accepted-outcome credit.
- **04:** explicit configuration-key loading is clear. The absent-update-key false requirement conflicts with preserving Default() true in the issue/reference. Both branches remain explicit and disputed.
- **05:** lifecycle-to-liveness mapping and its single update path are repairs; existing initialization and change-only emissions are preservation. Missing or failed test execution is not proof of that behavior.
- **06:** distinguish enum/schema changes from each evaluation outcome. Broad ErrNotFound handling can misclassify later store errors; generated-file changes alone do not prove outcome semantics.
- **07:** filesystem/zip behavior and cache keys matter, not one exact implementation. Python compatibility and the missing-directory assertion-message failure are separately recorded.
- **08:** tab command/provider/docs migration is repair; tab selection/count/window logic already exists. Source-boundary instructions and an unchanged configuration binding leave a scope conflict.
- **09:** require the pure `_sort_values` helper, not the broad unrelated observations migration in the reference.
- **10:** per-server settings/direct map use are repairs; Status filtering and presence signaling already exist. Global override precedence and legacy pointer compatibility require separate treatment.

These are reviewed model-coded requirements. Conflicts unsupported by available sources are not invented away. Recorded benchmark success is not independent verification that every listed requirement is satisfied.

## Baseline diagnoses and inspected examples

Exact-repeat, target-revisit and saved novelty labels are compared at the shared native unit. `reconciled_baseline_comparison.csv` reports coverage and uncertain cases separately; the novelty baseline covers only the 333 Gemini calls here. Common-coverage results are separate. Apparent precision/recall is agreement with model-coded contribution, not accuracy against human truth.

Concrete inspected cases (B/C judgments are shown so disagreement is visible):

| Component | Diagnosis from trace | B | C |
|---|---|---|---|
| 04:Y000.c3 | Configuration grep supplies missing-field/key observation; markers/file inventory in same call do not. | direct | direct |
| 04:X027.c0 | Cached config suite repeats X019 after binary cleanup, with no new relevant code/property. | non_direct | non_direct |
| 07:Y021.c0 | Zip missing-directory check exposes assertion-message TypeError and motivates Y022 repair. | direct | direct |
| 09:X009.c0 | Passing ratings test predates the sorting helper and does not check required ordering. | non_direct | non_direct |

The four examples illustrate attribution/property/state diagnoses unavailable from count totals alone; they are not a population-level claim of framework accuracy. Every baseline counterexample is exported. Different commands and revisits can contribute; passing novelty can still be unrelated.

## State repairs and evidence links

Repairs preserve unknown effects alongside known paths, invalidate state on branch changes, track multiple parsed mutation targets, reject failed/ambiguous restores, retain unknown dirt after partial restores, and retain stash dirty paths. Status and plain diff text cannot prove complete repository identity, including staged/untracked/truncated content, so text-based reanchoring/merging was removed.

Among the 16 rebuilt default pilot graphs, two version counts change and one old apparent backtrack disappears. Ten compact fields differ; this is not a count of all changed state facts. The remaining historical corpus and old labels retain pre-repair facts. Graphs remain heuristic reconstructions even after the seven probes pass.

`scoped_links.json` records three manually inspected restore/defect/repair relationships with specific scope. `evidence_links.jsonl` preserves reviewer references without inventing their causal direction. No new progress curve or claim about safely removable actions is asserted.

## What the paper can say now

The existing pilot is now a reproducible validation attempt with corrected units, reviewed requirements, two blinded component passes, disagreement bounds and baseline examples. The useful result is that unit choice and attribution reliability materially affect a system comparison. Do not reuse the original precision ranking as a validated measure of heuristic quality.

Before scaling or claiming two substantive model/harness findings, resolve the most consequential disputed requirements/labels with an independent expert and acceptance evidence. Human validation is still missing. Failed-run recall is deferred until requirements and assessable final states pass that gate; no dataset-wide recall or safe-stopping result is promised.

Suggested manuscript paragraph:

> We re-examined eight matched successful task pairs using 769 candidate work components from 449 native calls. Two blinded model-coded annotation passes agreed on 85.8% of component contribution labels (Cohen κ=0.759). Holding one pass's judgments fixed, replacing strongest-component call credit with separate component credit changed the model comparison. Conservative cross-review bounds did not establish a model ranking. The results support treating action granularity and attribution reliability as measurement requirements; they do not establish human-validated efficiency or safely removable verification.

## Reproduce

```bash
bash scripts/precision_validation/run_all.sh
```

Uses local raw shards and saved reviewer files. No downloads, labeling API jobs or task-command execution are hidden in the command. Historical results and manuscript are preserved. See `manifest.json`, `run.log`, `status.json`, `component_review_status.json`, `audit_checks.txt` and `test_results.txt`.
