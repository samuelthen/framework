"""View B: code-version graph (TRACE-style). Node = a distinct code version; edges = moves between versions.

- A repository write (write=true with a repo path, or write=unknown) creates a new version. Before that, View B
  resolves write=unknown for inline Node.js (`node -e` with fs.writeFileSync etc.) and JS/TS test/lint tools
  (parse/jsinline.py); the v2 facts and labels are not changed by this. An unknown write's
  version is flagged uncertain.
- A successful standalone restore can return to the root only when all dirty
  state is accounted for. Unknown effects survive partial restores. A stash
  records both its version and dirty paths. Status and diff text cannot prove
  complete content identity and never merge versions.
- Non-write operations attach to the current version as evidence. A `run` op is a verify self-loop, except inline
  Python that only reads files with stdlib imports (an inspection, counted as evidence, not a verify).
- Rule edge labels: initial (first move off the root), correct (new version after a failing run on the current
  version), revise (new version, no failing run: left for the LLM `version_move` add-on), backtrack (return to an
  earlier version), noop (a write that lands on the same version), final (submit).
- Layout as in TRACE: a new version goes one step right; a backtrack followed by a new version goes up one row.
"""
from __future__ import annotations

import hashlib
import re
import shlex

from .parse import shell

ROOT = 0
_FULL_REVERT = re.compile(r"^git\s+(reset\s+--hard(?:\s+HEAD)?$|checkout\s+(--\s+)?\.$|restore\s+(--staged\s+--worktree\s+)?\.$|stash(\s+(push|save)\b.*)?$)")
_STASH_POP = re.compile(r"^git\s+stash\s+(pop|apply)\b")
_CLEAN = "nothing to commit, working tree clean"


def _h(s: str) -> str:
    return hashlib.sha1((s or "").strip().encode("utf-8", "replace")).hexdigest()[:12]


def _is_artifact(path: str) -> bool:
    """The submission artifact (`git diff > patch.txt`), not a code change."""
    return (path.rsplit("/", 1)[-1] in ("patch.txt", "patch.diff") or path.endswith((".patch", ".diff", ".test"))
            or path in ("<build-artifact>", "") or path.startswith("node_modules/"))


def refine_unknown(op: dict):
    """View B only: resolve write='unknown' for inline Node.js and JS/TS tooling (see parse/jsinline.py).
    Parts not handled there keep their v2 fact; a part that the v2 facts already call a write keeps unknown."""
    from .parse import jsinline
    res, paths = False, []
    for part in op.get("parts") or [op.get("command") or ""]:
        r = jsinline.refine_part(part)
        if r is None:
            w, pp = shell.write_info([part])
            r = (w, pp)
        w, pp = r
        if w == "unknown":
            return "unknown", []
        if w is True:
            res = True
            paths += pp
    return res, paths


def repo_write(op: dict) -> bool | str:
    """True: writes the repository; 'unknown': may write it; False: no repository write (incl. /tmp-only writes)."""
    if op["write"] == "unknown":
        w, p = refine_unknown(op)
        if w == "unknown":
            return "unknown"
        if w is False:
            return False
        if p and all(_is_artifact(x) or x.startswith("/") for x in p):
            return False
        return (not p) or any(not x.startswith("/") and not _is_artifact(x) for x in p)
    if op["write"] == "true":
        p = op.get("written_paths") or []
        if p and all(_is_artifact(x) for x in p):
            return False
        return (not p) or any(not x.startswith("/") for x in p)
    return False


_STDLIB = {"os", "sys", "re", "json", "pathlib", "glob", "ast", "inspect", "textwrap", "difflib", "itertools", "collections",
           "io", "codecs", "tokenize", "fnmatch", "pprint", "yaml", "toml", "tomllib", "csv", "subprocess", "shutil"}


def is_inspection(op: dict) -> bool:
    """A `run` op that is really a read: inline Python that imports only stdlib modules and reads files
    (e.g. `python -c "print(open('a.py').read()[100:200])"`). Not a verification of the code."""
    import ast
    import warnings
    from .parse import pyinline
    for part in op.get("parts") or []:
        try:
            toks = shell._strip_prefix(shlex.split(part.split("<<", 1)[0] if "<<" in part.split("\n", 1)[0] else part))
        except ValueError:
            continue
        src = pyinline.python_source(toks, part) if toks else None
        if not src or src[0] != "inline":
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(src[1])
        except (SyntaxError, ValueError):
            return False
        mods = {(n.module or "") if isinstance(n, ast.ImportFrom) else a.name for n in ast.walk(tree)
                if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [n])}
        reads = any(isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) in ("open", "read_text", "readlines")
                    for n in ast.walk(tree))
        return reads and all(m.split(".")[0] in _STDLIB for m in mods)
    return False


def _content_probe(parts: list[str]) -> str | None:
    """'diff' for a whole-tree `git diff` (content), 'status' for a whole-tree `git status`, else None."""
    if not shell.is_state_probe(parts):
        return None
    toks = [t for p in parts for t in p.split()]
    if "status" in toks:
        return "status"
    if any(t in toks for t in ("--stat", "--name-only", "--short", "-s", "--porcelain")):
        return None
    return "diff"


def _revert_target(parts: list[str]):
    """('root',) | ('pop',) | ('paths', [..]) | None"""
    for p in parts:
        c = " ".join(p.split())
        if _STASH_POP.match(c):
            return ("pop",)
        if _FULL_REVERT.match(c):
            return ("root",)
    for p in parts:
        toks = p.split()
        if len(toks) >= 3 and toks[0] == "git" and toks[1] in ("checkout", "restore"):
            if toks[1] == "checkout" and "--" not in toks:
                continue  # path-like branch names are still ambiguous
            if toks[1] == 'restore' and any(t.startswith(('--staged', '--source', '-s')) for t in toks[2:]):
                continue  # index-only or non-baseline-source restore is not root
            paths = [shell.norm_path(t) for t in toks[2:] if not t.startswith("-") and t not in ("HEAD",)]
            if paths:
                return ("paths", paths)
    return None


def write_paths(op: dict) -> list[str]:
    """Repository paths an op writes (v2 facts, or the View B refinement of an unknown write)."""
    wp = op.get("written_paths") or (refine_unknown(op)[1] if op["write"] == "unknown" else [])
    wp = [p for p in wp if not p.startswith(("/", ">", "<", "&", "|")) and not _is_artifact(p)]
    return [p for p in wp if not any(q.startswith(p.rstrip("/") + "/") for q in wp)]  # drop a dir when a file in it is listed


_INPLACE = re.compile(r"\b(sed|perl)\s+(-\w*\s+)*-i|\bpatch\b|\bgit\s+apply\b")


def _deletes(op: dict, path: str) -> bool:
    for part in op.get("parts") or []:
        toks = part.split("\n", 1)[0].split()
        if toks and toks[0] in ("rm", "git") and (toks[0] == "rm" or toks[1:2] == ["rm"]):
            if any(shell.norm_path(t) == path for t in toks[1:] if not t.startswith("-")):
                return True
    return False


def support_candidates(ops: list[dict], submission_files: list[str] | None, submission_new: list[str] | None = None) -> dict:
    """Rule hint (not a label): a written repository file is a support candidate if it is new (not in the original
    repo) and is either deleted later in the run or absent from the final submission diff.
    New = the submission marks it as a new file, or before its first write it never appeared as an op's object or
    in any op's output, and the first write is not an in-place edit (sed -i, patch, git apply).
    Returns {path: {"new": bool, "deleted_later": bool, "in_submission": bool, "candidate": bool}}."""
    sub, sub_new = set(submission_files or []), set(submission_new or [])
    first: dict[str, int] = {}
    for i, op in enumerate(ops):
        if repo_write(op) is True or (op["write"] == "unknown" and refine_unknown(op)[0] is True):
            for p in write_paths(op):
                first.setdefault(p, i)
    out = {}
    for p, i in first.items():
        if p in sub_new:
            new = True
        elif p in sub:
            new = False
        else:
            seen = any(o.get("object") == p or p in (o.get("output") or "") for o in ops[:i])
            new = not seen and not _INPLACE.search(ops[i].get("command") or "")
        deleted = any(_deletes(o, p) for o in ops[i + 1:])
        out[p] = {"new": new, "deleted_later": deleted, "in_submission": p in sub,
                  "candidate": new and (deleted or p not in sub)}
    return out


def version_sequence(ops: list[dict], unknown_creates_version: bool = True, support_paths: set | None = None) -> list[dict]:
    """First pass: a provisional version id per op (the version the op runs on, and the one it leaves), plus the
    content hashes observed on each provisional version. Returns per-op dicts.
    support_paths (variant b): a write whose repository paths are all support files creates no version; it is kept
    as evidence (kind 'support') on the current version."""
    cur, nxt = ROOT, 1
    dirty: set[str] = set()          # repo files written since the last return to the root
    stash: list[tuple[int, set[str]]] = []
    uncertain: set[int] = set()
    baseline_tracked: set[str] = set()
    baseline_clean = False
    pristine = True
    seq = []
    for op in ops:
        parts = op.get("parts") or [op.get("command") or ""]
        before = cur
        if pristine and op.get('exit_code') == 0 and not any(
                op.get(k) for k in ('truncated', 'agent_saw_truncated', 'missing_result')) and len(parts) == 1:
            toks = shell._tokens(parts[0])
            out = op.get('output') or ''
            if toks in (['git', 'ls-files'], ['git', 'ls-files', '--cached']):
                baseline_tracked.update(shell.norm_path(p) for p in out.splitlines()
                                        if p and not p.startswith('"') and '\\' not in p)
            if toks in (['git', 'status'], ['git', 'status', '--short'],
                        ['git', 'status', '--porcelain'], ['git', 'status', '--porcelain=v1']):
                baseline_clean = (_CLEAN in out or (len(toks) > 2 and not out.strip()))
        w = repo_write(op)
        if w == "unknown" and not unknown_creates_version:
            # A version-count sensitivity must not erase restore-scope doubt.
            dirty.add(f"<unknown:{op['op_index']}>")
            uncertain.add(cur)
            pristine = False
            w = False
        kind = op["kind"]
        if support_paths and w is True:
            wp = write_paths(op)
            if wp and all(p in support_paths for p in wp):
                w, kind = False, "support"
        move = None
        rv = _revert_target(parts) if op["kind"] == "revert" or any(k == "revert" for k in op.get("part_kinds", [])) else None
        # Whole-call success does not establish the outcome of an interior
        # restore in a compound command. A failed restore may mutate partially.
        if rv and (op.get("exit_code") != 0 or len(parts) != 1):
            rv, w = None, "unknown"
        if rv and rv[0] in ('root', 'paths'):
            # checkout/restore use the index; reset/stash cover tracked files.
            # None of these establishes removal of unknown/untracked files.
            # Initial status/ls-files observations are used only as baseline
            # scope evidence, never to reanchor a changed repository by text.
            covered = baseline_clean and all(p in baseline_tracked for p in dirty)
            if not covered:
                rv, w = None, 'unknown'
        if w == 'unknown' and not unknown_creates_version:
            dirty.add(f"<unknown:{op['op_index']}>")
            uncertain.add(cur)
            pristine = False
            w = False
        if rv and rv[0] == "root":
            if " ".join(parts[0].split()).startswith("git stash") and not dirty:
                rv = None  # stash of a clean tree: nothing happens
            else:
                if parts and " ".join(parts[0].split()).startswith("git stash"):
                    stash.append((cur, set(dirty)))
                if any(p.startswith("<unknown:") for p in dirty):
                    # A tracked-tree restore does not clear unknown side effects
                    # or untracked files. Keep their uncertainty alive.
                    rv, w = None, "unknown"
                else:
                    cur, move, dirty = ROOT, "restore", set()
        elif rv and rv[0] == "pop":
            if stash:
                (cur, dirty), move = stash.pop(), "restore"
            else:
                cur, nxt, move = nxt, nxt + 1, "write"
                uncertain.add(cur)
        elif rv and rv[0] == "paths":
            dirty -= set(rv[1])
            if not dirty:
                cur, move = ROOT, "restore"
            else:
                cur, nxt, move = nxt, nxt + 1, "write"
        if move is None and w:
            cur, nxt, move = nxt, nxt + 1, "write"
            if w == "unknown":
                uncertain.add(cur)
                dirty.add(f"<unknown:{op['op_index']}>")
            else:
                wp = op.get("written_paths") or (refine_unknown(op)[1] if op["write"] == "unknown" else [])
                dirty |= {p for p in wp if not p.startswith("/")} or {f"<op{op['op_index']}>"}
        if w or move:
            pristine = False
        h = None
        # Neither status nor plain git diff establishes complete content
        # identity. In particular, do not collapse versions on truncated diffs,
        # staged-content omissions, or absent untracked files.
        seq.append({"op_index": op["op_index"], "op_id": op["op_id"], "kind": kind, "before": before, "after": cur,
                    "move": move, "hash": h, "exit_code": op.get("exit_code"), "write": w,
                    "inspection": op["kind"] == "run" and is_inspection(op)})
    return seq, uncertain


def _merge(seq: list[dict], uncertain: set[int]):
    """Union provisional versions that showed the same content hash; renumber by first appearance."""
    parent: dict[int, int] = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            lo, hi = min(a, b), max(a, b)   # keep the earlier version's id
            parent[hi] = lo

    first: dict[str, int] = {"root": ROOT}
    for s in seq:
        if s["hash"]:
            v = s["after"]
            if s["hash"] in first:
                union(first[s["hash"]], v)
            else:
                first[s["hash"]] = v
    order: dict[int, int] = {ROOT: 0}
    for s in seq:
        for k in ("before", "after"):
            r = find(s[k])
            if r not in order:
                order[r] = len(order)
            s[k] = order[r]
    unc = {order[find(u)] for u in uncertain if find(u) in order}
    return seq, unc


def build_version_graph(run: dict, ops: list[dict], labels: dict | None = None, unknown_creates_version: bool = True,
                        support_paths: set | None = None) -> dict:
    """unknown_creates_version=False is the sensitivity variant: only known repository writes create versions.
    support_paths: variant (b), support-only changes do not create versions."""
    labels = labels or {}
    seq, unc = _merge(*version_sequence(ops, unknown_creates_version, support_paths))
    nodes = {ROOT: {"v": ROOT, "x": 0, "y": 0, "first_op": -1, "entries": 1, "verify": 0, "verify_fail": 0,
                    "evidence": {}, "uncertain": ROOT in unc}}
    edges = []
    row, pending_row, prev_fail = 1, False, False
    first_move = True
    for s in seq:
        a, b = s["before"], s["after"]
        if s["move"]:
            if b not in nodes:
                if pending_row:
                    row += 1
                    pending_row = False
                nodes[b] = {"v": b, "x": len(nodes), "y": row, "first_op": s["op_index"], "entries": 0, "verify": 0,
                            "verify_fail": 0, "evidence": {}, "uncertain": b in unc}
                label = "initial" if first_move else ("correct" if prev_fail else "revise")
            elif b == a:
                label = "noop"
            else:
                label = "backtrack"
                pending_row = True
            first_move = False
            if b != a:
                nodes[b]["entries"] += 1
                prev_fail = False
            edges.append({"src": a, "dst": b, "label": label, "op_index": s["op_index"], "op_id": s["op_id"],
                          "version_move": (labels.get(s["op_id"]) or {}).get("version_move")})
        else:
            n = nodes[b]
            n["evidence"][s["kind"]] = n["evidence"].get(s["kind"], 0) + 1
            if s["kind"] == "run" and not s["inspection"]:
                n["verify"] += 1
                failed = s["exit_code"] not in (0, None)
                n["verify_fail"] += failed
                prev_fail = failed
            if s["kind"] == "submit":
                edges.append({"src": b, "dst": "final", "label": "final", "op_index": s["op_index"], "op_id": s["op_id"]})
    final = next((e["src"] for e in reversed(edges) if e["label"] == "final"), seq[-1]["after"] if seq else ROOT)
    for n in nodes.values():
        n["final"] = n["v"] == final
    return {"run_id": run["run_id"], "task_id": run["task_id"], "model": run["model"], "resolved": run.get("resolved"),
            "n_versions": len(nodes) - 1, "final": final,
            "final_is_initial": final == ROOT and not nodes[final]['uncertain'],
            "final_x": nodes[final]["x"], "final_y": nodes[final]["y"],
            "nodes": list(nodes.values()), "edges": edges, "op_version": [s["after"] for s in seq]}


def summarize(g: dict) -> dict:
    """Per-run row: versions, rows, edge-label counts, verify on the final version vs earlier ones."""
    from collections import Counter
    lab = Counter(e["label"] for e in g["edges"])
    final = [n for n in g["nodes"] if n["final"]][0]
    others = [n for n in g["nodes"] if not n["final"] and n["v"] != ROOT]
    return {"run_id": g["run_id"], "task_id": g["task_id"], "model": g["model"], "resolved": g["resolved"],
            "n_versions": g["n_versions"], "n_rows": max(n["y"] for n in g["nodes"]),
            "n_uncertain": sum(n["uncertain"] for n in g["nodes"]), "final_is_root": final["v"] == ROOT and not final['uncertain'],
            "final_x": g["final_x"], "verify_final": final["verify"], "verify_root": g["nodes"][0]["verify"],
            "verify_other_mean": (sum(n["verify"] for n in others) / len(others)) if others else None,
            "verify_other_total": sum(n["verify"] for n in others),
            **{f"edge_{k}": lab.get(k, 0) for k in ("initial", "correct", "revise", "backtrack", "noop", "final")}}


def aggregate(graphs: list[dict], threshold: float = 0.3) -> dict:
    """Stage 4 for View B: align runs by version coordinates (x, y). Node weight = share of runs with the node
    (plus mean entries); edge weight = share of runs with the (src, dst) move,
    coloured by its majority rule label, with the label mix kept; self-loop = mean verify runs
    on the version. Prune nodes and edges below `threshold`. Final share: runs ending on the node, and the share
    of those that resolved."""
    from collections import defaultdict
    n = len(graphs)
    pres, entries, verify, vfail, finals, res = (defaultdict(float) for _ in range(6))
    epres = defaultdict(float)
    elab = defaultdict(lambda: defaultdict(float))  # (src, dst) -> label -> runs
    for g in graphs:
        xy = {nd["v"]: (nd["x"], nd["y"]) for nd in g["nodes"]}
        for nd in g["nodes"]:
            k = xy[nd["v"]]
            pres[k] += 1
            entries[k] += nd["entries"]
            verify[k] += nd["verify"]
            vfail[k] += nd["verify_fail"]
            if nd["final"]:
                finals[k] += 1
                res[k] += bool(g["resolved"])
        moves = {}
        for e in g["edges"]:
            if e["dst"] != "final":
                moves.setdefault((xy[e["src"]], xy[e["dst"]]), set()).add(e["label"])
        for key, labs in moves.items():
            epres[key] += 1
            for lab in labs:
                elab[key][lab] += 1
    nodes = [{"x": k[0], "y": k[1], "weight": pres[k] / n, "entries": entries[k] / pres[k], "verify": verify[k] / pres[k],
              "verify_fail": vfail[k] / pres[k], "final_share": finals[k] / n,
              "final_resolved": (res[k] / finals[k]) if finals[k] else None}
             for k in sorted(pres) if pres[k] / n >= threshold]
    keep = {(d["x"], d["y"]) for d in nodes}
    edges = []
    for (s, d), w in sorted(epres.items()):
        if w / n >= threshold and s in keep and d in keep:
            mix = {k: v / w for k, v in sorted(elab[(s, d)].items(), key=lambda kv: -kv[1])}
            edges.append({"src": s, "dst": d, "label": next(iter(mix)), "labels": mix, "weight": w / n})
    return {"runs": n, "resolved": sum(bool(g["resolved"]) for g in graphs) / n if n else None,
            "nodes": nodes, "edges": edges, "threshold": threshold}
