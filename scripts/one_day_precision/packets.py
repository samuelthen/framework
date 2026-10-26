"""Section 4: blinded annotation packets for the frozen pilot tasks (calibration + evaluation).

Each packet holds the task reference (issue, SWE-bench Pro requirements/interface text, reference patch, fail-to-pass test
ids) and, for each of the two runs under a seeded anonymous label (run X / run Y), every executed tool action with its
command, exit code and output excerpt, plus the run's final submission. Model identity and earlier WorkTrace labels are
not shown; the key is written separately (packets/blinding_key.csv).

usage: python scripts/one_day_precision/packets.py   -> packets/<order>_<task>.md, packets/blinding_key.csv"""
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, ROOT, SEED, SHARD, log  # noqa: E402
from inventory import reference_table  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402

CMD_CHARS, OUT_HEAD, OUT_TAIL = 6000, 1200, 500


def _clip(s, n):
    s = s or ""
    return s if len(s) <= n else s[:n] + f"\n…[{len(s) - n} more chars]"


def _out(s):
    s = s or ""
    if len(s) <= OUT_HEAD + OUT_TAIL:
        return s
    return s[:OUT_HEAD] + f"\n…[{len(s) - OUT_HEAD - OUT_TAIL} chars omitted in this packet]…\n" + s[-OUT_TAIL:]


def load_runs(run_ids):
    want = {}
    for rid in run_ids:
        _, shard_model, inst, rep = rid.split(":")
        want.setdefault(f"{shard_model}-run{rep[1:]}", set()).add(inst)
    got = {}
    for shard, insts in want.items():
        for b in pq.ParquetFile(f"{ROOT}/raw/jetbrains/{shard}.parquet").iter_batches(batch_size=25):
            for row in b.to_pylist():
                if row["instance_id"] in insts:
                    run, ops = J.load_row(row)
                    got[run["run_id"]] = (run, ops, row.get("submission") or "")
    return got


def main():
    S = pd.read_csv(f"{OUT}/sample_manifest.csv")
    S = S[S.split.isin(["calibration", "evaluation"])]
    ref = reference_table()
    runs = load_runs(S.run_id)
    os.makedirs(f"{OUT}/packets", exist_ok=True)
    rng = np.random.default_rng(SEED)
    key = []
    for (order, task), g in S.groupby(["order", "task_id"]):
        g = g.sort_values("model")
        labels = ["X", "Y"] if rng.random() < 0.5 else ["Y", "X"]
        cfg, r = ref[task]
        lines = [f"# Packet {order} ({g.split.iloc[0]}): {task}", "",
                 "## Reference (SWE-bench Pro, config `%s`; base commit `%s`)" % (cfg, r.base_commit), "",
                 "### Problem statement", "", r.problem_statement.strip(), "",
                 "### Requirements text (dataset field)", "", str(r.requirements).strip(), "",
                 "### Interface (dataset field)", "", str(r.interface).strip(), "",
                 "### Fail-to-pass tests (ids only; not executed here)", "", str(r.fail_to_pass), "",
                 "### Reference patch (accepted solution evidence; one valid route)", "", "```diff", r.patch.strip(), "```", ""]
        for lab, row in sorted(zip(labels, g.itertuples()), key=lambda t: t[0]):
            run, ops, sub = runs[row.run_id]
            key.append({"order": order, "task_id": task, "label": lab, "run_id": row.run_id, "model": row.model})
            lines += [f"## Run {lab}: {len(ops)} actions; recorded outcome: resolved", ""]
            for i, o in enumerate(ops):
                lines += [f"### {lab}{i:03d}  (action {i}, exit {o['exit_code']}"
                          + (", output truncated for the agent" if o.get("agent_saw_truncated") else "") + ")",
                          "Thought (excerpt): " + _clip((o.get("agent_message") or "").strip().replace("\n", " "), 400), "",
                          "```", _clip(o["command"], CMD_CHARS), "```", "Output:", "```", _out(o["output"]), "```", ""]
            lines += [f"### Run {lab} final submission", "", "```diff", sub.strip() or "(empty)", "```", ""]
        with open(f"{OUT}/packets/{order:02d}_{task[:80]}.md", "w") as f:
            f.write("\n".join(lines))
    pd.DataFrame(key).to_csv(f"{OUT}/packets/blinding_key.csv", index=False)
    log(f"packets: {S.task_id.nunique()} tasks, {len(key)} runs, {sum(len(runs[r][1]) for r in S.run_id)} actions -> packets/")


if __name__ == "__main__":
    main()
