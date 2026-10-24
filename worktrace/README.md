# WorkTrace — pilot implementation

Implements Appendices A–D of the WorkTrace draft up to the pilot (M0–M8 on 50 runs; M9 and the interventions are out of scope).

## Run

```bash
cd worktrace
../.venv/bin/python -m pytest -q tests                 # D.9 / D.11 fact tests
../.venv/bin/python scripts/m1_m3_benchmark.py         # M1-M3: all 6,300 JetBrains runs, no LLM
../.venv/bin/python scripts/m4_pilot.py sample         # pilot: 50 runs -> data/events/jetbrains/
../.venv/bin/python scripts/m4_pilot.py label          # M4: LLM labels -> data/labels/pilot.jsonl (cached, resumable)
../.venv/bin/python scripts/m4_pilot.py label --llm-only   # B.8 LLM-only baseline (matched ops only)
../.venv/bin/python scripts/m4_pilot.py analyze        # M6-M7: graphs, signatures, measures, go/no-go
../.venv/bin/python scripts/m5_annotation.py export    # M5: blind human-annotation sample -> annotation/pilot.csv
../.venv/bin/python scripts/m5_annotation.py agree annotation/pilot_filled.csv   # after humans label it
../.venv/bin/python scripts/m8_figures.py              # M8: figures/ and viewer/index.html
```

The annotator endpoint/model come from `../soclaas.env` (`SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY`, `SOCLAAS_MODEL`).
Every bracketed number from the draft is in `config.yaml`.

## Deviations from the draft (decided for the pilot; confirm before M9)

1. **JetBrains only.** Open-SWE-Traces v1.2 (Qwen3.8-27B, ~21 GB) could not be fetched in time: Hugging Face
   throughput from this machine was ~1 MB/s and each parquet is a single large row group, so even one row costs a
   full ~250 MB column read. The loader for it is not written yet. Note: the dataset now also has a **v2.0**
   (`qwen38_flash_next`, default config, dated after the draft's Oct 23 check).
2. **Annotator** = SoCLaaS `x-test-2`, served as `deepseek-v4.1-flash-1017`, temperature 0. The per-key queue
   admits only ~3–4 concurrent requests, and full reasoning took ~17–40 s/label. So: `reasoning_effort=low` for
   operations that have a match candidate (relation/contribution need a comparison), and thinking **off** for
   operations without any candidate (relation is unmatched by construction). The mode is stored per label (`reasoning`).
3. **Annotator IDs.** The prompt shows short local IDs (`op12`) instead of the long run IDs; they are mapped back.
4. **Visit sequences and signatures are reported by object** (targets merged by object) as the primary view, and by
   (object, purpose) as a second view: free-text purposes rarely repeat verbatim, so (object, purpose) targets
   almost never recur.
5. **LLM-only baseline** sees the previous 10 operations (no rule facts, no candidates) and is run on matched
   operations only.
6. **Code state** after `git diff`/`git status` is anchored on the hash of that output; `git status` and `git diff`
   of the same tree therefore give different state IDs (conservative: never claims "unchanged" wrongly).
7. **Gold patches**: joined from `ScaleAI/SWE-bench_Pro` (`patch` column; `v1` config, then `default`).
8. **Pilot sample**: 17 tasks (seed 0) × 3 models, one random run index per (task, model), truncated to 50 runs.
