from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph, summarize


def _run(cmds):
    ops = [{"op_id": f"r:t{i}.0", "turn_id": f"r:t{i}", "command": c, "output": o, "exit_code": e}
           for i, (c, o, e) in enumerate(cmds)]
    extract_facts(ops)
    return build_version_graph({"run_id": "r", "task_id": "t", "model": "m", "resolved": True}, ops)


def labels(g):
    return [e["label"] for e in g["edges"]]


def baseline(*paths):
    return [('git status --porcelain', '', 0), ('git ls-files', '\n'.join(paths)+'\n', 0)]


def test_linear_edits_and_verify():
    g = _run([("cat a.py", "x = 1\n" * 5, 0), ("sed -i 's/1/2/' a.py", "", 0), ("pytest", "FAILED test_a - assert", 1),
              ("sed -i 's/2/3/' a.py", "", 0), ("pytest", "1 passed", 0), ("pytest", "1 passed", 0), ("git diff > patch.txt", "", 0),
              ("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt", "", 0)])
    assert g["n_versions"] == 2
    assert labels(g) == ["initial", "correct", "final"]
    s = summarize(g)
    assert s["verify_final"] == 2 and s["verify_other_total"] == 1
    assert [(n["x"], n["y"]) for n in g["nodes"]] == [(0, 0), (1, 1), (2, 1)]


def test_tmp_write_is_not_a_version():
    g = _run([("cat > /tmp/x.py <<'EOF'\nprint(1)\nEOF", "", 0), ("python /tmp/x.py", "1", 0)])
    assert g["n_versions"] == 0


def test_full_revert_returns_to_root_and_next_version_goes_up_a_row():
    g = _run(baseline('a.py') + [("sed -i 's/a/b/' a.py", "", 0), ("git checkout .", "", 0), ("sed -i 's/a/c/' a.py", "", 0)])
    assert labels(g) == ["initial", "backtrack", "revise"]
    assert g["n_versions"] == 2
    assert [(n["x"], n["y"]) for n in g["nodes"]] == [(0, 0), (1, 1), (2, 2)]


def test_partial_revert_of_all_written_files_is_root():
    g = _run(baseline('a.py') + [("sed -i 's/a/b/' a.py", "", 0), ("git checkout -- a.py", "", 0)])
    assert labels(g) == ["initial", "backtrack"] and g["final"] == 0


def test_identical_plain_diff_is_not_complete_content_identity():
    d = "diff --git a/a.py b/a.py\n-x\n+y\n"
    g = _run([("sed -i 's/x/y/' a.py", "", 0), ("git diff", d, 0), ("sed -i 's/y/z/' a.py", "", 0),
              ("sed -i 's/z/y/' a.py", "", 0), ("git diff", d, 0)])
    assert g["n_versions"] == 3
    assert labels(g) == ["initial", "revise", "revise"]


def test_stash_pop_returns_to_stashed_version():
    g = _run(baseline('a.py') + [("sed -i 's/x/y/' a.py", "", 0), ("git stash", "Saved", 0), ("pytest", "fail", 1), ("git stash pop", "", 0)])
    assert labels(g) == ["initial", "backtrack", "backtrack"]
    assert g["final"] == 1 and g["nodes"][0]["verify"] == 1


def test_unknown_write_is_uncertain_version():
    g = _run([("make -C build", "", 0)])
    assert g["n_versions"] == 1 and g["nodes"][1]["uncertain"]


def test_inline_read_script_is_not_a_verify():
    g = _run([("python3 -c \"\nwith open('a.py') as f:\n    print(f.read())\n\"", "x = 1\n" * 5, 0),
              ("python3 -c \"\nfrom pkg import mod\nprint(mod.f())\n\"", "ok", 0)])
    assert g["nodes"][0]["verify"] == 1


def test_error_loop_signature():
    from worktrace.signatures import error_loops, error_signature
    bb = "grep: unrecognized option: include=*.py\nBusyBox v1.36.1 multi-call binary.\n\nUsage: grep [-HhnlLoqvsrRiwFE]"
    ops = [{"op_id": f"r:t{i}.0", "turn_id": f"r:t{i}", "command": c, "output": o, "exit_code": e}
           for i, (c, o, e) in enumerate([("ls", "a.py", 0), ("grep -r --include=*.py x .", bb, 2),
                                          ("grep -rn --include=*.py y src", bb, 2), ("grep --include=*.py -r z", bb, 2),
                                          ("cat a.py", "x = 1\n" * 5, 0)])]
    extract_facts(ops)
    assert error_signature(ops[0]) is None
    assert error_signature(ops[1]) == "grep: unrecognized option: include=*.py"
    loops = error_loops(ops)
    assert [[o["op_index"] for o in l] for l in loops] == [[1, 2, 3]]
    t = [{"output": "FAILED t.py::a - AssertionError\n=== 1 failed in 0.29s ===", "exit_code": 1},
         {"output": "FAILED t.py::a - AssertionError\n=== 1 failed in 0.31s ===", "exit_code": 1}]
    assert error_signature(t[0]) == error_signature(t[1])
    assert error_signature({"output": "Traceback (most recent call last):\nKeyError: 'x'", "exit_code": 0}) == "keyerror: 'x'"


def test_js_refinement_in_view_b():
    from worktrace.versions import repo_write
    g = _run([("node -e 'console.log(JSON.parse(require(\"fs\").readFileSync(\"package.json\")).scripts)'", "{}", 0),
              ("npx eslint src/a.ts", "", 0), ("./node_modules/.bin/tsc --noEmit true", "", 0),
              ("node -e '\nconst fs = require(\"fs\");\nconst file = \"src/a.ts\";\nlet c = fs.readFileSync(file, \"utf8\");\nfs.writeFileSync(file, c.replace(\"a\", \"b\"));\n'", "", 0),
              ("make -C build", "", 0)])
    assert g["n_versions"] == 2
    assert [n["uncertain"] for n in g["nodes"]] == [False, False, True]


def test_support_candidates_and_variant_b():
    from worktrace.versions import support_candidates
    cmds = [("cat src/a.py", "x = 1\n" * 5, 0), ("cat > repro.py <<'EOF'\nimport a\nEOF", "", 0), ("python repro.py", "boom", 1),
            ("sed -i 's/1/2/' src/a.py", "", 0), ("python repro.py", "ok", 0), ("rm repro.py", "", 0),
            ("cat > tests/test_new.py <<'EOF'\ndef test(): pass\nEOF", "", 0)]
    ops = [{"op_id": f"r:t{i}.0", "turn_id": f"r:t{i}", "command": c, "output": o, "exit_code": e} for i, (c, o, e) in enumerate(cmds)]
    extract_facts(ops)
    sc = support_candidates(ops, ["src/a.py", "tests/test_new.py"], ["tests/test_new.py"])
    assert sc["repro.py"] == {"new": True, "deleted_later": True, "in_submission": False, "candidate": True}
    assert not sc["src/a.py"]["candidate"] and not sc["tests/test_new.py"]["candidate"]
    run = {"run_id": "r", "task_id": "t", "model": "m", "resolved": True}
    from worktrace.versions import build_version_graph
    assert build_version_graph(run, ops)["n_versions"] == 4
    gb = build_version_graph(run, ops, support_paths={p for p, v in sc.items() if v["candidate"]})
    assert gb["n_versions"] == 2 and gb["nodes"][0]["evidence"].get("support") == 1


def test_js_go_tool_refinement():
    g = _run([("yarn workspace proton-mail check-types", "", 0), ("yarn prettier --check a.ts", "", 0), ("go test ./model", "ok", 0),
              ("go test -c ./lib/kube/proxy && ./proxy.test", "PASS", 0), ("./proxy.test -test.run TestA", "PASS", 0),
              ("rm -f proxy.test", "", 0), ("make -j4 -C /app/node_modules/better-sqlite3/build", "", 0)])
    assert g["n_versions"] == 0
