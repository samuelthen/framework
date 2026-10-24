"""Open-SWE-Traces v1.2 (nvidia/Open-SWE-Traces, Qwen3.8-27B; OpenHands, SWE-agent, mini-swe-agent) -> event log.

All three harnesses are stored as OpenAI-style chat `messages` (role, content, reasoning_content, tool_calls).
Tool messages carry no tool_call_id, so results are paired with calls by position: the tool messages that follow an
assistant message answer its tool calls in order (checked: the only unpaired call per run is the final `finish` /
`submit`, which gets no reply). A turn is one assistant message; an operation is one tool call (or, for
mini-swe-agent, the bash block of the assistant message).
"""
from __future__ import annotations

import json
import re

REVISION = "a85dc97891bd18942ef6f3ab87750af99f487bba"
MODEL = "qwen3.8-27b"
HARNESS = {"openhands": "openhands", "sweagent": "swe-agent", "minisweagent": "mini-swe-agent"}

_OH_EXIT = re.compile(r"\[The command completed with exit code (-?\d+)\.\]")


def _editor_cmd(args: dict) -> str:
    sub, path = args.get("command", ""), args.get("path", "")
    extra = {k: v for k, v in args.items() if k not in ("command", "path")}
    body = "\n".join(f"{k}: {v}" for k, v in extra.items())
    return f"tool:str_replace_editor {sub} {path}" + (f"\n{body}" if body else "")


def _issue(msgs: list[dict]) -> str:
    c = next((m.get("content") or "" for m in msgs if m["role"] == "user"), "")
    m = (re.search(r"<issue_description>\n?(.*?)</issue_description>", c, re.S) or re.search(r"<pr_description>\n?(.*?)</pr_description>", c, re.S)
         or re.search(r"--- BEGIN ISSUE ---\n?(.*?)--- END ISSUE ---", c, re.S))
    return (m.group(1) if m else c).strip()


def _tool_cmd(name: str, raw_args: str) -> tuple[str, dict]:
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        args = {"command": raw_args or ""}
    if not isinstance(args, dict):
        args = {"command": str(args)}
    if name in ("execute_bash", "bash"):
        return args.get("command", ""), args
    if name == "str_replace_editor":
        return _editor_cmd(args), args
    return f"tool:{name} " + json.dumps(args)[:2000], args


def _calls_with_results(msgs: list[dict]):
    """Yield (turn index, assistant message, [(tool_call, result text or None)])."""
    t = 0
    for i, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        replies, k = [], i + 1
        while k < len(msgs) and msgs[k]["role"] == "tool":
            replies.append(msgs[k].get("content"))
            k += 1
        calls = m.get("tool_calls") or []
        yield t, m, [(tc, replies[j] if j < len(replies) else None) for j, tc in enumerate(calls)], len(replies)
        t += 1


def _op(run_id, turn, k, message, tool, command, output, exit_code, harness, task_id):
    tid = f"{run_id}:t{turn}"
    return {"source": "openswe", "model": MODEL, "harness": harness, "task_id": task_id, "run_id": run_id,
            "turn_id": tid, "op_id": f"{tid}.{k}", "agent_message": message if k == 0 else "(same turn as previous operation)",
            "tool": tool, "command": command, "exit_code": exit_code, "output": output or "",
            "agent_saw_truncated": False, "missing_result": output is None}


def _message_text(m: dict) -> str:
    return "\n".join(x for x in ((m.get("reasoning_content") or "").strip(), (m.get("content") or "").strip()) if x)


def load_openhands(row: dict, run_id: str) -> tuple[list[dict], int, int]:
    ops, lost, extra = [], 0, 0
    for t, m, pairs, n_replies in _calls_with_results(row["messages"]):
        extra += max(0, n_replies - len(pairs))
        for k, (tc, out) in enumerate(pairs):
            name = tc["function"]["name"]
            cmd, _ = _tool_cmd(name, tc["function"].get("arguments"))
            if out is None and name not in ("finish", "think"):
                lost += 1
            ec = _OH_EXIT.search(out or "")
            ops.append(_op(run_id, t, k, _message_text(m), "bash" if name == "execute_bash" else name, cmd, out,
                           int(ec.group(1)) if ec else None, "openhands", row["instance_id"]))
    return ops, lost, extra


def load_sweagent(row: dict, run_id: str) -> tuple[list[dict], int, int]:
    """SWE-agent: one tool call per assistant message (bash, str_replace_editor, submit). Observations start with
    'OBSERVATION:' and carry no exit code (exit_code stays None). The first `submit` returns the harness's review
    checklist; the last one gets no reply."""
    ops, lost, extra = [], 0, 0
    for t, m, pairs, n_replies in _calls_with_results(row["messages"]):
        extra += max(0, n_replies - len(pairs))
        for k, (tc, out) in enumerate(pairs):
            name = tc["function"]["name"]
            cmd, _ = _tool_cmd(name, tc["function"].get("arguments"))
            if name == "submit":
                cmd = "tool:submit"
            if out is None and name != "submit":
                lost += 1
            if out is not None:
                out = re.sub(r"^(OBSERVATION|Observation):\n?", "", out)
            ops.append(_op(run_id, t, k, _message_text(m), name, cmd, out, None, "swe-agent", row["instance_id"]))
    return ops, lost, extra


def _mini_result(content):
    """mini-swe-agent tool reply: JSON {returncode, output} or, when the harness truncated a long output,
    {returncode, output_head, output_tail, elided_chars, warning} (only the truncated view is stored)."""
    try:
        d = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return content, None, False
    if not isinstance(d, dict):
        return content, None, False
    if "output" in d:
        out, trunc = d.get("output") or "", False
    else:
        out = f"{d.get('output_head') or ''}\n[... {d.get('elided_chars')} characters elided ...]\n{d.get('output_tail') or ''}"
        trunc = True
    if d.get("exception_info"):
        out = f"{out}\n{d['exception_info']}".strip()
    rc = d.get("returncode")
    return out, int(rc) if isinstance(rc, (int, float)) or (isinstance(rc, str) and rc.lstrip("-").isdigit()) else None, trunc


def load_minisweagent(row: dict, run_id: str) -> tuple[list[dict], int, int]:
    """mini-swe-agent (tool-calling variant): `bash` tool calls; the final call (echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
    ...) gets no reply."""
    ops, lost, extra = [], 0, 0
    for t, m, pairs, n_replies in _calls_with_results(row["messages"]):
        extra += max(0, n_replies - len(pairs))
        for k, (tc, raw) in enumerate(pairs):
            name = tc["function"]["name"]
            cmd, _ = _tool_cmd(name, tc["function"].get("arguments"))
            out, rc, trunc = _mini_result(raw) if raw is not None else (None, None, False)
            if raw is None and "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" not in cmd:
                lost += 1
            o = _op(run_id, t, k, _message_text(m), name, cmd, out, rc, "mini-swe-agent", row["instance_id"])
            o["agent_saw_truncated"] = trunc
            ops.append(o)
    return ops, lost, extra


LOADERS = {"openhands": load_openhands, "sweagent": load_sweagent, "minisweagent": load_minisweagent}


def load_row(row: dict, harness: str) -> tuple[dict, list[dict]]:
    """One dataset row of the given harness directory -> (run record, operation events)."""
    run_id = f"os:{harness}:{row['instance_id']}:{row['trajectory_id'][:8]}"
    ops, lost, extra = LOADERS[harness](row, run_id)
    md = row.get("metadata") or {}
    ref = md.get("reference_patch") or {}
    run = {"source": "openswe", "model": MODEL, "harness": HARNESS[harness], "task_id": row["instance_id"],
           "run_id": run_id, "trajectory_id": row["trajectory_id"], "repo": row.get("repo"), "language": row.get("language"),
           "subset": row.get("hf_dataset_name"), "category": md.get("category"),
           "resolved": bool(row["resolved"]) if row["resolved"] in (0, 1) else None,
           "n_turns": sum(1 for m in row["messages"] if m["role"] == "assistant"), "n_ops": len(ops),
           "lost_results": lost, "unpaired_replies": extra, "issue": _issue(row["messages"]),
           "gold_files": ref.get("num_modified_files"), "gold_lines": ref.get("num_modified_lines"),
           "submission": (md.get("model_patch") or {}).get("patch"),
           "input_tokens": None, "output_tokens": None}
    return run, ops
