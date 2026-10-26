"""D.9 / D.11 fact tests."""
import pytest

from worktrace.facts import extract_facts
from worktrace.parse import shell
from worktrace.parse.normalize import norm_hash

FILE_A = "def f():\n    return 1\n" * 5
FILE_B = "class B:\n    pass\n" * 5
PASS = "===== 3 passed in 0.12s =====\n" + "x" * 30
PASS2 = "===== 3 passed in 0.31s =====\n" + "x" * 30
FAIL = "===== 1 failed, 2 passed in 0.20s =====\nAssertionError: 1 != 2"


def mk(*cmds_outs):
    ops = []
    for i, (c, o, *rest) in enumerate(cmds_outs):
        ops.append({"op_id": f"op{i}", "turn_id": f"r:t{i}", "command": c, "output": o,
                    "exit_code": rest[0] if rest else 0})
    return extract_facts(ops)


# --- command table (classify / split / write / probe) ---
CASES = [
    ("cat a.py", ["read"], False),
    ("cat /app/a.py", ["read"], False),
    ("head -n 50 src/x.py", ["read"], False),
    ("tail -20 log.txt", ["read"], False),
    ("sed -n '1,80p' lib/a.py", ["read"], False),
    ("nl -ba a.py | sed -n '10,40p'", ["read", "other"], False),
    ("grep -rn foo src/", ["search"], False),
    ("rg -n 'def x' .", ["search"], False),
    ("find . -name '*.py'", ["search"], False),
    ("ls -la", ["search"], False),
    ("git grep -n foo", ["search"], False),
    ("git log --oneline -5", ["search"], False),
    ("sed -i 's/x/y/' a.py", ["edit"], True),
    ("perl -pi -e 's/a/b/' a.py", ["edit"], True),
    ("echo hi > a.txt", ["edit"], True),
    ("cat <<'EOF' > a.py\nprint(1)\nEOF", ["edit"], True),
    ("tee a.py <<EOF\nx\nEOF", ["edit"], True),
    ("patch -p1 < fix.diff", ["edit"], True),
    ("git apply fix.diff", ["edit"], True),
    ("git checkout -- a.py", ["revert"], True),
    ("git restore a.py", ["revert"], True),
    ("git stash", ["revert"], True),
    ("pytest tests/test_a.py -q", ["run"], False),
    ("python -m pytest -x", ["run"], False),
    ("go test ./...", ["run"], False),
    ("npm test", ["run"], False),
    ("cargo test", ["run"], False),
    ("python fix.py", ["run"], "unknown"),
    ("python -c 'print(1)'", ["run"], False),
    ("make build", ["run"], "unknown"),
    ("git diff", ["probe"], False),
    ("git status", ["probe"], False),
    ("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt", ["submit", "read"], False),
    ("git diff -- a.py > patch.txt", ["probe"], True),
    ("cd /app && grep -n x a.py && sed -i 's/x/y/' a.py && pytest", ["other", "search", "edit", "run"], True),
    ("mkdir x", ["other"], False),
    ("touch y", ["edit"], True),
    ("rm -f a.py", ["edit"], True),
    ("grep foo a.py 2>/dev/null | head -5", ["search", "other"], False),
    ("timeout 60 pytest -q", ["run"], False),
    ("tool:str_replace_editor view /testbed/a.py", ["read"], False),
    ("tool:str_replace_editor str_replace /testbed/a.py", ["edit"], True),
]


@pytest.mark.parametrize("cmd,kinds,write", CASES)
def test_command_table(cmd, kinds, write):
    parts = shell.split_chain(cmd)
    assert [shell.classify(p) for p in parts] == kinds
    assert shell.may_write(parts) == write


def test_probe():
    assert shell.is_state_probe(["git diff"]) and shell.is_state_probe(["git status --short"])
    assert not shell.is_state_probe(["git diff -- a.py > patch.txt"])


def test_objects():
    assert shell.main_kind_and_object(shell.split_chain("cd /app && sed -n '1,80p' lib/a.py"))[:2] == ("read", "lib/a.py")
    assert shell.main_kind_and_object(shell.split_chain("cat /app/lib/a.py"))[:2] == ("read", "lib/a.py")
    assert shell.main_kind_and_object(shell.split_chain("cd lib && cat a.py"))[:2] == ("read", "lib/a.py")


def test_normalization():
    assert norm_hash(PASS, 0, "run") == norm_hash(PASS2, 0, "run")
    assert norm_hash(PASS, 0, "run") != norm_hash(PASS, 1, "run")
    assert norm_hash("def f():\n    x", 0, "read") != norm_hash("def f():\n  x", 0, "read")


# --- D.11 synthetic cases ---
def test_case1_reread():
    ops = mk(("cat A.py", FILE_A), ("cat B.py", FILE_B), ("cat A.py", FILE_A))
    o = ops[2]
    assert o["cand_object"] == "op0" and o["cand_output"] == "op0"
    assert o["cand_facts"]["op0"] == {"same_output": True, "object_written_since": "no", "any_code_written_since": "no"}
    assert o["exact_repeat"]


def test_case3_other_file_written():
    ops = mk(("cat A.py", FILE_A), ("echo x >> README", ""), ("cat A.py", FILE_A))
    f = ops[2]["cand_facts"]["op0"]
    assert f["object_written_since"] == "no" and f["any_code_written_since"] == "yes"


def test_case4_edit_test_edit_test():
    ops = mk(("sed -i 's/a/b/' A.py", ""), ("pytest", FAIL, 1), ("sed -i 's/b/c/' A.py", ""), ("pytest", PASS, 0))
    f = ops[3]["cand_facts"]["op1"]
    assert f["any_code_written_since"] == "yes" and not f["same_output"]


def test_case5_test_rerun():
    ops = mk(("pytest", PASS), ("pytest", PASS2))
    f = ops[1]["cand_facts"]["op0"]
    assert f == {"same_output": True, "object_written_since": "no", "any_code_written_since": "no"}
    assert ops[1]["exact_repeat"]


def test_case6_mixed():
    o = mk(("grep x a.py && sed -i 's/x/y/' a.py && pytest", PASS))[0]
    assert o["part_kinds"] == ["search", "edit", "run"] and o["mixed"] and o["write"] == "true"
    assert o["written_paths"] == ["a.py"]


def test_case7_unknown_write():
    ops = mk(("cat A.py", FILE_A), ("python fix.py", "done"), ("cat A.py", FILE_A))
    assert ops[2]["cand_facts"]["op0"]["object_written_since"] == "unknown"
    assert ops[2]["state"] is None


def test_case8_empty_outputs():
    ops = mk(("mkdir x", ""), ("touch y", ""), ("echo OK", "OK"), ("echo OK", "OK"))
    assert all(o["cand_output"] is None for o in ops)


def test_plain_diff_does_not_recover_unknown_complete_state():
    ops = mk(("python fix.py", "done"), ("git diff", "diff --git a/x b/x\n+1\n"), ("git diff", "diff --git a/x b/x\n+1\n"), ("ls", "a\nb"))
    assert ops[1]["state"] is None
    assert ops[2]["state"] is None and ops[3]["state"] is None


def test_aba_output_candidate():
    ops = mk(("cat A.py", FILE_A), ("cat B.py", FILE_B), ("sed -n '1,999p' A.py", FILE_A))
    assert ops[2]["cand_output"] == "op0"


def test_submit_is_main_kind():
    assert shell.main_kind_and_object(shell.split_chain("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt"))[0] == "submit"


def test_redirect_not_object():
    assert shell.main_kind_and_object(shell.split_chain("cat a.py 2>/dev/null"))[:2] == ("read", "a.py")
    assert shell.main_kind_and_object(shell.split_chain("cat a.py 2> /dev/null"))[:2] == ("read", "a.py")


def test_heredoc_scripts_distinct_objects():
    a = shell.main_kind_and_object(shell.split_chain("python - <<'PY'\nprint(1)\nPY"))[1]
    b = shell.main_kind_and_object(shell.split_chain("python - <<'PY'\nprint(2)\nPY"))[1]
    assert a != b


# --- Task 1 (v2): inline Python write detection ---
PY_READONLY = "cd /app && python3 - <<'PY'\nfrom pathlib import Path\nsrc = Path('lib/a.py').read_text()\nprint(src.count('def '))\nPY"
PY_REWRITE = "cd /app && python3 - <<'PY'\nfrom pathlib import Path\np = Path('lib/a.py')\ns = p.read_text()\np.write_text(s.replace('x', 'y'))\nPY"
PY_COMPUTED = "python3 - <<'PY'\nimport sys\nname = sys.argv[0] + '.py'\nopen(name, 'w').write('x')\nPY"
PY_PRINT = "python -c \"print('hello')\""


def test_py_readonly_heredoc():
    assert shell.write_info(shell.split_chain(PY_READONLY)) == (False, [])


def test_py_rewrite_literal_path():
    assert shell.write_info(shell.split_chain(PY_REWRITE)) == (True, ["lib/a.py"])


def test_py_computed_path_unknown():
    assert shell.write_info(shell.split_chain(PY_COMPUTED))[0] == "unknown"


def test_py_c_print():
    assert shell.write_info(shell.split_chain(PY_PRINT)) == (False, [])


def test_py_c_multiline_open_write():
    cmd = "python3 -c \"\nwith open('/app/src/x.py', 'a') as f:\n    f.write('#')\n\""
    assert shell.write_info(shell.split_chain(cmd)) == (True, ["src/x.py"])


def test_py_open_modes_and_ops():
    from worktrace.parse.pyinline import analyze
    assert analyze("open('a.txt').read()") == (False, [])
    assert analyze("open('a.txt', 'r+').write('x')") == (True, ["a.txt"])
    assert analyze("import json\njson.dump({}, open('c.json', 'w'))") == (True, ["c.json"])
    assert analyze("import os\nos.remove('d.py')") == (True, ["d.py"])
    assert analyze("import shutil\nshutil.copy('a', 'b')") == (True, ["b"])
    assert analyze("import os\nos.rename('a', 'b')") == (True, ["a", "b"])
    assert analyze("for f in ['a.py', 'b.py']:\n    open(f, 'w').write('')") == (True, ["a.py", "b.py"])
    assert analyze("exec(open('x.py').read())")[0] == "unknown"
    sh = shell._shell_write_for_python
    assert analyze("import subprocess\nsubprocess.run(['pytest', '-q'])", sh) == (False, [])
    assert analyze("import subprocess\nsubprocess.run(cmd, shell=True)", sh)[0] == "unknown"
    assert analyze("s = open('a').read()\nprint(s.replace('x', 'y'))") == (False, [])
    assert analyze("def broken(:\n open('z', 'w')") == (True, ["z"])  # regex fallback, literal path
    assert analyze("def broken(:\n open(name, 'w')")[0] == "unknown"  # regex fallback, computed path
    assert analyze("def broken(:\n print(1)") == (False, [])


def test_heredoc_script_written_then_executed():
    ops = mk(("cat A.py", FILE_A),
             ("cat > /tmp/fix.py <<'EOF'\nfrom pathlib import Path\nPath('A.py').write_text('new')\nEOF", ""),
             ("python /tmp/fix.py", ""),
             ("cat A.py", FILE_A))
    assert ops[1]["write"] == "true" and ops[1]["state"] == ops[2]["state"]  # /tmp write: code state unchanged
    assert ops[2]["write"] == "true" and ops[2]["written_paths"] == ["A.py"]
    assert ops[3]["cand_facts"]["op0"]["object_written_since"] == "yes"


def test_readonly_script_keeps_state_known():
    ops = mk(("pytest", PASS), (PY_READONLY, "3 defs found here ok"), ("pytest", PASS2))
    assert ops[2]["cand_facts"]["op0"]["any_code_written_since"] == "no"


def test_git_checkout_path_is_revert():
    assert shell.classify("git checkout lib/ansible/utils/encrypt.py") == "revert"
    assert shell.classify("git checkout setup.py") == "revert"
    assert shell.classify("git checkout main") == "other"


def test_tempfile_paths_outside_repo():
    from worktrace.parse.pyinline import analyze
    w, p = analyze("import tempfile, shutil\nd = tempfile.mkdtemp()\nshutil.rmtree(d)")
    assert w is True and all(x.startswith("/tmp/") for x in p)
    w, p = analyze("import tempfile, os\nwith tempfile.TemporaryDirectory() as d:\n    open(os.path.join(d, 'x'), 'w').write('1')")
    assert w is True and all(x.startswith("/tmp/") for x in p)
