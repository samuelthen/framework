"""Kind-dependent output normalization before hashing (B.2 step 3)."""
from __future__ import annotations

import hashlib
import re

_VOLATILE = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TS>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b"), "<TIME>"),
    (re.compile(r"\b\d+(?:\.\d+)?\s?(?:ms|s|sec|secs|seconds|µs|us|ns|m)\b(?=[\s)\]\.,=]|$)"), "<DUR>"),
    (re.compile(r"\bin \d+(?:\.\d+)?s\b"), "in <DUR>"),
    (re.compile(r"\(\d+(?:\.\d+)?s\)"), "(<DUR>)"),
    (re.compile(r"0x[0-9a-fA-F]{6,}"), "<ADDR>"),
    (re.compile(r"\b(?:pid|PID|process)[ =:]+\d+"), "pid=<PID>"),
    (re.compile(r"/tmp/[A-Za-z0-9_.\-/]+"), "<TMP>"),
    (re.compile(r"/var/folders/[A-Za-z0-9_.\-/]+"), "<TMP>"),
    (re.compile(r"\b[0-9a-f]{32,64}\b"), "<HASH>"),
    (re.compile(r"seed[ =:]+\d+", re.I), "seed=<SEED>"),
    (re.compile(r"\bok\s+(\S+)\s+\d+\.\d+s"), r"ok \1 <DUR>"),  # go test
]

TRUNC_MARKERS = ("<output_head>", "<elided_chars>", "[... Observation truncated", "Observations should not exceed",
                 "<response clipped>", "[Output truncated", "output was truncated", "characters elided")


def normalize(output: str, kind: str) -> str:
    if output is None:
        return ""
    if kind in ("run", "probe", "other", "submit"):
        s = output
        for rx, rep in _VOLATILE:
            s = rx.sub(rep, s)
        return s
    return output  # reads, searches, edits: byte-for-byte


def norm_hash(output: str, exit_code, kind: str) -> str:
    h = hashlib.sha1()
    h.update(normalize(output, kind).encode("utf-8", "replace"))
    if kind in ("run", "probe", "other"):
        h.update(f"\x00exit={exit_code}".encode())
    return h.hexdigest()[:16]


def is_truncated(output: str) -> bool:
    return bool(output) and any(m in output for m in TRUNC_MARKERS)


def norm_command(cmd: str) -> str:
    s = re.sub(r"\s+", " ", cmd or "").strip()
    for root in ("cd /app && ", "cd /testbed && ", "cd /app; ", "cd /testbed; "):
        if s.startswith(root):
            s = s[len(root):]
    return s
