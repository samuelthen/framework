"""Files in each run's final submission diff (raw `submission` column) -> data/submissions.parquet."""
import glob
import os
import re

import pandas as pd
import pyarrow.parquet as pq

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
rows = []
for f in sorted(glob.glob(f"{ROOT}/raw/jetbrains/*.parquet")):
    t = pq.read_table(f, columns=["model", "instance_id", "run", "submission"]).to_pylist()
    for r in t:
        sub = r["submission"] or ""
        files = sorted(set(re.findall(r"^diff --git a/(\S+) b/", sub, re.M)))
        new = sorted(set(re.findall(r"^diff --git a/\S+ b/(\S+)\nnew file mode", sub, re.M)))
        rows.append({"run_id": f"jb:{r['model']}:{r['instance_id']}:r{int(r['run'])}", "submission_files": files,
                     "submission_new_files": new, "submission_empty": not sub.strip()})
d = pd.DataFrame(rows)
d.to_parquet(f"{ROOT}/data/submissions.parquet")
print(len(d), "runs;", d.submission_empty.mean(), "empty;", d.submission_files.map(len).mean(), "files/run")
