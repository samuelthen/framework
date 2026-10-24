# View B: code-version graphs (facts only, all 6,300 runs; no LLM)

## Code and rules
- **Code:** `worktrace/versions.py`, `parse/jsinline.py`, `scripts/v2_viewb.py` (`scale`, `report spec|support|known`, `pilot`). 11 unit tests in `tests/test_versions.py`.
- **A version** is a distinct code state:
  - Each repository write creates a new version.
  - A revert, `git stash pop`, an identical non-empty `git diff`, or a clean `git status` returns to an earlier node.
- **Not versions** (counted as evidence on the current version):
  - writes under `/tmp`;
  - the `patch.txt` submission artifact;
  - build outputs: `go test -c`/`go build` binaries, `*.test`, `node_modules/`.
- **Verify self-loop:** a `run` op on the current version, except inline Python that only reads files.
- **View B-only write refinement.** This does not change the v2 facts or labels. It resolves `write=unknown` for:
  - inline Node (`node -e` with `fs.writeFileSync`);
  - JS/TS test, lint and type-check scripts (`yarn workspace X check-types`, `npx jest`, `tsc --noEmit`);
  - `prettier --check`;
  - `go test`/`go vet`.
  The remaining unknown writes create uncertain versions, as specified.

## Two variants (as decided)
- **(a) Every write is a version:** `version_graphs_v2.jsonl`, outputs in this directory.
- **(b) Support-only changes create no version** (`support_no_version/`).
  - A change is support-only if every repository file it writes is a support candidate.
  - Support candidate = a new file that is deleted later or absent from the final submission diff.
  - Such a change attaches as `support` evidence on the current version.
- **Sensitivity variant:** `known_writes/`, where only known writes create versions.

### Versions per run (% of runs)
| Model | variant | 1 | 2 | 3 | 4 | 5 | 6–9 | 10+ | mean [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| Gemini | (a) | 12.5 | 12.0 | 11.9 | 10.8 | 10.0 | 24.5 | 17.1 | 5.72 [5.44, 6.01] |
| Gemini | (b) | 16.9 | 16.2 | 14.4 | 11.0 | 8.2 | 20.6 | 11.5 | 4.78 [4.53, 5.04] |
| Luna | (a) | 27.2 | 30.2 | 18.8 | 12.0 | 5.3 | 6.2 | 0.4 | 2.65 [2.55, 2.76] |
| Luna | (b) | 27.9 | 30.1 | 18.8 | 11.7 | 5.2 | 6.0 | 0.3 | 2.61 [2.51, 2.72] |
| Terra | (a) | 29.4 | 27.6 | 19.3 | 11.1 | 5.9 | 6.3 | 0.3 | 2.62 [2.53, 2.72] |
| Terra | (b) | 30.4 | 27.3 | 19.0 | 11.0 | 5.6 | 6.2 | 0.3 | 2.59 [2.50, 2.69] |

The 0-version share is ≤1.1% for every model.
- (b) removes about one version per Gemini run: Gemini writes verification scripts and scratch tests into the repository.
- Luna and Terra barely change: they keep scratch work in `/tmp`.
- **(b) differs substantially for Gemini, so the pattern figures use (b).**
- Runs with an uncertain version: Gemini 32.3%, Luna 12.2%, Terra 22.0%.

### Verify self-loop: final version vs earlier versions (runs with ≥2 versions; task-clustered 95% CIs)
| Model | variant | verify runs on final version | per earlier version | share of all verifies on final | final verified ≥3 times |
|---|---|---|---|---|---|
| Gemini | (a) | 2.34 [2.18, 2.51] | 0.76 [0.69, 0.84] | 40.5% [37.7, 43.2] | 34.4% [31.7, 37.1] |
| Gemini | (b) | **3.20 [3.01, 3.40]** | 0.71 [0.63, 0.80] | **54.5% [51.3, 57.3]** | **48.4% [45.5, 51.1]** |
| Luna | (b) | 0.39 [0.35, 0.43] | 0.46 [0.43, 0.51] | 32.3% [29.5, 35.2] | 1.9% [1.3, 2.7] |
| Terra | (b) | 0.47 [0.42, 0.52] | 0.54 [0.49, 0.58] | 32.5% [29.5, 35.3] | 2.7% [1.9, 3.6] |

- **What these final-version verifies are** (`results/v2/reconcile/SUMMARY.md`):
  - 92% use a different command from the earlier verify runs on that version: broader suites, other tests, inline checks, lint and builds.
  - Only 1.9% are identical reruns (same command and output).
  - Six Gemini runs end with the code restored to the original state. For them this table counts the root's verify runs, including pre-edit reproduction runs. Counting them as 0 gives 3.17 instead of 3.20.
- **Gemini is Late-Landing-like.** Under (b), the final version is verified 4.5× as often as an earlier version. Half of Gemini's multi-version runs verify the final version 3 or more times.
- Luna and Terra verify each version about equally, and rarely more than twice.
- **Backtracks are rare:** runs with any backtrack are Gemini 3.7%, Luna 0.2%, Terra 0.7%.
- Together with prompt_v2.1 (`branch_out` = 0.6% of changes), this shows the runs are **linear refinement chains, not explorations**.
- On the pilot (v2 LLM labels), ops on the final version are rarely judged non-distinct: 1.2% [0, 2.8], compared with 5.5% on earlier versions.
  - The extra final verification therefore looks intended rather than labelled redundant.
  - This rests on LLM labels only; it is not human-validated.

## Pattern figures (variant b): `figures/v2/viewb_patterns_{model}_support.png`
- **Grouping:** by model and number of versions (1–8, groups of ≥20 runs).
- **Alignment and pruning:** versions are aligned by order; nodes and edges present in <30% of runs are pruned.
- **Encoding:**
  - node label = share of runs that have the node;
  - self-loop = mean verify runs;
  - edges coloured by majority rule label, with "C x%" giving the share of the move that is a rule `correct` (new version after a failing run);
  - the dashed ring marks the final node, with its share and resolve rate.
- **Gemini, all groups:** the root gets 4–5 verify runs (reproduction before the first edit), middle versions 0.2–1.1, and the final version about 3.
- **Gemini resolve rate:** falls from 72% (1 version) to 45–58% (5–8 versions).
- **Other variants:** variant (a) and known-writes figures are kept beside these (no suffix and `_known_writes`).
- **Example runs:** `figures/v2/viewb_runs/`.
