"""Work-progression graph: targets, edges, visit sequences (Stage 3, B.5, B.6, D.6)."""
from __future__ import annotations

import re

ROOT = "<root>"


def norm_purpose(p: str | None) -> str:
    p = (p or "unspecified").strip().lower()
    p = re.sub(r"[^a-z0-9 _./-]+", "", p)
    return "unspecified" if p in ("", "unspecified", "none", "n/a") else p


def target_of(op: dict, lab: dict | None, by: str = "target") -> str:
    """by='target': object::purpose (purpose may be unspecified); by='object': merge targets by object."""
    if by == "object":
        return op["object"]
    pur = norm_purpose((lab or {}).get("purpose"))
    return op["object"] if pur == "unspecified" else f"{op['object']}::{pur}"


def build_graph(run: dict, ops: list[dict], labels: dict[str, dict], by: str = "target") -> dict:
    nodes, edges = {ROOT: {"id": ROOT, "first_visit": -1, "visits": 0}}, []
    prev = ROOT
    for op in ops:
        lab = labels.get(op["op_id"], {})
        t = target_of(op, lab, by)
        if t not in nodes:
            nodes[t] = {"id": t, "object": op["object"], "kind": op["kind"], "first_visit": len(nodes) - 1, "visits": 0,
                        "row": 0}
        nodes[t]["visits"] += 1
        edges.append({"src": prev, "dst": t, "op_id": op["op_id"], "turn_id": op["turn_id"], "agent_id": "main",
                      "op_index": op["op_index"], "kind": op["kind"], "role": lab.get("role"),
                      "relation": lab.get("relation"), "contribution": lab.get("contribution"),
                      "matched_op": lab.get("matched_op"), "exact_repeat": op["exact_repeat"],
                      "self_loop": prev == t, "back_edge": prev != t and nodes[t]["visits"] > 1})
        prev = t
    # rows: a branch_out starts a new row
    row = 0
    for e in edges:
        if e["role"] == "branch_out":
            row += 1
        n = nodes[e["dst"]]
        if n["visits"] and n.get("_rowset") is None:
            n["row"], n["_rowset"] = row, True
    for n in nodes.values():
        n.pop("_rowset", None)
    gold = set(run.get("gold_file_list") or [])
    for n in nodes.values():
        n["gold"] = n.get("object") in gold
    last_edit = next((e["dst"] for e in reversed(edges) if e["kind"] == "edit"), None)
    if last_edit:
        nodes[last_edit]["final_edit"] = True
    return {"run_id": run["run_id"], "by": by, "nodes": list(nodes.values()), "edges": edges}


def visit_sequences(edges: list[dict]) -> dict[str, list[dict]]:
    """For each target: visits in order with contribution and #distinct other targets since the previous visit."""
    seq: dict[str, list[dict]] = {}
    last_pos: dict[str, int] = {}
    order = [e["dst"] for e in edges]
    for i, e in enumerate(edges):
        t = e["dst"]
        detours = None
        if t in last_pos:
            detours = len(set(order[last_pos[t] + 1:i]) - {t})
        seq.setdefault(t, []).append({"op_id": e["op_id"], "i": i, "contribution": e["contribution"],
                                      "relation": e["relation"], "detours": detours, "exact_repeat": e["exact_repeat"]})
        last_pos[t] = i
    return seq


def fmt_visits(v: list[dict]) -> str:
    code = {"distinct": "D", "non_distinct": "N", "uncertain": "U", None: "?"}
    out = []
    for x in v:
        if x["detours"]:
            out.append(f"({x['detours']} detour{'s' if x['detours'] > 1 else ''})")
        out.append(code.get(x["contribution"], "?"))
    return " ".join(out)
