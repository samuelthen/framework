# Annotation guide: direct solution contribution in successful runs

**Status: v1, frozen after the three calibration tasks (packets 00–02) and before any evaluation task (03–10) was opened.**

**Calibration labels:** they were written under the draft and are kept. Calibration decisions that became rules are listed under "Rules settled on calibration" and were applied back to the calibration labels:
- `unrelated_check` and `style_only` were introduced during calibration;
- one calibration label was renamed to `unrelated_check`.

**Annotator:** Claude (model-coded, preliminary). One annotator; no second pass, and no human review.

## Unit and denominator
- **Unit:** one native executed tool action. In mini-swe-agent that is one bash command per step, kept whole even if it chains several shell commands with `&&` or `;`.
- **Denominator N:** every action, including failed commands and errors.
- **The final submission action** (`echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT …`) is counted in N and labelled `non_direct`, reason `administration`. Scores are also reported with submission actions excluded.
- **Actions with no recorded result** are `uncertain`, reason `missing_result`.

## Roles
| role | what it covers |
|---|---|
| `exploration` | read, search, list, inspect |
| `edit` | changes repository files |
| `verification` | runs tests, scripts, builds or type checks, or inspects the diff to confirm an edit |
| `administration` | submission, patch file creation and inspection, `git status`, tooling discovery, invalid tool invocations |

## Labels
### `direct`
The visible action does one of the following, with a citable link.

1. **Establishes a solution-bearing observation:** its output shows content that a later surviving edit or decisive check relies on. Examples:
   - the code that is changed;
   - a definition, signature, import location or data file the final patch uses;
   - the failing behaviour the fix addresses.
2. **Implements a requirement:** an edit whose change survives, at least in part, into the final submission and serves a reference requirement or the run's accepted route to it.
3. **Checks a defined property of the solution:** on a code state that contains the relevant edit, and the result supports the solution. Two cases count:
   - the first check of each distinct property;
   - a failing check whose information a later surviving edit acts on.

### `non_direct`
Give one reason:
- `negative_detour`: search or read with a negative or empty result that motivates nothing that survives, or that targets irrelevant files.
- `unused_context`: relevant-area information that no later surviving action or decisive check relies on. Examples: call sites that are not changed; overviews; test files read but not used; scaffolding for check scripts.
- `repeated_support`: re-reading or re-inspecting content already shown and unchanged since, even when it is read again just before editing.
- `discarded_edit`: an edit that failed to write, or was fully overwritten or reverted.
- `superseded_check`: any of the following:
  - a pre-change baseline run whose result is not acted on;
  - a check on an intermediate state whose result is not acted on;
  - a check that fails because the check script itself is wrong.
- `unrelated_check`: a check of an unmodified component, or an investigation of a pre-existing unrelated failure.
- `style_only`: lint or format checks and style-only edits not tied to a requirement.
- `scaffolding`: creating or deleting scratch or repro files that are not part of the final submission. Running them is judged as verification.
- `administration`: see the role table.

### `uncertain`
The trace cannot establish the label. Typical causes:
- a tool timed out with no result;
- the output the judgement would need is not visible;
- the support link to a surviving change is plausible but cannot be established;
- the effect of an inline script on files is not visible.

Missing evidence is not proof of non-contribution.

## Rules settled on calibration
1. **Compound actions** (several shell commands in one action) take the label of their strongest supported component, and the components are recorded. Example: a failed edit plus a passing test is `direct` verification.
2. **The exit code does not decide whether an edit landed.** Later evidence decides. Example: a heredoc write followed by a shell syntax error still wrote the file.
3. **A negative result is `direct`** only when the absence itself motivates a surviving change. Example: a missing alias leads to an alias table.
4. **A locating search** (grep or find of a definition) is `direct` when the located target is changed or used by the final patch, or is read by a following `direct` read.
5. **The first diff or state inspection after each surviving edit** is `direct` verification. Later inspections of the same unchanged diff are `repeated_support`.
6. **Pre-change baseline test runs** are `superseded_check`, unless their failure establishes the bug behaviour that the fix addresses.
7. **No action is credited because the run succeeded,** and a check is not credited because it passed. The checked property must belong to the solution: a requirement, or a regression property of the changed code.
8. **Alternative valid routes:** an accepted run's own route counts (for example a fallback in a helper rather than in the reference's location). The requirement is the behaviour, not the reference's lines.
9. **Model identity is hidden** behind run labels X/Y. The annotator could often infer it from run length; this is recorded as a limitation.

## Change log
- **v0:** draft before calibration.
- **v1:**
  - Rules 1–9 added.
  - Reasons `unused_context`, `unrelated_check` and `style_only` added.
  - Frozen before opening packets 03–10.
