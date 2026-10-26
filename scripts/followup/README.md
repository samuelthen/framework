# Follow-up study tools

**Current one-hour scope:** [`CODEX_FRAMEWORK_ONE_HOUR.md`](../../CODEX_FRAMEWORK_ONE_HOUR.md).
`framework_quickcheck.py --out <fresh-directory>` creates the fixed two-task/four-run
sample, archived role precision, two trajectory figures and component examples.
Optional `--jetbrains-shard` flags add actual usage extraction from local files.
The script does not execute benchmark checkpoints or create empirical PASS markers.

For the component/version/token and intermediate-checkpoint study, start with
[`CODEX_FRAMEWORK_VALIDATION.md`](../../CODEX_FRAMEWORK_VALIDATION.md). Response
accounting is implemented in `component_resources.py`; independent checkpoint
replay and empirical PASS overlays remain pending. The plotting examples use
synthetic data and are not result figures.

```bash
bash scripts/followup/run_all.sh
```

Outputs: `results/followup_20261026/`. Existing validation artifacts are read-only.
Uses local archived data. No task commands, labeling endpoint or live agent is
invoked. Real Git regressions run only authored commands in disposable test repos.

- `review_packets.py`: fixed-denominator impact priority, 30 blinded cases (up to
  32 planned; task 09 has no label disagreements) plus
  769-unit full review form; prior model labels stay outside `expert_blind/`.
- `expert_gate.py`: human-reference status/evaluation only when names, actual
  annotator type, accepted requirement reviews and evidence-linked labels exist.
  Blank/model-coded rows never count as expert truth. The enriched sample is not
  population accuracy. Forms are preserved on reruns.
- `role_precision.py`: equal-run role precision; paired completeness and pooled
  shares are explicit. Archived reconciliation has asymmetric non-verification
  role treatment; the report preserves that limitation.
- `verification_audit.py`: existing labels plus a strict repeated-support screen.
  Environment cues and unrelated checks are separate, not over-verification.
- `freeze_samples.py`: disjoint-from-development archived task panels. All-attempt
  and joint-success samples have different purposes/denominators. Seeded sample
  identities are checked on reruns. Reference size is not outcome difficulty.
- `rebuild_states.py`: repaired facts/graphs for the 16 development trajectories,
  in a separate process/output namespace to preserve old inputs.
- `ablation_packets.py`: paired input specs, same raw context, explicit derived
  state present/withheld. These are not model outputs or human accuracy results.
- `property_curves.py`: only approved normalized expert property/state records
  can produce curves. Complete `verification_property_review.jsonl`, including
  `relevant_state_id`, `normalized_property_ids`, `contribution_label`, `evidence`,
  `reviewer_type`, `reviewer_name`, and `assessment_status=approved`.
- `policy.py`: prefix-only pure controllers. No harness integration or actual
  cost/success experiment is claimed. k remains unselected pending calibration.

Full protocol, remaining gates and machine-readable status are saved with the
results. Suppression eligibility requires dedicated checks and assessed complete
runtime scope; unknown state or a mixed call permits further work. A graph epoch
is not a verified content snapshot. Human requirements/labels and configured
target harness/model environments remain external inputs.
