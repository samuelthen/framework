# Four-label contribution rubric — one-hour review

Classification, contextual relation, contribution and resource usage are separate
fields. Classify the performed component using the full task requirements,
accepted solution evidence, observations and later trajectory. Alternative valid
repairs are allowed; matching the final patch's exact implementation is not required.

| Stored label | Meaning | Evidence required |
| --- | --- | --- |
| `direct` | Establishes solution-bearing information, implements a valid change, or verifies a relevant repair/preservation property. | Identify the content/property, requirement, relevant code state and observation/change. |
| `indirect` | Demonstrably guides later useful work without directly establishing the solution. | Explain the observed decision/dependency and link at least one later performed direct component in the same run. |
| `no_demonstrated` | Available evidence shows no supported contribution to the solution or subsequent useful work. | Identify the assessed result and why no useful support is demonstrated; do not claim proof of zero causal effect. |
| `uncertain` | Available evidence cannot reliably establish a category. | State the missing output, unclear dependency, unresolved state or reference conflict. |

An irrelevant-file search gets indirect credit only when the trace shows that its
result guides a useful next step. Do not infer indirect credit merely because an
agent eventually finds the right file. A negative result can directly establish
a missing required behavior; judge its content rather than its positive/negative
wording. A baseline check can contribute when it establishes relevant preservation
or a comparison actually used in the repair. Environment failures are not
automatically no-contribution or over-verification. Incomplete observations stay
uncertain. A repeated check needs assessment of its property, state and supported
contribution; an identical string is only contextual evidence.

## Preserve historical labels

The existing `non_direct` label is **legacy unsplit**, meaning indirect versus no
demonstrated contribution has not been separated. It is not an automatic mapping
to `no_demonstrated`. Preserve source files and the original judgment in
`archived_contribution_label`. Apply changes in an additive review overlay.

The fixed one-hour review sample contains up to five cases per selected run:
three legacy non-direct cases (including exploration and verification where
available), one direct control and one uncertain control. Cases follow chronology.
For the four selected runs the prepared packet contains 20 cases. This enriched
sample tests rubric feasibility; it cannot estimate population category prevalence
or independent labeling accuracy. Do not force every new category to appear.

## Complete the review overlay

Run `framework_quickcheck.py` to prepare `contribution_review_template.jsonl` and
`contribution_review_packet.md`. Copy the template to a new file. For each case,
read the full linked source packet and actual raw trajectory where available,
then fill the following fields. Keep the component ID and source hash unchanged.

```json
{"component_id":"EXAMPLE_ONLY","source_command_sha256":"copied_from_template","assessment_status":"reviewed","contribution_label":"indirect","evidence":"Explain the observed result and later decision; cite exact action/observation IDs.","supporting_component_ids":["LATER_DIRECT_COMPONENT"],"reviewer_type":"model","reviewer_name":"Actual runtime/model identity, or Codex (model identifier unavailable)"}
```

This is a schema example, not a real annotation. Use `pending` with a null label
for cases not reviewed. A completed assessment uses `reviewed`, one of the four
labels, nonempty evidence and actual reviewer provenance. `supporting_component_ids`
is required for indirect and must point to later performed direct work in the
same run. The software checks identity/order and provenance completeness; it
does not establish semantic correctness. Link evidence and reviewer reasoning
must still be assessed. Model-coded review never counts as human validation.

Re-run with `--contribution-review <completed-copy.jsonl>`. The quick script caps
reviews to the fixed packet, preserves all 175 candidate components and leaves
unreviewed historical non-direct cases as legacy unsplit. Do not pass only the
20 reviewed cases to the resource exporter; that would corrupt shared budgets.

## Scores and resource accounting

For a fully annotated role, let N = D + I + Z + U, where Z is no demonstrated
contribution. Direct precision is D/N, with label bounds D/N to (D+U)/N.
Indirect support is a separate category; it gets no direct-precision credit and
does not enter the uncertain upper numerator. Z likewise stays outside that
numerator. Counts, shares and token expenditure should retain all four categories.

For partially reviewed legacy data, additionally report L, the legacy-unsplit
count, and N = D + I + Z + U + L. Conditional on retaining the archived judgment
that L is non-direct, the direct bounds remain D/N to (D+U)/N. Label this a partial
review. Do not present it as a fully validated v2 estimate. These bounds do not
cover systematic annotation error; reviewing controls may expose such errors.
Report how many cases were reviewed, and show the reviewed subset separately as
an enriched feasibility sample. No role denominator means undefined, not zero.

Known unexecuted candidates stay outside performed-component precision but retain
their inference-expenditure shares. Input, cached input and output are separate;
shared-response costs remain allocated estimates. Unassigned response expenditure
stays uncertain rather than receiving a no-contribution label by default.

## Context and graph encoding

Record target history (`initial`, `revisit`, `unknown`) separately from command
recurrence (`exact_repeat`, `new_command`, `unknown`). Both can hold for the same
component. Preserve available code-state context. Neither contextual field
determines contribution by itself.

Use shape for action type: circle exploration, diamond edit, square verification,
triangle administration. Use solid color for contribution: green direct, blue
indirect, orange no demonstrated, gray uncertain. A neutral beige symbol labeled
**legacy unsplit** denotes unreviewed historical non-direct data; this is a review
status, not a fifth contribution category. Borders carry no separate meaning.
Keep sizes fixed in the primary figure and put input/cache/output in a table.
Version PASS/FAIL/UNTESTED labels remain a separate evaluation result.
