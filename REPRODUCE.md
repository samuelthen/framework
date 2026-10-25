# Reproducing WorkTrace on another machine

**What is in the git repository:** code, configuration, every LLM label (`data/labels/*.jsonl`), run tables, results, figures and the View B graphs of all 6,300 JetBrains runs.

**What is not in it:**
- the raw third-party datasets (1.2 GB JetBrains, 20.7 GB Open-SWE);
- the per-run event logs built from them;
- the API caches and credentials.

You therefore download the raw data once and rebuild from it. **No API key is needed** to build graphs or re-run the analyses: all labels are in the repository. A key is only needed to label new runs.

## 1. Set up (Python 3.12)
```bash
git clone https://github.com/samuelthen/framework.git && cd framework
python3.12 -m venv .venv
.venv/bin/pip install -r worktrace/requirements.txt
cd worktrace
../.venv/bin/python -m pytest -q tests        # fact tests
```

## 2. Look without downloading anything
| What | Where |
|---|---|
| View B code-version graphs, all 6,300 JetBrains runs (one JSON object per run; variant (b) in `..._support.jsonl`) | `data/version_graphs_v2*.jsonl` |
| Interactive viewer of the 50 pilot runs (hover a step for command, output and label) | `viewer/index.html` |
| Labelled pilot traces, View B examples and aggregates | `figures/traces/`, `figures/v2/` |

## 3. Download the raw data
```bash
../.venv/bin/python scripts/download_data.py jetbrains   # ~1.2 GB: 9 trajectory shards + SWE-bench Pro gold patches
../.venv/bin/python scripts/download_data.py openswe     # ~20.7 GB: Open-SWE-Traces v1.2 shards of the Task 5 sample (optional)
../.venv/bin/python scripts/v2_task5.py events           # Open-SWE only: per-run event logs -> data/events/openswe/
```
- **Revisions:** every download is pinned to the revision in `config.yaml` (`datasets`).
- **Hugging Face token:** setting `HF_TOKEN` speeds up the download.

## 4. Build and draw the graphs of any run
```bash
../.venv/bin/python scripts/graph_run.py --list jetbrains 5          # some run ids (or: --list openswe 5)
../.venv/bin/python scripts/graph_run.py 'jb:gemini_3_7_flash:<instance_id>:r1' [out_dir]
../.venv/bin/python scripts/graph_run.py 'os:openhands:<instance_id>:<traj8>'
```
Output goes to `figures/runs/` by default:
- **`<run>.graphs.json`:**
  - `view_a_target` and `view_a_object`: the operation graph. Nodes are work targets/objects; edges are operations, with labels.
  - `view_b`: the code-version graph, variant (b).
- **`<run>.view_a.png`:** View A by object. Green back-edges are revisits, red are reproductions, a ring is a self-loop.
- **`<run>.view_b.png`:** View B code versions. Self-loops are verify runs.
- **`<run>.trace.png`:** every op on its target, coloured by label. Only drawn if the run is labelled.

**Which labels are used:**
- **JetBrains runs:** the scale labels cover all Gemini runs and the Luna/Terra 10% samples; pilot labels cover the 50 pilot runs. Other runs are drawn without labels.
- **Qwen runs:** labels exist for the pilot and the 500-task main run.

## 5. Re-run the analyses (no API calls)
```bash
../.venv/bin/python scripts/m1_m3_benchmark.py          # Section 3 benchmark, all JetBrains runs
../.venv/bin/python scripts/m4_pilot.py sample && ../.venv/bin/python scripts/m4_pilot.py analyze   # pilot
../.venv/bin/python scripts/v2_viewb.py scale            # View B for all runs (Pool(2); needs ~8 GB RAM)
../.venv/bin/python scripts/v2_task6_analyze.py build && ../.venv/bin/python scripts/v2_task6_analyze.py report  # scale measures, return-after-k
../.venv/bin/python scripts/v2_task5.py benchmark        # Open-SWE benchmark (after step 3)
```
- **Memory:** one JetBrains Gemini shard with facts takes about 4.7 GB of RAM.
- **Labeling** (`m4_pilot.py label`, `v2_task6.py label`, `v2_qwen.py`) needs `soclaas.env` with `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY` and `SOCLAAS_MODEL`. It is not in the repository.
