"""Download the raw data the analyses and graphs are built from, at the pinned revisions (config.yaml `datasets`).

usage: download_data.py jetbrains    # 9 trajectory shards (~1.2 GB) -> raw/jetbrains/ + SWE-bench Pro gold patches -> raw/swebenchpro/
       download_data.py openswe      # Open-SWE-Traces v1.2 shards for the Task 5 sample (~20.7 GB) -> raw/openswe_v12/
       download_data.py all"""
import os
import shutil
import subprocess
import sys

import yaml
from huggingface_hub import hf_hub_download

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = yaml.safe_load(open(f"{ROOT}/worktrace/config.yaml"))["datasets"]
JB = "JetBrains-Research/SWE-TaskFlow-SWE-Bench-Pro-Trajectories"
SHARDS = [f"{m}-run{r}" for m in ("gemini_3_7_flash", "luna", "terra") for r in (1, 2, 3)]


def _get(repo, path, rev, dst):
    if os.path.exists(dst):
        print("have", dst)
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    p = hf_hub_download(repo, path, repo_type="dataset", revision=rev, local_dir=f"{ROOT}/raw/.hf")
    shutil.move(p, dst)
    print("got", dst, flush=True)


def jetbrains():
    for s in SHARDS:
        _get(JB, f"data/single_prompt/{s}.parquet", D["jetbrains_revision"], f"{ROOT}/raw/jetbrains/{s}.parquet")
    for cfg in ("default", "v1"):
        _get("ScaleAI/SWE-bench_Pro", f"data/{cfg}/test-00000-of-00001.parquet", D["swebench_pro_revision"],
             f"{ROOT}/raw/swebenchpro/{cfg}.parquet")


def openswe():
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "openswe_download.py")], check=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "jetbrains"
    if what in ("jetbrains", "all"):
        jetbrains()
    if what in ("openswe", "all"):
        openswe()
