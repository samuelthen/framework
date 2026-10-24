"""View B refinement of write='unknown' operations (not used by the v2 facts): inline Node.js (`node -e`) and common
JS/TS tooling. Returns (True, paths) / (False, []) / ("unknown", [])."""
from __future__ import annotations

import re
import shlex

_JS_WRITE_CALL = re.compile(r"\b(?:fs\.|fsp\.|promises\.)?(writeFileSync|writeFile|appendFileSync|appendFile|renameSync|unlinkSync|"
                            r"rmSync|rmdirSync|copyFileSync|cpSync|createWriteStream|outputFileSync)\s*\(\s*([^,)]+)")
_JS_OPAQUE = re.compile(r"child_process|execSync|spawnSync|\bspawn\(|\bexec\(|\beval\(|require\(\s*[^'\"`]")
_JS_ASSIGN = re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(['\"`])([^'\"`]+)\2")
_TEST_RUNNERS = {"jest", "vitest", "mocha", "tsc", "eslint", "karma", "ava", "tap", "playwright"}
_CHECK_SCRIPTS = {"test", "t", "lint", "check-types", "type-check", "typecheck", "tsc", "check", "test:unit", "jest", "eslint"}
_WRITE_FLAGS = {"--fix", "-w", "--write", "-u", "--updateSnapshot"}


def _literal(arg: str, env: dict) -> str | None:
    a = arg.strip()
    m = re.fullmatch(r"(['\"`])([^'\"`$]+)\1", a)
    if m:
        return m.group(2)
    return env.get(a)


def analyze_js(code: str):
    env = {m.group(1): m.group(3) for m in _JS_ASSIGN.finditer(code)}
    paths, unknown = [], False
    for m in _JS_WRITE_CALL.finditer(code):
        p = _literal(m.group(2), env)
        if p is None:
            unknown = True
        else:
            paths.append(p.lstrip("./") if p.startswith("./") else p)
    if _JS_OPAQUE.search(code):
        return "unknown", []
    if paths and not unknown:
        return True, sorted(set(paths))
    if unknown:
        return True, []  # a write whose target is not a literal: a write, path unknown
    return False, []


def refine_part(part: str):
    head = part.split("\n", 1)[0]
    try:
        toks = shlex.split(part) if "-e" in head else shlex.split(head)
    except ValueError:
        return "unknown", []
    while toks and re.match(r"^[A-Za-z_]\w*=", toks[0]):
        toks = toks[1:]
    if not toks:
        return None
    c0 = toks[0].rsplit("/", 1)[-1]
    if c0 == "node" and len(toks) >= 3 and toks[1] in ("-e", "--eval", "-p", "--print"):
        return analyze_js(toks[2])
    if c0 in ("yarn", "npm", "pnpm") and len(toks) > 2 and toks[1] in ("workspace", "-w", "--workspace", "run"):
        script = toks[3] if toks[1] != "run" and len(toks) > 3 else toks[2]
        if script in _CHECK_SCRIPTS and not (_WRITE_FLAGS & set(toks)):
            return False, []
    if c0 in ("yarn", "npm", "pnpm") and len(toks) > 1 and toks[1] in _CHECK_SCRIPTS and not (_WRITE_FLAGS & set(toks)):
        return False, []
    if c0 == "go" and len(toks) > 1 and toks[1] in ("test", "vet") and "-c" not in toks and "-o" not in toks:
        return False, []
    if c0 == "go" and len(toks) > 1 and toks[1] in ("test", "build"):
        return True, ["<build-artifact>"]   # go test -c / go build write a binary: not code
    if re.fullmatch(r"\./[\w.-]+\.test", toks[0]):
        return False, []                    # a compiled Go test binary
    if c0 == "make" and any("node_modules" in t for t in toks):
        return True, ["<build-artifact>"]   # building a dependency, not repository code
    tool = toks[1] if c0 in ("npx", "yarn", "pnpm") and len(toks) > 1 else c0
    tool = tool.rsplit("/", 1)[-1]
    if tool in _TEST_RUNNERS or (c0 in ("npm", "yarn", "pnpm") and len(toks) > 1 and toks[1] in ("test", "t")):
        if not (_WRITE_FLAGS & set(toks)):
            return False, []
    if tool == "prettier" and ({"--check", "-c", "--list-different", "-l"} & set(toks)) and not ({"-w", "--write"} & set(toks)):
        return False, []
    if tool == "prettier" and ({"-w", "--write"} & set(toks)):
        return True, [t for t in toks[2:] if not t.startswith(("-", ">", "<", "2>", "&", "|"))]
    return None  # not handled here
