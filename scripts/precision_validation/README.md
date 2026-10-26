# Eight-pair precision validation

Run from the repository root:

```bash
bash scripts/precision_validation/run_all.sh
```

Uses `.venv/bin/python` (override with `PY`) and the already installed project
dependencies. Reads the two local JetBrains repeat-1 shards and saved labels,
packets, references and graphs. No acquisition or labeling API is invoked.
`bash -n` parses command text without executing it. Never run trajectory commands
on the host.

Outputs are under `results/precision_validation_20261026/`. Original study
outputs under `results/one_day_precision_20261026/` remain read-only.

- `prepare.py`: canonical candidate components, anonymous X/Y full agent-visible
  evidence. Pipelines/control constructs/inline programs are coherent units;
  malformed attempts are opaque. This is not a formal shell interpreter.
- `review_requirements.py`: recorded primary review of eight task references.
- `compare_states.py`: fresh pilot facts/default graphs and historical comparison.
- `analyze.py`: rejects missing/duplicate reviews; computes component and native
  sensitivities, verification precision, shared-call agreement and baseline
  disagreements; exports evidence claims, plots, hashes and status.
- `compare_reviewers.py`: validates common frozen requirements, measures
  component agreement, retains all disagreements and recomputes conservative
  cross-review uncertainty bounds.
- `report_final.py`: two-pass report and scientific figure from actual outputs.
  `report.py` retains the earlier single-pass report helper.
- `test_validation.py`: denominator/uncertainty, decomposition and state regressions.

Reviewer input is `reviewer_b/03.json` through `10.json`. Each file has `order`,
`requirements` with unique `id`, and `components` matching the complete inventory
by `blinded_label/action_index/component_index`. Every component uses
`contribution_label: direct|non_direct|uncertain`, a role, reason, evidence,
requirement IDs and `execution_status: executed|not_executed|uncertain`.
Verification additionally records property, relevant state change, prior checks
and gain. See the saved annotation guide. No script generates semantic labels.

Current B/C inputs are two blinded model-coded component passes, each with one
judgment per component. Legacy Claude labels used calls. C receives the frozen
reviewed requirements, but sees no B contribution labels. Component disagreement
is retained as uncertainty, not declared consensus. The passes share a model
family and do not provide human validation. Role-only root adjudications are
separate JSON and preserve raw reviewer files. Ambiguous requirement conflicts
are not resolved by recorded benchmark success.
