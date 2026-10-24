# Task 5: Open-SWE-Traces, v1.2 or v2.0? (inspection only; nothing bulk-downloaded)

## Sources
- `list_repo_files` / `list_repo_tree` at `main` = `9b4efcd` (2026-10-23) and at the pinned `a85dc97`.
- `README.md` and `data_distribution.md` at both revisions: `raw/openswe_meta/`.
- The `instance_id` and `resolved` columns of every shard of the three harnesses: `openswe_ids.parquet`, `scripts/v2_openswe_ids.py`.

## What each version contains (OpenHands, SWE-agent and mini-SWE-agent only)
| | v1.2 | v2.0 |
|---|---|---|
| Agent model | Qwen3.8-27B (thinking, xhigh) | Qwen3.8-Flash-Next (thinking, xhigh) |
| Released | 09/26; files unchanged since | uploaded 2026-10-23 (yesterday); the card dates it "10/26" |
| Trajectories (OH / SWE-agent / mini) | 25,599 / 33,210 / 107,267 | 26,027 / 34,688 / 36,577 |
| Runs per instance | 1 / 1 / 2.6 | 1 / 1 / 1 |
| `resolved` known | 93.6% overall; mini-SWE has 10,672 "unknown" (9.9% of its runs) | 100% |
| instance_ids shared by all three harnesses | **22,059** | **22,229** |
| Size of the three harnesses | 20.7 GB (70 shards) | 10.8 GB (43 shards) |
| In our pinned revision `a85dc97` | yes, byte-identical to `main` (70/70 shard hashes) | partly: 3 harnesses present, but not the final card and distribution |
| Other harnesses | Claude Code, OpenCode (added later) | Claude Code, OpenCode |

Both versions easily support sampling 2,000 shared instance_ids. Either way, reading only the needed rows (column- and row-group-selective) avoids pulling the full shards.

## Recommendation: **v1.2** (Qwen3.8-27B), pinned at `a85dc97`
1. **It matches the plan.** The plan names Qwen3.8-27B, and `config.yaml` already pins this revision.
2. **It is stable.** Its shards have not changed for a month and are byte-identical at today's `main`.
   - v2.0 went up yesterday, and the README and distribution table were edited about 10 times that day.
   - The card's release date ("10/26") is still in the future.
   - It may still change under us. Pinning a commit protects reproducibility, but not against a re-upload that fixes v2.0's data.
3. **Repeat runs.** mini-SWE-agent's 2.6 runs per instance in v1.2 give within-task variation for free. The harness comparison still samples one run per harness per instance (seed 0).

**Costs of choosing v1.2:**
- Drop mini-SWE runs with unknown `resolved` before sampling (9.9% of mini-SWE runs).
- The three harnesses total about twice v2.0's size. With selective reads this costs time, not disk.

**When v2.0 would be the better choice:** if you want the newest model, one run per instance and full `resolved` labels, and accept a dataset that is one day old.

**Note on annotator independence:** our annotation endpoint also serves Qwen3.8-Flash-Next (`x-test-3`). Neither annotator is Qwen (DeepSeek primary, GLM as MODEL_2), so either choice keeps the annotators independent of the agent family.

**Stopped here for your decision (v1.2 or v2.0).** Nothing has been downloaded beyond the metadata and the two id columns.
