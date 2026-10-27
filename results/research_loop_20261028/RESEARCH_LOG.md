# Active research loop — 28 October 2026

The user requested sustained work until the scientific gaps are closed. An active goal tracks the research; ACL acceptance is not a guaranteed or mechanically testable endpoint. Preserve evidence, failed hypotheses and exposure history.

## User constraints and authorization

- Use executable validation where possible; no human reviewers are available.
- The user authorized Soc LLM model experiments, describing the service as free and saying to use available models.
- The existing Soc configuration was found at `/Users/samuelthen/Desktop/soc-llm/soclaas.env`. Read it internally; never print, copy or commit the API key. No configuration exists in this framework checkout.
- Keep work and artifacts here; do not change the sibling Soc project or its running studies. Preserve the user's modified `paper/worktrace-draft/FRAMEWORK_REVIEW.md`.

## Completed observations

1. Frozen the pre-existing 30-task all-attempt model confirmation panel and 30-task harness panel in `analysis_plan.json` before extracting the new work-unit metrics. Discovery has 631 tasks per model; 11 old development tasks are separate. The semantic-success panel overlaps the attempt panel on two tasks, leaving 28 exclusive rows under the disjoint split labels.
2. Extracted **2,100 archived runs, 61,769 native calls, 110,354 candidate components and 54,350 stored responses** from Luna, Gemini and the declared Terra extension. All raw shards are local. Terra's pinned 21.6 MB shard is verified in `terra_input.json`.
3. Primary frozen-panel means: Gemini 54.83 calls / 60.07 candidates / 50,718.6 output tokens; Luna 17.10 / 50.10 / 4,496.7. Paired-bootstrap ratios: 3.207 native calls [2.821,3.590], 1.199 candidates [1.039,1.366], 11.279 reported output tokens [9.618,13.047]. Nine of 30 task-level orderings reverse between calls and candidates; nine reverse between candidates and output tokens.
4. Terra extension: native-call ratio to Luna 1.164 [1.069,1.261], candidate ratio 1.055 [0.953,1.194], output ratio 1.219 [1.112,1.333]. Eight of 30 call/candidate orderings reverse. This is a declared extension on the same tasks, not an independent task sample.
5. Equal-split role expenditure is not identified by recorded usage. For exploration output shares, the primary mean Gemini-minus-Luna association bounds span approximately −0.052 to +0.461; an equal split gives +0.236. These are allocation bounds, not confidence intervals or causal token costs. Full-run bounds that retain unlocalized residuals are in `full_run_share_bounds.json`.
6. All three token fields reconcile on 1,843/2,100 runs: Luna 696/700, Gemini 529/700, Terra 618/700. Missing residuals are not assigned to actions.
7. The cross-harness secondary arithmetic uses the existing 6,000-run Qwen table. On the frozen 30 tasks, OpenHands-minus-mini has 6.7 extra calls, including 5.67 extra edit calls. SWE-agent-minus-mini has 12.43 extra calls, including 4.1 extra edit calls. This decomposition does not establish causal harness overhead; tokens are unavailable.
8. Executable validation includes **all five Flipt tasks** in the frozen attempt panel. Base, Luna, Gemini and reference were checked on each task. Reference patches pass 5/5; agent patches pass 3/10. Seven of the 20 snapshots have a source-build failure; five have test failures. Baselines fail on all five tasks. These are selected-check outcomes in pinned Go containers, not full benchmark certification.
9. Four leave-one-source-file-out interventions on passing agent patches: three make the selected checks fail; one detects no loss (`internal/cmd/auth.go` in the readonly-config case). The intervention unit is an entire file's submitted changes, not an individual action. Causal action utility remains null.
10. Repository software tests passed 161 before the latest four scoped-quality tests were added; rerun before finalizing. Source compiler failures are distinguished from dependency, disk, timeout and unknown infrastructure failures.

## Current work

Soc API `/models` is reachable and exposes the two aliases and named Qwen models. First tiny chat preflight returned `glm-5.3-flash` for `x-test-1`; the second probe may still need polling (exec session 18256). Credentials remain host-only. The new live experiment must be **matched snapshot continuations**, not falsely described as continuation of the original Luna/Gemini policy or hidden original reasoning.

Proposed fixed diagnostic pilot: three archived candidate snapshots, two Soc aliases, fresh public check / valid warm-cache observation / bypass, two replicates. Independent hidden evaluator patches remain outside agent containers. Public diagnostic checks use only existing repository tests. Keep compiler/image identity, private build caches, tool time, model usage, API errors and cache-fill overhead explicit. A small pilot cannot establish population non-inferiority or universal redundancy.

The same user owns a sibling Soc verification project with a working OpenAI-compatible client and mini-SWE-agent adapter. Read-only code can inform the new adapter, but its source paths and running experiments must not be mutated. API requests are experimental subjects, not research delegation to assistant subagents.

## Artifacts and execution

- `scripts/research_loop/extract.py`: syntax-checked decomposition; no recorded command execution. Uses the existing `scripts/precision_validation/prepare.py` parser.
- `analyze.py`, `demand_harness.py`, `robustness.py`: paired bootstrap, work-unit and cost sensitivities, compiler-diagnostic classification.
- `executable_panel.py`: pinned source preparation and offline checking. Two pinned compiler images: Go 1.20.14 and Go 1.24.0. Raw copies under `raw/research_executable/` are ignored.
- `patch_ablation.py`: four executed file interventions and their scoped outcomes.
- Main Python: `/Users/samuelthen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`; use `PYTHONPATH=/private/tmp/worktrace-analysis-deps:worktrace` for pandas/pyarrow. Add `/private/tmp/worktrace-audit-deps` for pytest.
- Figure runtime: `/opt/homebrew/bin/python3`, `PYTHONPATH=/private/tmp/worktrace-paper-mpl:/private/tmp/worktrace-paper-deps`, `MPLCONFIGDIR=/private/tmp/worktrace-cost-band-mpl`.
- The sibling Soc `.venv/bin/python` has mini-SWE-agent installed. Prevent writes to that project by overriding startup paths and keeping all logs/configuration here.
- Disk last checked: about 4.8 GB free. Maintain a 3 GB reserve; do not download the 20 GB cross-harness raw corpus. Go module/cache directories are dedicated under this project's ignored `raw/`.
- Latest committed/pushed audit is `70dccf8`; all current research-loop changes remain uncommitted. Commit only relevant scripts, compact derived evidence, reports and figures. Preserve unrelated manuscript files.

## Closest prior work read

- TRACE, ACL 2026: `https://aclanthology.org/2026.acl-long.773/` — decomposition/progression-pattern motivation. Graphs and utility language alone cannot establish novelty.
- AgentLens: `https://arxiv.org/html/2605.12925v1` — task-specific multi-solution PTA references and process scoring already exist. Our candidate distinction concerns auditable state/cost attribution; it remains a claim to substantiate.
- Graphectory: `https://arxiv.org/html/2512.02393v2` — composite disaggregation, process graphs and online interventions already exist.
- Cost-inefficient coding agents: `https://arxiv.org/html/2609.30725v3`, especially Appendix A.1.2 — already attributes generated content and later input/cache charges to behavior, using tokenization. We must compare to this concrete attribution approach, not claim first action-cost analysis.
- CER: `https://arxiv.org/html/2609.31995` — contextual terminal-reward prediction exists; do not rename it as a novel universal action reward.

The scientific recommendation remains to claim only measurements and mechanisms supported by these experiments. Do not force over-exploration or over-verification findings, treat repeated decoding as new tasks, or turn a scoped no-loss check into proof of no contribution.

## Resumed DeepSeek loop: completed

The user explicitly selected DeepSeek and later asked to resume. Both Soc aliases passed tiny preflight; `x-test-2` returned `deepseek-v4.1-flash-1017`. No credential was printed or copied into the repository.

The first live pilot ended with 18 scheduled rows, 48 model requests, six disk-reserve blocks and one extra grading gap. All artifacts are preserved. It is a protocol-development run and cannot support balanced arm comparisons. The repaired v2 uses the same snapshots, eight calls, visible candidate diffs and private APFS copy-on-write cache snapshots. Its frozen plan predates its model episodes.

**V2 completed all 18 episodes with 139 requests, no unknown-usage attempts, and usable independent grading.** Every arm retains identical production patches per snapshot. Exact-context success is 4/6 in each arm; fixture-complete success is 6/6 in each arm. Four episodes submit; fourteen reach the call budget. Mean fresh public-check overhead is 2.152 s versus 0.057 s for warm reuse. These observations establish local execution avoidance, not population non-inferiority or a reliable model-token-saving effect.

The readonly task revealed fixture dependence: its source-only candidate passes when the missing reference testdata fixture is supplied equally to candidates. This secondary context must not replace the exact one without disclosure. `grade_audit.py` independently regrades initial and saved v1 candidates with both contexts. All production-code reference contents remain outside agent inputs.

`WORKTRACE_MEASUREMENT_PAPER_20261028.md` now provides the full working paper. It leads with two supported measurement findings, keeps semantic precision and causal utility distinct, and records the nearest prior methods. A direct end-to-end comparison to the strongest behavior-cost attribution method and broader executable repositories remain scientific work; no unsupported ACL-readiness claim is made.

The resumed loop adds an actual available-command-token baseline using `o200k_base`. It reverses the mean edit-share ranking (+4.8 points under equal splitting, −19.0 under command-token weighting) while preserving response totals. Available reasoning text is absent for the 396 Luna and 387 Terra confirmation responses but present for all 1,641 Gemini responses. Retokenized text does not replace reported usage, and this adaptation does not reproduce full downstream context/cache charging. The final software suite passes 207 tests. `finalize.py` verifies claim arithmetic and exports compact usage/provenance without credentials or raw conversations.
