"""Task 5: Open-SWE-Traces v1.2 (Qwen3.8-27B; OpenHands, SWE-agent, mini-swe-agent), the 2,000-task sample.

usage: v2_task5.py events      # sampled rows of every downloaded shard -> data/events/openswe/ (facts included)
       v2_task5.py audit       # 10 runs per harness (seed 0): ops vs the raw messages, printed and checked
       v2_task5.py benchmark   # Section 3 benchmark (no LLM): Table 1 by harness, Table 2 by gold-patch size
Raw shards: raw/openswe_v12/ (scripts/openswe_download.py); sample: results/v2/task5/sample.csv."""
import glob
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from v2_viewb import _rci  # noqa: E402
from worktrace.facts import extract_facts  # noqa: E402
from worktrace.loaders import openswe as O  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW, EV, OUT = f"{ROOT}/raw/openswe_v12", f"{ROOT}/data/events/openswe", f"{ROOT}/results/v2/task5"


def _safe(rid):
    return rid.replace(":", "__").replace("/", "_")


def _rows(path, wanted, batch=25):
    """Stream a shard (one large row group) in small batches and yield (row index, row) for the wanted rows."""
    wanted, base = set(wanted), 0
    for b in pq.ParquetFile(path).iter_batches(batch_size=batch):
        hit = [i for i in range(b.num_rows) if base + i in wanted]
        if hit:
            for i, r in zip(hit, b.take(hit).to_pylist()):
                yield base + i, r
        base += b.num_rows


def _shard_events(path_rows):
    """Load the sampled rows of one shard, extract facts, write one event log per run. Returns run records."""
    rel, rows = path_rows
    harness = rel.split("/")[1]
    runs = []
    for i, row in _rows(f"{RAW}/{rel}", rows):
        run, ops = O.load_row(row, harness)
        extract_facts(ops)
        run["file"], run["row"] = rel, int(i)
        run["chars_assistant"] = sum(len(m.get("content") or "") + len(m.get("reasoning_content") or "") +
                                     sum(len(tc["function"].get("arguments") or "") for tc in m.get("tool_calls") or [])
                                     for m in row["messages"] if m["role"] == "assistant")
        run["chars_context_final"] = sum(len(m.get("content") or "") + len(m.get("reasoning_content") or "") for m in row["messages"])
        with open(f"{EV}/{_safe(run['run_id'])}.jsonl", "w") as f:
            for o in ops:
                f.write(json.dumps(o, default=str) + "\n")
        json.dump({k: v for k, v in run.items() if k != "submission"} | {"submission": run["submission"]},
                  open(f"{EV}/{_safe(run['run_id'])}.run.json", "w"))
        runs.append({k: v for k, v in run.items() if k not in ("issue", "submission")})
    print(rel, len(runs), flush=True)
    return runs


def events():
    os.makedirs(EV, exist_ok=True)
    S = pd.read_csv(f"{OUT}/sample.csv")
    done = set(pd.read_parquet(f"{OUT}/runs.parquet").file) if os.path.exists(f"{OUT}/runs.parquet") else set()
    ok = {l.split(" ", 1)[1].strip() for l in open(f"{OUT}/download.log") if l.startswith("OK ")}
    jobs = [(f, list(g.row)) for f, g in S.groupby("file") if f in ok and f not in done]
    print("shards to process:", len(jobs), "| already done:", len(done), "| not downloaded yet:", S.file.nunique() - len(ok))
    with Pool(2, maxtasksperchild=1) as p:
        new = [r for rs in p.map(_shard_events, jobs) for r in rs]
    old = pd.read_parquet(f"{OUT}/runs.parquet") if done else pd.DataFrame()
    R = pd.concat([old, pd.DataFrame(new)], ignore_index=True)
    R.to_parquet(f"{OUT}/runs.parquet")
    print("runs with event logs:", len(R), R.groupby("harness").size().to_dict())


def _load(run_id):
    run = json.load(open(f"{EV}/{_safe(run_id)}.run.json"))
    ops = [json.loads(l) for l in open(f"{EV}/{_safe(run_id)}.jsonl")]
    return run, ops


def audit(n="10"):
    n = int(n)
    """Automated audit: for 10 runs per harness, rebuild the raw (call, reply) list straight from the parquet row and
    check it against the event log one to one (command text, output, exit code, turn). Prints the ops of each run."""
    R = pd.read_parquet(f"{OUT}/runs.parquet")
    rows, rng = [], np.random.default_rng(0)
    for h, g in R.groupby("harness"):
        for _, r in g.iloc[rng.choice(len(g), size=min(n, len(g)), replace=False)].iterrows():
            raw = next(row for _, row in _rows(f"{RAW}/{r.file}", [int(r.row)]))
            assert raw["trajectory_id"] == r.trajectory_id
            run, ops = _load(r.run_id)
            calls = []
            for t, m, pairs, n_rep in O._calls_with_results(raw["messages"]):
                calls += [(t, tc, rep) for tc, rep in pairs]
            problems = []
            if len(calls) != len(ops):
                problems.append(f"{len(calls)} raw calls vs {len(ops)} ops")
            for (t, tc, rep), o in zip(calls, ops):
                if o["turn_id"] != f"{run['run_id']}:t{t}":
                    problems.append(f"turn mismatch at {o['op_id']}")
                args = json.loads(tc["function"].get("arguments") or "{}")
                if tc["function"]["name"] in ("bash", "execute_bash") and o["command"] != args.get("command", ""):
                    problems.append(f"command mismatch at {o['op_id']}")
                if rep is not None and h != "mini-swe-agent" and (o["output"] or "") not in rep:
                    problems.append(f"output mismatch at {o['op_id']}")
                if rep is not None and h == "mini-swe-agent":
                    d = json.loads(rep)
                    if d.get("returncode") != o["exit_code"] or ("output" in d and d["output"] not in o["output"]):
                        problems.append(f"output/exit mismatch at {o['op_id']}")
            n_asst = sum(1 for m in raw["messages"] if m["role"] == "assistant")
            n_tool = sum(1 for m in raw["messages"] if m["role"] == "tool")
            last = raw["messages"][-1]
            rows.append({"harness": h, "run_id": r.run_id, "assistant_msgs": n_asst, "turns": run["n_turns"], "tool_msgs": n_tool,
                         "raw_calls": len(calls), "ops": len(ops), "replies_paired": sum(rep is not None for _, _, rep in calls),
                         "unreplied_calls": sum(rep is None for _, _, rep in calls), "last_msg_role": last["role"],
                         "last_op_kind": ops[-1]["kind"] if ops else None, "lost_results": run["lost_results"],
                         "kinds": json.dumps(pd.Series([o["kind"] for o in ops]).value_counts().to_dict()),
                         "edits_with_written_paths": sum(bool(o.get("written_paths")) for o in ops if o["kind"] == "edit"),
                         "edits": sum(o["kind"] == "edit" for o in ops), "exact_repeats": sum(o["exact_repeat"] for o in ops),
                         "exit_known": sum(o["exit_code"] is not None for o in ops if o["kind"] != "submit"),
                         "problems": "; ".join(problems[:5]) or "none"})
    A = pd.DataFrame(rows)
    A.to_csv(f"{OUT}/audit_10_per_harness.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(A.drop(columns=["run_id", "kinds"]).to_string())
    print("runs with problems:", int((A.problems != "none").sum()))


def benchmark():
    R = pd.read_parquet(f"{OUT}/runs.parquet")
    per = []
    for rid in R.run_id:
        _, ops = _load(rid)
        n = len(ops)
        per.append({"run_id": rid, "exact_repeats": sum(o["exact_repeat"] for o in ops),
                    "same_object": sum(o["cand_object"] is not None for o in ops),
                    "truncated_seen": sum(bool(o.get("agent_saw_truncated")) for o in ops),
                    **{f"kind_{k}": sum(o["kind"] == k for o in ops) for k in ("read", "search", "edit", "revert", "run", "probe", "submit", "other")}})
    R = R.merge(pd.DataFrame(per), on="run_id")
    R["exact_repeat_rate"] = R.exact_repeats / R.n_ops.clip(lower=1)
    R["same_object_rate"] = R.same_object / R.n_ops.clip(lower=1)
    R["resolved_f"] = R.resolved.astype(float)
    R.to_parquet(f"{OUT}/runs_benchmark.parquet")
    f = lambda t, pct=True: f"{100 * t[0]:.2f}% [{100 * t[1]:.2f}, {100 * t[2]:.2f}]" if pct else f"{t[0]:.1f} [{t[1]:.1f}, {t[2]:.1f}]"  # noqa: E731
    t1 = []
    for h, g in R.groupby("harness"):
        t1.append({"harness": h, "model": O.MODEL, "runs": len(g), "tasks": g.task_id.nunique(),
                   "resolve_rate": f(_rci(g, "resolved_f")), "turns": f(_rci(g, "n_turns"), False),
                   "tool_calls": f(_rci(g, "n_ops"), False),
                   "assistant_chars_k": f"{g.chars_assistant.mean() / 1e3:.1f}", "final_context_chars_k": f"{g.chars_context_final.mean() / 1e3:.1f}",
                   "exact_repeat_rate (pooled)": f(_rci(g, "exact_repeats", "n_ops")),
                   "exact_repeat_rate (run mean)": f(_rci(g, "exact_repeat_rate")),
                   "same_object_revisit (pooled)": f(_rci(g, "same_object", "n_ops")),
                   "runs_with_any_exact_repeat": f(_rci(g, lambda d: (d.exact_repeats > 0).astype(float))),
                   "ops_agent_saw_truncated": f(_rci(g, "truncated_seen", "n_ops")),
                   "lost_results": int(g.lost_results.sum())})
    T1 = pd.DataFrame(t1)
    T1.to_csv(f"{OUT}/table1_by_harness.csv", index=False)
    # Table 2: four equal-size task bins on gold-patch lines (same tasks in every harness)
    tv = R.groupby("task_id").gold_lines.first().dropna()
    bins = pd.qcut(tv.rank(method="first"), 4, labels=["Q1 easiest", "Q2", "Q3", "Q4 hardest"])
    R["bin"] = R.task_id.map(bins)
    t2 = []
    for (b, h), g in list(R.dropna(subset=["bin"]).groupby(["bin", "harness"], observed=True)) + \
            [((b, "ALL"), g) for b, g in R.dropna(subset=["bin"]).groupby("bin", observed=True)]:
        t2.append({"bin": b, "harness": h, "runs": len(g), "tasks": g.task_id.nunique(),
                   "gold_lines_range": f"{tv[bins == b].min():.0f}-{tv[bins == b].max():.0f}",
                   "resolve_rate": f(_rci(g, "resolved_f")), "tool_calls": f(_rci(g, "n_ops"), False),
                   "exact_repeat_rate (pooled)": f(_rci(g, "exact_repeats", "n_ops")),
                   "same_object_revisit (pooled)": f(_rci(g, "same_object", "n_ops")),
                   "runs_with_any_exact_repeat": f(_rci(g, lambda d: (d.exact_repeats > 0).astype(float)))})
    T2 = pd.DataFrame(t2)
    T2.to_csv(f"{OUT}/table2_gold_patch_bins.csv", index=False)
    K = R.groupby("harness")[[c for c in R.columns if c.startswith("kind_")]].sum()
    (K.div(K.sum(1), axis=0) * 100).round(1).to_csv(f"{OUT}/op_kinds_by_harness_pct.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(T1.T.to_string()); print(T2.to_string()); print((K.div(K.sum(1), axis=0) * 100).round(1).to_string())


if __name__ == "__main__":
    {"events": events, "audit": audit, "benchmark": benchmark}[sys.argv[1]](*sys.argv[2:])
