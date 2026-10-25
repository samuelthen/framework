"""Build and draw the graphs of one run from the raw data: View A (operation graph by target and by object, with labels
when a label file has them) and View B (code-version graph, variant (b): support-only changes create no version).

Needs the raw data from scripts/download_data.py. JetBrains runs are read from raw/jetbrains/; Open-SWE runs from their
event log in data/events/openswe/ (built by `v2_task5.py events`).

usage: graph_run.py <run_id> [out_dir]     # e.g. graph_run.py 'jb:gemini_3_7_flash:instance_ansible__ansible-...:r1'
       graph_run.py --list [jetbrains|openswe] [n]   # print some run ids
Writes <out_dir>/<run>.graphs.json (view_a_target, view_a_object, view_b) and three PNGs; default out_dir figures/runs/."""
import glob
import json
import os
import sys

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.graph import build_graph  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402
from worktrace.versions import build_version_graph, support_candidates  # noqa: E402
from worktrace.viz.static import plot_labeled_trace, plot_run_graph  # noqa: E402
from worktrace.viz.versions import plot_version_graph  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAB = f"{ROOT}/data/labels"


def _safe(rid):
    return rid.replace(":", "__").replace("/", "_")


def load(run_id):
    if run_id.startswith("jb:"):
        shard = f"{run_id.split(':')[1]}-run{run_id.rsplit(':r', 1)[1]}"
        inst = run_id.split(":")[2]
        for b in pq.ParquetFile(f"{ROOT}/raw/jetbrains/{shard}.parquet").iter_batches(batch_size=25):
            for row in b.to_pylist():
                if row["instance_id"] == inst:
                    run, ops = J.load_row(row)
                    if run["run_id"] == run_id:
                        extract_facts(ops)
                        return run, ops
        raise KeyError(run_id)
    ev = f"{ROOT}/data/events/openswe/{_safe(run_id)}"
    run = json.load(open(f"{ev}.run.json"))
    return run, [json.loads(l) for l in open(f"{ev}.jsonl")]


def labels_for(run_id, ops):
    """The newest label file that covers this run: scale/Qwen-main labels, then pilot v2, then pilot v1."""
    ids = {o["op_id"] for o in ops}
    pats = (["scale_*.jsonl", "pilot_v2.jsonl", "pilot.jsonl"] if run_id.startswith("jb:")
            else ["qwen_main_*.jsonl", "qwen_pilot.jsonl"])
    for p in pats:
        for f in sorted(glob.glob(f"{LAB}/{p}")):
            if "model2" in f:
                continue
            got = {}
            for line in open(f):
                if line.startswith('{"op_id": "' + run_id + ":") or run_id in line[:300]:
                    r = json.loads(line)
                    if r["op_id"] in ids:
                        got[r["op_id"]] = r
            if got:
                return got, os.path.basename(f)
    return {}, None


def support_paths(run, ops):
    if run["run_id"].startswith("jb:"):
        S = pd.read_parquet(f"{ROOT}/data/submissions.parquet").set_index("run_id")
        sub = S.loc[run["run_id"]] if run["run_id"] in S.index else None
        files = list(sub.submission_files) if sub is not None else []
        new = list(sub.submission_new_files) if sub is not None else []
    else:  # Open-SWE: files of the submitted patch
        diff = run.get("submission") or ""
        files = [l.split(" b/", 1)[1] for l in diff.splitlines() if l.startswith("diff --git ") and " b/" in l]
        new = []
    return {p for p, v in support_candidates(ops, files, new).items() if v["candidate"]}


def main(run_id, out_dir=f"{ROOT}/figures/runs"):
    os.makedirs(out_dir, exist_ok=True)
    run, ops = load(run_id)
    labels, src = labels_for(run_id, ops)
    ga, go = build_graph(run, ops, labels, by="target"), build_graph(run, ops, labels, by="object")
    gb = build_version_graph(run, ops, labels, support_paths=support_paths(run, ops))
    base = f"{out_dir}/{_safe(run_id)}"
    json.dump({"run_id": run_id, "labels": src, "view_a_target": ga, "view_a_object": go, "view_b": gb},
              open(f"{base}.graphs.json", "w"), default=str)
    short = run_id.split(":")[1] + " " + run_id.split(":")[2][:50]
    plot_run_graph(go, f"{base}.view_a.png", title=f"View A (by object): {short}")
    plot_version_graph(gb, f"{base}.view_b.png", title=f"View B: {short}")
    if labels:
        plot_labeled_trace(run, ops, labels, f"{base}.trace.png")
    print(f"ops {len(ops)}, labels from {src or 'none (unlabelled run)'}\n  {base}.graphs.json\n  {base}.view_a.png\n  {base}.view_b.png"
          + (f"\n  {base}.trace.png" if labels else ""))


def list_runs(source="jetbrains", n="10"):
    f = f"{ROOT}/data/runs.parquet" if source == "jetbrains" else f"{ROOT}/results/v2/task5/runs.parquet"
    print("\n".join(pd.read_parquet(f, columns=["run_id"]).run_id.head(int(n))))


if __name__ == "__main__":
    if sys.argv[1] == "--list":
        list_runs(*sys.argv[2:])
    else:
        main(*sys.argv[1:])
