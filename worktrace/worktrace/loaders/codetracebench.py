"""CodeTraceBench (NJU-LINK/CodeTraceBench, verified split, SWE-bench trajectories) -> WorkTrace event log.

Step alignment with the human labels (step_id is 1-based):
- mini-SWE-agent: step i = the i-th assistant message (its bash block) and the next user message (observation).
- SWE-agent: step i = trajectory[i-1] (action, observation).
- OpenHands (per-LLM-call completion logs): step i = the i-th tool call in the message history of the log file with
  the longest history; its observation is the matching `tool` message. (Verified: the number of tool calls there
  equals the manifest step_count; see scripts/v2_ctb.py verify.)
Editor calls become pseudo-commands `tool:str_replace_editor <sub> <path> ...` that parse/shell.py classifies.
"""
from __future__ import annotations

import glob
import json
import os
import re

_BASH_BLOCK = re.compile(r"```(?:bash|sh)?\s*\n(.*?)```", re.S)
_RC = re.compile(r"<returncode>(-?\d+)</returncode>")
_OUT = re.compile(r"<output>\n?(.*?)</output>", re.S)
_OH_EXIT = re.compile(r"\[The command completed with exit code (-?\d+)\.\]")


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content or "")


def _editor_cmd(args: dict) -> str:
    sub, path = args.get("command", ""), args.get("path", "")
    extra = {k: v for k, v in args.items() if k not in ("command", "path")}
    body = "\n".join(f"{k}: {v}" for k, v in extra.items())
    return f"tool:str_replace_editor {sub} {path}" + (f"\n{body}" if body else "")


def _op(run_id, i, message, command, output, exit_code):
    return {"op_id": f"{run_id}:t{i}.0", "turn_id": f"{run_id}:t{i}", "step_id": i + 1, "agent_message": message or "",
            "tool": "bash", "command": command, "output": output or "", "exit_code": exit_code,
            "agent_saw_truncated": False, "missing_result": output is None}


def load_miniswe(path: str, run_id: str) -> tuple[list[dict], str]:
    t = json.load(open(path))
    msgs = t["messages"]
    issue = _text(next((m["content"] for m in msgs if m["role"] == "user"), ""))
    ops = []
    for i, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        txt = _text(m["content"])
        b = _BASH_BLOCK.findall(txt)
        cmd = b[0].strip() if b else ""
        thought = txt.split("```", 1)[0].strip()
        nxt = next((x for x in msgs[i + 1:i + 2] if x["role"] == "user"), None)
        obs = _text(nxt["content"]) if nxt else None
        rc = _RC.search(obs or "")
        out = _OUT.search(obs or "")
        ops.append(_op(run_id, len(ops), thought, cmd, out.group(1) if out else obs, int(rc.group(1)) if rc else None))
    return ops, issue


def load_sweagent(path: str, run_id: str) -> tuple[list[dict], str]:
    t = json.load(open(path))
    hist = t.get("history") or []
    issue = _text(next((m.get("content") for m in hist if m.get("role") == "user"), ""))
    ops = []
    for s in t["trajectory"]:
        a = (s.get("action") or "").strip()
        if a in ("submit", "exit_forfeit", "exit_cost", "exit_context"):
            a = "tool:submit" if a == "submit" else f"tool:{a}"
        elif a.startswith("str_replace_editor "):
            first, _, rest = a.partition("\n")
            a = "tool:" + first + (("\n" + rest) if rest else "")
        ops.append(_op(run_id, len(ops), s.get("thought"), a, s.get("observation"), None))
    return ops, issue


def load_openhands(run_dir: str, run_id: str) -> tuple[list[dict], str]:
    files = [f for f in glob.glob(os.path.join(run_dir, "*.json")) if re.search(r"-\d+\.\d+\.json$", f)]
    best = max(files, key=lambda f: (len(json.load(open(f)).get("messages") or []), f))
    msgs = json.load(open(best))["messages"]
    issue = _text(next((m["content"] for m in msgs if m["role"] == "user"), ""))
    results = {m.get("tool_call_id"): _text(m.get("content")) for m in msgs if m.get("role") == "tool"}
    ops = []
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            fn = tc["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            name = fn.get("name")
            if name == "execute_bash":
                cmd = args.get("command", "")
            elif name == "str_replace_editor":
                cmd = _editor_cmd(args)
            else:
                cmd = f"tool:{name} " + json.dumps(args)[:2000]
            out = results.get(tc.get("id"))
            ec = _OH_EXIT.search(out or "")
            ops.append(_op(run_id, len(ops), _text(m.get("content")), cmd, out, int(ec.group(1)) if ec else None))
    return ops, issue


def load(extracted_root: str, row) -> tuple[dict, list[dict]]:
    rel = row["source_relpath"]
    d = os.path.join(extracted_root, rel)
    run_id = f"ctb:{row['traj_id']}"
    if row["agent"] == "mini-SWE-agent":
        ops, issue = load_miniswe(glob.glob(os.path.join(d, "*.traj.json"))[0], run_id)
    elif row["agent"] == "SWE-agent":
        ops, issue = load_sweagent(glob.glob(os.path.join(d, "*.traj"))[0], run_id)
    else:
        ops, issue = load_openhands(d, run_id)
    for o in ops:
        o.update({"source": "codetracebench", "model": row["model"], "harness": row["agent"], "task_id": row["task_name"],
                  "run_id": run_id})
    unuseful = sorted({int(s) for st in row["incorrect_stages"] for s in (st.get("unuseful_step_ids") if st.get("unuseful_step_ids") is not None else [])})
    incorrect = sorted({int(s) for st in row["incorrect_stages"] for s in (st.get("incorrect_step_ids") if st.get("incorrect_step_ids") is not None else [])})
    run = {"source": "codetracebench", "run_id": run_id, "task_id": row["task_name"], "model": row["model"], "harness": row["agent"],
           "resolved": bool(row["solved"]), "issue": issue, "step_count": int(row["step_count"]), "n_ops": len(ops),
           "unuseful_steps": unuseful, "incorrect_steps": incorrect}
    return run, ops
