# Codex execution brief: one-day contribution-precision study

Work in `/Users/samuelthen/Desktop/framework`. Execute this brief through runnable analyses, evidence-linked outputs, figures, and a short report. Do not stop after proposing another plan. The goal is an informative result within one working day, with a successful-run contribution pilot if the inputs support it. A favorable model ranking or significant difference is not a completion requirement.

## 1. Scope and priority

Primary question: **Among successful runs on the same task under the same harness, how much performed work directly supports the accepted correct solution, and does that share differ between systems?**

Primary semantic comparison: Gemini 3.7 Flash versus GPT-5.6 Luna, under mini-swe-agent, on tasks where both selected runs succeed. Use dataset identifiers rather than guessing endpoint/model names. Treat saved `resolved` as the dataset's acceptance outcome; do not imply independent execution verification unless actually performed.

Produce the saved-data matched effort analysis in Section 6 regardless of whether semantic annotation succeeds. It gives a concrete result today and identifies what semantic precision must explain. Do not equate tool-call differences with redundant work.

Failed-run recall is an optional extension with a strict reference gate. Do not spend the day inventing gold solutions for failures. Do not launch fresh SWE-agent benchmark runs or a large annotation job. Existing matched traces are the priority.

## 2. Preserve the project and inspect known limitations

Read `AUDIT.md`, `paper/worktrace-draft/OUTCOME_CONDITIONED_PRECISION_RECALL.md`, `paper/worktrace-draft/READING_NOTES_TRACE_COMPLEMENT.md`, and applicable AGENTS.md instructions. Do not reset or discard existing changes. Preserve all existing results and label files.

Create `results/one_day_precision_20261026/` for this study and `scripts/one_day_precision/` for new scripts. Write a run log, package versions, source hashes, task/run selection manifest, and machine-readable completion status. Keep new preliminary results separate from the published-looking draft until the report is complete.

Use existing approved tools and runtimes. No new paid API or GPU workload is required. If no authorized model endpoint or second reviewer is available, continue with local computation and explicitly provisional Codex-coded examples. Do not claim independent human validation or run another model merely to manufacture agreement.

Useful runtime already checked:

```sh
PYTHONPATH=/private/tmp/worktrace-analysis-deps /Users/samuelthen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 your_script.py
```

This environment can read the Parquet files. Discover a working plotting environment; `/private/tmp/worktrace-paper-mpl` and `/private/tmp/worktrace-paper-deps` may contain prior dependencies. Record what actually works rather than assuming these temporary paths persist.

## 3. First 45–60 minutes: inventory and freeze the route

Inspect these verified files:

- `data/runs.parquet`: 6,300 runs, outcome, model, repeat, calls, and token/cost metadata. It does not retain issue text.
- `data/ops_compact.parquet`: 188,609 operations, IDs, kinds, targets, mixed-call flags, and computed facts. It does not retain full commands or outputs.
- `data/submissions.parquet`: final submission file lists and emptiness, not full patches.
- `results/v2/task5/runs_benchmark.parquet`: 6,000 fixed-Qwen harness runs, outcomes, calls, source shard and row, and reference-patch size metadata.
- `results/v2/task5/sample.csv`: selected task/harness/shard mapping.
- `viewer/index.html`: embedded `const DATA` JSON for 50 runs / 1,432 operations. Outputs are clipped to about 1,200 characters. Its `gold` field is a path list, not a correct solution or full patch.
- `data/labels/pilot_v2.jsonl` and `data/labels/qwen_pilot.jsonl`: old contribution/novelty labels. These are not ground truth for the new metric.

Discover full events/raw rows from the configured project paths, local dataset caches, and source files referenced by loaders. Read-only recovery of a small, selected public-data sample is appropriate if available. Do not bulk-download the entire benchmark. Inspect `worktrace/worktrace/loaders/jetbrains.py`, `worktrace/worktrace/loaders/openswe.py`, and download/sample scripts for the recorded dataset revisions. Inspect actual source schemas: reference-patch metadata may contain only file/line counts.

For each candidate run, inventory: issue text, complete commands/arguments, observations and truncation, outcome provenance, initial revision, code changes/final patch, accepted-reference availability, and whether code state can be checked. Record missing fields explicitly.

At the end of the timebox choose:

- **Route A:** sufficient full traces and accepted-solution evidence exist. Execute Sections 4–7.
- **Route B:** only compact records or clipped viewer traces exist. Execute Section 6 fully; produce an annotation packet and clearly limited case studies, but do not label a semantic contribution score as established. Write exactly which source rows are needed next. Do not wait indefinitely for unavailable data.

Both routes must end with actual tables, figures, a runnable command, and a report.

## 4. Successful-run contribution precision pilot

### Freeze the sample before judging contribution

Use seed `20261026`. For the primary pair, select repeat 1 for both models. If complete source recovery is impossible for repeat 1, define a deterministic earliest-complete-success rule before inspecting contribution labels, apply it symmetrically, and report the change. Never choose each model's shortest or most favorable successful trajectory.

Restrict to the same tasks with two accepted successful runs and usable context. Record how this availability/outcome selection changes the task population. Randomize tasks in a reproducible order. Use three tasks for calibration if available, then target eight different tasks / sixteen runs for evaluation. Complete whole task pairs in the frozen order before expanding. A smaller complete pilot is preferable to selectively finishing favorable cases. Report actual task counts; this is a feasibility sample, not confirmation of population prevalence.

If the primary pair has too few complete matched tasks, use one explicitly named alternate pair selected by input completeness before semantic labels are inspected. Do not search model pairs for a desired precision gap.

### Build a reference without prescribing commands

For each task, extract a small set of concrete requirements from the issue and accepted correct implementation evidence. Each requirement needs an ID, description, source citation, verification status, and permissible alternative implementations. Requirements are behavior/repair obligations, not the reference patch's exact lines, file paths, or tool sequence. Separate repair requirements from behavior already satisfied in the initial repository.

An accepted successful run provides evidence for one valid route, not an exhaustive specification of all correct solutions. Check its patch against the issue and mark unresolved requirements uncertain. If the available evidence cannot establish the requirement or solution, do not manufacture it.

Do not expose an expected command trajectory to the annotator. Hide model identity and previous automatic labels where feasible. Keep the task reference common across compared runs. Document any route-specific requirement.

### Annotate all performed actions in each selected run

Primary unit: native executed tool operation, matching the user's all-actions definition. Keep errors and unsuccessful attempts in the denominator. Document how non-executed finish signals, missing results, and submission operations are treated. Preserve compound-call groupings. Record a sensitivity analysis for mixed/bundled calls when a defensible common unit is available; otherwise keep the pilot within one harness and acknowledge the boundary.

For each action record:

`task_id, run_id, op_id, role, requirement_ids, contribution_label, contributed_content, evidence_spans, downstream_support, relevant_state, survives_to_final, uncertainty_reason, annotator_provenance`.

Labels: `direct`, `non_direct`, `uncertain`.

- `direct`: the visible action establishes a concrete solution-bearing observation, implements a valid requirement, or checks a defined property that supports the accepted solution. Cite the observed content and its support link. Relevance to the right file alone is insufficient.
- `non_direct`: no direct solution contribution under the frozen guide. Under the user's definition, negative-only searches through irrelevant files receive no direct credit. Keep a reason category such as negative detour, discarded edit, administration, or repeated support.
- `uncertain`: the context, downstream link, state, or requirement cannot be established. Missing evidence is not proof of non-contribution.

Resolve on calibration tasks how repeated support, checks of distinct properties, useful intermediate edits, reversions, and scaffolding receive credit. Apply the same rule to both systems. Do not automatically credit every successful test or every edit in a successful run. Do not infer causal necessity merely from a plausible support link.

Freeze the guide before evaluation. Keep old `distinct/non_distinct` labels hidden and never relabel them mechanically as `direct/non_direct`. If Codex performs the coding, record it as model-coded and preliminary. A second pass by the same model is a consistency check, not an independent human reference.

### Compute scores with uncertainty visible

For each run let N be all denominator actions, D the directly contributing actions, and U the uncertain actions. Export:

- lower bound = D/N;
- upper bound = (D+U)/N;
- uncertain share = U/N;
- direct labels by exploration/edit/verification role.

These bounds concern unresolved label assignment; they do not cover errors in apparently certain judgments. Do not report a single precise score while silently dropping U. If a complete adjudicated reference exists, also report the resolved D/N point score with its provenance.

Compute paired per-task model differences and task-level uncertainty only on the actual evaluation set. On a tiny pilot emphasize pair distributions and cases, not significance. Report mean, median, and each task pair. Keep sampling uncertainty separate from annotation uncertainty. Show success rate and sample selection beside conditional precision.

## 5. Failed-run extension: run only if the gate passes

For a failed run require an independent accepted correct solution or executable task requirements. A failed patch and an LLM-invented answer do not pass this gate. A successful solution to the same task can support a reference-conditional assessment, but allow valid alternatives and record limitations.

Use only failure cases already associated with the sampled tasks. Check requirements against the failed run's actual code state; inspecting or mentioning a requirement does not achieve it. Units must be valid together at the endpoint. Unknown state yields unknown coverage. Report initial, peak if recoverable, and terminal coverage separately.

For K reference requirements, H achieved and U_req uncertain, export coverage bounds H/K and (H+U_req)/K. Call this `reference_requirement_coverage`; discuss its recall interpretation only within this reference. Do not call useful failed actions divided by all actions recall: that is Q_failure, a contribution density.

If references or reconstructable states are missing, export `recall_status=not_identifiable` with reasons and continue. Do not block today's successful-run experiment.

## 6. Guaranteed saved-data analysis: outcome-matched effort

Implement a new reproducible analysis using the saved run tables. It should not require semantic labels or inferred code-version graphs.

For the model panel:

1. Primary comparison Gemini versus Luna under mini-swe-agent, using repeat 1.
2. Partition shared tasks into both-success, first-only-success, second-only-success, and both-failure. Unknown outcomes remain separate.
3. Report number of tasks, mean/median calls, paired mean/median call difference, and call distributions in every cell. Do not conflate differences between outcome cells with causal effects.
4. On both-success tasks report paired action differences and descriptive ratios; handle zero denominators explicitly. This measures effort conditional on common success, not redundancy or semantic precision.
5. Sensitivity: repeat 2 and repeat 3 separately, plus task-level aggregation of successful runs, keeping each denominator and eligibility definition explicit. Do not treat repeated runs of one task as independent tasks.

For the harness panel use Qwen fixed, mini-swe-agent versus OpenHands as the primary pair, with SWE-agent as a reported secondary comparison. Apply the same four-cell analysis. Native-call packaging differs across harnesses: interpret call counts as recorded interaction effort, not a normalized count of reasoning or productive actions. Record source-dataset strata as a sensitivity check.

Use 5,000 task-bootstrap replicates, seed `20261026`, and 95% intervals for broad saved-data contrasts. Report the paired estimates even if intervals include zero. On the semantic pilot, report uncertainty appropriate to its small sample. Do not create post-hoc task groups until the fixed primary outputs are saved.

Connect this analysis to the pilot: select explanatory examples using a declared rule such as median-gap and disagreement cases, not only the largest favorable gap. Compare conclusions available from effort alone against conclusions enabled by contribution links. If semantic labels are unavailable, stop that interpretation at recorded effort.

## 7. Reliability work: bounded, relevant, and transparent

Run these separately from the repository root:

```sh
python3 audit/reproduce_reliability.py
```

```sh
PYTHONPATH=worktrace python3 -m pytest worktrace/tests
```

The seven audit checks are currently expected to fail. If your scoring uses inferred states, spend at most about 90 minutes repairing the relevant failures in parser/facts/versions and add meaningful regression coverage. Priorities are false content equality, hidden writes, branch changes, and failed/partial restores. Preserve uncertainty on incomplete observations.

Passing the seven probes does not validate every real trace. If state reconstruction remains unreliable, use directly inspected evidence for the small pilot, mark unverifiable states uncertain, and keep automatic version claims out of the new results. The Section 6 analysis should proceed regardless.

Do not spend the day rebuilding every historical graph or fixing unrelated infrastructure. Do not execute shell commands copied from trajectories on the host machine. If actual task tests are needed, use the task's isolated environment and inspect the test commands and setup first.

## 8. Required deliverables

Within `results/one_day_precision_20261026/`, produce:

1. `availability.csv`: trace/reference/state completeness and reasons for missingness.
2. `sample_manifest.csv`: frozen task/run IDs, split, selection order, outcome, and exclusions.
3. `requirements.jsonl`: actual accepted requirements if available; otherwise a schema plus explicit availability status, not invented entries.
4. `action_annotations.jsonl`: evidence-linked pilot labels with honest provenance; keep unfilled review material separate.
5. `scores_by_run.csv`: P bounds and uncertainty; optional Q/coverage only where supported. Missing scores must remain null with reasons.
6. `matched_effort.csv` and `matched_differences.csv`: both comparison panels, outcome-cell counts, and uncertainty.
7. `diagnostics.md`: annotation disagreements/unknowns, bundling, alternative fixes, lost progress, and test outcomes actually checked.
8. Standalone scientific figures: outcome-matched effort; contribution precision bounds if available; one readable trajectory-to-requirement example; optional coverage curve if verified. Export PDF and PNG with sample sizes and clear units. Inspect the rendered figures.
9. `RESULTS.md`: question, actual inputs, exact estimates, what the pilot establishes, counterexamples, limitations, and next experiment. Separate descriptive results from hypotheses and causal claims. Include one short manuscript-ready results paragraph with no unsupported numbers.
10. `manifest.json`, `run.log`, and `status.json`: hashes/versions, commands, completed/partial/blocked status per deliverable, and exact missing inputs or human review.

Provide a single documented command to reproduce all completed analyses without silently invoking an API, downloading data, or overwriting earlier results. Separate optional acquisition, annotation, and sandboxed test execution commands. Add meaningful tests for score denominators, unknown bounds, task matching, and state-sensitive achievement; do not add vacuous implementation-mirroring tests.

## 9. Time allocation and stopping rule

- First hour: availability inventory, choose Route A/B, freeze primary analysis.
- Next 1–2 hours: implement saved-data comparisons and contribution scorer/schema; repair only relevant state failures.
- Next 3–4 hours: recover and annotate the small pilot if feasible; complete task pairs in order. Produce the review packet without waiting for a human response.
- Final 1–2 hours: baseline comparison, figures, checks, report, and runnable delivery.

Continue autonomously through recoverable local failures. If a reference or human reviewer is unavailable, finish unaffected deliverables and explicitly label the corresponding scientific claim unvalidated. No fabricated annotations, outcomes, or missing-source substitutions.

The final response must state: what actually ran, the strongest supported numerical result, whether semantic precision was measured or only prepared, whether failed coverage was identifiable, the main limitation, and links to outputs. Do not claim ACL readiness from a one-day pilot.
