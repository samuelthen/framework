"""Rule-computed facts per operation (Appendix A.1, B.3)."""
from __future__ import annotations

import hashlib

from .parse import shell
from .parse.normalize import is_truncated, norm_command, norm_hash

MIN_OUT_CHARS = 20


def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8", "replace")).hexdigest()[:12]


def _yn(v) -> str:
    return {True: "yes", False: "no"}.get(v, "unknown")


def extract_facts(ops: list[dict], min_out_chars: int = MIN_OUT_CHARS) -> list[dict]:
    """ops: event-log dicts in order, each with op_id, command, output, exit_code, (optional) truncated.
    Adds parts, part_kinds, mixed, kind, object, out_hash, truncated, write, written_paths, state, cand_object,
    cand_output, cand_facts, exact_repeat. Returns the same list."""
    last_by_object: dict[str, dict] = {}
    last_by_output: dict[tuple, dict] = {}
    last_write: dict[str, int] = {}
    unknown_writes: list[int] = []
    seen_exact: set[tuple] = set()
    state: str | None = "git:" + _sha1("")
    scripts: dict[str, str] = {}  # path -> source of scripts written by a heredoc earlier in the run

    def written_since(path, since_idx):
        if any(u > since_idx for u in unknown_writes):
            return "unknown"
        return last_write.get(path, -1) > since_idx

    def same_state(a_state, b_state):
        if a_state is None or b_state is None:
            return "unknown"
        return a_state == b_state

    for idx, op in enumerate(ops):
        op["op_index"] = idx
        parts = shell.split_chain(op["command"] or "") or [op["command"] or ""]
        kind, obj, kinds, _ = shell.main_kind_and_object(parts)
        op["parts"], op["part_kinds"], op["kind"], op["object"] = parts, kinds, kind, obj
        op["mixed"] = len({k for k in kinds if k != "other"}) > 1
        out = op.get("output") or ""
        op["out_hash"] = norm_hash(out, op.get("exit_code"), kind)
        op["truncated"] = bool(op.get("truncated")) or is_truncated(out)
        op["state"] = state

        cand_obj = last_by_object.get(obj)
        usable = (not op["truncated"]) and len(out.strip()) >= min_out_chars
        cand_out = last_by_output.get((kind, op["out_hash"])) if usable else None
        op["cand_object"] = cand_obj["op_id"] if cand_obj else None
        op["cand_output"] = cand_out["op_id"] if cand_out else None
        op["cand_facts"] = {}
        for c in (cand_obj, cand_out):
            if c is None or c["op_id"] in op["cand_facts"]:
                continue
            ss = same_state(c["state"], state)
            op["cand_facts"][c["op_id"]] = {
                "same_output": c["out_hash"] == op["out_hash"],
                "object_written_since": _yn(written_since(obj, c["op_index"])),
                "any_code_written_since": {True: "no", False: "yes"}.get(ss, "unknown"),
            }

        key = (norm_command(op["command"]), op["out_hash"])
        op["exact_repeat"] = key in seen_exact and kind != "submit"
        seen_exact.add(key)

        w, wpaths = shell.write_info(parts, scripts)
        op["write"] = {True: "true", False: "false"}.get(w, "unknown")
        op["written_paths"] = wpaths if w is True else []
        scripts.update(shell.heredoc_script_writes(parts))
        if w is True:
            for p in op["written_paths"]:
                last_write[p] = idx
            # writes outside the repository (e.g. /tmp helper scripts) do not change the code state
            if not op["written_paths"] or any(not p.startswith("/") for p in op["written_paths"]):
                state = None if state is None else f"{state}+w{idx}"
        elif w == "unknown":
            unknown_writes.append(idx)
            state = None
        if shell.is_state_probe(parts):
            state = "git:" + _sha1(out)

        last_by_object[obj] = op
        if usable:
            last_by_output[(kind, op["out_hash"])] = op
    return ops
