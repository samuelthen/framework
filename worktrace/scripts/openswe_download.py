"""Download the Open-SWE-Traces v1.2 shards the Task 5 sample needs (results/v2/task5/sample_shards.csv) at the pinned
revision into raw/openswe_v12/, resumable (curl -C -), 4 at a time, each verified against the Hub's LFS sha256."""
import hashlib
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from huggingface_hub import HfApi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO, REV = "nvidia/Open-SWE-Traces", "a85dc97891bd18942ef6f3ab87750af99f487bba"
DST = f"{ROOT}/raw/openswe_v12"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def one(info):
    path, size, want = info.path, info.size, info.lfs.sha256
    out = f"{DST}/{path}"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{REV}/{path}"
    for attempt in range(5):
        if os.path.exists(out) and os.path.getsize(out) == size:
            break
        subprocess.run(["curl", "-sSL", "--retry", "5", "-C", "-", "-o", out, url])
    ok = os.path.exists(out) and os.path.getsize(out) == size and sha256(out) == want
    print(("OK " if ok else "BAD ") + path, flush=True)
    return path, ok


def main():
    files = list(pd.read_csv(f"{ROOT}/results/v2/task5/sample_shards.csv").file)
    infos = HfApi().get_paths_info(REPO, files, revision=REV, repo_type="dataset")
    print("files", len(infos), "GB", round(sum(i.size for i in infos) / 1e9, 2), flush=True)
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, sorted(infos, key=lambda i: i.path)))
    bad = [p for p, ok in res if not ok]
    print("DONE", len(res) - len(bad), "ok;", "bad:", bad, flush=True)


if __name__ == "__main__":
    main()
