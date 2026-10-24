"""LLM labeling, one call per operation (A.2, D.5). Resumable, cached by prompt hash."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import ValidationError

from .schema import Label, evidence_rule_errors

PROMPT_DIR = Path(__file__).parent
# 'low' for operations with a match candidate, 'off' for operations without one (see README)
REASONING = {"low": {"reasoning_effort": "low"}, "off": {"chat_template_kwargs": {"thinking": False, "enable_thinking": False}}}
SYSTEM = "You are a careful annotator of coding-agent trajectories. Answer with one JSON object and nothing else."


def short(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= 2 * n else s[:n] + "\n[...]\n" + s[-n:]


def sid(op: dict) -> str:
    """Short, local op id shown to the annotator."""
    return f"op{op['op_index']}"


def _cand_block(c: dict | None, n: int) -> str:
    if c is None:
        return "(none)"
    return (f"{sid(c)} (turn {c['turn_id'].rsplit(':t', 1)[-1]}):\n  Agent message: {short(c['agent_message'], 600)}\n"
            f"  Command: {short(c['command'], 800)}\n  Exit code: {c['exit_code']}\n  Result:\n{short(c['output'], n)}")


def fill_prompt(op: dict, by_id: dict, issue: str, template: str, n: int) -> str:
    ca, cb = by_id.get(op["cand_object"]), by_id.get(op["cand_output"])
    facts_vs = []
    for name, c in (("A", ca), ("B", cb)):
        if c is not None:
            f = op["cand_facts"][c["op_id"]]
            facts_vs.append(f"  vs {name} ({sid(c)}): same output={'yes' if f['same_output'] else 'no'}; "
                            f"this object written since={f['object_written_since']}; any code written since={f['any_code_written_since']}")
    return template.format(
        issue=short(issue, 1500), op_id=sid(op), turn=op["turn_id"].rsplit(":t", 1)[-1],
        message=short(op["agent_message"], 1000), command=short(op["command"], 1500), exit_code=op["exit_code"],
        result=short(op["output"], n), object=short(op["object"], 200), cand_a=_cand_block(ca, n),
        cand_b=_cand_block(cb, n) if (cb is not None and cb is not ca) else ("(same as candidate A)" if cb is not None else "(none)"),
        kinds=op["part_kinds"], mixed=str(op["mixed"]).lower(), write=op["write"],
        facts_vs="\n".join(facts_vs) or "  (no candidates)", n=n)


def fill_prompt_llm_only(op: dict, prev: list[dict], issue: str, template: str, n: int) -> str:
    """Baseline (B.8): no rule facts, no candidates; the annotator sees the last k earlier operations instead."""
    hist = "\n\n".join(f"{sid(p)}: Command: {short(p['command'], 300)}\n  Exit code: {p['exit_code']}\n  Result:\n{short(p['output'], 400)}" for p in prev) or "(none)"
    return template.format(issue=short(issue, 1500), op_id=sid(op), turn=op["turn_id"].rsplit(":t", 1)[-1],
                           message=short(op["agent_message"], 1000), command=short(op["command"], 1500),
                           exit_code=op["exit_code"], result=short(op["output"], n), history=hist)


class Client:
    def __init__(self, base_url: str, api_key: str, model: str, max_tokens: int = 2048, timeout: int = 180):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.model, self.max_tokens, self.timeout = model, max_tokens, timeout
        self.temperature = 0
        self.served_model = None
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
        self._lock = threading.Lock()

    def chat(self, prompt: str, reasoning: str = "low") -> str:
        body = {"model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens,
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}}
        body.update(REASONING[reasoning])
        for attempt in range(40):
            try:
                r = requests.post(self.url, headers=self.h, json=body, timeout=self.timeout)
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(min(2 + attempt, 15)); continue
                r.raise_for_status()
                j = r.json()
                with self._lock:
                    self.served_model = j.get("model")
                    u = j.get("usage") or {}
                    self.usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                    self.usage["completion_tokens"] += u.get("completion_tokens", 0)
                    self.usage["calls"] += 1
                return j["choices"][0]["message"]["content"] or ""
            except (requests.RequestException, KeyError, ValueError):
                if attempt >= 8:
                    raise
                time.sleep(min(2 + attempt, 15))
        raise RuntimeError("unreachable")


def parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object")
    return json.loads(m.group(0))


class Cache:
    def __init__(self, path: Path):
        self.path, self.d, self.lock = path, {}, threading.Lock()
        if path.exists():
            for line in path.open():
                try:
                    r = json.loads(line); self.d[r["key"]] = r["raw"]
                except (json.JSONDecodeError, KeyError):
                    pass

    def get(self, k):
        return self.d.get(k)

    def put(self, k, raw):
        with self.lock:
            self.d[k] = raw
            with self.path.open("a") as f:
                f.write(json.dumps({"key": k, "raw": raw}) + "\n")


def label_one(client: Client, cache: Cache, prompt: str, op: dict, by_short: dict, cands: set[str],
              prompt_version: str, retries: int = 2, check_rules: bool = True, reasoning: str = "low") -> dict:
    key = hashlib.sha1((client.model + prompt_version + reasoning + prompt).encode()).hexdigest()
    errs: list[str] = []
    for attempt in range(retries + 1):
        k = key if attempt == 0 else f"{key}:retry{attempt}"
        raw = cache.get(k)
        if raw is None:
            p = prompt if attempt == 0 else prompt + "\n\nYour previous answer was invalid: " + "; ".join(errs) + ". Fix it and return JSON only."
            raw = client.chat(p, reasoning)
            cache.put(k, raw)
        try:
            lab = Label(**parse_json(raw))
        except (ValueError, ValidationError, TypeError) as e:
            errs = [f"invalid JSON/schema: {str(e)[:200]}"]; continue
        # map short ids back to full op ids
        lab.matched_op = by_short.get(lab.matched_op, lab.matched_op) if lab.matched_op else None
        lab.evidence_refs = [by_short.get(r, r) for r in lab.evidence_refs]
        errs = evidence_rule_errors(lab, op["op_id"], cands) if check_rules else []
        if not errs:
            return {"op_id": op["op_id"], **lab.model_dump(), "label_error": False, "retries": attempt, "reasoning": reasoning}
    return {"op_id": op["op_id"], "purpose": "unspecified", "role": None, "relation": "uncertain", "matched_op": None,
            "contribution": "uncertain", "evidence_refs": [], "evidence": "; ".join(errs)[:300], "label_error": True,
            "retries": retries, "reasoning": reasoning}


def label_runs(runs: dict[str, tuple[dict, list[dict]]], out_path: Path, cache_path: Path, client: Client,
               prompt_version: str = "v1", n_chars: int = 2000, workers: int = 16, llm_only: bool = False,
               history_k: int = 10, reasoning_matched: str = "low", reasoning_unmatched: str = "off",
               only_matched: bool = False, op_filter=None, cache_tag: str = "") -> list[dict]:
    """cache_tag: appended to the prompt version in the cache key only (e.g. repeated samples at temperature > 0)."""
    template = (PROMPT_DIR / f"prompt_{prompt_version}.md").read_text()
    cache = Cache(cache_path)
    jobs = []
    for run_id, (run, ops) in runs.items():
        by_id = {o["op_id"]: o for o in ops}
        by_short = {sid(o): o["op_id"] for o in ops}
        for i, op in enumerate(ops):
            if llm_only:
                prompt = fill_prompt_llm_only(op, ops[max(0, i - history_k):i], run["issue"], template, n_chars)
                cands = {o["op_id"] for o in ops[max(0, i - history_k):i]}
            else:
                prompt = fill_prompt(op, by_id, run["issue"], template, n_chars)
                cands = {c for c in (op["cand_object"], op["cand_output"]) if c}
            has_cand = bool(op["cand_object"] or op["cand_output"])
            if only_matched and not has_cand:
                continue
            if op_filter is not None and not op_filter(op):
                continue
            jobs.append((prompt, op, by_short, cands, reasoning_matched if has_cand else reasoning_unmatched))
    out = []
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        # matched operations first, so the most informative labels arrive earliest
        jobs.sort(key=lambda j: j[4] != reasoning_matched)
        futs = [ex.submit(label_one, client, cache, p, op, bs, c, prompt_version + cache_tag, 2, not llm_only, rs) for p, op, bs, c, rs in jobs]
        for f in as_completed(futs):
            r = f.result()
            r.update({"annotator": client.served_model or client.model, "annotator_alias": client.model,
                      "prompt_version": prompt_version, "labeled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            out.append(r)
            done += 1
            if done % 100 == 0:
                print(f"  labeled {done}/{len(jobs)} ({time.time() - t0:.0f}s)", flush=True)
    order = {j[1]["op_id"]: i for i, j in enumerate(jobs)}
    out.sort(key=lambda r: order[r["op_id"]])
    with out_path.open("w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    return out


def client_from_env(env_file: str | None = None) -> Client:
    if env_file and os.path.exists(env_file):
        for line in open(env_file):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)
    return Client(os.environ["SOCLAAS_BASE_URL"], os.environ["SOCLAAS_API_KEY"], os.environ["SOCLAAS_MODEL"])
