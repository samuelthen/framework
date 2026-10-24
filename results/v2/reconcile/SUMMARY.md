# View B vs the tail measure (Gemini): what are the final-version verify runs?

**The question.** View B variant (b) shows Gemini verifying its final version about 3 times per run. The tail measure (ops after the last distinct op, v1 labels) is 0 for every Gemini pilot run. If the extra final verification were redundant, the two would disagree.

**Method.** Code: `worktrace/scripts/v2_reconcile.py` (`pilot`, `scale`). It takes exactly the steps View B counts as the verify self-loop on the final version: a non-move `run` step that is not a read-only inspection. An assert checks that the per-run count equals the graph's. Each step is compared with the earlier verify runs on the same version:
- **(i) identical rerun:** same command and same output hash.
- **(ii) same command, different output.**
- **(iii) different command.** The first verify run on the final version is (iii) by definition; it is flagged separately.

Class (iii) is split into rough sub-types by a command regex (`subtype`).

## Answer: the final-version verify load is (iii), not (i)
- **Different commands make up 92% of it.** The rest is identical reruns 1.9% and same-command-different-output 6.2%.
- **Identical reruns are rare.** 95% of Gemini runs have none on the final version.
- **The tail measure therefore agrees with View B.** The extra final verification is mostly *different* checks (broader suites, other test files, inline check scripts, lint/type checks and builds). Each adds new information, so it is labelled distinct, and no non-distinct tail forms.
- **"Late-Landing-like" is the right reading.** The runs settle on the final version, then verify it with a widening set of checks. They do not loop on the same command.

### All Gemini runs (facts only, no LLM; 2,100 runs, 700 tasks; task-clustered 95% CIs): `scale_summary.csv`
| | all runs | runs with ≥2 versions |
|---|---|---|
| verify runs on the final version, per run | 3.19 [3.04, 3.35] | 3.17 [2.98, 3.37] |
| (i) identical reruns, per run | 0.06 [0.05, 0.07] | 0.06 [0.04, 0.07] |
| (i) share of final-version verifies | **1.9% [1.5, 2.3]** | 1.8% [1.4, 2.2] |
| (ii) same command, different output | 6.2% [5.2, 7.2] | 5.9% [4.8, 6.9] |
| (iii) different command | **91.9% [90.8, 93.0]** | 92.3% [91.2, 93.5] |
| runs with ≥1 identical rerun on the final version | 5.3% [4.2, 6.5] | 4.8% [3.8, 5.9] |

**Identical reruns on the final version, per run** (runs with ≥2 versions, `scale_identical_reruns_dist.csv`):

| count | 0 | 1 | 2 | 3 | 4+ |
|---|---|---|---|---|---|
| share of runs | 95.2% | 4.3% | 0.3% | 0.2% | 0.06% |

**Class (iii) sub-types** (runs with ≥2 versions, 5,033 runs of a command; `scale_class_iii_subtypes.csv`):

| sub-type | first on final | later | all |
|---|---|---|---|
| broader suite (directory, package or whole suite) | 574 | 1,342 | 1,916 (38%) |
| inline check script (`python -c`, `node -e`) | 169 | 832 | 1,001 (20%) |
| build (`go build`, `go test -c`, `make`) | 133 | 476 | 609 (12%) |
| other test file | 247 | 302 | 549 (11%) |
| other: test runners the regex misses (`yarn workspace … test`, `npx mocha`), heredoc scripts, `go run`, `npm run build`, `py_compile` | 119 | 416 | 535 (11%) |
| lint / format / type check | 144 | 207 | 351 (7%) |
| same test files, other flags | 0 | 72 | 72 (1%) |

The sub-type regex is rough. The split between "broader suite" and "other test file" in particular depends on the path syntax.

### Pilot, the 16 Gemini runs, with the v1 and v2 LLM labels: `final_verify_ops.csv`, `per_run.csv`
40 verify runs on final versions: 3 are (i), 1 is (ii) and 36 are (iii).

| class | n | v1: distinct | v1: non-distinct | v1: uncertain | v2: distinct | v2: non-distinct | v2: uncertain |
|---|---|---|---|---|---|---|---|
| (i) identical rerun | 3 | 0 | 1 | 2 | 1 | 2 | 0 |
| (ii) same command, different output | 1 | 1 | 0 | 0 | 1 | 0 | 0 |
| (iii) different command | 36 | 32 | 0 | 4 | 33 | 0 | 3 |

- **Are identical reruns labelled non-distinct?** Mostly, but not always.
  - Under v1, 1 of 3 is non-distinct and the other 2 are `uncertain`: the annotator could not tell whether code had changed in between.
  - Under v2, 2 of 3 are non-distinct.
  - The third (ansible-502270 op34) is labelled `distinct` "after intervening code changes", but ops 30–33 are two inline checks, a `git status` and a `git diff`, with no write. That label is wrong on the facts. It is reported as is; the label has not been changed.
- **No class (iii) op is labelled non-distinct** under either label version.
- **The class (ii) case** (navidrome op23) runs 37 specs, then 38. A scratch test was added in between: a support-only change, which creates no version under (b).
- **Identical reruns per run on the final version:** 0 in 14 runs, 1 in one run (qutebrowser-6dd402) and 2 in one run (ansible-502270).
- **Tail:** 0 ops in every Gemini pilot run, under both `lo` and `hi`.

**Note on the View B summary's 3.20.** `viewb/SUMMARY.md` reports 3.20 verify runs per final version. The 3.17 here differs because six Gemini runs end with the code restored to the original state (`git checkout`/`stash`). For those, the summary counts the root's verify runs as "final-version" verifies; they include the reproduction runs before the first edit. This file counts 0 for them. The graphs themselves are identical run for run.

These labels come from LLM annotators, and the checks are an automated audit by a third model. Nothing here is human-validated.
