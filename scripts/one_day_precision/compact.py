"""Compact annotation views (packets_compact/): every action with its op kind, full command for edits and for commands
that write files, otherwise the first 500 command chars, and the head/tail of the output. Same blinding as packets/.
The full packets remain the review record; the annotator opened them where the compact view was insufficient.

usage: python scripts/one_day_precision/compact.py"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, log  # noqa: E402
from packets import load_runs  # noqa: E402
from worktrace.facts import extract_facts  # noqa: E402

WRITE = re.compile(r"cat\s*>|<<|sed\s+-i|\.write|write_text|>\s*\S+\.(py|js|ts|tsx|go|java|rb|json)|perl\s+-pi|tee\s|patch\s|git\s+(apply|checkout|stash|restore)")


def main():
    K = pd.read_csv(f"{OUT}/packets/blinding_key.csv")
    runs = load_runs(K.run_id)
    os.makedirs(f"{OUT}/packets_compact", exist_ok=True)
    for (order, task), g in K.groupby(["order", "task_id"]):
        lines = [f"# Compact packet {order}: {task}", "(reference: see packets/ full packet)", ""]
        for r in g.sort_values("label").itertuples():
            run, ops, sub = runs[r.run_id]
            extract_facts(ops)
            lines += [f"## Run {r.label}: {len(ops)} actions", ""]
            for i, o in enumerate(ops):
                c = o["command"] or ""
                full = o["kind"] in ("edit", "revert") or WRITE.search(c)
                cmd = c if full or len(c) <= 500 else c[:500] + f" …[+{len(c) - 500}]"
                out = o["output"] or ""
                out = out if len(out) <= 700 else out[:450] + f"\n…[{len(out) - 650} omitted]…\n" + out[-200:]
                lines += [f"### {r.label}{i:03d} kind={o['kind']} exit={o['exit_code']}" + (" TRUNC" if o.get("agent_saw_truncated") else ""),
                          "```", cmd, "```", "→ " + out.replace("\n", "\n  "), ""]
            lines += [f"## Run {r.label} final submission", "```diff", sub.strip() or "(empty)", "```", ""]
        with open(f"{OUT}/packets_compact/{order:02d}.md", "w") as f:
            f.write("\n".join(lines))
    log("compact packets written (packets_compact/)")


if __name__ == "__main__":
    main()
