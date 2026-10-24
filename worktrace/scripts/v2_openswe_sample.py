"""Task 5 sample: 2,000 instance_ids shared by OpenHands, SWE-agent and mini-SWE-agent in Open-SWE-Traces v1.2
(Qwen3.8-27B, revision a85dc97), seed 0; one run per harness per instance.
Runs with unknown `resolved` (-1; mini-SWE only) are dropped before the shared set is formed. Where a harness has
several runs of an instance (mini-SWE: 2.6 on average), one is drawn with the same seed.
Writes results/v2/task5/sample.csv (instance_id, harness, file, row) and the list of shards it needs."""
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = f"{ROOT}/results/v2/task5"
N, SEED = 2000, 0


def main():
    d = pd.read_parquet(f"{OUT}/openswe_ids.parquet")
    d = d[d.version == "v1.2"].copy()
    d["row"] = d.index  # position within its shard (the id inventory kept per-file order)
    d = d.reset_index(drop=True)
    known = d[d.resolved >= 0]
    sets = [set(g.instance_id) for _, g in known.groupby("harness")]
    shared = sorted(set.intersection(*sets))
    rng = np.random.default_rng(SEED)
    ids = sorted(rng.choice(shared, size=N, replace=False))
    k = known[known.instance_id.isin(ids)].sort_values(["harness", "instance_id", "file", "row"])
    k = k.assign(_r=rng.random(len(k)))  # one run per (harness, instance): the one with the smallest draw
    pick = k.sort_values("_r").groupby(["harness", "instance_id"]).head(1).sort_values(["harness", "instance_id"])
    pick = pick[["instance_id", "harness", "resolved", "file", "row"]].reset_index(drop=True)
    pick.to_csv(f"{OUT}/sample.csv", index=False)
    shards = sorted(pick.file.unique())
    pd.Series(shards, name="file").to_csv(f"{OUT}/sample_shards.csv", index=False)
    print("shared (known resolved):", len(shared), "| sampled ids:", len(ids), "| runs:", len(pick))
    print(pick.groupby("harness").agg(runs=("instance_id", "size"), resolved=("resolved", "mean")))
    print("shards needed:", len(shards), "of", d.file.nunique())


if __name__ == "__main__":
    main()
