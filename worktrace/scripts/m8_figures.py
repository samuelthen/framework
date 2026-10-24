"""M8: pilot figures + self-contained viewer (D.8)."""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from m4_pilot import ROOT, _safe, load_pilot, read_labels  # noqa: E402
from worktrace.graph import target_of  # noqa: E402
from worktrace.label.annotate import short, sid  # noqa: E402
from worktrace.viz import static  # noqa: E402

FIG = f"{ROOT}/figures"


def main():
    os.makedirs(f"{FIG}/runs", exist_ok=True)
    runs, labels = load_pilot(), read_labels("pilot")
    M = pd.read_csv(f"{ROOT}/results/pilot/run_measures.csv")
    ST = pd.read_csv(f"{ROOT}/results/pilot/signatures.csv")
    MT = pd.read_csv(f"{ROOT}/results/pilot/measures_by_model.csv")
    MT = MT[MT.model != "ALL"]
    static.bar_by_model(MT, ["exact_repeat_rate", "same_object_repeat_rate", "cand_redundancy_rate_lo", "cand_redundancy_rate_hi"],
                        ["exact repeat", "same-object\nrevisit", "candidate redundant\n(lo)", "candidate redundant\n(hi)"],
                        f"{FIG}/repeat_vs_redundancy_by_model.png", "Repetition vs. candidate redundancy (pilot, share of ops)", "share of operations")
    static.bar_by_model(MT, ["tail_share_lo", "tail_share_hi", "late_nd_rate_lo", "late_nd_rate_hi"],
                        ["tail share (lo)", "tail share (hi)", "late non-distinct\n(lo)", "late non-distinct\n(hi)"],
                        f"{FIG}/tails_by_model.png", "Low-contribution tails (pilot)", "share")
    S = ST[(ST.by == "object") & (ST.matches > 0)].sort_values("matches", ascending=False)
    static.stacked_contribution([(f"{r.signature} (n={r.matches})", r.distinct, r.non_distinct, r.uncertain, r.exact_repeat_share)
                                 for r in S.itertuples()], f"{FIG}/signature_contribution_mix.png",
                                "Signature contribution mix vs. exact-repeat share (black tick)")
    # per-run graphs: top-3 runs by candidate redundancy per model, plus one random
    pick = M.sort_values("cand_redundancy_rate_hi", ascending=False).groupby("model").head(3).run_id.tolist()
    for rid in pick:
        g = json.load(open(f"{ROOT}/data/graphs/{_safe(rid)}.object.json"))
        run = runs[rid][0]
        static.plot_run_graph(g, f"{FIG}/runs/{_safe(rid)}.png",
                              title=f"{run['model']} · {run['task_id'][:60]} · resolved={run['resolved']}")
    # viewer
    data = {}
    for rid, (run, ops) in runs.items():
        data[rid] = {"label": f"{run['model']} · {run['task_id'][9:60]} · {len(ops)} ops · resolved={run['resolved']}",
                     "gold": run.get("gold_file_list") or [],
                     "ops": [{"sid": sid(o), "kind": o["kind"], "object": o["object"],
                              "target": target_of(o, labels.get(o["op_id"]), "target"),
                              "relation": labels.get(o["op_id"], {}).get("relation"),
                              "contribution": labels.get(o["op_id"], {}).get("contribution"),
                              "matched": (lambda m: f"op{m.rsplit('.', 1)[0].rsplit(':t', 1)[-1]}" if False else m)(labels.get(o["op_id"], {}).get("matched_op")),
                              "purpose": labels.get(o["op_id"], {}).get("purpose"),
                              "evidence": labels.get(o["op_id"], {}).get("evidence"),
                              "exact_repeat": o["exact_repeat"], "command": short(o["command"], 500),
                              "exit_code": o["exit_code"], "output": short(o["output"], 600)} for o in ops]}
        sid_of = {o["op_id"]: sid(o) for o in ops}
        for x in data[rid]["ops"]:
            x["matched"] = sid_of.get(x["matched"], x["matched"])
    html = open(os.path.join(os.path.dirname(__file__), "..", "worktrace", "viz", "viewer.html")).read()
    os.makedirs(f"{ROOT}/viewer", exist_ok=True)
    open(f"{ROOT}/viewer/index.html", "w").write(html.replace("/*DATA*/{}", json.dumps(data).replace("</", "<\\/")))
    print("figures ->", FIG, "; viewer ->", f"{ROOT}/viewer/index.html")


if __name__ == "__main__":
    main()
