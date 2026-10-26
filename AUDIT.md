# WorkTrace reliability audit — 25 October 2026

**Verdict: useful as an exploratory research prototype; not yet a validated measure of agent waste.** The saved pilot arithmetic checks out, but important state-tracking errors are reproducible, the skip-rule check is constrained by the label definition, and the intended human-validation gates remain unmet. The overview's statement that “the method works” is stronger than the available evidence supports.

Audited revision: `239406b`. Scope: local code, tests, saved pilot/scale labels, annotation files, and result summaries. No external model calls, paid labeling, or raw-data download was performed. No implementation or saved result was changed. The probes below demonstrate possible failures; this audit does **not** estimate their frequency or numerical impact in the original trajectories.

## Findings, ordered by priority

### 1. High — the unmatched skip check cannot validate missed redundancy

`worktrace/worktrace/label/schema.py:24–35` rejects every `non_distinct` label unless it cites a matched operation drawn from the two rule candidates. An operation with no candidates therefore cannot receive an accepted `non_distinct` label. The prompt also explicitly defines non-distinctness relative to that match. Retries enforce the restriction; exhausted retries become uncertain.

`worktrace/scripts/v2_task6.py:1–11` then treats a ≥98% distinct rate among these unmatched operations as evidence that labeling them can be skipped. This can measure the rate of uncertainty under the constrained prompt, but cannot measure whether candidate retrieval missed a redundant operation. Candidate A and B expose only the latest same-object operation and the latest same-kind/equal-output operation, so retrieval recall needs independent testing.

The problem matters at scale: the saved Gemini runs 1–2 contain 74,132 labels, of which 57,207 (77.2%) are `rule_skip`; Terra contains 4,132, of which 3,688 (89.3%) are `rule_skip`. Those labels are assumptions under the candidate-restricted definition, not independent judgments of usefulness.

**Action:** retain “candidate redundancy” as an explicitly restricted construct. Validate retrieval recall on a blind sample with broader trajectory context and permission to match any earlier operation. Report actual LLM labels and rule assignments separately. Do not infer that almost all unmatched work is useful from this check.

### 2. High — code-state equality can be asserted without content equality

`worktrace/worktrace/facts.py:86–87` hashes the output of any accepted state probe. `worktrace/worktrace/parse/shell.py:404–411` accepts `git status --short`, `git diff --stat`, and `git diff --name-only`. These summarize paths/status or counts, not file contents.

**Reproduced:** `git status --short` → test → unknown script → the same status listing → test produces `any_code_written_since='no'`, although the script's changes remain unknown. Two different contents can have the same ` M a.py` status. A successful `git checkout other_branch` is also classified as `other` with no write, leaving tests on potentially different branches marked as running on unchanged code.

**Impact:** the annotator receives false “unchanged code” facts, which can alter reproduction labels and test-rerun signatures.

**Action:** distinguish status observations from content identity; invalidate state on branch/HEAD changes. Use content snapshots when available and preserve uncertainty otherwise. Even a full plain `git diff` needs care because it omits untracked files and, by default, staged changes.

### 3. High — write detection loses uncertainty and changed paths

`worktrace/worktrace/parse/shell.py:335–360` gives a known write precedence over an unknown write. The representation has no independent flag for additional unknown side effects. It also records only `main_object(...)` for shell edit operations.

**Reproduced:**

- `echo x > A.py && python fix.py` records only a known write to `A.py`. A later read of `B.py` gets `object_written_since='no'`, although `fix.py` could have changed it.
- `sed -i 's/x/y/' A.py B.py` records only `B.py`. A later read of `A.py` gets `object_written_since='no'`.

**Impact:** unchanged-object facts, read-repetition signatures, support-file inference, and partial-revert bookkeeping can be wrong.

**Action:** track known paths and unknown side effects independently; collect every mutation target. Carry unresolved effects into subsequent facts rather than letting one recognized write remove them.

### 4. High — version graphs can invent backtracks and collapse distinct versions

`worktrace/worktrace/versions.py:207–241` applies revert semantics without checking whether the revert succeeded. Unknown writes create uncertain versions but do not enter the `dirty` set. Content-probe hashing ignores the operation's truncation flag.

**Reproduced:**

- An edit followed by `git checkout .` with exit code 1 still returns to root and emits `backtrack`.
- An unknown script, an edit to `a.py`, and a successful revert of only `a.py` return to root, discarding unresolved script changes.
- Two edits followed by identical truncated `git diff` displays collapse to one version and turn the later edit into `noop`.

**Impact:** reported version counts, linearity/backtrack rates, and which checks attach to the final version can change. The saved graph summaries are heuristic reconstructions, not verified code snapshots. The existing known-writes sensitivity analysis is useful but does not cover these errors.

**Action:** require evidence of successful restores, preserve unknown dirty state across partial restores, and never merge on incomplete observations. Rebuild graph outputs after these fixes and compare headline results.

### 5. High for research claims — agreement is demonstrated; accuracy against the intended construct is not

`results/v2/B10_STATUS.md` correctly says the human criteria remain pending. The 200 rows in `annotation/pilot.csv` have **zero adjudicated contribution labels**. Model agreement and self-consistency are useful stability checks, but both annotators receive the same restricted candidates and computed facts, so they can share systematic errors.

The saved external evaluation (`results/v2/task4/SUMMARY.md`) reports candidate-redundancy precision/recall of **3.5% / 27.5%**, compared with **5.6% / 33.3%** for exact repeats. Its different target construct limits interpretation, but it does not provide positive validation of WorkTrace's intended construct either.

“Distinct” means the result establishes something new under the annotation rules. It does not establish that the action was necessary, efficient, or causally useful for solving the issue. Operation-count rates also do not directly measure wasted time, tokens, or cost.

**Action:** complete independent human validation on the intended construct, including missed candidates and changed-code cases. Limit current claims to what the labels measure. Use matched comparisons and cost measures, or interventions, before claiming savings or explaining causal effects.

### 6. Medium — validation and reproduction need versioned inputs

`worktrace/scripts/m5_annotation.py` reads `read_labels('pilot')` in both `export()` and `agree()`, so the advertised human-validation command evaluates **v1**, while current conclusions use `pilot_v2`. It needs an explicit label/fact version and a matching regenerated annotation packet.

The checkout has no dependency manifest or lockfile. The README points to a nonexistent `../.venv`. Raw datasets, event logs, prior fact snapshots, issues, and API caches are excluded. Dataset revisions are recorded, which helps, but the documented commands cannot regenerate all results from this checkout as supplied. Saved labels alone also do not retain the full inputs needed to inspect every decision.

**Action:** add pinned dependencies, a complete reconstruction command sequence, and a manifest connecting dataset revision, parser revision, prompt hash, model/settings, label provenance, and outputs. Make human-validation tools accept and record the specific label/fact version being evaluated.

## Verification performed

- **Existing tests:** 79 passed, using Python 3.13 and a temporary installation of pytest 9.1.1. These tests cover parser/fact and version examples, but omit the reproduced cases.
- **Adversarial checks:** all seven desired-behavior checks in `audit/reproduce_reliability.py` fail on the audited implementation. Run `python3 audit/reproduce_reliability.py` from the repository root. This script needs only the standard library, imports local modules, and never executes trajectory commands.
- **Pilot integrity:** 1,432 operations and 1,432 labels; 225 operations with candidates; 51 non-distinct labels; 21 candidate-redundant labels. These reproduce the saved 22.7% non-distinct share among matched operations and 3.6% among all operations. All non-error pilot labels satisfy the current evidence-reference validator. This establishes internal consistency, not semantic correctness.
- **Scale label integrity:** all eight saved scale label files parse, with no duplicate operation IDs within a file. Provenance separates LLM and rule assignments.
- **Limits:** no end-to-end regeneration, raw-trajectory loader audit, independent human annotation, or estimate of affected real-run frequency was possible from the supplied artifacts alone. Saved aggregate values were not treated as evidence that the underlying parsing is correct.

## What can be trusted now

| Use | Assessment |
|---|---|
| Exploring traces and generating hypotheses | Useful, with inspection of the underlying operations |
| Saved pilot arithmetic and basic label-file integrity | Checked and internally consistent |
| Exact-repeat and object-revisit statistics | Descriptive heuristics; still depend on loaders, parsing, and normalization |
| Code-version/backtrack/final-version summaries | Provisional until state and graph bugs are fixed and outputs rerun |
| A general claim that agents waste only about 1–2% of work | Not established by candidate-redundancy labels |
| Automated suppression of supposedly redundant actions | Not validated |

The next useful milestone is to fix the state/graph failures, rerun affected facts and downstream outputs, and validate candidate retrieval and contribution labels independently. Scaling the current labeling pipeline alone will not resolve these reliability gaps.
