"""JetBrains SWE-TaskFlow (SWE-bench Pro, mini-swe-agent, OpenAI Responses format) -> event log (D.3)."""
from __future__ import annotations

import json
import re

import pandas as pd

from ..resources import normalize_usage, response_ledger

REVISION = "a5ec6ad8428715a689ee62cf7cef82334773c958"
MODEL_NAMES = {"luna": "gpt-5.6-luna", "terra": "gpt-5.6-terra", "gemini_3_7_flash": "gemini-3.7-flash", "mini": "gpt-5.4-mini"}
INFRA_STATUSES = {"failed"}


def _issue_text(msgs: list[dict]) -> str:
    for m in msgs:
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, list):
                c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
            c = c or ""
            # keep only the issue, not the harness's submission instructions
            c = re.sub(r"^(<[a-z_]+>.*?</[a-z_]+>\s*)+", "", c, flags=re.S)
            return c.split("\nIssue phase for this user message.")[0].strip()
    return ""


def _agent_message(output: list[dict]) -> str:
    texts = []
    for o in output:
        if o.get("type") == "message":
            for c in o.get("content") or []:
                if isinstance(c, dict) and c.get("text"):
                    texts.append(c["text"])
        elif o.get("type") == "reasoning":
            for s in o.get("summary") or []:
                if isinstance(s, dict) and s.get("text"):
                    texts.append(s["text"])
    return "\n".join(texts).strip()


def load_row(row) -> tuple[dict, list[dict]]:
    """One dataset row -> (run record, list of operation events)."""
    model = MODEL_NAMES.get(row["model"], row["model"])
    run_id = f"jb:{row['model']}:{row['instance_id']}:r{int(row['run'])}"
    msgs = json.loads(row["messages"])
    results = {}
    for m in msgs:
        if m.get("type") == "function_call_output":
            ex = m.get("extra") or {}
            raw = ex.get("raw_output")
            results[m["call_id"]] = {
                "output": raw if raw is not None else (m.get("output") or ""),
                "agent_output": m.get("output") or "",
                "exit_code": ex.get("returncode"),
                "agent_saw_truncated": raw is not None and "<warning>" in (m.get("output") or "") and len(m.get("output") or "") < len(raw),
            }
    ops, turn_idx, n_turns, lost = [], 0, 0, 0
    for m in msgs:
        if m.get("object") != "response":
            continue
        n_turns += 1
        turn_id = f"{run_id}:t{turn_idx}"
        output = m.get("output") or []
        msg = _agent_message(output)
        k = 0
        for o in output:
            if o.get("type") != "function_call":
                continue
            try:
                args = json.loads(o.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {"command": o.get("arguments") or ""}
            cmd = args.get("command") if isinstance(args, dict) else str(args)
            if cmd is None:
                cmd = f"tool:{o.get('name')} {json.dumps(args)}"
            res = results.get(o["call_id"])
            if res is None:
                lost += 1
                res = {"output": "", "exit_code": None, "agent_saw_truncated": False}
            ops.append({
                "source": "jetbrains", "model": model, "harness": "mini-swe-agent",
                "task_id": row["instance_id"], "run_id": run_id, "turn_id": turn_id,
                "response_id": turn_id, "op_id": f"{turn_id}.{k}",
                "agent_message": msg if k == 0 else "(same turn as previous operation)",
                "tool": o.get("name") or "bash", "command": cmd, "exit_code": res["exit_code"], "output": res["output"],
                "agent_saw_truncated": res["agent_saw_truncated"], "missing_result": o["call_id"] not in results,
                "agent_output": res.get("agent_output", res["output"]),
            })
            k += 1
        turn_idx += 1
    run = {
        "source": "jetbrains", "model": model, "harness": "mini-swe-agent", "task_id": row["instance_id"],
        "run_id": run_id, "run_index": int(row["run"]), "resolved": bool(row["resolved"]) if row["reward"] is not None and not pd.isna(row["reward"]) else None,
        "status": row["status"], "exit_status": row.get("exit_status"),
        "input_tokens": _int(row.get("input_tokens")), "cached_input_tokens": _int(row.get("cached_input_tokens")),
        "output_tokens": _int(row.get("output_tokens")), "api_calls": _int(row.get("api_calls")),
        "cost_usd": float(row["cost_usd"]) if row.get("cost_usd") is not None else None,
        "n_turns": n_turns, "n_ops": len(ops), "lost_results": lost, "issue": _issue_text(msgs),
        "gold_files": None, "gold_lines": None,
    }
    return run, ops


def load_response_usage(row) -> list[dict]:
    """Separate response-level ledger; never copies shared usage onto tool ops.

    Existing load_row callers retain their return shape and run-level totals.
    Missing response usage is null even when a run total is available.
    """
    run_id = f"jb:{row['model']}:{row['instance_id']}:r{int(row['run'])}"
    messages = json.loads(row["messages"])
    ledger = response_ledger(messages, run_id)
    stored = [m for m in messages if m.get("object") == "response"]
    for record, message in zip(ledger, stored):
        extra_cost = (message.get("extra") or {}).get("cost")
        record["raw_extra_cost"] = extra_cost
        record["run_cost_source"] = row.get("cost_source")
        # Inspected SWE-TaskFlow payloads put harness-recorded response cost in
        # extra.cost. Gemini's public-map run costs coexist with zero response
        # placeholders: those zeros are not observations of free responses.
        if record["usage"]["cost_usd"] is not None:
            record["cost_provenance"] = "stored usage.cost_usd"
        elif row.get("cost_source") == "harbor_agent_result" and extra_cost is not None:
            record["usage"]["cost_usd"] = normalize_usage({"cost_usd": extra_cost})["cost_usd"]
            record["cost_provenance"] = "stored response extra.cost; harness-reported, not independently billed"
        else:
            record["cost_provenance"] = "unavailable; extra.cost not accepted for this run cost_source"
    return ledger


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def is_infra_failure(row) -> bool:
    return row["status"] in INFRA_STATUSES and (row.get("api_calls") or 0) == 0
