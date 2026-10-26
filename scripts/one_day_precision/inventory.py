"""Section 3: availability inventory for the primary pair (Gemini 3.7 Flash vs GPT-5.6 Luna, mini-swe-agent, repeat 1),
and the frozen pilot sample (Section 4). Reads the raw JetBrains shards and the SWE-bench Pro reference table read-only.

usage: python scripts/one_day_precision/inventory.py   -> availability.csv, sample_manifest.csv"""
import ast
import json
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, PRIMARY, ROOT, SEED, SHARD, log  # noqa: E402
from worktrace.loaders import jetbrains as J  # noqa: E402

N_CAL, N_EVAL = 3, 8


def reference_table():
    ref = {}
    for cfg in ("v1", "default"):  # same order as the project's gold-patch join
        d = pd.read_parquet(f"{ROOT}/raw/swebenchpro/{cfg}.parquet")
        for r in d.itertuples():
            ref.setdefault(r.instance_id, (cfg, r))
    return ref


def inventory(repeat=1):
    ref = reference_table()
    rows = []
    for m in PRIMARY:
        path = f"{ROOT}/raw/jetbrains/{SHARD[m]}-run{repeat}.parquet"
        for b in pq.ParquetFile(path).iter_batches(batch_size=25):
            for row in b.to_pylist():
                infra = J.is_infra_failure(row)
                run, ops = J.load_row(row) if not infra else ({"issue": ""}, [])
                cfg, r = ref.get(row["instance_id"], (None, None))
                miss = []
                if infra:
                    miss.append("infrastructure failure (no trajectory)")
                if not run.get("issue"):
                    miss.append("issue text")
                if r is None:
                    miss.append("SWE-bench Pro reference row")
                if not (row.get("submission") or "").strip():
                    miss.append("final submission patch (empty)")
                n_trunc = sum(bool(o.get("agent_saw_truncated")) for o in ops)
                n_missing = sum(bool(o.get("missing_result")) for o in ops)
                rows.append({
                    "model": m, "repeat": repeat, "task_id": row["instance_id"],
                    "run_id": f"jb:{SHARD[m]}:{row['instance_id']}:r{repeat}",
                    "resolved": row.get("resolved"), "outcome_provenance": "dataset field `resolved` (SWE-bench Pro evaluation recorded by the trajectory dataset); not re-executed here",
                    "issue_text": bool(run.get("issue")), "issue_chars": len(run.get("issue") or ""),
                    "n_actions": len(ops), "commands_complete": all(bool(o.get("command")) for o in ops) if ops else False,
                    "observations_missing": n_missing, "observations_truncated_seen_by_agent": n_trunc,
                    "final_patch": bool((row.get("submission") or "").strip()), "final_patch_chars": len(row.get("submission") or ""),
                    "initial_revision": getattr(r, "base_commit", None) if r is not None else None,
                    "reference_patch": bool(r is not None and str(r.patch).strip()),
                    "reference_requirements_text": bool(r is not None and str(r.requirements).strip() not in ("", "nan")),
                    "fail_to_pass_tests": len(ast.literal_eval(r.fail_to_pass)) if r is not None and str(r.fail_to_pass).startswith("[") else (None if r is None else -1),
                    "reference_config": cfg,
                    "code_state_checkable": "trace-only: no task environment is available locally; state is inferred from logged commands/outputs, not executed",
                    "missing": "; ".join(miss) or "none"})
        log(f"inventory: {m} repeat {repeat} done")
    A = pd.DataFrame(rows)
    A.to_csv(f"{OUT}/availability.csv", index=False)
    return A


def freeze_sample(A):
    """Tasks where both repeat-1 runs succeeded and have usable context, in a seeded random order."""
    w = A.pivot_table(index="task_id", columns="model", values="resolved", aggfunc="first")
    usable = A.groupby("task_id").apply(lambda g: bool((g.missing == "none").all() and len(g) == 2), include_groups=False)
    both = sorted(t for t in w.index if all(bool(w.loc[t, m]) for m in PRIMARY) and usable.get(t, False))
    order = list(np.random.default_rng(SEED).permutation(both))
    rows = []
    for i, t in enumerate(order):
        split = "calibration" if i < N_CAL else ("evaluation" if i < N_CAL + N_EVAL else "reserve")
        for m in PRIMARY:
            a = A[(A.task_id == t) & (A.model == m)].iloc[0]
            rows.append({"order": i, "split": split, "task_id": t, "model": m, "run_id": a.run_id, "repeat": 1,
                         "resolved": a.resolved, "n_actions": a.n_actions, "exclusion": ""})
    S = pd.DataFrame(rows)
    S.to_csv(f"{OUT}/sample_manifest.csv", index=False)
    n_tasks = A.task_id.nunique()
    log(f"sample frozen: {n_tasks} shared tasks; both-success with usable context {len(both)}; "
        f"calibration {N_CAL}, evaluation {N_EVAL}, reserve {len(both) - N_CAL - N_EVAL}")
    return S, both


if __name__ == "__main__":
    A = inventory()
    S, both = freeze_sample(A)
    print(A.groupby("model")[["issue_text", "commands_complete", "final_patch", "reference_patch", "reference_requirements_text"]].mean())
    print(A.groupby("model").resolved.mean(), A.missing.value_counts().head())
    print(S[S.split != "reserve"])
