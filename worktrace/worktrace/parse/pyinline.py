"""Static write analysis for inline Python (`python - <<PY`, `python -c "..."`, scripts written by a heredoc).

analyze(code) -> (write, paths): write is True (paths = literal targets), False (parses, no write call), or
"unknown" (a write whose target is not a literal, or something that may write: exec, subprocess, unparsable code).
"""
from __future__ import annotations

import ast
import re
import shlex
import warnings

WRITE_MODES = set("wax+")
PATH_WRITE_METHODS = {"write_text", "write_bytes", "unlink", "rename", "replace", "touch", "rmdir", "symlink_to",
                      "hardlink_to", "chmod"}
OS_WRITE_FUNCS = {"remove", "unlink", "rename", "replace", "rmdir", "removedirs", "renames", "truncate", "chmod",
                  "symlink", "link"}
SHUTIL_WRITE_FUNCS = {"copy", "copy2", "copyfile", "copytree", "copyfileobj", "move", "rmtree", "chown"}
OPAQUE_CALLS = {"exec", "eval", "compile", "__import__"}
SUBPROCESS_FUNCS = {"run", "call", "check_call", "check_output", "Popen", "getoutput", "getstatusoutput"}


class _Unknown(Exception):
    pass


def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


class _Analyzer(ast.NodeVisitor):
    def __init__(self, shell_may_write=None):
        self.env: dict[str, list[str] | None] = {}   # name -> literal path values (None = not literal)
        self.writes: list[str] = []
        self.unknown = False
        self.shell_may_write = shell_may_write

    # --- literal path resolution -------------------------------------------------------------
    def _vals(self, node) -> list[str] | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.Name):
            return self.env.get(node.id)
        if isinstance(node, ast.Call):
            f = _dotted(node.func)
            if f.split(".")[-1] in ("Path", "PurePath", "PosixPath") and node.args:
                vals = [self._vals(a) for a in node.args]
                if any(v is None for v in vals):
                    return None
                out = vals[0]
                for v in vals[1:]:
                    out = [a.rstrip("/") + "/" + b for a in out for b in v]
                return out
            if f in ("os.path.join",) and node.args:
                vals = [self._vals(a) for a in node.args]
                if any(v is None for v in vals):
                    return None
                out = vals[0]
                for v in vals[1:]:
                    out = [a.rstrip("/") + "/" + b for a in out for b in v]
                return out
            if f.startswith("tempfile.") or f in ("mkdtemp", "mkstemp", "gettempdir"):
                return ["/tmp/<tempfile>"]  # always outside the repository
            if f.endswith(".resolve") or f.endswith(".absolute") or f.endswith(".expanduser"):
                return self._vals(node.func.value) if isinstance(node.func, ast.Attribute) else None
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
            l, r = self._vals(node.left), self._vals(node.right)
            if l is None or r is None:
                return None
            sep = "/" if isinstance(node.op, ast.Div) else ""
            return [a.rstrip("/") + sep + b if sep else a + b for a in l for b in r]
        return None

    def _target(self, node):
        v = self._vals(node)
        if v is None:
            self.unknown = True
        else:
            self.writes.extend(v)

    # --- bindings ----------------------------------------------------------------------------
    def visit_Assign(self, node):
        self.generic_visit(node)
        v = self._vals(node.value)
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.env[t.id] = v

    def visit_For(self, node):
        if isinstance(node.target, ast.Name) and isinstance(node.iter, (ast.List, ast.Tuple)):
            vals = [self._vals(e) for e in node.iter.elts]
            self.env[node.target.id] = None if any(v is None for v in vals) else [x for v in vals for x in v]
        elif isinstance(node.target, ast.Name):
            self.env[node.target.id] = None
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if isinstance(item.optional_vars, ast.Name):
                f = _dotted(item.context_expr.func) if isinstance(item.context_expr, ast.Call) else ""
                # a TemporaryDirectory yields a temp path; anything else (open(...)) yields a handle, not a path
                self.env[item.optional_vars.id] = ["/tmp/<tempfile>"] if f.endswith("TemporaryDirectory") else None
        self.generic_visit(node)

    # --- calls -------------------------------------------------------------------------------
    def _mode(self, node: ast.Call, pos: int):
        m = node.args[pos] if len(node.args) > pos else next((k.value for k in node.keywords if k.arg == "mode"), None)
        if m is None:
            return "r"
        if isinstance(m, ast.Constant) and isinstance(m.value, str):
            return m.value
        return None  # non-literal mode

    def visit_Call(self, node):
        f = _dotted(node.func)
        last = f.split(".")[-1]
        if f in ("open", "io.open", "codecs.open", "os.open", "builtins.open") and node.args:
            mode = self._mode(node, 1)
            if f == "os.open":
                flags = ast.unparse(node.args[1]) if len(node.args) > 1 else ""
                if re.search(r"O_(WRONLY|RDWR|CREAT|TRUNC|APPEND)", flags):
                    self._target(node.args[0])
            elif mode is None:
                self.unknown = True
            elif WRITE_MODES & set(mode):
                self._target(node.args[0])
        elif isinstance(node.func, ast.Attribute) and last == "open" and not f.startswith(("os.", "io.", "codecs.")):
            mode = self._mode(node, 0)  # Path(...).open(mode)
            if mode is None:
                self.unknown = True
            elif WRITE_MODES & set(mode):
                self._target(node.func.value)
        elif isinstance(node.func, ast.Attribute) and last in PATH_WRITE_METHODS and not f.startswith(("os.", "shutil.")):
            if last in ("rename", "replace"):
                if len(node.args) + len(node.keywords) == 1:  # Path.rename(target); str.replace takes 2-3 args
                    self._target(node.func.value)
                    self._target(node.args[0] if node.args else node.keywords[0].value)
            elif last == "chmod":
                pass
            else:
                self._target(node.func.value)
        elif f.startswith("os.") and last in OS_WRITE_FUNCS and node.args:
            if last != "chmod":
                for a in node.args[:2 if last in ("rename", "replace", "renames", "symlink", "link") else 1]:
                    self._target(a)
        elif f.startswith("shutil.") and last in SHUTIL_WRITE_FUNCS:
            if last == "copyfileobj":
                pass  # needs a handle opened for writing, caught at open()
            elif last == "rmtree" and node.args:
                self._target(node.args[0])
            elif len(node.args) >= 2:
                self._target(node.args[1])
                if last == "move":
                    self._target(node.args[0])
            else:
                self.unknown = True
        elif f in ("os.system", "os.popen") or (f.startswith("subprocess.") and last in SUBPROCESS_FUNCS):
            self._subprocess(node)
        elif f in OPAQUE_CALLS or f.startswith("importlib.") or f in ("runpy.run_path", "runpy.run_module"):
            self.unknown = True
        self.generic_visit(node)

    def _subprocess(self, node):
        if not node.args or self.shell_may_write is None:
            self.unknown = True
            return
        a = node.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            cmd = a.value
        elif isinstance(a, (ast.List, ast.Tuple)) and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in a.elts):
            cmd = " ".join(shlex.quote(e.value) for e in a.elts)
        else:
            self.unknown = True
            return
        w, paths = self.shell_may_write(cmd)
        if w is True:
            self.writes.extend(paths)
        elif w == "unknown":
            self.unknown = True
            self.writes.extend(paths)


_REGEX_WRITES = [
    re.compile(r"""open\(\s*(['"])([^'"]+)\1\s*,\s*(?:mode\s*=\s*)?(['"])[^'"]*[wax+][^'"]*\3"""),
    re.compile(r"""Path\(\s*(['"])([^'"]+)\1\s*\)\s*\.\s*write_(?:text|bytes)\("""),
]
_REGEX_ANY_WRITE = re.compile(r"""open\([^)]*['"][^'"]*[wax+][^'"]*['"]|\.write_(text|bytes)\(|os\.(remove|unlink|rename|replace|rmdir)\(|"""
                              r"""shutil\.(copy\w*|move|rmtree)\(|subprocess\.|os\.system\(|\bexec\(|\.unlink\(|\.touch\(|open\([^)]*mode\s*=""")


def analyze(code: str, shell_may_write=None) -> tuple[bool | str, list[str]]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return _regex_fallback(code)
    a = _Analyzer(shell_may_write)
    try:
        a.visit(tree)
    except (_Unknown, RecursionError):
        return "unknown", []
    if a.unknown:
        return "unknown", sorted(set(a.writes))
    if a.writes:
        return True, sorted(set(a.writes))
    return False, []


def _regex_fallback(code: str) -> tuple[bool | str, list[str]]:
    paths = [m.group(2) for rx in _REGEX_WRITES for m in rx.finditer(code)]
    rest = code
    for rx in _REGEX_WRITES:
        rest = rx.sub("", rest)
    if _REGEX_ANY_WRITE.search(rest):
        return "unknown", paths
    if paths:
        return True, sorted(set(paths))
    return False, []


# --- extracting the Python source from a shell part ------------------------------------------------
_PY = re.compile(r"^(?:python(?:\d(?:\.\d+)?)?|pypy3?)$")


def heredoc_body(part: str) -> tuple[str, bool] | None:
    """(body, quoted_delimiter) of the first heredoc in a part, if any."""
    m = re.search(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2", part.split("\n", 1)[0])
    if not m or "\n" not in part:
        return None
    lines = part.split("\n")[1:]
    body = []
    for line in lines:
        if (line.lstrip("\t") if m.group(1) else line).strip() == m.group(3):
            break
        body.append(line)
    return "\n".join(body), bool(m.group(2))


def python_source(toks: list[str], part: str) -> tuple[str, str] | None:
    """For a python invocation, return ('inline', code) for -c / stdin heredoc, ('script', path) for a script file,
    or None if this is not a python run whose code we can locate (e.g. -m module)."""
    if not toks or not _PY.match(toks[0].rsplit("/", 1)[-1]):
        return None
    i = 1
    while i < len(toks):
        t = toks[i]
        if t == "-c" and i + 1 < len(toks):
            return "inline", toks[i + 1]
        if t.startswith("-c") and len(t) > 2:
            return "inline", t[2:]
        if t == "-m":
            return None
        if t == "-" or t.startswith("<<"):
            hb = heredoc_body(part)
            return ("inline", hb[0]) if hb else None
        if t.startswith("-"):
            i += 1
            continue
        return "script", t
    hb = heredoc_body(part)  # `python <<EOF` with no dash
    return ("inline", hb[0]) if hb else None
