# Task 2: relabel the pilot under v2 facts

## What was done
- Only the 222 pilot ops whose facts changed in Task 1 were relabeled. These are ops where any of `write`, candidates, candidate facts, object or part kinds differ from `data/v1_snapshot`.
- The setup is otherwise unchanged: annotator `x-test-2` (deepseek-v4.1-flash), prompt v1, the same reasoning settings.
- The other 1,210 ops keep their v1 labels unchanged. This is guaranteed by construction: their prompts are byte-identical to v1.
- Labels:
  - `data/labels/pilot_v2_relabel.jsonl` holds the 222 relabeled ops.
  - `data/labels/pilot_v2.jsonl` is the merged set of 1,432.
  - `data/labels/pilot.jsonl` (v1) is untouched.
- The relabel took 222 calls with 0 label errors (524k prompt tokens, 53k completion tokens).
- View A graphs for v2 are in `data/graphs_v2/`; the v1 graphs in `data/graphs/` are untouched.

## What the relabel changed (`relabel_*_v1_vs_v2.csv`)
| v1 → v2 contribution | distinct | non_distinct |
|---|---|---|
| distinct | 201 | 0 |
| non_distinct | 4 | 13 |
| uncertain | 3 | 1 |

- **Relation:**
  - 3 v1 `uncertain` → `reproduces`, 1 `revisits` → `reproduces`, 2 `unmatched` → `revisits`.
  - The `uncertain` cases were ops where v1 code state was unknown.
- **Candidate-redundant ops: 17 → 21.** None were lost and 4 were gained.
- An automated audit by a third model (Claude) checked all 4 gained ops:
  - Two are test reruns where v1 had code state "unknown" after a `python -c` edit.
    - Example: Gemini ansible-502270c op 29 reruns op 26's `pytest test_hostname.py`. The output is identical, and between them there are only two pytest runs and no writes.
  - Two are re-reads of an unchanged file.

## Contribution tables (task-clustered 95% CIs, 1,000 resamples) — `contribution_tables.csv`

### (b) Matched ops (has a candidate), n = 225
| Model | ops | distinct | non-distinct | cand. redundant | exact repeat | non-distinct given exact repeat | non-distinct given not exact repeat |
|---|---|---|---|---|---|---|---|
| Gemini | 150 | 72.7% [66.1, 79.1] | 26.0% [20.8, 31.8] | 8.7% [4.6, 14.6] | 14.0% [8.7, 22.5] | 47.6% [23.5, 68.4] (n=21) | 22.5% [14.8, 29.3] |
| Luna | 41 | 75.6% [52.8, 100] | 24.4% [0.0, 47.2] | 19.5% [0.0, 38.2] | 0% | — (n=0) | 24.4% [0.0, 47.2] |
| Terra | 34 | 94.1% [86.1, 100] | 5.9% [0.0, 13.9] | 0% | 0% | — (n=0) | 5.9% [0.0, 13.9] |
| All | 225 | 76.4% [69.6, 82.8] | 22.7% [16.7, 29.6] | 9.3% [4.9, 15.5] | 9.3% [5.9, 14.1] | 47.6% [25.0, 69.2] | 20.1% [13.2, 27.6] |

### (a) All ops, n = 1,432
| Model | ops | distinct | non-distinct | cand. redundant | exact repeat |
|---|---|---|---|---|---|
| Gemini | 789 | 94.3% [92.7, 96.1] | 4.9% [3.3, 6.4] | 1.6% [0.8, 2.7] | 2.7% [1.7, 3.8] |
| Luna | 315 | 94.9% [91.8, 98.2] | 3.2% [0.0, 6.5] | 2.5% [0.0, 5.4] | 0% |
| Terra | 328 | 97.9% [95.7, 99.7] | 0.6% [0.0, 1.4] | 0% | 0% |
| All | 1,432 | 95.3% [93.9, 96.6] | 3.6% [2.5, 4.6] | 1.5% [0.8, 2.3] | 1.5% [0.9, 2.2] |

- **Exact repeats compared with candidate redundancy:**
  - 7 ops are both an exact repeat and candidate-redundant (v1: 4).
  - 14 exact repeats are not candidate-redundant.
  - 14 candidate-redundant ops are not exact repeats (v1: 13).
- **Uncertain share of matched ops:** 2.2% (v1: 4.9%).

## Other rates with CIs
- `measures_by_model.csv` gives per-run measures with CIs.
  - Candidate-redundancy rate, low and high bounds:
    - Gemini 1.9% [1.0, 3.0] / 2.4% [1.4, 3.4]
    - Luna 1.4% [0, 3.3]
    - Terra 0%
  - Late non-distinct rate: Gemini 4.7% [1.7, 8.3].
  - Tail ops: 0 for every model.
- `signatures_ci.csv` compares each signature's non-distinct share with its exact-repeat share. Signatures not defined by the labels:

  | Signature | matches | non-distinct − exact repeat |
  |---|---|---|
  | `reread_unchanged_same_output` | 12 | +75.0 pts [+16.7, +95.0] |
  | `self_repeat` | 60 | +13.3 [+4.0, +23.0] |
  | `return_any` | 153 | +7.2 [−1.4, +15.8] |

  The CI for `return_any` includes 0.
- `return_after_k_ci.csv` (Gemini):

  | k | n | non-distinct |
  |---|---|---|
  | 1 | 19 | 5.3% [0, 20] |
  | 2 | 5 | 80% |
  | 3 | 3 | 33% |
  | ≥4 | 76 | 30.3% [17.9, 43.0] |

  The k = 2 and k = 3 bins are too small to read. Task 3 models these confounds.
- These are LLM labels only. No result in this task is human-validated.
