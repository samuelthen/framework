"""Shell-command parsing: split_chain, classify, may_write, is_state_probe, written_paths (Appendix A.3, B.2)."""
from __future__ import annotations

import hashlib
import re
import shlex

from . import pyinline

SUBMIT_MARKERS = ("COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT", "MINI_SWE_AGENT_FINAL_OUTPUT")
REPO_ROOTS = ("/app/", "/testbed/", "/workspace/", "/repo/", "/src/")

READ_CMDS = {"cat", "head", "tail", "nl", "less", "more", "bat", "view", "xxd", "od", "strings"}
SEARCH_CMDS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "find", "ls", "tree", "fd", "locate", "which", "file", "stat", "wc", "du"}
RUN_CMDS = {"pytest", "py.test", "tox", "nox", "go", "npm", "npx", "yarn", "pnpm", "node", "cargo", "make", "cmake",
            "mvn", "gradle", "./gradlew", "jest", "mocha", "vitest", "ruby", "rspec", "bundle", "rake", "php", "phpunit",
            "composer", "java", "javac", "dotnet", "deno", "bun", "tsc", "ctest", "ninja", "bazel", "unittest", "nosetests",
            "python", "python3", "python2", "bash", "sh", "zsh", "perl", "Rscript", "julia", "lua", "swift", "elixir", "mix",
            "gcc", "g++", "clang", "rustc", "timeout", "coverage", "uv", "poetry", "hatch", "pip", "pip3", "django-admin"}
# run commands that cannot modify source files
RUN_NO_WRITE = {"pytest", "py.test", "jest", "mocha", "vitest", "rspec", "phpunit", "nosetests", "tsc", "ctest", "unittest"}
OTHER_CMDS = {"cd", "echo", "printf", "true", "false", ":", "export", "set", "unset", "source", ".", "sleep", "pwd",
              "env", "clear", "mkdir", "date", "whoami", "id", "uname", "type", "alias", "history", "exit", "test", "["}
WRITE_CMDS = {"rm", "mv", "cp", "touch", "tee", "patch", "chmod", "ln", "rsync", "truncate", "dd", "install", "unzip", "tar"}

_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PREFIX_CMDS = {"sudo", "env", "command", "exec", "nice", "time", "stdbuf", "xargs", "nohup"}


def split_chain(command: str, *, split_pipelines: bool = True) -> list[str]:
    """Split a shell command on &&, ||, ;, | and newlines, respecting quotes, $(...), and heredoc bodies.
    With split_pipelines=False, keep output-producing pipelines together.
    A heredoc body stays attached to the part that opened it. Structured tool calls ('tool:...') are one part."""
    if command.startswith("tool:"):
        return [command]
    parts, buf = [], []
    i, n = 0, len(command)
    quote = None
    depth = 0  # $( ... ) / ( ... ) nesting
    pending_heredocs: list[tuple[str, bool]] = []

    def flush():
        s = "".join(buf).strip()
        if s:
            parts.append(s)
        buf.clear()

    while i < n:
        c = command[i]
        if quote:
            buf.append(c)
            if c == "\\" and quote == '"' and i + 1 < n:
                buf.append(command[i + 1]); i += 2; continue
            if c == quote:
                quote = None
            i += 1; continue
        if c in "'\"`":
            quote = c; buf.append(c); i += 1; continue
        if c == "\\" and i + 1 < n:
            buf.append(command[i:i + 2]); i += 2; continue
        if c == "#" and (not buf or buf[-1] in " \t\n") and depth == 0:
            j = command.find("\n", i)
            i = n if j < 0 else j
            continue
        if command.startswith("$(", i):
            depth += 1; buf.append("$("); i += 2; continue
        if c == "(":
            depth += 1; buf.append(c); i += 1; continue
        if c == ")" and depth > 0:
            depth -= 1; buf.append(c); i += 1; continue
        if depth == 0 and command.startswith("<<", i) and not command.startswith("<<<", i):
            m = re.match(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2", command[i:])
            if m:
                pending_heredocs.append((m.group(3), m.group(1) == "-"))
                buf.append(m.group(0)); i += len(m.group(0)); continue
        if c == "\n" and depth == 0:
            if pending_heredocs:
                # consume heredoc bodies into the current part
                j = i + 1
                for delim, strip_tabs in pending_heredocs:
                    while j <= n:
                        k = command.find("\n", j)
                        line = command[j:] if k < 0 else command[j:k]
                        if (line.lstrip("\t") if strip_tabs else line).strip() == delim:
                            j = n if k < 0 else k + 1
                            break
                        j = n + 1 if k < 0 else k + 1
                buf.append(command[i:min(j, n)])
                pending_heredocs = []
                i = j
                flush()
                continue
            flush(); i += 1; continue
        if depth == 0 and (command.startswith("&&", i) or command.startswith("||", i)):
            flush(); i += 2; continue
        if depth == 0 and c == "|" and not command.startswith("|&", i) and split_pipelines:
            flush(); i += 1; continue
        if depth == 0 and c == ";":
            flush(); i += 1; continue
        if depth == 0 and c == "&" and not command.startswith("&>", i) and (i == 0 or command[i - 1] not in "<>"):
            flush(); i += 1; continue
        buf.append(c); i += 1
    if quote or depth or pending_heredocs:
        # Malformed/unsupported shell text is one opaque attempted action, not
        # dozens of fictitious commands from an unterminated quoted script.
        return [command] if command.strip() else []
    flush()
    return parts


def _tokens(part: str) -> list[str]:
    head = part.split("\n", 1)[0]  # heredoc bodies are not tokens
    try:
        return shlex.split(head, posix=True)
    except ValueError:
        return head.split()


def _strip_prefix(toks: list[str]) -> list[str]:
    i = 0
    while i < len(toks):
        t = toks[i]
        if _ENV_ASSIGN.match(t):
            i += 1
        elif t in _PREFIX_CMDS:
            i += 1
            while i < len(toks) and toks[i].startswith("-"):
                i += 1
        elif t == "timeout":
            i += 1
            while i < len(toks) and (toks[i].startswith("-") or re.match(r"^\d+[smh]?$", toks[i])):
                i += 1
        else:
            break
    return toks[i:]


def _redirect_targets(part: str) -> list[str]:
    head = part.split("\n", 1)[0]
    # drop quoted strings so '>' inside them is ignored
    h = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", head)
    out = []
    for m in re.finditer(r"(?<![0-9&<])(?:[12])?>>?\s*([^\s;&|<>]+)", h):
        tgt = m.group(1)
        if tgt.startswith("&") or tgt in ("/dev/null", "/dev/stderr", "/dev/stdout"):
            continue
        out.append(tgt)
    for m in re.finditer(r"&>>?\s*([^\s;&|<>]+)", h):
        if m.group(1) != "/dev/null":
            out.append(m.group(1))
    return out


def norm_path(p: str) -> str:
    p = p.strip().strip("'\"")
    for root in REPO_ROOTS:
        if p.startswith(root):
            rest = p[len(root):]
            # /workspace/<repo>/x -> x
            if root == "/workspace/":
                rest = rest.split("/", 1)[1] if "/" in rest else ""  # /workspace/<repo> is the repository root
            p = rest
            break
    while p.startswith("./"):
        p = p[2:]
    return re.sub(r"/+", "/", p)


def _file_args(toks: list[str]) -> list[str]:
    out, skip = [], False
    for t in toks[1:]:
        if skip:
            skip = False; continue
        if re.match(r"^(\d*|&)(>>?|<<?)(&\d)?$", t):  # bare redirection operator: its target is not an argument
            skip = True; continue
        if re.match(r"^(\d*|&)(>>?|<)", t):  # attached redirection such as 2>/dev/null
            continue
        if t in ("-n", "-c", "-e", "-f", "-A", "-B", "-C", "-m", "--lines", "--bytes") and toks[0] in ("head", "tail", "grep", "rg"):
            skip = True; continue
        if t.startswith("-") or t.startswith("+"):
            continue
        out.append(t)
    return out


def classify(part: str) -> str:
    """Kind of one chain part: read|search|edit|revert|run|probe|submit|other."""
    if any(m in part for m in SUBMIT_MARKERS):
        return "submit"
    if part.startswith("tool:"):
        return _classify_tool(part)
    toks = _strip_prefix(_tokens(part))
    if not toks:
        return "other"
    c0 = toks[0].rsplit("/", 1)[-1] if toks[0].startswith("/") else toks[0]
    redir = _redirect_targets(part)
    if c0 == "git":
        sub = next((t for t in toks[1:] if not t.startswith("-")), "")
        if sub in ("diff", "status"):
            return "probe"
        if sub in ("checkout", "restore", "stash", "reset", "revert", "clean"):
            if sub == "checkout" and "--" not in toks and not any(t == "." or "/" in t or re.search(r"\.\w{1,5}$", t)
                                                                 for t in toks[2:] if not t.startswith("-")):
                return "other"  # branch switch (no path-like argument)
            return "revert"
        if sub == "apply" or sub == "am":
            return "edit"
        if sub in ("grep", "log", "ls-files", "blame", "show", "rev-parse", "branch"):
            return "search"
        return "other"
    if c0 in ("sed", "perl") and any(t == "-i" or t.startswith("-i") or t.startswith("--in-place")
                                     or (c0 == "perl" and re.match(r"^-[a-hj-zA-Z]*i", t)) for t in toks[1:]):
        return "edit"
    if c0 in ("apply_patch", "patch", "tee", "applypatch"):
        return "edit"
    if redir and c0 not in RUN_CMDS:
        return "edit"  # cat <<EOF > f, echo x > f, printf > f
    if c0 == "sed":
        return "read" if len([a for a in _file_args(toks) if not re.match(r"^[0-9,$]+p?$", a)]) >= 2 or len(_file_args(toks)) >= 2 else "other"
    if c0 == "awk":
        return "read" if _file_args(toks) else "other"
    if c0 in READ_CMDS:
        return "read" if _file_args(toks) else "other"
    if c0 in SEARCH_CMDS:
        return "search"
    if c0 in WRITE_CMDS:
        return "edit"
    if c0 in OTHER_CMDS:
        return "other"
    if c0 in ("pip", "pip3", "apt", "apt-get", "conda", "uv") and len(toks) > 1 and toks[1] in ("install", "uninstall", "add", "sync"):
        return "other"
    if c0 in RUN_CMDS or c0.startswith("./") or c0.endswith(".sh") or c0.endswith(".py"):
        return "run"
    return "other"


def _classify_tool(part: str) -> str:
    """Pseudo-commands 'tool:<name> <args>' for structured tools (OpenHands, SWE-agent)."""
    name, _, args = part[5:].partition(" ")
    name = name.lower()
    if name in ("str_replace_editor", "str_replace_based_edit_tool", "file_editor", "edit_file"):
        sub = args.split(" ", 1)[0]
        return {"view": "read", "create": "edit", "str_replace": "edit", "insert": "edit",
                "undo_edit": "revert"}.get(sub, "other")
    if name in ("open", "goto", "scroll_up", "scroll_down", "view", "read_file"):
        return "read"
    if name in ("find_file", "search_file", "search_dir", "grep", "glob", "list_files"):
        return "search"
    if name in ("edit", "create", "insert", "append", "write_file", "str_replace"):
        return "edit"
    if name in ("submit", "finish"):
        return "submit"
    return "other"


def main_object(part: str, kind: str, cwd: str = "") -> str:
    if part.startswith("tool:"):
        name, _, args = part[5:].partition(" ")
        bits = args.split()
        if name.lower() in ("str_replace_editor", "str_replace_based_edit_tool", "file_editor") and len(bits) > 1:
            return norm_path(bits[1])
        return norm_path(bits[0]) if bits else name
    toks = _strip_prefix(_tokens(part))
    if kind in ("read",):
        fa = _file_args(toks)
        if toks and toks[0] == "sed":
            fa = [a for a in fa if not re.match(r"^\d+(,\d+)?p?$|^[0-9,$]+p$", a)] or fa
            fa = fa[1:] if len(fa) > 1 else fa
        if toks and toks[0] == "awk" and len(fa) > 1:
            fa = fa[1:]
        return _join(cwd, fa[-1]) if fa else _norm_cmd(part)
    if kind == "edit":
        red = _redirect_targets(part)
        if red:
            return _join(cwd, red[-1])
        fa = _file_args(toks)
        if toks and toks[0] in ("sed", "perl"):
            fa = fa[1:] if len(fa) > 1 else fa
        return _join(cwd, fa[-1]) if fa else _norm_cmd(part)
    if kind == "revert":
        fa = [t for t in toks[2:] if not t.startswith("-")]
        return _join(cwd, fa[-1]) if fa else _norm_cmd(part)
    return _norm_cmd(part)


def _join(cwd: str, p: str) -> str:
    p = norm_path(p)
    if cwd and not p.startswith("/") and cwd not in (".",):
        p = norm_path(cwd.rstrip("/") + "/" + p) if norm_path(cwd) else p
    return p


def _norm_cmd(part: str) -> str:
    if "\n" in part:
        head, body = part.split("\n", 1)
        head = head + " <<body:" + hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()[:8] + ">>"
    else:
        head = part
    head = re.sub(r"\s+", " ", head).strip()
    for root in REPO_ROOTS:
        head = head.replace(root, "")
    return head


def written_paths(parts: list[str], cwd: str = "") -> list[str]:
    out = []
    for p in parts:
        k = classify(p)
        if k in ("edit", "revert"):
            out.extend(_mutation_paths(p, cwd))
        else:
            for t in _redirect_targets(p):
                out.append(_join(cwd, t))
    return list(dict.fromkeys(out))


def _mutation_paths(part: str, cwd: str = "") -> list[str]:
    """Known mutation operands, independently of any unknown additional effects."""
    toks = _strip_prefix(_tokens(part))
    red = [_join(cwd, t) for t in _redirect_targets(part)]
    if toks and toks[0] in ("sed", "perl"):
        args, skip, expressions = [], False, False
        for t in toks[1:]:
            if skip:
                skip = False
                continue
            if t in ("-e", "--expression", "-f", "--file"):
                expressions, skip = True, True
                continue
            if t.startswith(("-e", "--expression=")):
                expressions = True
                continue
            if t.startswith("-"):
                continue
            args.append(t)
        files = args if expressions else args[1:]
        return list(dict.fromkeys(red + [_join(cwd, p) for p in files]))
    if toks and toks[0] in ("rm", "touch", "truncate", "tee"):
        return list(dict.fromkeys(red + [_join(cwd, p) for p in _file_args(toks)]))
    return list(dict.fromkeys(red + [main_object(part, classify(part), cwd)]))


def _python_code(part: str, toks: list[str], cwd: str, scripts: dict | None):
    """Locate inline/script Python source for a python run part. Returns code, or None if not locatable."""
    src = pyinline.python_source(toks, part)
    if src is None:
        return None
    kind, val = src
    if kind == "inline":
        if "-c" in toks and "\n" in part:  # multi-line -c: tokens of the first line are incomplete
            try:
                full = shlex.split(re.sub(r"<<-?\s*['\"]?\w+['\"]?.*", "", part, flags=re.S), posix=True)
                i = full.index("-c")
                return full[i + 1] if i + 1 < len(full) else None
            except ValueError:
                return None
        return val
    if scripts is not None:
        return scripts.get(_join(cwd, val))
    return None


def _shell_write_for_python(cmd: str):
    parts = split_chain(cmd) or [cmd]
    return write_info(parts)


def write_info(parts: list[str], scripts: dict | None = None) -> tuple[bool | str, list[str]]:
    """Return known paths and write=True/False/'unknown' independently.
    Unknown additional effects take precedence over a known write, retaining
    its known paths. Inline Python is analysed statically (pyinline)."""
    cwd, res, paths, unknown = "", False, [], False
    for p in parts:
        k = classify(p)
        if k in ("edit", "revert"):
            res = True
            paths += _mutation_paths(p, cwd)
        toks = _strip_prefix(_tokens(p))
        # Branch/HEAD changes can alter all tracked files, even when classified
        # as `other`. They cannot be described as an unchanged repository.
        if (toks[:2] == ["git", "switch"] or
                (toks[:2] == ["git", "checkout"] and "--" not in toks and toks[2:] != ["."])):
            unknown = True
        if toks[:2] in (["git", "add"], ["git", "commit"], ["git", "update-index"],
                        ["git", "read-tree"], ["git", "rm"]):
            # Index/HEAD changes affect the meaning of a later worktree restore.
            # They are not evidence that source state stayed unchanged.
            unknown = True
        red = _redirect_targets(p)
        if red and k not in ("edit", "revert"):
            res = True
            paths += [_join(cwd, t) for t in red]
        if k == "run":
            toks = _strip_prefix(_tokens(p))
            c0 = toks[0] if toks else ""
            w = _run_write(p, toks, c0, cwd, scripts)
            if w is not None:
                ww, pp = w
                if ww is True:
                    res = True
                    paths += pp
                elif ww == "unknown":
                    unknown = True
                    paths += pp
        cwd = cwd_after(p, cwd)
    return "unknown" if unknown else res, list(dict.fromkeys(paths))


def _run_write(p, toks, c0, cwd, scripts):
    if c0 in RUN_NO_WRITE:
        return None
    if pyinline.python_source(toks, p) is not None:
        code = _python_code(p, toks, cwd, scripts)
        if code is None:
            return "unknown", []
        w, pp = pyinline.analyze(code, _shell_write_for_python)
        return w, [_join(cwd, x) for x in pp]
    if c0 in ("python", "python3", "python2") and len(toks) > 2 and toks[1] == "-m" and toks[2] in (
            "pytest", "unittest", "py_compile", "compileall", "doctest", "json.tool", "pip", "mypy", "pyflakes", "flake8"):
        return None
    if c0 == "go" and len(toks) > 1 and toks[1] in ("test", "vet", "build", "run", "version", "list", "env", "doc"):
        return None
    if c0 == "cargo" and len(toks) > 1 and toks[1] in ("test", "check", "build", "run", "clippy"):
        return None
    if c0 in ("npm", "yarn", "pnpm", "npx") and len(toks) > 1 and toks[1] in ("test", "run", "jest", "vitest", "tsc", "mocha"):
        return None
    return "unknown", []


def may_write(parts: list[str], scripts: dict | None = None) -> bool | str:
    return write_info(parts, scripts)[0]


def heredoc_script_writes(parts: list[str]) -> dict[str, str]:
    """Scripts written by `cat > f <<EOF ... EOF` / `tee f <<EOF`, so a later `python f` can be analysed."""
    out, cwd = {}, ""
    for p in parts:
        if classify(p) == "edit" and "<<" in p.split("\n", 1)[0]:
            hb = pyinline.heredoc_body(p)
            red = _redirect_targets(p)
            toks = _tokens(p)
            tgt = red[-1] if red else (next((t for t in toks[1:] if not t.startswith("-") and not t.startswith("<<")), None)
                                       if toks and toks[0] == "tee" else None)
            if hb and tgt:
                out[_join(cwd, tgt)] = hb[0]
        cwd = cwd_after(p, cwd)
    return out


def is_state_probe(parts: list[str]) -> bool:
    """A plain `git diff` (whole tree) or `git status`, with no write and no path filter."""
    for p in parts:
        toks = _strip_prefix(_tokens(p))
        if len(toks) >= 2 and toks[0] == "git" and toks[1] in ("diff", "status"):
            extra = [t for t in toks[2:] if t not in ("--stat", "--short", "-s", "--porcelain", "--no-color", "--name-only", "HEAD", "--", ".")]
            if not extra and not _redirect_targets(p):
                return True
    return False


def cwd_after(part: str, cwd: str) -> str:
    toks = _tokens(part)
    if toks and toks[0] == "cd":
        tgt = toks[1] if len(toks) > 1 else ""
        n = norm_path(tgt)
        if tgt.rstrip("/") in ("/app", "/testbed", "/repo") or n == "":
            return ""
        if tgt.startswith("/"):
            return n if any(tgt.startswith(r) for r in REPO_ROOTS) else tgt
        return _join(cwd, tgt)
    return cwd


def main_kind_and_object(parts: list[str]) -> tuple[str, str, list[str], list[str]]:
    """Returns (main kind, main object, part kinds, part objects). Main = first read/edit/run/revert part,
    else the first part that is not 'other'."""
    cwd, kinds, objs = "", [], []
    for p in parts:
        k = classify(p)
        kinds.append(k)
        objs.append(main_object(p, k, cwd) if k != "other" else _norm_cmd(p))
        cwd = cwd_after(p, cwd)
    if "submit" in kinds:  # the harness's submit command is the Final operation, whatever else it chains
        return "submit", objs[kinds.index("submit")], kinds, objs
    for pri in (("read", "edit", "run", "revert"), ("search", "probe")):
        for k, o in zip(kinds, objs):
            if k in pri:
                return k, o, kinds, objs
    return "other", (objs[0] if objs else ""), kinds, objs


def written_paths_cwd(parts: list[str], scripts: dict | None = None) -> list[str]:
    return write_info(parts, scripts)[1]
