"""Reconcile View B (variant b) final-version verify load with the tail measure (Gemini).

Each verify run on the final version (exactly the steps build_version_graph counts as the verify self-loop: a non-move
`run` step that is not a read-only inspection) is classed against the earlier verify runs on the same version:
  (i)   identical rerun: same command and same out_hash as an earlier run on that version;
  (ii)  same command, different output;
  (iii) different command.
The first verify run on the final version has no earlier run there, so it is class (iii) by definition; it is flagged
`first`. Class (iii) is split into rough sub-types by command (`subtype`).

usage: v2_reconcile.py pilot   # the 16 Gemini pilot runs, with v1 and v2 contribution labels and the tail measure
       v2_reconcile.py scale   # all Gemini JetBrains runs (facts only, no LLM)
Writes results/v2/reconcile/."""
import glob
import os
import re
import sys
from multiprocessing import Pool

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import m4_pilot as P  # noqa: E402
from v2_viewb import _rci  # noqa: E402
from worktrace.measures import run_measures  # noqa: E402
from worktrace.versions import _merge, build_version_graph, support_candidates, version_sequence  # noqa: E402

OUT = f"{P.ROOT}/results/v2/reconcile"
CLASSES = ("i_identical", "ii_same_cmd_diff_out", "iii_diff_cmd")


def subtype(cmd: str, earlier: list[str]) -> str:
    """Rough sub-type of a verify command (class iii is split by it)."""
    c = cmd.lower()
    if re.search(r"\b(lint|eslint|prettier|gofmt|go fmt|go vet|misc_checks|check-types|tsc|npm run types|flake8|mypy|pylint)\b", c):
        return "lint/format/type check"
    if re.search(r"\bgo build\b|go test -c\b|\bmake\b", c):
        return "build"
    if re.search(r"\b(python3?|node) -[ce]\b", c):
        return "inline check script"
    if re.search(r"\b(pytest|jest|go test|npm run test|yarn test)\b", c):
        tg = lambda x: {t for t in x.split() if "/" in t and not t.startswith("-") and "=" not in t}  # noqa: E731
        tgt, prev = tg(cmd), set().union(*map(tg, earlier)) if earlier else set()
        if not tgt or any(t.endswith("/") or "..." in t or not re.search(r"\.\w+$", t) for t in tgt):
            return "broader suite"
        return "same tests, other flags" if tgt <= prev else "other test file"
    return "other"


def classify_run(run, ops, sub):
    """Rows for the verify runs on the final version (variant b), plus the graph."""
    sc = support_candidates(ops, list(sub.submission_files) if sub is not None else [],
                            list(sub.submission_new_files) if sub is not None else [])
    sp = {p for p, v in sc.items() if v["candidate"]}
    g = build_version_graph(run, ops, support_paths=sp)
    seq, _ = _merge(*version_sequence(ops, support_paths=sp))  # the same steps build_version_graph counts
    final, rows, seen = g["final"], [], []  # seen: (command, out_hash) of earlier verify runs on the final version
    for o, s in zip(ops, seq):
        if s["after"] != final or final == 0 or s["move"] or s["kind"] != "run" or s["inspection"]:
            continue
        cmd = " ".join(o["command"].split())
        if (cmd, o["out_hash"]) in seen:
            cls = "i_identical"
        elif any(c == cmd for c, _ in seen):
            cls = "ii_same_cmd_diff_out"
        else:
            cls = "iii_diff_cmd"
        rows.append({"run_id": run["run_id"], "task_id": run["task_id"], "op_id": o["op_id"], "op_index": o["op_index"],
                     "first": not seen, "class": cls, "exit_code": o["exit_code"], "exact_repeat": bool(o["exact_repeat"]),
                     "subtype": subtype(cmd, [c for c, _ in seen]) if cls == "iii_diff_cmd" else "", "command": cmd[:160]})
        seen.append((cmd, o["out_hash"]))
    assert final == 0 or len(rows) == next(n["verify"] for n in g["nodes"] if n["v"] == final), run["run_id"]
    return rows, g


def run_row(run, g, R):
    return {"run_id": run["run_id"], "task_id": run["task_id"], "resolved": run.get("resolved"), "n_versions": g["n_versions"],
            "verify_final": len(R), "identical_reruns_final": sum(r["class"] == "i_identical" for r in R),
            "same_cmd_diff_out_final": sum(r["class"] == "ii_same_cmd_diff_out" for r in R),
            "diff_cmd_final": sum(r["class"] == "iii_diff_cmd" for r in R)}


def pilot(model="gemini"):
    os.makedirs(OUT, exist_ok=True)
    subs = pd.read_parquet(f"{P.ROOT}/data/submissions.parquet").set_index("run_id")
    v1, v2 = P.read_labels("pilot"), P.read_labels("pilot_v2")
    rows, per_run = [], []
    for rid, (run, ops) in P.load_pilot().items():
        if model not in run["model"]:
            continue
        R, g = classify_run(run, ops, subs.loc[rid] if rid in subs.index else None)
        for r in R:
            l1, l2 = v1.get(r["op_id"]) or {}, v2.get(r["op_id"]) or {}
            r.update({"contribution_v1": l1.get("contribution"), "relation_v1": l1.get("relation"), "contribution_v2": l2.get("contribution")})
        rows += R
        tail = run_measures(run, ops, v1)
        per_run.append(run_row(run, g, R) | {"tail_ops_lo": tail.get("tail_ops_lo"), "tail_ops_hi": tail.get("tail_ops_hi")})
    D, PR = pd.DataFrame(rows), pd.DataFrame(per_run)
    D.to_csv(f"{OUT}/final_verify_ops.csv", index=False)
    PR.to_csv(f"{OUT}/per_run.csv", index=False)
    pd.crosstab(D["class"], D.contribution_v1.fillna("none"), margins=True).to_csv(f"{OUT}/class_by_v1_contribution.csv")
    pd.crosstab(D["class"], D.contribution_v2.fillna("none"), margins=True).to_csv(f"{OUT}/class_by_v2_contribution.csv")
    iii = D[D["class"] == "iii_diff_cmd"]
    pd.crosstab(iii.subtype, iii["first"].map({True: "first on final", False: "later"}), margins=True).to_csv(f"{OUT}/class_iii_subtypes.csv")
    pd.set_option("display.width", 220)
    for f in ("class_by_v1_contribution", "class_by_v2_contribution", "class_iii_subtypes"):
        print(pd.read_csv(f"{OUT}/{f}.csv").to_string())
    print(PR.drop(columns=["run_id", "task_id"]).to_string())


def _scale_file(path):
    from worktrace.facts import extract_facts
    from worktrace.loaders import jetbrains as J
    subs = pd.read_parquet(f"{P.ROOT}/data/submissions.parquet").set_index("run_id")
    rows, per_run = [], []
    for row in (r for b in pq.ParquetFile(path).iter_batches(batch_size=25) for r in b.to_pylist()):
        if J.is_infra_failure(row):
            continue
        run, ops = J.load_row(row)
        extract_facts(ops)
        R, g = classify_run(run, ops, subs.loc[run["run_id"]] if run["run_id"] in subs.index else None)
        rows += [{k: v for k, v in r.items() if k != "command"} | {"command": r["command"][:80]} for r in R]
        per_run.append(run_row(run, g, R))
    return rows, per_run


def scale(model="gemini"):
    os.makedirs(OUT, exist_ok=True)
    with Pool(3, maxtasksperchild=1) as p:
        res = p.map(_scale_file, sorted(glob.glob(f"{P.ROOT}/raw/jetbrains/{model}*.parquet")))
    D = pd.DataFrame([r for rs, _ in res for r in rs])
    PR = pd.DataFrame([r for _, ps in res for r in ps])
    D.to_parquet(f"{OUT}/scale_final_verify_ops.parquet")
    PR.to_csv(f"{OUT}/scale_per_run.csv", index=False)
    M = PR[PR.n_versions >= 2]  # the View B summary's population for the final-version verify load
    out = []
    for name, d in (("all runs", PR), ("runs with >=2 versions", M)):
        r = {"population": name, "runs": len(d), "tasks": d.task_id.nunique(),
             "verify_final_per_run": _f(_rci(d, "verify_final"), pct=False)}
        for c, col in zip(CLASSES, ("identical_reruns_final", "same_cmd_diff_out_final", "diff_cmd_final")):
            r[f"{c}_per_run"] = _f(_rci(d, col), pct=False)
            r[f"{c}_share"] = _f(_rci(d, col, "verify_final"))
        r["runs_with_any_identical_rerun"] = _f(_rci(d, lambda x: (x.identical_reruns_final > 0).astype(float)))
        out.append(r)
    S = pd.DataFrame(out)
    S.to_csv(f"{OUT}/scale_summary.csv", index=False)
    Dm = D[D.run_id.isin(set(M.run_id))]
    iii = Dm[Dm["class"] == "iii_diff_cmd"]
    pd.crosstab(iii.subtype, iii["first"].map({True: "first on final", False: "later"}), margins=True).to_csv(f"{OUT}/scale_class_iii_subtypes.csv")
    dist = M.identical_reruns_final.clip(upper=5).value_counts(normalize=True).sort_index()
    dist.rename(index={5: "5+"}).to_csv(f"{OUT}/scale_identical_reruns_dist.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(S.T.to_string()); print(pd.read_csv(f"{OUT}/scale_class_iii_subtypes.csv").to_string()); print(dist)


def _f(t, pct=True):
    pt, lo, hi = t
    return f"{100 * pt:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]" if pct else f"{pt:.2f} [{lo:.2f}, {hi:.2f}]"


if __name__ == "__main__":
    {"pilot": pilot, "scale": scale}[sys.argv[1]](*sys.argv[2:])
