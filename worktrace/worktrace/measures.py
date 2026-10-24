"""Per-run measures (B.7). 'lo' counts uncertain as distinct, 'hi' counts uncertain as non-distinct."""
from __future__ import annotations


def _is_nd(lab, mode):
    c = lab.get("contribution")
    return c == "non_distinct" or (mode == "hi" and c == "uncertain")


def _is_cand_redundant(op, lab, mode):
    has_cand = bool(op["cand_object"] or op["cand_output"])
    rel = lab.get("relation")
    rel_ok = rel == "reproduces" or (mode == "hi" and rel == "uncertain" and has_cand)
    return rel_ok and _is_nd(lab, mode)


def run_measures(run: dict, ops: list[dict], labels: dict[str, dict]) -> dict:
    n = len(ops)
    labs = [labels.get(o["op_id"], {}) for o in ops]
    r = {"run_id": run["run_id"], "task_id": run["task_id"], "source": run["source"], "model": run["model"],
         "harness": run["harness"], "resolved": run.get("resolved"), "n_ops": n, "n_turns": run.get("n_turns")}
    if n == 0:
        return r
    r["exact_repeat_rate"] = sum(o["exact_repeat"] for o in ops) / n
    r["same_object_repeat_rate"] = sum(bool(o["cand_object"]) for o in ops) / n
    for mode in ("lo", "hi"):
        r[f"cand_redundancy_rate_{mode}"] = sum(_is_cand_redundant(o, l, mode) for o, l in zip(ops, labs)) / n
        # low-contribution tail: ops after the last distinct one, before submit
        sub = next((i for i in range(n - 1, -1, -1) if ops[i]["kind"] == "submit"), n)
        body = list(range(sub))
        distinct = [i for i in body if labs[i].get("contribution") == "distinct" or (mode == "lo" and labs[i].get("contribution") == "uncertain")]
        last_d = distinct[-1] if distinct else -1
        tail = max(0, sub - 1 - last_d)
        r[f"tail_ops_{mode}"] = tail
        r[f"tail_share_{mode}"] = tail / n
        k = max(1, round(0.2 * n))
        late = labs[n - k:]
        r[f"late_nd_rate_{mode}"] = sum(_is_nd(l, mode) for l in late) / len(late)
    r["uncertain_share_matched"] = (lambda m: sum(l.get("contribution") == "uncertain" or l.get("relation") == "uncertain" for l in m) / len(m) if m else None)(
        [l for o, l in zip(ops, labs) if o["cand_object"] or o["cand_output"]])
    r["n_matched"] = sum(bool(o["cand_object"] or o["cand_output"]) for o in ops)
    gold = set(run.get("gold_file_list") or [])
    if gold:
        opened = [i for i, o in enumerate(ops) if o["kind"] == "read" and o["object"] in gold]
        r["gold_opened"] = bool(opened)
        r["gold_first_open_frac"] = (opened[0] + 1) / n if opened else None
    return r
