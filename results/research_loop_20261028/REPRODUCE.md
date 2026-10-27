# Reproduce the measurement study

Run from `/Users/samuelthen/Desktop/framework`. Python needs pandas, pyarrow, numpy and pytest; figures also need matplotlib. Live continuations need the installed mini-SWE-agent adapter dependencies. Do not place API keys in tracked files.

## Archived inputs and fixed plans

The two original shards and task reference are verified by `scripts/utility_audit/download_inputs.py`. Terra's pinned input and SHA-256 are in `terra_input.json`. `analysis_plan.json` and `analysis_amendments.md` preserve selection and exposure history. Do not regenerate the task split based on results.

```sh
PYTHONPATH=worktrace python3 scripts/research_loop/extract.py
PYTHONPATH=worktrace python3 scripts/research_loop/analyze.py
PYTHONPATH=worktrace python3 scripts/research_loop/demand_harness.py
PYTHONPATH=worktrace python3 scripts/research_loop/robustness.py
PYTHONPATH=worktrace python3 scripts/research_loop/allocation_witness.py
python3 scripts/research_loop/text_baseline.py
```

Extraction reuses the frozen syntax-checked decomposition. It executes `bash -n` for parsing but never runs a recorded command. It can take several minutes. Native counts, candidate counts, operational categories and response usage remain distinct.

The available-text baseline also needs `tiktoken`. It uses `o200k_base`, reports its version, and compares estimated text counts with recorded usage without replacing it. The tokenizer may fetch a public vocabulary file on first use. This sensitivity does not reproduce the closest cost paper's full future-context/cache charging model.

The large `runs.jsonl`, `responses.jsonl`, validation inventory and witness file remain locally generated artifacts. Compact summaries and CSV results suffice to inspect the published claims. Rebuild these ledgers when reproducing exact accounting witnesses.

## Independent checks

```sh
PYTHONPATH=worktrace python3 scripts/research_loop/executable_panel.py prepare
PYTHONPATH=worktrace python3 scripts/research_loop/executable_panel.py modules
PYTHONPATH=worktrace python3 scripts/research_loop/executable_panel.py execute
PYTHONPATH=worktrace python3 scripts/research_loop/patch_ablation.py
```

Preparation downloads exact source commits. Module preparation uses network; actual checking disables it. All five selected tasks are retained. The fifth requires the separately pinned Go 1.24 image. Current scripts overwrite their own phase outputs on repeat; retain original results first if comparing executions. No operation runs recorded trajectory shell programs. These are scoped package checks, not original benchmark certification.

## Soc LLM pilot

The user selected DeepSeek, `x-test-2`, whose preflight returned `deepseek-v4.1-flash-1017`. The existing credential file is read internally from a local path. Pricing is not inferred from the endpoint or assumed free in the metrics.

```sh
docker build -f scripts/research_loop/Agent.Dockerfile \
  -t worktrace/utility-agent:20261028 scripts/research_loop
PYTHONPATH=worktrace python3 scripts/research_loop/live_pilot.py prepare
PYTHONPATH=worktrace python3 scripts/research_loop/live_pilot.py smoke --env-file /local/private/soclaas.env
PYTHONPATH=worktrace python3 scripts/research_loop/live_v2.py prepare
PYTHONPATH=worktrace python3 scripts/research_loop/live_v2.py execute --env-file /local/private/soclaas.env
PYTHONPATH=worktrace python3 scripts/research_loop/grade_audit.py
```

The original v1 execution is not needed to initialize v2, but its preflight public source/cache records are used. Frozen existing plans and completed episodes are retained. A new experiment needs a new output root. Docker workspaces expose only source, a private build cache and read-only Go modules. Hidden evaluator patches, fixtures, grading caches and credentials never enter agent containers. Only production source edits are exported for grading.

The v2 schedule has 18 episodes, eight calls each, two workers, a 160-attempt ceiling and a three-million accounted-token ceiling. Budget reservation includes pending requests and unknown-usage failures. macOS uses private copy-on-write directory clones, not hard links. A 3 GB disk reserve blocks new episodes instead of silently discarding results. Do not interpret blocked episodes as model failures.

The exact context applies the dataset test patch. The fixture-complete sensitivity adds only reference testdata assets equally. Public observations are normalized test outcomes; cache reuse does not reproduce timestamps, side effects or full logs. This is a controlled warm-cache diagnostic study, not a deployed universal evidence cache.

## Summaries and software validation

```sh
PYTHONPATH=worktrace python3 scripts/research_loop/live_report.py
python3 scripts/research_loop/plot_paper.py
PYTHONPATH=worktrace python3 -m pytest -q worktrace/tests \
  scripts/one_day_precision/test_one_day.py \
  scripts/precision_validation/test_validation.py \
  scripts/followup/test_followup.py
```

Independent tasks, snapshots, decodes, test cases and software regression tests are different units. The reports do not pool them into one sample size.
