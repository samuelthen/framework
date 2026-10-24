"""prompt_v2 / v2.1: the `version_move` add-on label on code changes that move between versions in View B
(variant a: every write is a version). A separate call; the v1 labels are not touched.

usage: v2_prompt_v2.py examples     # v2 proposal: 10 examples (kept for the record)
       v2_prompt_v2.py label        # v2.1 on every pilot change (rule label initial / correct / revise / backtrack)
       v2_prompt_v2.py analyze      # distribution + hand-check sheet"""
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from worktrace.label.annotate import Cache, client_from_env, parse_json, short, sid  # noqa: E402
from worktrace.versions import build_version_graph, repo_write, support_candidates, write_paths  # noqa: E402
import m4_pilot as P  # noqa: E402

ROOT = P.ROOT
OUT = f"{ROOT}/results/v2/prompt_v2"
LDIR = Path(__file__).parent.parent / "worktrace/label"
N = 2000
VERSIONS = {"v2": ("prompt_v2_version_move.md", ("correct", "branch_out", "sidetrack", "uncertain")),
            "v2.1": ("prompt_v2_1_version_move.md", ("correct", "branch_out", "support", "sidetrack", "uncertain"))}


class VersionMove(BaseModel):
    version_move: Literal["correct", "branch_out", "support", "sidetrack", "uncertain"]
    evidence_refs: list[str] = []
    evidence: str = ""


def files(op):
    return write_paths(op) or (["(unknown)"] if op["write"] == "unknown" else [])


def submissions():
    d = pd.read_parquet(f"{ROOT}/data/submissions.parquet").set_index("run_id")
    return {r: (list(x.submission_files), list(x.submission_new_files)) for r, x in d.iterrows()}


def items(runs, version="v2.1", labels=("initial", "correct", "revise", "backtrack")):
    """Every change that moves to another version (variant a), with its prompt."""
    template = (LDIR / VERSIONS[version][0]).read_text()
    subs = submissions()
    out = []
    for rid, (run, ops) in runs.items():
        g = build_version_graph(run, ops)
        sc = support_candidates(ops, *subs.get(rid, ([], [])))
        by_idx = {o["op_index"]: o for o in ops}
        for e in g["edges"]:
            if e["label"] not in labels:
                continue
            op = by_idx[e["op_index"]]
            prev = [by_idx[m["op_index"]] for m in g["edges"] if m["op_index"] < e["op_index"] and m["dst"] != "final" and m["label"] != "noop"]
            hist = "\n".join(f"{sid(p)}: files={files(p)} exit={p['exit_code']}\n  Command: {short(p['command'], 300)}" for p in prev) or "(none: this is the first change)"
            runs_before = [o for o in ops[:e["op_index"]] if o["kind"] == "run" and not repo_write(o)]
            lr = runs_before[-1] if runs_before else None
            last = (f"{sid(lr)}: Command: {short(lr['command'], 300)}\n  Exit code: {lr['exit_code']}\n  Result:\n{short(lr['output'], 800)}"
                    if lr else "(none)")
            supp = [p for p in write_paths(op) if sc.get(p, {}).get("candidate")]
            kw = dict(issue=short(run["issue"], 1500), history=hist, last_run=last, op_id=sid(op),
                      turn=op["turn_id"].rsplit(":t", 1)[-1], message=short(op["agent_message"], 1000),
                      command=short(op["command"], 1500), exit_code=op["exit_code"], result=short(op["output"], N),
                      files=files(op), prev_files=sorted({f for p in prev for f in files(p)}),
                      last_failed="unknown" if lr is None else str(lr["exit_code"] not in (0, None)).lower(), n=N)
            if version == "v2.1":
                kw["support"] = supp or "none"
            out.append({"run_id": rid, "task_id": run["task_id"], "model": run["model"], "op_id": op["op_id"], "op": sid(op),
                        "rule_label": e["label"], "prompt": template.format(**kw), "command": op["command"],
                        "message": op["agent_message"], "files": files(op), "support_candidate": bool(supp),
                        "support_files": supp, "resolved": run.get("resolved")})
    return out


def label_item(client, cache, it, version):
    key = hashlib.sha1((client.model + f"{version}_version_move" + "low" + it["prompt"]).encode()).hexdigest()
    allowed = VERSIONS[version][1]
    err = ""
    for attempt in range(3):
        k = key if attempt == 0 else f"{key}:retry{attempt}"
        raw = cache.get(k)
        if raw is None:
            raw = client.chat(it["prompt"] if attempt == 0 else it["prompt"] + f"\n\nYour previous answer was invalid: {err}. Return JSON only.", "low")
            cache.put(k, raw)
        try:
            lab = VersionMove(**parse_json(raw)).model_dump()
            if lab["version_move"] not in allowed:
                raise ValueError(f"version_move must be one of {allowed}")
            if it["op"] not in lab["evidence_refs"]:
                raise ValueError("cite the current operation in evidence_refs")
            return lab | {"label_error": False, "retries": attempt}
        except Exception as ex:  # noqa: BLE001
            err = str(ex)[:200]
    return {"version_move": "uncertain", "evidence_refs": [], "evidence": f"invalid: {err}", "label_error": True, "retries": 2}


def label(version="v2.1"):
    os.makedirs(OUT, exist_ok=True)
    its = items(P.load_pilot(), version)
    client = client_from_env(f"{ROOT}/soclaas.env")
    cache = Cache(Path(f"{ROOT}/data/labels/cache_prompt_v2.jsonl"))
    with ThreadPoolExecutor(4) as ex:
        labs = list(ex.map(lambda it: label_item(client, cache, it, version), its))
    rows = [{k: it[k] for k in ("run_id", "task_id", "model", "op_id", "op", "rule_label", "files", "support_candidate", "support_files", "resolved")}
            | lab | {"annotator": client.served_model or client.model, "prompt_version": version} for it, lab in zip(its, labs)]
    with open(f"{ROOT}/data/labels/pilot_version_move_{version}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows), "labels; errors", sum(r["label_error"] for r in rows), "usage", client.usage)


def analyze(version="v2.1"):
    L = pd.DataFrame(map(json.loads, open(f"{ROOT}/data/labels/pilot_version_move_{version}.jsonl")))
    vals = list(VERSIONS[version][1])
    by_model = pd.crosstab(L.model, L.version_move, margins=True).reindex(columns=vals + ["All"], fill_value=0)
    by_rule = pd.crosstab(L.rule_label, L.version_move, margins=True).reindex(columns=vals + ["All"], fill_value=0)
    by_hint = pd.crosstab(L.support_candidate, L.version_move, margins=True).reindex(columns=vals + ["All"], fill_value=0)
    by_model.to_csv(f"{OUT}/v2_1_by_model.csv"); by_rule.to_csv(f"{OUT}/v2_1_by_rule_label.csv"); by_hint.to_csv(f"{OUT}/v2_1_by_support_hint.csv")
    # hand-check sheet: every branch_out / support / sidetrack / uncertain, plus 30 random correct (seed 0)
    rng = np.random.default_rng(0)
    corr = L[L.version_move == "correct"]
    pick = pd.concat([L[L.version_move != "correct"], corr.iloc[rng.choice(len(corr), size=min(30, len(corr)), replace=False)]])
    pick.to_csv(f"{OUT}/v2_1_handcheck_items.csv", index=False)
    print(by_model); print(by_rule); print(by_hint); print("hand-check items:", len(pick))


if __name__ == "__main__":
    {"label": label, "analyze": analyze}[sys.argv[1]](*sys.argv[2:])
