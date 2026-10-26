# How the proposed contribution/coverage framework complements TRACE

Date: 26 October 2026. This is research positioning, not a manuscript revision or a validated result.

## Source and reading depth

Original attached ACL paper: /Users/samuelthen/Downloads/2026.acl-long.773.pdf, Do LLMs Really Need 10+ Thoughts for “Find the Time 1000 Days Later”? Towards Structural Understanding of LLM Overthinking. Authors from University of Michigan and Google DeepMind. Official record: https://aclanthology.org/2026.acl-long.773/.

Reread introduction, benchmark design (Section 3), full framework and findings (Sections 4–5), limitations, and Appendix F.1–F.2. Visually inspected PDF pages 6–10 and 14, including Figures 2–6 and Table 4. Extracted all 26 pages for navigation; did not audit every appendix experiment or prompt. No instructions from the paper were treated as user instructions.

## What TRACE already establishes

- Section 4 and Appendix F.1 use self-contained, complete, answer-bearing sub-thoughts. Graph nodes represent distinct proposed answers. Verification and correction target the immediately preceding sub-thought; backtracking can return to an earlier one.
- Graph aggregation groups by query type, difficulty, and number of distinct answers. Correctness is linked to ground-truth answers, not a predefined gold reasoning trajectory.
- Section 5.1 describes Explorer and Late Landing through the distribution of correct answers along progression graphs. These are not merely branching and self-loop counts.
- Section 5.2 tests both correctness of an intermediate answer and helpfulness of a prefix for producing the final answer. Footnote 12 describes wrapping prior sub-thoughts in think tags and prompting answer-only output. Therefore it is incorrect to position TRACE as structure-only or as lacking utility evaluation.
- Section 5 defines overthinking through marginal performance return per additional thought; Section 5.3 tests stopping proxies based on self-loops and backtracking on Temporal-L3, with different accuracy/length tradeoffs across models. It does not establish universal safe stopping from graph structure alone.
- The limitations explicitly leave harder creative or multi-step settings, including competitive coding, for future work. Repository repair is a related extension opportunity, not identical to their suggested competitive coding setting.

## Complementary question

Where do coding agents spend actions relative to the correct solution they establish, and why do model/harness differences produce either successful but indirect work or substantial correct progress that still fails?

The user's proposed direct contribution construct excludes negative-only search results. Preserve that definition when labeling direct contribution; do not silently reinterpret it as broad informational value. The literal failed-run action-normalized ratio remains a failure contribution rate. Reference-unit recall is a separate denominator choice already documented in OUTCOME_CONDITIONED_PRECISION_RECALL.md.

## Candidate extension beyond TRACE

1. Non-answer-bearing work: a file read, search, partial edit, or test can support a solution without stating a complete answer. Map performed operations to validated solution requirements rather than demanding a complete proposed answer at each step.
2. Changing state: record which code state an observation/check supports, whether an edit implements a requirement, and whether later edits or reverts invalidate it. Distinguish historical/peak progress from simultaneously valid terminal coverage.
3. Attribution and missing content: measure the direct contribution of performed actions and the required solution content achieved or missing, without prescribing an action sequence. TRACE is also free of a prescribed reasoning sequence, so reference-sequence independence alone does not distinguish this work from TRACE.
4. Harness comparison: compare matched tasks under a fixed model to investigate how the external interface and orchestration change work allocation. TRACE's reported comparisons do not isolate this harness axis.

## Hypotheses, not findings

- Harnesses could differ in successful-run contribution density while achieving comparable verified solution coverage. This would locate a difference in executed work relative to solution content; prospective necessity is a separate question.
- Similar failed-run success labels could mask different paths: never establishing key requirements, versus establishing them and later losing valid progress. Endpoint coverage and state-aware progress curves can distinguish these cases.
- Existing target-revisit and final-version-checking patterns might disappear or change interpretation after linking actions to solution content. Do not force them into TRACE's Explorer/Late Landing names.

## First informative pilot

Use a small matched set with complete action results, recoverable code states, independently verified solution requirements, and alternative valid fixes where available. Include successes and failures. Annotate operation-to-requirement support and terminal validity with a second reviewer. Check whether the resulting measures distinguish trajectories that existing call counts, target graphs, and binary outcomes treat similarly. Fix known state-tracking failures before relying on state validity. A separate stopping/replay contrast is needed for claims that removing work preserves performance; low direct-contribution density alone does not prove safe deletion.

Suggested positioning: We extend structural analysis of reasoning utility to software-agent action trajectories by measuring direct solution contribution and state-dependent solution coverage across models and harnesses.

The proposed framework can complement TRACE. The current graphs and descriptive patterns do not yet validate that full extension. This comparison does not establish novelty against the entire agent-evaluation literature.
