# prompt_v2.1 `version_move`: all pilot changes, with an automated audit by a third model

## Setup
- **Prompt:** `worktrace/label/prompt_v2_1_version_move.md`. Changes from v2:
  - a new value, `support` (serves the fix but is not part of it);
  - `sidetrack` narrowed to changes irrelevant to the issue;
  - a rule fact passed to the annotator: *support-candidate files* (`versions.support_candidates`). A file qualifies if it is new and is either deleted later or absent from the final submission diff.
- **Submission diffs:** taken from the raw `submission` column (`data/submissions.parquet`).
- **Annotator:** `x-test-2` (deepseek-v4.1-flash), temperature 0, reasoning "low", one call per change.
  - 0 label errors; 470k prompt tokens.
  - Labels: `data/labels/pilot_version_move_v2.1.jsonl`.
- **What was labeled:** 177 changes, i.e. every View B move whose rule label is `initial`, `correct`, `revise` or `backtrack`.
  - The 182 in the proposal fell to 177 after the View B Node/JS write check, which removed `tsc` and similar non-changes.

## Distribution (`v2_1_by_model.csv`, `v2_1_by_rule_label.csv`)
| Model | correct | branch_out | support | sidetrack | uncertain | n |
|---|---|---|---|---|---|---|
| Gemini | 52 | 1 | 22 | 3 | 0 | 78 |
| Luna | 42 | 0 | 3 | 1 | 0 | 46 |
| Terra | 47 | 0 | 5 | 1 | 0 | 53 |
| **All** | **141 (79.7%)** | **1 (0.6%)** | **30 (16.9%)** | **5 (2.8%)** | 0 | 177 |

| Rule label | correct | branch_out | support | sidetrack |
|---|---|---|---|---|
| initial (50) | 45 | 0 | 5 | 0 |
| correct (15) | 13 | 0 | 2 | 0 |
| revise (111) | 83 | 0 | 23 | 5 |
| backtrack (1) | 0 | 1 | 0 | 0 |

Support hint (10 changes): 8 labelled `support`, 1 `sidetrack`, 1 `correct`. The annotator follows the hint but does not copy it.

## Automated audit by a third model (Claude; `v2_1_handcheck.csv`): every non-`correct` label (36) plus 30 random `correct` (seed 0)

**21 of the 66 are not code changes at all.** They are `yarn check-types`/`lint`/`test`, `prettier --check`, `go test`, `./proxy.test`, `make` inside `node_modules`, `find`, and Python probes that write temp files.
- The v2 facts mark them `write=unknown`, so View B made them versions.
- The annotator could only pick from the five values. It chose `support` for 20 of them, a sensible answer for verification steps, and `sidetrack` for 1.
- This is a fact-layer problem, not an annotator error.
- **Fix applied, View B only:** test, lint and type-check scripts, `prettier --check`, `go test`/`go vet`, compiled test binaries and builds inside `node_modules` are no longer versions. This removed 11 of the 21.
- The other 10 are genuinely opaque (Python with `exec`/`subprocess`, `node test/test.js`, `make && node …`). As specified, they stay as uncertain versions.

**On the 45 real code changes the audit agrees with 41 (91%):**

| annotator → / audit label ↓ | branch_out | correct | sidetrack | support |
|---|---|---|---|---|
| branch_out | 1 | 0 | 0 | 0 |
| correct | 0 | 29 | 1 | 0 |
| sidetrack | 0 | 0 | 1 | 0 |
| support | 0 | 1 | 2 | 10 |

The four disagreements:
- Terra qutebrowser op7: removing blank lines inside the agent's own fix is `correct`, not `sidetrack`.
- Gemini flipt op73: restoring `go.work.sum` to keep the patch clean is `support`, not `sidetrack`.
- Gemini teleport op43: `rm -f proxy.test` is `support`, not `sidetrack`. The same action at op25 was labelled `support`.
- Gemini navidrome op22: extending a scratch test file deleted at op24 is `support`, not `correct`. Its sibling ops were labelled `support`.

**Random `correct` sample: 29/30 agree.** The one exception is navidrome op22 above. **None of the 30 should be `branch_out`.**
- The closest call is Luna webclients op29: "the automated replacement targeted a similar block in another function … I'll correct the WKD function directly".
- That repairs a misapplied edit inside the same approach. It is not a new strategy.

## branch_out is under 5%
- `branch_out` is 1 of 177 changes (0.6%), and 1 of the 162 still counted as versions.
- The audit found no `correct` that should be `branch_out`.
- The single `branch_out` is the pilot's only backtrack: a `git checkout` before redoing the same edit with a cleaner script.
- **These runs are mostly linear refinement of one approach. This is not an annotator failure.**
- View B patterns should therefore be reported as **Late-Landing-like**: a chain of refinements whose verification concentrates on the final version, not an exploration with branches.
- These are LLM labels plus an automated audit by a third model (Claude). They are not human-validated.
