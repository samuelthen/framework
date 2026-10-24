"""Build an index (instance_id, harness, file, row, resolved, teacher) of Open-SWE-Traces v1.2 by reading only small columns."""
import sys, pandas as pd, pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
from concurrent.futures import ThreadPoolExecutor
REV = "a85dc97891bd18942ef6f3ab87750af99f487bba"
R = f"datasets/nvidia/Open-SWE-Traces@{REV}"
fs = HfFileSystem()
files = [(h, f) for h in ["openhands", "sweagent", "minisweagent"] for f in sorted(fs.glob(f"{R}/data/{h}/qwen38_27b/*/*.parquet"))]
def one(hf):
    h, f = hf
    t = pq.read_table(fs.open(f), columns=["instance_id", "trajectory_id", "resolved", "metadata"]).to_pandas()
    t["teacher"] = t["metadata"].map(lambda m: m["teacher_model"]["name"])
    t["gold_files"] = t["metadata"].map(lambda m: m["reference_patch"]["num_modified_files"])
    t["gold_lines"] = t["metadata"].map(lambda m: m["reference_patch"]["num_modified_lines"])
    t = t.drop(columns="metadata"); t["harness"] = h; t["file"] = f; t["row"] = range(len(t))
    print(h, f.split("/")[-2:], len(t), flush=True)
    return t
with ThreadPoolExecutor(8) as ex:
    df = pd.concat(list(ex.map(one, files)))
df.to_parquet(sys.argv[1])
print(df.groupby("harness").size(), df.teacher.value_counts())
