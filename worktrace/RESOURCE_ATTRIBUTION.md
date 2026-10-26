# Response usage and component-region accounting

This extension joins components to recorded model-response usage. It does not
reconstruct hidden reasoning, infer tokens from characters, or distribute a run
total across responses when response usage is missing.

## Data contract

A response ledger has one record per stored response:

```json
{"response_id":"run:t0","run_id":"run","generation_version":"V0","usage":{"input_tokens":1000,"cached_input_tokens":800,"output_tokens":300,"reasoning_tokens":null,"cost_usd":null}}
```

Numbers illustrate the schema, not experimental data. Fields remain separate;
check source accounting before interpreting subsets or deriving total cost.

Every component needs `component_id` and `response_id`. Optional fields are
`role`, `contribution_label`, `version_region` and `target_region`. Supply the
complete emitted candidate inventory, not only useful/executed components.
No-tool responses enter an unassigned bucket. A response with multiple calls
shares its usage across all their components, not a separate full budget per call.

One component has one accounting region per partition. Use `mixed` or `unknown`
when targets or versions cannot be uniquely assigned. Default version context is
the explicitly supplied generation state; post-edit state is never substituted.
Result interpretation is a later response. Future episode links must avoid
charging that response twice. Purpose/episode annotation is not automated here.

## Allocation

The default is 1/k of response usage per emitted component. This is an allocation
assumption, even when response usage is recorded. Failed/unexecuted generated
commands retain their share of inference expenditure. Performed-component
precision uses its own execution-aware denominator.

A region containing every allocation of a response has its full recorded-
associated usage. A partial region has estimated shares. Output separates these
amounts and exports a mixed-response sensitivity. Graph views partition the same
ledger and must not be summed together.

`known_total` can be partial: inspect `usage_coverage_response_weight` and
`unknown_usage_responses`. Mean per component is null if usage is incomplete.
Expenditure-contribution ratios are null for missing/zero usage. All unknown
fields remain null. Cost is accepted only when recorded; no price is applied.

## Export normalized inputs

From repository root:

```bash
python scripts/followup/component_resources.py \
  --responses response_usage.jsonl \
  --components complete_components_with_response_ids.jsonl \
  --out results/component_resources
```

## Export selected existing pilot runs from local raw shards

Requires pandas/pyarrow and already downloaded raw inputs. No download, model
API, annotation or trajectory command execution occurs:

```bash
python scripts/followup/component_resources.py \
  --jetbrains-shard raw/jetbrains/gemini_3_7_flash-run1.parquet \
  --jetbrains-shard raw/jetbrains/luna-run1.parquet \
  --components results/precision_validation_20261026/reconciled_component_annotations.jsonl \
  --out results/component_resources_reconciled
```

The existing blinding key joins complete anonymous components to raw operations.
Missing selected runs, omitted native calls, duplicate IDs and repeated source
response IDs are rejected. Normalization accepts explicit input/output or
prompt/completion fields and nested detail dictionaries. Unsupported provider
schemas require a documented adapter; raw usage is retained. Run totals are
reconciliation targets, never substitutes for absent response usage.

## Outputs

- `response_usage.jsonl`: measurements including missing/no-tool responses.
- `components_with_responses.jsonl`: exact identity joins.
- `component_allocations.jsonl`: shares, metadata and visual attributes.
- `region_totals.jsonl`: per-run role/version/target/contribution partitions and mixed sensitivity.
- `contribution_expenditure_bounds.jsonl`: allocation-dependent direct-expenditure shares.
- `run_usage_reconciliation.jsonl`: sums versus recorded run totals and discrepancies.
- `graph_overlay.json`: role markers, contribution colors, optional output-token sizing and region labels.
- `manifest.json`: input hashes, usage availability and method status.

Graph-overlay data is implemented; existing viewer rendering is not yet wired to
it. The exporter does not change previous labels, figures, manuscripts or results.
Use a fresh output directory for each method/input version. Real per-response
usage and empirical token-colored graphs remain pending source recovery.

## Component-versus-version figure and checkpoint follow-up

The primary proposed trajectory view uses component order on x and categorical
code versions on y. Points retain role, contribution, response ID and the separate
input/cache/output fields. Edits lie on state transitions; reads/checks stay on
their execution state. Generation context remains a separate accounting field.
Shape encodes action type (circle exploration, diamond edit, square verification,
triangle administration); solid color encodes direct/non-direct/uncertain
contribution (green/orange/gray). Borders have no semantic meaning. Keep primary
sequence markers the same size and show token triplets in a table. The overlay
exports `role_marker` and `contribution_color`; its optional `size_value` applies
only when an explicitly labeled resource-size view is requested.
Cache inclusion must be checked in the source schema before deriving uncached
input. A shared response never provides exact per-component reasoning usage.

`scripts/followup/draw_component_version_example.py` produces a synthetic example
in `output/figures/`. It includes hypothetical evaluated PASS highlights. This is
an illustration, not an empirical checkpoint exporter or viewer integration.

Independent final-benchmark evaluation of complete intermediate snapshots is
needed before highlighting real passing versions or reporting post-pass spending.
The replay adapter, checkpoint outcome join, and mixed-boundary accounting remain
to be implemented/tested on real inputs. Full instructions and proposed schema are
in `CODEX_FRAMEWORK_VALIDATION.md`; actual local checks are recorded separately
under `results/framework_validation_20261027/`.
