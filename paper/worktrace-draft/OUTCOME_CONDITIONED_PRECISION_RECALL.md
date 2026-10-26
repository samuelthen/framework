# Outcome-conditioned solution precision and recall

Date: 26 October 2026. Status: proposed definitions, not validated metrics or computed results. The manuscript is unchanged.

## User's clarified intent

This proposal supersedes the earlier interpretation of the user's precision/recall analogy as success versus cost. The user now explicitly conditions the measures on run outcome:

- Precision: among actions in successful trajectories, the share contributing directly to the final correct solution.
- Proposed recall: among actions in unsuccessful trajectories, the share contributing toward a correct solution.
- Diagnostic negative findings receive no direct solution credit by design. This is a retrospective solution-contribution construct, not a judgment of whether every action was reasonable prospectively.

## First distinguish two possible failed-run measures

Let A(tau) be the performed actions. Let D(tau) be the subset with validated direct contribution toward an accepted correct solution. The literal user-defined pair is:

P_success(m) = E[ |D(tau)| / |A(tau)| | Y=1, system=m ]
Q_failure(m) = E[ |D(tau)| / |A(tau)| | Y=0, system=m ]

This exactly preserves the proposed successful/failed split. Both quantities are contribution densities over performed actions. The second is not conventional recall, because its denominator contains performed actions rather than all required positive units. It can still be useful under the name failure contribution rate.

The recommended precision–recall-like version keeps successful-run precision and changes the failed-run denominator:

- Construct independently validated solution units U_i for task i, representing required behaviors, repair components, or solution-bearing evidence under an explicitly accepted solution route.
- Let H(tau) be the distinct units in U_i that the trajectory validly establishes or implements.
- R_failure(m) = E[ |H(tau)| / |U_i| | Y=0, system=m ].

This measures how much correct solution content the agent recovered despite failing. Inserting irrelevant actions should lower precision/density, while leaving the set of already achieved solution units unchanged. An action-normalized failed-run ratio lacks that recall property.

Use unit weights only if fixed independently of the evaluated system and justified. Multiple actions can establish one unit, and one compound call can address several units. Do not use literal command matching against a single gold trajectory. Credit rules must control duplication and call packaging. Negative-only diagnostic branches are excluded from direct credit under the user's chosen construct.

## Ground contribution in a correct target

For successful runs, identify actions that establish or implement solution-bearing content supporting the verified solution. Cite action IDs and the supported unit. Final success does not automatically make every prior operation a contributor.

For failed runs, use an independent correct target: executable acceptance criteria, validated repair obligations, or an adjudicated successful solution route for the same task. Do not attribute contribution merely because an action supports the agent's incorrect final answer.

Tasks can admit different valid repairs. Record which requirements are invariant and which units are conditional on a particular accepted route. Apply the same route-selection and alignment rules across systems. Report reference-conditional coverage rather than claiming the reference enumerates every correct approach.

Do not aggregate incompatible correct fragments across versions into one apparently complete solution. For a terminal-coverage measure, units must remain valid together at the evaluated endpoint. If analyzing peak progress, label it separately from terminal progress. A coverage curve can distinguish never getting close from making and losing progress.

## What the joint analysis could reveal

- Low successful-run precision: successful runs contain substantial direct-solution detours or overhead under the defined reference.
- High failed-run recall: failures reach much of a valid solution but omit or invalidate a smaller component.
- Low failed-run recall: failures establish little of the required solution content.

These are hypotheses about behavior, not established results. High recall does not by itself prove that more budget would fix the run. Low precision does not identify every excluded action as safely removable.

Report success rate and total effort alongside both quantities. Otherwise a system with a few easy successes can look precise while failing almost everything. Outcome-conditioned comparisons also change task composition: stronger systems may succeed on harder tasks and fail only on the hardest. Use shared-task comparisons, task-difficulty strata, and task-level uncertainty estimates. Report both-success, both-failure, and discordant outcome cases separately where informative.

## Role of WorkTrace

The framework can attach operation IDs to solution units, retain code-state validity, distinguish branches retained in the accepted solution from discarded branches, and count omitted or invalidated units. Its target and version views provide provenance. Existing novelty labels are not direct-contribution labels and cannot be silently reused as the proposed ground truth.

The seven state audit failures must be repaired before stronger state-validity claims. Reference construction and direct attribution require independent checks. Current saved final outcomes and compact summaries are insufficient for a complete computation without the new solution-unit reference and necessary observation context.

## Prior-work checks and novelty limits

- [CoTJudger](https://arxiv.org/html/2603.07078), Sections 4.4–4.6, extracts validated Shortest Effective Paths and defines R = (|V| - L_eff)/|V|. A successful-run retained-solution share overlaps conceptually with 1-R. The prior attached ACL version was already read in detail.
- [AgentBoard](https://arxiv.org/html/2401.13178), Section 2.2 and Appendix L.1, measures progress using independently annotated subgoals or task-state matching. It already addresses partial progress that final success misses. Its multi-route limitations are relevant when designing a software solution-unit reference.
- [Quality, Not Just Outcome](https://arxiv.org/html/2610.13152) was also located. Only its abstract, introduction, and section inventory were inspected in this search; its full method and results have not been audited. It is relevant to process quality among successful coding-agent trajectories.

These checks do not establish that the exact combined framework has already been proposed. They also do not support certifying it as novel from the names or the outcome split alone. The candidate contribution is validated, state-aware direct-solution attribution and missing-solution coverage, jointly used to explain matched model/harness differences.

## Additional prior-art search: trajectory precision and recall

Verified on 26 October 2026. This bounded search found a direct precedent for the broad agent-action precision/recall framing, but did not locate the exact successful-run/failed-run conditional pair.

- Google Cloud's [24 January 2025 announcement](https://cloud.google.com/blog/products/ai-machine-learning/introducing-agent-evaluation-in-vertex-ai-gen-ai-evaluation-service/) explicitly introduces trajectory precision as the proportion of predicted actions present in a reference trajectory, and trajectory recall as the proportion of reference actions present in the predicted trajectory. The [official documentation](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/evaluation-agents) gives those denominators. This is strong prior art against claiming the first precision/recall framework for agent actions. It is reference-action matching, rather than demonstrated semantic contribution to a correct software solution; the definitions do not condition precision on task success and recall on task failure.
- Pydantic's [TrajectoryMatch documentation](https://pydantic.dev/docs/ai/evals/evaluators/agentic/#trajectorymatch) compares tool-name sequences. In-order mode uses longest-common-subsequence overlap, with precision = overlap / actual sequence length and recall = overlap / expected sequence length. Any-order mode uses multiset overlap. Extra calls lower precision and missing calls lower recall. Its include_failed option concerns individual calls ending in an error, not conditioning on whole-task failure. No first-release date was verified for this implementation.

Positioning implication: cite existing trajectory precision/recall as a baseline. A possible distinction is how credit is established across different valid commands and code states, plus a controlled outcome-conditioned comparison. The outcome split alone does not establish a substantial methodological contribution. Keep the user's literal failed-run action-normalized contribution rate distinct from reference-unit recall. No empirical validation or novelty guarantee follows from this search.

## First design test

Choose a few tasks with a validated solution reference and both successful and failed runs. Annotate direct contribution and reference-unit coverage independently. Test invariants: an irrelevant insertion should reduce contribution density but not achieved-unit coverage; valid alternative implementations should retain credit; invalidated fragments should not count as terminal achievement. Establish whether annotators can apply these rules before scaling comparisons or rewriting the paper around the metrics.
