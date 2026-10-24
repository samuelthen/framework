# Task 3: return-after-k confounds (pilot, v2 labels, k unchanged)

**Data**
- Unit: every return in the pilot (signature `return_any`, object view). 153 returns; 2 have an `uncertain` contribution and are dropped, leaving 151.
- Outcome: 32 returns are non-distinct.
- Clusters: 17 tasks, 34 runs.
- `k` keeps its definition: the number of distinct other objects visited since the previous visit to the same object.
- Binned as 1 / 2–3 / 4+. The 2 and 3 bins each had n ≤ 15, so they are merged.

**Code:** `scripts/v2_task3.py`.

**Outputs**
- `coefficients.csv` (both models)
- `return_after_k_by_run_length.csv`

## Model: `non_distinct ~ k_bin + relative position + log(run length) + model`
Logistic GEE with exchangeable correlation and task clusters. A plain logit with task-clustered SEs gives the same picture.

| Term (reference) | Odds ratio | 95% CI | p |
|---|---|---|---|
| k = 2–3 (vs k = 1) | 32.7 | [2.3, 456] | 0.010 |
| k ≥ 4 (vs k = 1) | 14.5 | [1.1, 193] | 0.043 |
| relative position (0 → 1) | 0.07 | [0.02, 0.34] | 0.001 |
| log(run length) | 1.08 | [0.37, 3.16] | 0.89 |
| Luna (vs Gemini) | 0.04 | [0.002, 1.0] | 0.050 |
| Terra (vs Gemini) | 0.07 | [0.008, 0.58] | 0.014 |

**Reading**
- The k effect survives adjustment. Returns after at least 2 detours are more often non-distinct than returns after one detour.
  - The size is very uncertain: k = 1 has only 1 non-distinct return out of 31, so the odds ratios have very wide CIs.
- Run length does not explain the pattern.
- Relative position goes the opposite way to a "fatigue" story. Adjusted for k, returns late in a run are *less* often non-distinct.
- Most non-distinct returns are Gemini's. The model terms mainly separate Gemini from the GPT models.
- With 32 events, 6 parameters and 17 clusters, this is about 5 events per parameter. Treat it as a direction check, not an estimate.

## Return-after-k by run-length tercile
Terciles are computed over all 50 pilot runs. The cut points are 16 and 32 ops.

| Run length | k = 1 | k = 2–3 | k ≥ 4 |
|---|---|---|---|
| short (≤16 ops) | 0% (n=3) | 25% (n=4) | 0% (n=1) |
| medium (17–32) | 0% (n=10) | 5.6% [0, 25] (n=18) | 7.7% [0, 21] (n=13) |
| long (>32) | 5.6% [0, 20] (n=18) | 45.5% [22, 78] (n=11) | 31.5% [19, 42] (n=73) |

- The rise with k appears only in long runs, which are mostly Gemini.
- Short and medium runs have too few returns to show a pattern.
- These are LLM labels only. Nothing here is human-validated.
