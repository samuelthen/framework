"""Stage 4 signatures. Each is run -> list of matched operations (dicts with op_id, contribution, exact_repeat)."""
from __future__ import annotations

import re

from .graph import visit_sequences

_ERR_WORD = re.compile(r"error|exception|traceback|not found|no such file|unrecognized|invalid|cannot|can't|failed|fatal|"
                       r"denied|unknown option|usage:|syntax", re.I)
_ERR_STRONG = re.compile(r"^(Traceback \(most recent call last\)|E\s+(\w+\.)*\w*(Error|Exception)\b|(\w+\.)*\w*(Error|Exception)(: |$)|"
                         r"(error|fatal|ERROR|FATAL|FAILED)\b[: ]|.*: command not found$|.*[Nn]o such file or directory|"
                         r".*unrecognized option|.*[Pp]ermission denied)")
ERROR_LOOP_MIN = 3


def _m(e: dict, **kw) -> dict:
    return {"op_id": e["op_id"], "contribution": e["contribution"], "exact_repeat": e["exact_repeat"],
            "relation": e["relation"], **kw}


def new_to_new(g, ops, by_id):
    seen, out, prev_new = set(), [], False
    for e in g["edges"]:
        new = e["dst"] not in seen
        if new and prev_new:
            out.append(_m(e))
        prev_new = new
        seen.add(e["dst"])
    return out


def edit_test_identical_test(g, ops, by_id):
    """A run identical to an earlier run of the same command, no code written in between, where an edit preceded the
    earlier run (i.e. the earlier run already verified the edited code)."""
    out, first_edit = [], None
    for op in ops:
        if op["kind"] == "run":
            c = by_id.get(op["cand_object"])
            if c is not None and first_edit is not None and c["op_index"] > first_edit:
                f = op["cand_facts"].get(c["op_id"], {})
                if f.get("same_output") and f.get("any_code_written_since") == "no":
                    out.append(_m(op["_edge"]))
        elif op["kind"] in ("edit", "revert") and first_edit is None:
            first_edit = op["op_index"]
    return out


def returns(g, ops, by_id):
    """A visit to an earlier target that is not an immediate repeat (k >= 1 detours)."""
    out = []
    for t, vs in visit_sequences(g["edges"]).items():
        for v in vs[1:]:
            if v["detours"]:
                out.append({"op_id": v["op_id"], "contribution": v["contribution"], "exact_repeat": v["exact_repeat"],
                            "relation": v["relation"], "k": v["detours"]})
    return out


def self_repeats(g, ops, by_id):
    """Immediate repeats on the same target (self-loops), e.g. a test rerun."""
    return [_m(e) for e in g["edges"] if e["self_loop"]]


def return_distinct(g, ops, by_id):
    return [r for r in returns(g, ops, by_id) if r["contribution"] == "distinct"]


def return_non_distinct(g, ops, by_id):
    return [r for r in returns(g, ops, by_id) if r["contribution"] == "non_distinct"]


def informative_then_redundant(g, ops, by_id):
    """Targets whose later visits switch from distinct to non-distinct (a D return followed by an N visit)."""
    out = []
    for t, vs in visit_sequences(g["edges"]).items():
        if len(vs) < 3:
            continue
        seen_d = False
        for v in vs[1:]:
            if v["contribution"] == "distinct":
                seen_d = True
            elif v["contribution"] == "non_distinct" and seen_d:
                out.append({"op_id": v["op_id"], "contribution": v["contribution"], "exact_repeat": v["exact_repeat"],
                            "relation": v["relation"], "target": t})
    return out


def reread_unchanged(g, ops, by_id):
    """Re-reader candidate: a read/search whose object-candidate is unchanged since (object not written)."""
    out = []
    for op in ops:
        if op["kind"] not in ("read", "search"):
            continue
        for cid in (op["cand_object"], op["cand_output"]):
            if cid and op["cand_facts"].get(cid, {}).get("object_written_since") == "no" and op["cand_facts"][cid]["same_output"]:
                out.append(_m(op["_edge"]))
                break
    return out


def error_signature(op: dict) -> str | None:
    """Normalized error line of an operation, or None if it did not error. An op errors if its exit code is non-zero,
    and a line looks like an error message (with exit 0: a strong
    error line (e.g. a Python traceback printed by a script that exits 0).
    The line is the last strong error line, else the last line with an error word, else the last line. Normalized:
    lower case, whitespace collapsed, hex/addresses, timings and /tmp names replaced; other digits are kept."""
    lines = [l.strip() for l in (op.get("output") or "").splitlines() if l.strip()]
    if not lines:
        return None
    failed = op.get("exit_code") not in (0, None)
    if not failed and op.get("kind") == "read":
        return None  # file contents, not an error message
    strong = [l for l in lines if _ERR_STRONG.match(l)]
    if not failed and not strong:
        return None
    weak = [l for l in lines if _ERR_WORD.search(l)]
    if not (strong or weak):
        return None  # non-zero exit without an error line (e.g. a timeout mid-build): no error signature
    line = (strong or weak)[-1].lower()
    line = re.sub(r"0x[0-9a-f]+", "<hex>", line)
    line = re.sub(r"\b[0-9a-f]{12,}\b", "<hex>", line)
    line = re.sub(r"\bin \d+(\.\d+)?\s*(s|sec|seconds|ms)\b", "in <t>", line)
    line = re.sub(r"\(\d+(\.\d+)?\s*(s|ms)\)", "(<t>)", line)
    line = re.sub(r"/tmp/[^\s'\":]+", "/tmp/<tmp>", line)
    line = re.sub(r"\s+", " ", line)
    return line[:200]


def error_loops(ops: list[dict], min_len: int = ERROR_LOOP_MIN) -> list[list[dict]]:
    """Maximal runs of >= min_len consecutive operations with the same error signature, regardless of command."""
    out, cur, sig = [], [], None
    for op in ops:
        s = error_signature(op)
        if s is not None and s == sig:
            cur.append(op)
        else:
            if len(cur) >= min_len:
                out.append(cur)
            cur, sig = ([op], s) if s is not None else ([], None)
    if len(cur) >= min_len:
        out.append(cur)
    return out


def error_loop(g, ops, by_id):
    """Error Loop: the 2nd and later members of a run of >= 3 consecutive ops with the same error signature."""
    return [_m(op["_edge"], loop_start=loop[0]["op_index"], loop_len=len(loop)) for loop in error_loops(ops) for op in loop[1:]]


SIGNATURES = {
    "new_to_new": new_to_new,
    "self_repeat": self_repeats,
    "edit_test_identical_test": edit_test_identical_test,
    "return_any": returns,
    "return_distinct": return_distinct,
    "return_non_distinct": return_non_distinct,
    "informative_then_redundant": informative_then_redundant,
    "reread_unchanged_same_output": reread_unchanged,
    "error_loop": error_loop,
}


def run_signatures(g, ops):
    by_id = {o["op_id"]: o for o in ops}
    em = {e["op_id"]: e for e in g["edges"]}
    for o in ops:
        o["_edge"] = em[o["op_id"]]
    res = {name: fn(g, ops, by_id) for name, fn in SIGNATURES.items()}
    for o in ops:
        o.pop("_edge", None)
    return res
