# Task 1 — write detection (v2 facts)

## What changed
- `parse/pyinline.py` (new): static analysis of inline Python with `ast` (regex fallback when it does not parse).
  Writes: `open(..., w/a/x/+)`, `Path.write_text/write_bytes/unlink/rename/replace/touch`, `os.remove/unlink/rename/replace/rmdir`,
  `shutil.copy*/move/rmtree`, `json/pickle.dump` (via the `open` call). Literal paths resolved through simple assignments,
  `Path(...) / 'x'`, `os.path.join`, and `for x in [literals]`. Non-literal target → `unknown`; `exec/eval/importlib`
  → `unknown`; `subprocess.*`/`os.system` with a literal command → classified by the shell rules, else `unknown`.
- Scripts written by a heredoc (`cat > f.py <<EOF`) are remembered and analysed when later run (`python f.py`).
- Writes outside the repository (absolute non-repo paths, e.g. `/tmp`) no longer change the code state.
- Two choices beyond the spec, for review: results of `tempfile.mkdtemp()/TemporaryDirectory()` are treated as
  `/tmp` paths rather than non-literal; `git checkout <path>` (no `--`) is now a revert (the automated audit by a third model found it
  was classified as a branch switch).
- Tests: 67 pass (10 new: read-only heredoc, literal-path rewrite, computed path → unknown, `python -c "print()"`,
  multi-line `-c`, open modes, script written then executed, tempfile, git checkout).

## Results (all 6,300 JetBrains runs, 188,609 ops) — `write_shares.csv`

| | write = true | false | unknown |
|---|---|---|---|
| v1 facts | 8.9% | 80.2% | **10.9%** |
| v2 facts | 15.1% | 81.2% | **3.7%** |

By model, unknown: Gemini 10.0% → 4.5%, Luna 11.9% → 1.9%, Terra 12.5% → 3.0%.
What remains unknown is mostly non-Python: `node -e`, `yarn`, `npx`, `make`, `prettier --write`, compiled test binaries.

Pilot test reruns (a run op whose same-object candidate is a run op): 30 in both versions.
Code state known: **6 → 19** of 30 (yes 15, no 4, unknown 11).

`edit → test → identical test on unchanged code` signature:
- pilot: 0 → 1 match
- all runs (v2): Gemini 68 matches, prevalence 2.3% of runs [1.6, 3.0]; Luna 1 (0.0%); Terra 3 (0.1%)
  (`edit_test_identical_test_at_scale.csv`; task-clustered bootstrap, 1,000 resamples).
  Of Gemini's 3,812 test reruns, code state is known for 65.5%, and 25.3% have identical output.

Pilot ops whose facts changed (to be relabeled in Task 2): 222 of 1,432.

## Automated audit by a third model (Claude, done while running this task)
- Gemini run (ansible 1bd7dcf, run 2): 73 tool calls in the raw row = 73 outputs = 73 ops; commands identical in order.
  Code state, candidates and exact-repeat flags checked op by op. Two bugs found and fixed (above).
- Luna run (webclients 715dbd4): labels checked against outputs. Ops 6–11 are five different `grep` commands that
  all fail with the same BusyBox `--include` error; the annotator marks the repeats non-distinct (correct). Op 19
  re-reads narrower ranges of an already-read file → non-distinct (correct). This "repeated failing command" pattern
  is not among the draft's hypotheses.
