# prompt_v2: proposed `version_move` add-on (not run widely; awaiting review)

- **Prompt file:** `worktrace/label/prompt_v2_version_move.md`
- **Runner:** `worktrace/scripts/v2_prompt_v2.py examples`
- **Status:** run on the 10 examples below only. The v1 labels, prompt v1 and the View A outputs are unchanged.

## What it labels
- **Which ops.** Only operations that create a new code version in View B. These are the changes whose rule label is `initial`, `correct` or `revise`. Backtracks and no-op writes are rule-labelled and need no LLM call.
  - The pilot has 182 such changes (50 initial, 14 correct, 118 revise).
- **Separate call.** The label is requested in its own call with its own output. This keeps the v1 fields (relation, contribution, role, purpose) exactly as they are.
- **Output field.** `version_move` = `correct | branch_out | sidetrack | uncertain`, plus `evidence_refs` and `evidence`.
- **What the annotator sees:**
  - the issue;
  - every earlier code change in the run (op id, files, command);
  - the latest test or script run before the change (command, exit code, output);
  - the change itself (agent message, command, result);
  - facts: files written by this change, files written before, and whether the latest run failed.
- **Annotator settings.** Same annotator as v1 (`x-test-2`), temperature 0, reasoning "low". Cached by prompt hash in `data/labels/cache_prompt_v2.jsonl`.

## Definitions (TRACE-adapted)
| `version_move` | Meaning |
|---|---|
| correct | Continues the current approach: fixes, completes or refines an earlier change, in the same place and with the same strategy. |
| branch_out | A different approach: a different strategy, a different place for the fix, or undoing and redoing it another way. |
| sidetrack | Not itself part of a fix: a reproduction or debug script, temporary prints, formatting, unrelated files. |
| uncertain | The log does not let you tell. |

## Decisions for you
1. **`uncertain` is an addition.** Your spec listed three values. I added `uncertain` so that a forced choice doesn't hide doubt, matching v1's convention. Drop it if you prefer.
2. **Scope of `sidetrack`.** It includes reproduction and debug scripts written into the repository. TRACE's *Sidetrack* is "irrelevant to solving". A repro script is relevant but is not the fix. The alternative is a fourth value, `support`.
3. **The first change is labeled too.** It gets `correct` if it is part of the fix and `sidetrack` if it is, for example, a repro script. This tells you whether a run's first version is a real attempt.

## The 10 examples (seed 0, spread over models and rule labels): `examples.json`, `examples_context.md`
| # | Model | Run | Op | Rule label | `version_move` | Annotator evidence (shortened) |
|---|---|---|---|---|---|---|
| 1 | Gemini | element-web 66d0b31 | op28 | initial | correct | First change; adds `currentState` to `PlaybackInterface` as planned |
| 2 | Gemini | element-web 66d0b31 | op41 | correct | correct | Refines the earlier VoiceBroadcastPlayback rewrite after failing tests |
| 3 | Gemini | webclients c6f65d2 | op41 | revise | correct | Renames the attachment header test ID, as the issue requires |
| 4 | Gemini | flipt b4bb5e1 | op63 | revise | correct | Continues the manifest_version work in the JSON/CUE schemas |
| 5 | Luna | teleport 96019ce | op6 | initial | correct | First change; preserves non-authorization errors as the issue asks |
| 6 | Luna | element-web 66d0b31 | op19 | correct | correct | Continues the seekbar integration from op16 |
| 7 | Luna | ansible 1bd7dcf | op12 | revise | correct | Extends the bcrypt `ident` change into the password lookup |
| 8 | Terra | ansible 1bd7dcf | op9 | initial | correct | First change; adds the optional `ident` parameter |
| 9 | Terra | tutanota f373ac3 | op20 | correct | **sidetrack** | "Only retries type-checking by invoking tsc directly …" |
| 10 | Terra | ansible 502270c | op10 | revise | correct | Continues the BaseStrategy refactor |

Extra example, chosen on purpose because it is the pilot's only backtrack (`extra_backtrack_example.json`):
- Gemini ansible 502270c op25 is the change after `git checkout` reverted the file.
- It was labeled **correct** because it "re-applies the same strategy-class replacement … that op19 attempted".
- This is a reasonable call: a backtrack followed by the same approach is not a branch-out.

## What the examples show
- **9 of 10 are `correct`, and none are `branch_out`.** On these runs most changes really do continue one approach. An automated audit by a third model (Claude) agrees with all ten labels.
  - With so few examples, these 10 cannot tell you whether the annotator can recognise `branch_out` at all.
  - Before running it widely, I suggest labeling the 182 pilot changes and auditing every `branch_out` and `sidetrack`.
- **Example 9 is not a code change.** The annotator caught this correctly.
  - The v2 facts mark the command (`./node_modules/.bin/tsc --noEmit`) as write=unknown.
  - At the time the examples were run, that made it a version.
  - View B now resolves `tsc --noEmit` and similar JS/TS tools as no-write, so this op would no longer be labeled.
  - The `sidetrack` value thus doubles as a check on the write facts.
- Cost was 10 calls, about 2.5k prompt tokens each. All 182 pilot changes would be about 450k prompt tokens.
- No result here is human-validated.
