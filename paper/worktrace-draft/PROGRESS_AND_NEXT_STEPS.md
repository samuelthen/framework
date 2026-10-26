# Follow-up experiments: contribution measurement and agent behavior

Updated 26 October 2026. The prior plan is preserved in
`results/followup_20261026/prior_experiment_plan.md`. The Mac-local review and
updated plan quoted by the user were not present in this checkout; the pasted
instructions supplied the new scope.

## Completed local work

See `results/followup_20261026/RESULTS.md` and `status.json` for actual results.
The original eight-pair outputs remain preserved under
`results/precision_validation_20261026/`.

- The 8da1f1a pilot has 769 candidates from 449 calls and two blinded model-coded
  passes. No overall model ranking or human accuracy is established.
- The two additional restore cases now have real-Git regression coverage:
  untracked files and staged edits survive worktree checkout. Restores require
  explicit baseline scope evidence; missing information remains uncertain.
- Consequential disagreements are prioritized separately for overall,
  exploration and verification precision. Twelve proposals were reviewed against
  concrete trace evidence; these are model-coded, not human adjudication.
- A 30-case blinded expert packet and full 769-component blank review form are
  prepared. No human judgments are supplied yet.
- Equal-run role precision reproduces the user's quoted values. Supported repeat
  candidates are separated from environment/setup failures and unrelated checks.
- Thirty-task attempt and joint-success semantic samples are frozen separately
  for the cross-model and cross-harness panels. Archived effort is computed;
  semantic confirmation has not been completed.
- Paired state-aware/derived-state-withheld inputs and prefix-only control
  prototypes are implemented. No live control experiment or cost saving is claimed.

## 1. Validate contribution annotation

Use the eight development task pairs. An independent expert first reviews raw
requirements/reference evidence, permits alternative valid fixes and resolves
or explicitly retains source conflicts. The expert then labels components
without seeing existing judgments or derived state facts. Preserve disagreements,
uncertainty, execution status, requirement links and evidence. Freeze the guide
only after this calibration/adjudication.

Start at `results/followup_20261026/expert_blind/README.md`. The initial 30 cases
contain up to two available high-impact disagreements and two random agreement
controls per task. Task 09 has no label disagreements; no cases were invented.
This enriched feasibility sample does not estimate population accuracy. Full
review forms for all 769 units are also provided. Empty/model-coded entries are
never accepted as human ground truth.

Against that independent reference, compare exact repeats, target revisits,
existing novelty labels and the same contribution annotator with explicit
computed state information withheld. Native-call totals are an effort baseline,
not a binary action classifier. Both ablation arms retain the same raw chronology,
issue and final patch; the withheld arm can still infer state from visible edits.
Include equivalent split/merged work, alternative valid fixes, and checks before
and after relevant edits. Do not score an unrun ablation or model self-agreement
as expert accuracy.

Gate: accepted human references and evidence-linked labels with explicit coverage.

## 2. Confirm model and harness comparisons

Use fresh-to-contribution-pilot tasks, keeping the existing development tasks out.
Cross-model: Gemini versus Luna, mini-swe-agent, archived repeat 1.
Cross-harness: fixed Qwen, mini-swe-agent/OpenHands/SWE-agent.

`confirmation_sample.csv` freezes two distinct samples per panel:

1. Thirty random shared tasks for all-attempt success/effort.
2. Thirty joint-success tasks for conditional contribution precision.

Keep their selection denominators separate. Report success, effort, direct,
non_direct and uncertain counts; per-run exploration/verification precision;
task-paired uncertainty; exclusions and unknown outcomes. Reference-patch-size
quartiles are a demand proxy independent of the observed success outcomes, not
an intrinsic reasoning-difficulty measurement.

The archived outcomes/counts are available now. New expert-calibrated component
labels, normalized units and paired role precision remain pending. Thirty is an
initial workload, not a power guarantee. Freeze expansion/interval rules before
using confirmation results; never stop according to which model wins.

## 3. Explain exploration and verification

Reuse the confirmation annotations. For exploration, locate solution-bearing
observations and non-direct detours. For verification, normalize checked property,
relevant code scope and assessed state, then plot cumulative distinct supported
properties against checks within that state. A new command is not a new property.
A flat property curve alone is not waste: justified confidence can still be direct.

Keep one contribution label (`direct / non_direct / uncertain`) and separate
reason fields: new relevant coverage, defect used in repair, repeated support,
environment/setup failure, unrelated checking and uncertainty. Environment cues
in mixed parent outputs are candidate diagnoses requiring attribution review.

The current strict repeat screen requires both passes to identify repeated
support on unchanged relevant state, cite a common earlier direct check, and show
no environment cue. It is a review screen, not proof that an action is removable.
`verification_property_review.jsonl` and `property_curves.py` support normalized
review and curves; none are populated with invented expert judgments.

Gate: property/state evidence supports interpretable comparisons and rules out
packaging or broader useful verification as explanations. Do not force either
candidate phenomenon to appear.

## 4. Evaluate a self-loop control policy

Compare unrestricted execution, a simple dedicated-check-count cap and a
property/state-aware threshold. `scripts/followup/policy.py` implements the pure
controllers, not a deployed harness integration. The intervention is suppressing
a dedicated check while continuing the agent; mixed calls are not rewritten.

Calibrate k=1,2,3 on development episodes, then freeze the selected k and simple
cap before held-out execution. k=1 suppresses the first repeated request after
established deterministic support; k=2 permits one completed repeat first.
Relevant edits and new properties reset the streak. Unknown state/property,
unsupported scope or incomplete observations allow more work.

The online policy requires complete relevant-content snapshots from the runtime,
not inferred graph IDs, the final patch or future contribution labels. Report
actual eligible/mixed-call coverage. Start with fixed Gemini/mini-swe-agent from
the development diagnosis; do not select the system after confirmation outcomes.
Evaluate all held-out attempts in every frozen arm, including failures. Record
actual model/tool cost, wall time, task success, uncertainty and introduced failures.
The proposed five-point absolute success-loss margin is not yet approved/powered;
freeze margin, sample size and analysis before live held-out execution.

Docker is available, but selected-task adapters and target model/harness backends
are not configured. No threshold is selected and no live episodes have run.

Experiments 1–3 support the framework-and-behavior story once their gates pass.
Experiment 4 supplies the stronger utility story. Failed-run recall remains
optional and deferred until independent requirements and final-state evidence exist.

## Reproduce completed work

```bash
bash scripts/followup/run_all.sh
```

This runs local analyses and authored regression tests only. It does not download
data, launch model jobs, execute trajectory commands or overwrite filled expert
forms. Machine-readable statuses distinguish computed results from prepared or
unavailable experiments.
