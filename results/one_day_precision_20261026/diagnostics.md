# Diagnostics: one-day contribution-precision pilot

All labels were coded by one model annotator: Claude (Anthropic), single pass, preliminary. There was no second reviewer and no human adjudication, so **no inter-annotator agreement could be measured.** Everything below is a self-report of known weaknesses, not a validation.

## 1. Annotation unknowns (`uncertain`)
- **Overall:** 17 of 675 actions are `uncertain`. In the 8 evaluation pairs: 9 of 333 Gemini actions and 4 of 116 Luna actions.
- **Causes:**
  - **No visible result:** the tool timed out (`exit -1`) with no output. This covers most cases: Go/TS test and type-check runs in tasks 1, 2, 3, 5 and 6, and `go build` in task 4.
  - **Failing final-state checks the agent did not act on:**
    - task 4, Run Y: `TestLoad/configured` fails after it changed the CheckForUpdates default;
    - task 10, Run X: wordpress tests fail to build against the old pointer signature.

    Whether these match the hidden updated tests is unknown.
  - **Support link not establishable:**
    - task 0: a negative import-safety grep;
    - task 10, Run X: a toml tag added to `IgnoreInactive`;
    - task 9, Run X: a core-test run that may not exercise the changed module.
  - **Packet clipping (task 0, X003):** the relevant output was omitted from the packet excerpt.
- **Effect on the result:** the bounds `[D/N, (D+U)/N]` cover these. They do **not** cover errors in labels that look certain.

## 2. Truncated observations (packet limitation found mid-study)
- **Problem:** packets show the full raw tool output. For actions flagged `agent_saw_truncated`, the agent saw only a head and a tail, with roughly 5,500 characters elided.
  - This matters for `repeated_support`: re-reading a region that was elided earlier is new information to the agent.
- **What was done:**
  - From task 05 on, truncated reads were judged against the agent's view, taken from the raw messages; see `run.log`.
  - Earlier truncated cases were re-checked, and no label changed. Task 05 Y004/Y005 were labelled `direct` for this reason.
- **Next run:** the packet builder should show the agent-visible output by default.

## 3. Bundling and the per-action unit
- **Unit and finding:** the unit is one native mini-swe-agent action (one bash call). After removing a leading `cd /app &&` (`bundling.csv`, evaluation runs):

  | model | mean commands per action | median | actions with ≥2 commands |
  |---|---|---|---|
  | GPT-5.6 Luna | 3.0 | 2 | **75%** |
  | Gemini 3.7 Flash | 2.3 | 1 | **14%** |

- **Why it matters:** Luna packs several steps into one call much more often. Compound actions take the label of their strongest component (guide rule 1), which favours bundlers. **Part of Luna's higher per-action precision may therefore come from packaging, not from less indirect work.**
- **No defensible common unit was available today.** Splitting compound calls would need per-segment outputs, which are not separated in the trace.
- **Unit-free view:** absolute counts per task are reported alongside the shares:

  | model | direct actions per task | non-direct actions per task |
  |---|---|---|
  | Gemini | 12.6 | 27.9 |
  | Luna | 6.6 | 7.4 |

  Even in shell-command segments, Gemini issues about 2.2× as many commands.

## 4. Alternative fixes and reference conflicts
- **Task 00:** Run X resolved via `get_marc21_language` plus a 2-name alias table, not the reference helpers. Run Y added a `languages.page` fallback inside `get_languages`. Both are credited as their own route (guide rule 8).
- **Task 04:** requirement bullet 3 (absent `check_for_updates` → false) conflicts with the reference, which keeps `Default()`. Run Y changed the default to false; Run X did not. Both are recorded as resolved.
- **Task 08:** Run X did not change the `configdata.yml` binding (R5) and is still recorded as resolved.
- **Task 09:** the reference rewrites the whole observations feature, but the requirements and the single fail-to-pass test cover only `_sort_values`. Both runs implemented only that.
- **Task 10:** Run Y made `searchCache` accept `interface{}` (map or pointer) rather than a map.
- **Treatment:** requirements were written as behaviours with permissible alternatives (`requirements.jsonl`). Route-specific reference changes are not required.

## 5. Lost progress, discarded and failed edits
- **Discarded or failed edits in evaluation runs:** Gemini 3, Luna 2. Mostly scripted replacements that failed (syntax errors, assertion misses), or reverts of unwanted side effects:
  - task 3, X031: a whole-file rewrite that silently changed unrelated cache log strings. It was caught by diff inspection and reverted.
  - task 6, X028: a regenerated `pb.gw.go` that was reverted.
  - task 10, Y009: `gofmt` reformatting that was reverted.
- **Not observed:** no successful run lost a requirement it had already met.

## 6. Tests actually run in this study
- `audit/reproduce_reliability.py`: 7 of 7 probes fail, as the audit expected (`audit_reliability_output.txt`). The pilot does not use inferred code states, so these were not repaired.
- `PYTHONPATH=worktrace pytest worktrace/tests`: 79 passed (`pytest_output.txt`).
- `pytest scripts/one_day_precision/test_one_day.py`: 8 passed. They cover:
  - denominators, uncertain bounds and empty runs;
  - label validation;
  - outcome cells, unknown outcomes and zero denominators;
  - terminal-coverage status handling.
- **No task tests were executed.** No task environments are available here. Outcomes are the dataset's recorded `resolved` field, and no trajectory command was executed on the host.

## 7. Blinding
- **How:** model identity was hidden behind seeded X/Y labels.
- **Limit:** run length nearly always reveals the model (Gemini runs are about 3× longer), so blinding was weak in practice.
- **Old labels:** old WorkTrace `distinct`/`non_distinct` labels were not consulted or converted.

## 8. Calibration vs evaluation
- **Calibration** (tasks 00–02, 226 actions) was labelled under draft v0. Rules found there were frozen into v1 (`annotation_guide.md`, sha256 prefix in `run.log`) before tasks 03–10 were opened.
- **Effect on results:** calibration pairs are reported separately and are not part of the evaluation estimates. They show the same direction: Luna is higher in all 3.
