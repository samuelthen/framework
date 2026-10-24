"""Download the CodeTraceBench verified-split SWE-bench artifacts at the pinned revision (one .tar.zst per trajectory)."""
import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from huggingface_hub import hf_hub_download

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REV = "aa213b84ffb6690fc37ca15766d6ca174ec36d4d"
D = f"{ROOT}/raw/codetracebench"
m = pd.read_parquet(f"{D}/bench_manifest.verified.parquet")
swe = m[m.source_relpath.str.startswith("swe_raw")]


def get(p):
    for attempt in range(5):
        try:
            return hf_hub_download("NJU-LINK/CodeTraceBench", p, repo_type="dataset", revision=REV, local_dir=D)
        except Exception as e:  # noqa: BLE001
            err = e
    print("FAILED", p, err, flush=True)


with ThreadPoolExecutor(4) as ex:
    for i, r in enumerate(ex.map(get, swe.artifact_path)):
        if i % 50 == 0:
            print(i, flush=True)
print("done", len(swe))
