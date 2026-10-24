"""Task 1 report: write='unknown' before/after, pilot test reruns with known code state, edit->test->identical test."""
import glob, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from worktrace.stats import cluster_bootstrap

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = f"{ROOT}/results/v2/task1"
os.makedirs(OUT, exist_ok=True)
v1 = pd.read_parquet(f"{ROOT}/data/v1_snapshot/ops_compact.parquet")
v2 = pd.read_parquet(f"{ROOT}/data/ops_compact.parquet")
rows = []
for name, d in (("v1", v1), ("v2", v2)):
    for m, g in list(d.groupby("model")) + [("ALL", d)]:
        rows.append({"facts": name, "model": m, "ops": len(g), **{f"write_{k}": (g.write == k).mean() for k in ("true", "false", "unknown")}})
W = pd.DataFrame(rows)
W.to_csv(f"{OUT}/write_shares.csv", index=False)

# what is still unknown (v2), by first command word
v2r = v2[v2.write == "unknown"]

# edit -> test -> identical test on unchanged code, at scale (v2 facts)
first_edit = v2[v2.kind.isin(["edit", "revert"])].groupby("run_id").op_index.min()
r = v2[(v2.kind == "run") & (v2.candA_kind == "run")].copy()
r["first_edit"] = r.run_id.map(first_edit)
r["sig"] = (r.candA_same_output == True) & (r.candA_code_since == "no") & (r.first_edit < r.candA_index)  # noqa: E712
r["state_known"] = r.candA_code_since.isin(["yes", "no"])
reruns = r.groupby("model").agg(test_reruns=("op_id", "size"), code_state_known=("state_known", "mean"),
                                same_output=("candA_same_output", "mean"), sig_matches=("sig", "sum"))
runs = pd.read_parquet(f"{ROOT}/data/runs.parquet")[["run_id", "task_id", "model"]]
hit = r.groupby("run_id").sig.any()
runs["has_sig"] = runs.run_id.map(hit).fillna(False).astype(bool)
prev = []
for m, g in runs.groupby("model"):
    pt, lo, hi = cluster_bootstrap(g, lambda d: d.has_sig.mean(), n=1000)
    prev.append({"model": m, "runs": len(g), "prevalence": pt, "ci": f"[{lo:.3f}, {hi:.3f}]"})
reruns = reruns.reset_index().merge(pd.DataFrame(prev), on="model")
reruns.to_csv(f"{OUT}/edit_test_identical_test_at_scale.csv", index=False)


# pilot: the test reruns (run op whose object-candidate is a run op), before vs after
def pilot(evdir):
    out = []
    for f in glob.glob(f"{evdir}/*.jsonl"):
        ops = [json.loads(l) for l in open(f)]
        by = {o["op_id"]: o for o in ops}
        fe = min((o["op_index"] for o in ops if o["kind"] in ("edit", "revert")), default=None)
        for o in ops:
            c = by.get(o["cand_object"])
            if o["kind"] == "run" and c is not None and c["kind"] == "run":
                fct = o["cand_facts"][c["op_id"]]
                out.append({"op_id": o["op_id"], "known": fct["any_code_written_since"] in ("yes", "no"),
                            "code_since": fct["any_code_written_since"], "same_output": fct["same_output"],
                            "sig": fct["same_output"] and fct["any_code_written_since"] == "no" and fe is not None and fe < c["op_index"]})
    return pd.DataFrame(out)
p1, p2 = pilot(f"{ROOT}/data/v1_snapshot/events/jetbrains"), pilot(f"{ROOT}/data/events/jetbrains")
P = {"v1": {"test_reruns": len(p1), "code_state_known": int(p1.known.sum()), "sig_matches": int(p1.sig.sum()), "code_since": p1.code_since.value_counts().to_dict()},
     "v2": {"test_reruns": len(p2), "code_state_known": int(p2.known.sum()), "sig_matches": int(p2.sig.sum()), "code_since": p2.code_since.value_counts().to_dict()}}
# which pilot ops changed facts (to relabel in Task 2)
changed = 0
for f in glob.glob(f"{ROOT}/data/events/jetbrains/*.jsonl"):
    a = {json.loads(l)["op_id"]: json.loads(l) for l in open(f.replace("/data/events/", "/data/v1_snapshot/events/"))}
    for l in open(f):
        o = json.loads(l)
        k = ("write", "cand_object", "cand_output", "cand_facts", "object", "part_kinds")
        changed += any(o[x] != a[o["op_id"]][x] for x in k)
P["pilot_ops_with_changed_facts"] = changed
json.dump(P, open(f"{OUT}/pilot_reruns.json", "w"), indent=1)
pd.set_option("display.width", 200)
print(W.round(4).to_string()); print(reruns.round(3).to_string()); print(json.dumps(P, indent=1))
print(v2r.assign(c=v2r.op_id).groupby("model").size())
