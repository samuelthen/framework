"""Task 5 inspection: instance_id (and resolved) per harness for Open-SWE-Traces v1.2 (Qwen3.8-27B) and v2.0
(Qwen3.8-Flash-Next), reading only those two columns of each shard at a pinned revision. No bulk download."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

REV = "9b4efcda46b8792216cc273b375be6b35418026d"  # main on 2026-10-24; v1.2 shards identical to a85dc97
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
fs = HfFileSystem()
R = f"datasets/nvidia/Open-SWE-Traces@{REV}"
jobs = [(v, h, f) for v, sub in (("v1.2", "qwen38_27b"), ("v2.0", "qwen38_flash_next"))
        for h in ("openhands", "sweagent", "minisweagent") for f in sorted(fs.glob(f"{R}/data/{h}/{sub}/*/*.parquet"))]


def one(j):
    v, h, f = j
    t = pq.read_table(fs.open(f), columns=["instance_id", "resolved"]).to_pandas()
    t["version"], t["harness"], t["file"] = v, h, f.split("@", 1)[1].split("/", 1)[1]
    print(v, h, len(t), flush=True)
    return t


with ThreadPoolExecutor(6) as ex:
    d = pd.concat(list(ex.map(one, jobs)))
d.to_parquet(f"{ROOT}/results/v2/task5/openswe_ids.parquet")
for v, g in d.groupby("version"):
    sets = {h: set(x.instance_id) for h, x in g.groupby("harness")}
    shared = set.intersection(*sets.values())
    known = g[g.resolved >= 0]
    print(v, {h: (len(x), x.instance_id.nunique()) for h, x in g.groupby("harness")}, "shared ids:", len(shared),
          "resolved known share:", round(len(known) / len(g), 3))
