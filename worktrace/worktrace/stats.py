"""Cluster and paired bootstrap over tasks (B.7, D.7)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def cluster_bootstrap(df: pd.DataFrame, stat, cluster: str = "task_id", n: int = 1000, seed: int = 0):
    """stat: DataFrame -> float. Resample clusters with replacement, keep every row of a sampled cluster."""
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in df.groupby(cluster)}
    keys = np.array(list(groups))
    point = stat(df)
    if len(keys) < 2:
        return point, np.nan, np.nan
    vals = []
    for _ in range(n):
        s = rng.choice(keys, size=len(keys), replace=True)
        vals.append(stat(pd.concat([groups[k] for k in s])))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return point, lo, hi


def paired_bootstrap(df: pd.DataFrame, value: str, by: str, a, b, cluster: str = "task_id", n: int = 1000, seed: int = 0):
    """Per-task difference (mean over runs of a) - (mean over runs of b), bootstrapped over tasks present in both."""
    m = df.groupby([cluster, by])[value].mean().unstack(by)
    d = (m[a] - m[b]).dropna()
    rng = np.random.default_rng(seed)
    if len(d) < 2:
        return d.mean(), np.nan, np.nan, len(d)
    vals = [rng.choice(d.values, size=len(d), replace=True).mean() for _ in range(n)]
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return d.mean(), lo, hi, len(d)
