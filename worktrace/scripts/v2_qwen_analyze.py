"""Qwen (Open-SWE-Traces v1.2) main-run analyses (user request 2026-10-25), 500 tasks x 3 harnesses, same tasks in each.
Labels: data/labels/qwen_main_<harness>.jsonl (primary annotator, prompt v1; unmatched ops rule-labelled `distinct`).

usage: v2_qwen_analyze.py build          # per-op / per-run tables, signatures, View B -> results/v2/qwen/main/
       v2_qwen_analyze.py report         # 1 headline, 2 read style, 3 post-submit, 4 return-after-k + Error Loop, 5 View B
       v2_qwen_analyze.py version_move   # prompt v2.1 on 300 sampled changes (100 per harness, seed 0)  [LLM]
       v2_qwen_analyze.py agree          # GLM (MODEL_2) vs primary on the 1,000-op sample, annotator range"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.graph import build_graph  # noqa: E402
from worktrace.measures import run_measures  # noqa: E402
from worktrace.signatures import run_signatures  # noqa: E402
from worktrace.versions import _merge, build_version_graph, support_candidates, version_sequence  # noqa: E402
from v2_task5 import _load  # noqa: E402
from v2_viewb import _rci, loop_rows  # noqa: E402
from v2_qwen import HARNESSES, main_runs  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAB, OUT = f"{ROOT}/data/labels", f"{ROOT}/results/v2/qwen/main"
REVISIT = ("revisits", "reproduces")


def _labels(h):
    return {r["op_id"]: r for r in map(json.loads, open(f"{LAB}/qwen_main_{h}.jsonl"))}


def read_style(op):
    """Read granularity of a read/search op: whole-file view, range read, grep/search, directory listing, other."""
    c = op["command"] or ""
    if c.startswith("tool:str_replace_editor view"):
        if "view_range" in c:
            return "range read"
        return "directory listing" if "files and directories" in (op["output"] or "")[:300] else "whole-file view"
    if op["kind"] == "search" or re.search(r"(^|[|;&]\s*)(grep|rg|ag|git grep|find)\b", c):
        return "grep / search"
    if re.search(r"\bsed\s+-n\b|\bhead\b|\btail\b|\bawk\s+'NR|\bnl\b.*\|\s*sed", c):
        return "range read"
    if re.search(r"(^|[|;&]\s*)(cat|less|more)\s+\S", c):
        return "whole-file view"
    if re.search(r"(^|[|;&]\s*)(ls|tree)\b", c):
        return "directory listing"
    return "other"


def _support(run, ops):
    diff = run.get("submission") or ""
    files = [l.split(" b/", 1)[1] for l in diff.splitlines() if l.startswith("diff --git ") and " b/" in l]
    return {p for p, v in support_candidates(ops, files, []).items() if v["candidate"]}


def build():
    S = main_runs()
    harness = S.set_index("run_id").harness.to_dict()
    ops_rows, meas, sig, loops, vb = [], [], [], [], []
    for h in HARNESSES:
        L = _labels(h)
        for rid in S[S.harness == h].run_id:
            run, ops = _load(rid)
            first_submit = next((o["op_index"] for o in ops if o["kind"] == "submit"), None)
            for o in ops:
                l = L[o["op_id"]]
                ops_rows.append({"run_id": rid, "task_id": run["task_id"], "harness": h, "op_id": o["op_id"],
                                 "op_index": o["op_index"], "n_ops": len(ops), "kind": o["kind"],
                                 "matched": bool(o["cand_object"] or o["cand_output"]), "exact_repeat": o["exact_repeat"],
                                 "read_style": read_style(o) if o["kind"] in ("read", "search") else None,
                                 "post_submit": first_submit is not None and o["op_index"] > first_submit,
                                 "contribution": l["contribution"], "relation": l["relation"],
                                 "label_error": l["label_error"], "label_source": l["label_source"]})
            meas.append({**run_measures(run, ops, L), "harness": h})
            g = build_graph(run, ops, L, by="object")
            for name, matches in run_signatures(g, ops).items():
                if name in ("return_any", "error_loop", "reread_unchanged_same_output", "self_repeat", "new_to_new"):
                    for mt in matches:
                        sig.append({"run_id": rid, "task_id": run["task_id"], "harness": h, "signature": name,
                                    "op_id": mt.get("op_id"), "contribution": mt.get("contribution"),
                                    "exact_repeat": mt.get("exact_repeat"), "k": mt.get("k")})
            loops += [r | {"harness": h} for r in loop_rows(run, ops)]
            sp = _support(run, ops)
            gv = build_version_graph(run, ops, support_paths=sp)
            final = next((n for n in gv["nodes"] if n.get("final")), None)
            steps = _merge(*version_sequence(ops, support_paths=sp))[0]
            vb.append({"run_id": rid, "task_id": run["task_id"], "harness": h, "resolved": run["resolved"] in (True, "True"),
                       "n_versions": gv["n_versions"], "verify_final": final["verify"] if final else 0,
                       "verify_total": sum(n["verify"] for n in gv["nodes"]),
                       "backtracks": sum(e["label"] == "backtrack" for e in gv["edges"]),
                       "n_support_files": len(sp), "n_steps": len(steps)})
        print(h, "done", flush=True)
    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame(ops_rows).to_parquet(f"{OUT}/ops.parquet")
    pd.DataFrame(meas).to_csv(f"{OUT}/run_measures.csv", index=False)
    pd.DataFrame(sig).to_csv(f"{OUT}/signature_matches.csv", index=False)
    pd.DataFrame(loops).drop(columns=["op_ids"], errors="ignore").to_csv(f"{OUT}/error_loops.csv", index=False)
    pd.DataFrame(vb).to_csv(f"{OUT}/viewb_runs.csv", index=False)


def _f(t, pct=True, d=1):
    return f"{100 * t[0]:.{d}f}% [{100 * t[1]:.{d}f}, {100 * t[2]:.{d}f}]" if pct else f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"


def _paired_diff(df, a, b, y, n=1000, seed=0):
    """Task-paired bootstrap of share(y | harness a) - share(y | harness b): the same resampled tasks for both."""
    t = df.groupby(["task_id", "harness"])[y].agg(["sum", "size"]).unstack("harness").fillna(0)
    Na, Da, Nb, Db = (t[("sum", a)].values, t[("size", a)].values, t[("sum", b)].values, t[("size", b)].values)
    pt = Na.sum() / Da.sum() - Nb.sum() / Db.sum()
    idx = np.random.default_rng(seed).integers(0, len(t), size=(n, len(t)))
    with np.errstate(invalid="ignore", divide="ignore"):
        v = Na[idx].sum(1) / Da[idx].sum(1) - Nb[idx].sum(1) / Db[idx].sum(1)
    lo, hi = np.nanpercentile(v, [2.5, 97.5])
    return pt, lo, hi


def r1_headline(O):
    rows, diffs = [], []
    O = O.assign(nd=(O.contribution == "non_distinct").astype(float), unc=(O.contribution == "uncertain").astype(float),
                 dist=(O.contribution == "distinct").astype(float), rev=O.relation.isin(REVISIT).astype(float))
    for subset, D in (("revisits (relation revisits or reproduces)", O[O.relation.isin(REVISIT)]), ("exact repeats", O[O.exact_repeat])):
        for h in HARNESSES:
            g = D[D.harness == h]
            rows.append({"subset": subset, "harness": h, "n": len(g), "distinct": _f(_rci(g, "dist")),
                         "non_distinct": _f(_rci(g, "nd")), "uncertain": _f(_rci(g, "unc"))})
        for a, b in (("openhands", "mini-swe-agent"), ("swe-agent", "mini-swe-agent"), ("swe-agent", "openhands")):
            diffs.append({"subset": subset, "comparison": f"{a} - {b}", "measure": "non-distinct share",
                          "diff_pts": "{:.1f} [{:.1f}, {:.1f}]".format(*(100 * x for x in _paired_diff(D, a, b, "nd")))})
    # work-level view: non-distinct revisits and all revisits as a share of all ops, and per run
    A = O.assign(nd_rev=O.nd * O.rev)
    for h in HARNESSES:
        g = A[A.harness == h]
        per_run = g.groupby(["run_id", "task_id"])[["nd_rev", "rev"]].sum().reset_index()
        rows.append({"subset": "all ops", "harness": h, "n": len(g), "revisit share of ops": _f(_rci(g, "rev")),
                     "non-distinct revisits, share of ops": _f(_rci(g, "nd_rev"), d=2),
                     "revisits per run": _f(_rci(per_run, "rev"), False), "non-distinct revisits per run": _f(_rci(per_run, "nd_rev"), False)})
    for a, b in (("openhands", "mini-swe-agent"), ("swe-agent", "mini-swe-agent")):
        for y, name in (("rev", "revisit share of ops"), ("nd_rev", "non-distinct revisit share of ops")):
            diffs.append({"subset": "all ops", "comparison": f"{a} - {b}", "measure": name,
                          "diff_pts": "{:.2f} [{:.2f}, {:.2f}]".format(*(100 * x for x in _paired_diff(A, a, b, y)))})
    T, D = pd.DataFrame(rows), pd.DataFrame(diffs)
    T.to_csv(f"{OUT}/1_headline.csv", index=False)
    D.to_csv(f"{OUT}/1_headline_paired_diffs.csv", index=False)
    print("\n## 1 headline\n", T.to_string(index=False), "\n", D.to_string(index=False))


def r2_read_style(O):
    R = O[O.kind.isin(["read", "search"])].assign(nd=lambda d: (d.contribution == "non_distinct").astype(float),
                                                  rev=lambda d: d.relation.isin(REVISIT).astype(float))
    rows = []
    for (h, s), g in R.groupby(["harness", "read_style"]):
        n_all = (O.harness == h).sum()
        rv = g[g.rev == 1]
        rows.append({"harness": h, "read_style": s, "ops": len(g), "share_of_all_ops": f"{100 * len(g) / n_all:.1f}%",
                     "revisits": len(rv), "revisits_share_of_all_ops": f"{100 * len(rv) / n_all:.1f}%",
                     "revisit_rate_within_style": f"{100 * len(rv) / max(1, len(g)):.1f}%",
                     "non_distinct_among_revisits": _f(_rci(rv, "nd")) if len(rv) > 1 else "n/a"})
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/2_read_style.csv", index=False)
    print("\n## 2 read style\n", T.to_string(index=False))


def r3_post_submit(O):
    W = O[O.harness == "swe-agent"].assign(nd=lambda d: (d.contribution == "non_distinct").astype(float),
                                          unc=lambda d: (d.contribution == "uncertain").astype(float))
    per = W.groupby("run_id").agg(post=("post_submit", "sum"), n=("op_id", "size"), sub=("kind", lambda k: (k == "submit").sum()))
    rows = [{"measure": "runs", "value": len(per)},
            {"measure": "runs with a submit", "value": int((per["sub"] > 0).sum())},
            {"measure": "runs with any op after the first submit", "value": int((per.post > 0).sum())},
            {"measure": "ops after the first submit (all runs)", "value": int(per.post.sum())},
            {"measure": "ops after the first submit, share of all ops", "value": f"{100 * per.post.sum() / per.n.sum():.1f}%"},
            {"measure": "ops after the first submit, per continuing run (mean / median)",
             "value": f"{per.post[per.post > 0].mean():.1f} / {per.post[per.post > 0].median():.0f}"}]
    for part, g in (("pre-submit", W[~W.post_submit]), ("post-submit", W[W.post_submit])):
        m = g[g.matched]
        rows += [{"measure": f"{part}: ops", "value": len(g)},
                 {"measure": f"{part}: matched share", "value": f"{100 * g.matched.mean():.1f}%"},
                 {"measure": f"{part}: non-distinct share of all ops", "value": _f(_rci(g, "nd"))},
                 {"measure": f"{part}: non-distinct share of matched ops", "value": _f(_rci(m, "nd"))},
                 {"measure": f"{part}: uncertain share of matched ops", "value": _f(_rci(m, "unc"))},
                 {"measure": f"{part}: op kinds", "value": ", ".join(f"{k} {100 * v:.0f}%" for k, v in g.kind.value_counts(normalize=True).head(6).items())}]
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/3_swe_agent_post_submit.csv", index=False)
    print("\n## 3 SWE-agent post-submit\n", T.to_string(index=False))


def r4_returns_and_loops(O):
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    S = pd.read_csv(f"{OUT}/signature_matches.csv")
    d = S[S.signature == "return_any"].merge(O[["op_id", "op_index", "n_ops"]], on="op_id")
    n_unc = int((d.contribution == "uncertain").sum())
    d = d[d.contribution.isin(["distinct", "non_distinct"])].copy()
    d["nd"] = (d.contribution == "non_distinct").astype(int)
    d["k_bin"] = pd.cut(d.k, [0, 1, 3, 1e9], labels=["1", "2-3", "4+"]).astype(str)
    d["rel_pos"] = d.op_index / (d.n_ops - 1).clip(lower=1)
    d["log_len"] = np.log(d.n_ops)
    raw, fits = [], []
    for (h, k), g in d.groupby(["harness", "k_bin"]):
        raw.append({"harness": h, "k_bin": k, "returns": len(g), "non_distinct": _f(_rci(g, "nd"))})
    f = "nd ~ C(k_bin, Treatment('1')) + rel_pos + log_len"
    for h in HARNESSES:
        g = d[d.harness == h]
        groups = pd.factorize(g.task_id)[0]
        r = smf.gee(f, groups=groups, data=g, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        ci = r.conf_int()
        ev = int(min(g.nd.sum(), len(g) - g.nd.sum()))
        k = len(r.params) - 1
        row = {"harness": h, "returns_used": len(g), "events": ev, "parameters": k, "events_per_parameter": round(ev / k, 1)}
        for t, nm in (("C(k_bin, Treatment('1'))[T.2-3]", "OR k2-3"), ("C(k_bin, Treatment('1'))[T.4+]", "OR k4+"),
                      ("rel_pos", "OR rel_pos"), ("log_len", "OR log_len")):
            row[nm] = f"{np.exp(r.params[t]):.2f} [{np.exp(ci.loc[t, 0]):.2f}, {np.exp(ci.loc[t, 1]):.2f}]"
        fits.append(row)
    R, F = pd.DataFrame(raw), pd.DataFrame(fits)
    R.to_csv(f"{OUT}/4_return_after_k_raw.csv", index=False)
    F.to_csv(f"{OUT}/4_return_after_k_gee.csv", index=False)
    # Error Loop: runs with >= 1 loop (3+ consecutive ops with the same error), and the error_loop signature's labels
    LP = pd.read_csv(f"{OUT}/error_loops.csv")
    M = pd.read_csv(f"{OUT}/run_measures.csv")
    el = []
    for h in HARNESSES:
        lp, sg = LP[LP.harness == h], S[(S.signature == "error_loop") & (S.harness == h)]
        el.append({"harness": h, "runs": int((M.harness == h).sum()), "runs_with_error_loop": f"{100 * lp.run_id.nunique() / (M.harness == h).sum():.1f}%",
                   "loops": len(lp), "mean_length": round(lp.length.mean(), 1) if len(lp) else None,
                   "error_loop_signature_matches": len(sg),
                   "non_distinct_share": f"{100 * (sg.contribution == 'non_distinct').mean():.1f}%" if len(sg) else "n/a"})
    E = pd.DataFrame(el)
    E.to_csv(f"{OUT}/4_error_loop.csv", index=False)
    print(f"\n## 4 return-after-k (uncertain dropped: {n_unc})\n", R.to_string(index=False), "\n", F.to_string(index=False),
          "\n", E.to_string(index=False))


def r5_viewb():
    V = pd.read_csv(f"{OUT}/viewb_runs.csv")
    rows = []
    for h, g in V.groupby("harness"):
        rows.append({"harness": h, "runs": len(g), "versions_per_run": _f(_rci(g, "n_versions"), False),
                     "median_versions": g.n_versions.median(), "runs_with_backtrack": f"{100 * (g.backtracks > 0).mean():.1f}%",
                     "verify_runs_on_final_version": _f(_rci(g, "verify_final"), False),
                     "verify_runs_total": _f(_rci(g, "verify_total"), False),
                     "final_share_of_verifies": f"{100 * g.verify_final.sum() / max(1, g.verify_total.sum()):.0f}%"})
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/5_viewb.csv", index=False)
    R = V.assign(nv=V.n_versions.clip(upper=6)).groupby(["harness", "nv"]).resolved.agg(["mean", "size"]).reset_index()
    R.to_csv(f"{OUT}/5_viewb_resolve_by_versions.csv", index=False)
    print("\n## 5 View B\n", T.to_string(index=False))
    p = Path(f"{LAB}/qwen_version_move_v2.1.jsonl")
    if p.exists():
        VM = pd.DataFrame(map(json.loads, open(p)))
        C = pd.crosstab(VM.harness, VM.version_move, normalize="index").mul(100).round(1)
        C["n"] = VM.groupby("harness").size()
        C.to_csv(f"{OUT}/5_version_move.csv")
        print(C.to_string())


def report():
    O = pd.read_parquet(f"{OUT}/ops.parquet")
    r1_headline(O); r2_read_style(O); r3_post_submit(O); r4_returns_and_loops(O); r5_viewb()


def version_move():
    """prompt v2.1 on 100 random changes per harness (variant a changes, as on the JetBrains pilot)."""
    import v2_prompt_v2 as P2
    from worktrace.label.annotate import Cache, client_from_env
    S = main_runs()
    rng = np.random.default_rng(0)
    its = []
    for h in HARNESSES:
        runs = {rid: _load(rid) for rid in S[S.harness == h].run_id}
        subs = {}
        for rid, (run, ops) in runs.items():
            diff = run.get("submission") or ""
            subs[rid] = ([l.split(" b/", 1)[1] for l in diff.splitlines() if l.startswith("diff --git ") and " b/" in l], [])
        P2.submissions = lambda subs=subs: subs
        allit = P2.items(runs, "v2.1")
        pick = rng.choice(len(allit), size=min(100, len(allit)), replace=False)
        its += [allit[i] | {"harness": h} for i in sorted(pick)]
        print(h, "changes", len(allit), flush=True)
        runs = None
    client = client_from_env(f"{ROOT}/soclaas.env")
    cache = Cache(Path(f"{LAB}/cache_qwen_version_move.jsonl"))
    with ThreadPoolExecutor(4) as ex:
        labs = list(ex.map(lambda it: P2.label_item(client, cache, it, "v2.1"), its))
    with open(f"{LAB}/qwen_version_move_v2.1.jsonl", "w") as f:
        for it, lab in zip(its, labs):
            f.write(json.dumps({k: it[k] for k in ("run_id", "task_id", "harness", "op_id", "op", "rule_label", "files",
                                                   "support_candidate", "resolved")} | lab
                               | {"annotator": client.served_model or client.model, "prompt_version": "v2.1"}, default=str) + "\n")
    print(len(its), "labels; errors", sum(l["label_error"] for l in labs), client.usage)


def agree():
    from v2_task4 import _compare
    ids = set(pd.read_csv(f"{OUT}/second_items.csv").op_id)
    M2 = {r["op_id"]: r for r in map(json.loads, open(f"{LAB}/qwen_main_model2.jsonl"))}
    P = {}
    for h in HARNESSES:
        P.update({k: v for k, v in _labels(h).items() if k in ids})
    items = pd.DataFrame({"op_id": sorted(ids), "matched": True})
    rows, conf = _compare(P, M2, items, "model2")
    A = pd.DataFrame([r for r in rows if r["subset"] in ("matched", "all") and r["n"]])
    A.to_csv(f"{OUT}/agree_model2.csv", index=False)
    print(A.to_string(index=False))
    print(conf[("contribution", "matched")])
    # annotator range of the candidate-redundancy rate, per harness: (matched share) x (cand-redundant share among sampled matched ops)
    O = pd.read_parquet(f"{OUT}/ops.parquet", columns=["op_id", "harness", "matched", "task_id"])
    hh = O.set_index("op_id").harness
    out = []
    cr = lambda l, hi: l["relation"] == "reproduces" and (l["contribution"] == "non_distinct" or (hi and l["contribution"] == "uncertain"))  # noqa: E731
    for h in HARNESSES:
        s = [i for i in ids if hh[i] == h]
        ms = O[O.harness == h].matched.mean()
        row = {"harness": h, "sampled_matched_ops": len(s), "matched_share_of_ops": f"{100 * ms:.1f}%"}
        for name, L in (("primary", P), ("model2", M2)):
            lo = np.mean([cr(L[i], False) for i in s if i in L])
            hi = np.mean([cr(L[i], True) for i in s if i in L])
            row[f"{name}: cand-redundant share of matched, lo-hi"] = f"{100 * lo:.1f}% - {100 * hi:.1f}%"
            row[f"{name}: implied rate (share of ops), lo-hi"] = f"{100 * lo * ms:.2f}% - {100 * hi * ms:.2f}%"
        out.append(row)
    R = pd.DataFrame(out)
    R.to_csv(f"{OUT}/annotator_range.csv", index=False)
    print(R.to_string(index=False))


if __name__ == "__main__":
    {"build": build, "report": report, "version_move": version_move, "agree": agree}[sys.argv[1]](*sys.argv[2:])
