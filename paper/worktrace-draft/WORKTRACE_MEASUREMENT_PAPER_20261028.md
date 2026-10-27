# What Counts as Work? State, Evidence, and Cost in Coding-Agent Trajectories

**Working paper. Empirical results updated on 28 October 2026.** This is a review draft, not a claim of ACL acceptance or a validated universal redundancy score. Figures and machine-readable results are in [`results/research_loop_20261028`](../../results/research_loop_20261028/).

## Abstract

Coding agents can solve the same task through different sequences of exploration, edits, and checks. Comparing their effort requires a common unit of work and a defensible link between actions and expenditure. We study these measurement choices using 2,100 archived trajectories from three model configurations. WorkTrace decomposes native calls into requested work components, links them to observed code states and evidence, and preserves the shared expenditure of each model response. On a frozen 30-task comparison, Gemini makes 3.21 times as many native calls as Luna, but only 1.20 times as many candidate components. Their ordering reverses on nine tasks when the counting unit changes. Reported output tokens differ by 11.28 times. We also construct allocations that preserve every recorded response total but reverse the mean exploration, edit, and verification cost-share rankings. Thus, response usage alone does not identify these rankings. Independent execution on five selected tasks and four source-file interventions shows why state changes, checker scope, and fixture completeness must remain explicit. Finally, an 18-episode DeepSeek pilot tests fresh verification, cached evidence, and bypass from three fixed snapshots. It establishes local execution-time savings under warm reuse, while leaving general action avoidability unresolved. These results support a measurement procedure for explaining agent effort without equating command counts, directness, and causal utility.

## 1 Introduction

Solve rate and total cost describe outcomes and expenditure. They do not show which work produced a repair, which work established evidence, or which extra work could be avoided. A useful process analysis should connect those questions while keeping their evidence requirements separate.

This distinction matters in coding tasks. One model response can request a read, an edit, and a test. Another system can issue those requests in three calls. A test can examine a changed implementation, recover a previously missing result, or repeat an established assertion. A passing implementation can still lack evidence visible to the agent. Each case has a different interpretation, even when the command strings look similar.

TRACE motivates a structural analysis: decompose a trajectory, construct a progression graph, and compare patterns across related tasks. Its graph and utility ideas do not by themselves establish a new contribution for coding agents. Graphectory already analyzes programming-agent processes, including composite actions and online interventions. AgentLens already scores coding processes against references formed from multiple successful trajectories. Recent cost studies also attribute expenditure to retrieval and test re-execution. We therefore ask a narrower question: **which conclusions about agent work remain supported when call packaging, shared response usage, and executable evaluation context are made explicit?**

We investigate three research questions:

1. How does the choice of work unit change model and harness comparisons?
2. Which action- or role-level expenditure claims can be identified from saved usage records?
3. How can executable checks distinguish implementation progress, evidence, and the effect of replacing a check?

Our contribution is a reproducible measurement study and procedure. The candidate novelty lies in demonstrating and handling these measurement failures together. We do not claim the first coding-agent process graph, first action-cost attribution method, or first contextual reward definition. Whether the resulting measurement contribution is sufficient for a venue requires comparison with the closest methods and independent review.

## 2 WorkTrace

### 2.1 Component decomposition

A trajectory contains model responses, native tool calls, and requested work components. We retain all three units. We split independent shell segments while preserving quoted programs, heredoc bodies, pipelines that produce one observation, and opaque control blocks. Directory changes supply context. A syntax-invalid request remains one opaque attempt.

This decomposition produces **candidate components**, not a claim that every branch executed. A successful parent exit code cannot establish execution or result attribution for all segments. The cost of generating an unexecuted request remains in the response ledger. It must not be removed merely because a performed-action precision denominator excludes that request.

For large-scale analysis we use operational command categories: exploration, edit, explicit verification, artifact inspection, administration, opaque execution, and mixed work. These are lexical proxies. They are not validated semantic intent labels. For example, an arbitrary Python script remains opaque unless static evidence identifies a read or write. We do not report an explicit-check count as the total amount of verification done by the agent.

### 2.2 State progression and evidence

The progression graph places components in execution order and attaches work to its observed or inferred implementation state. A target view shows movement among files or other objects. A version view shows implementation changes and checks attached to the version examined. Restores and state equality require supporting evidence; neither a command string nor a graph-node ID proves content identity.

Each component records its role, target, execution status, agent-visible observation, relevant pre/post state, requirement or property, and expenditure source. A separate contribution annotation can remain Direct, Indirect, or Uncertain. Broad Indirect does not imply zero utility. Missing evidence remains uncertain.

We keep four relations separate: target revisit, exact command recurrence, relevant state match, and evidence reuse eligibility. Repeating a test after an edit is not the same event as repeating a test on unchanged dependencies. Repeating after a timeout may recover missing evidence. Returning a cached result preserves evidence; bypass removes it. Those interventions answer different questions.

### 2.3 Response expenditure and partial identification

Let response \(r\) have observed expenditure \(C_r\) and candidate components \(c_{r1},\ldots,c_{rn_r}\). The API reports \(C_r\), but usually does not report a separate amount \(x_{rj}\) for each component. A nonnegative allocation satisfies

\[
x_{rj}\geq 0,\qquad \sum_j x_{rj}=C_r.
\]

Equal allocation, \(x_{rj}=C_r/n_r\), is one accounting convention. It is not a measurement of the reasoning devoted to each component. A singleton response has a clear response association, but even that association does not establish the marginal cost of an action or the purpose of every reasoning token.

For a fixed operational category \(k\), define a lower bound by assigning a response's full expenditure to \(k\) only when all its components have category \(k\). Define the upper bound by allowing that full expenditure whenever at least one component has category \(k\):

\[
L_k=\sum_r C_r\,\mathbf{1}[\text{all components in }r\text{ have category }k],
\]
\[
U_k=\sum_r C_r\,\mathbf{1}[\text{some component in }r\text{ has category }k].
\]

These bounds are attainable under arbitrary within-response allocations: assign mixed-response expenditure to a component outside \(k\) for the minimum and to a component in \(k\) for the maximum. They are conditional on the fixed categories and the chosen accounting interpretation. They do not recover latent semantic intent or causal token cost. Opaque work remains visible instead of being silently assigned a semantic role.

We reconcile stored response sums with recorded run totals for each metric. A positive unlocalized residual can expand a full-run category's upper bound; its lower bound receives no automatic credit. We do not distribute that residual proportionally to observed actions. Missing metrics remain missing. Input, cached input, output, and reported reasoning details stay separate; cached input is not added again to total input.

### 2.4 Executable contribution and utility

An executable context \(c\) specifies a property, checker, environment, dependencies, and preservation requirements. A before/after check can establish a scoped behavior transition. A source-file ablation can establish that a file's submitted changes are necessary for that checker. Neither result measures the utility of an earlier read, an individual edit action, or a diagnostic observation to the original policy.

We therefore retain three quantities rather than forcing one score:

- **Implementation progress:** comparable property outcomes before and after a change.
- **Evidence gain:** the relevant assertion newly established and available to the agent.
- **Replacement effect:** the change in independent quality and resources when execution is replaced by valid reuse or bypass.

Each quantity carries its context and uncertainty. For a fixed continuation policy, an action's utility relative to replacement \(b\) can be defined as

\[
U_i(c;b)=\mathbb{E}[J_c(\text{fresh execution})]-\mathbb{E}[J_c(b)],
\]

where \(J_c\) is declared before evaluation. We report quality and resource differences separately instead of selecting weights that favor a result. Deterministic reuse requires a complete prior observation and matching checker scope, relevant state, and environment. Empirical stability is a check on this assumption, not proof of universal determinism.

## 3 Study setup

### 3.1 Archived trajectories and comparison panels

We use the pinned JetBrains SWE-TaskFlow SWE-bench Pro run-1 shards for Gemini, Luna, and Terra. There are 700 tasks per configuration: **2,100 runs, 61,769 native calls, 110,354 candidate components, and 54,350 stored responses**. Model names identify recorded configurations; provider accounting and generation settings need not be equivalent.

The primary comparison uses a previously frozen random 30-task all-attempt panel. It does not condition on success. Eleven earlier development tasks are kept separate. The disjoint discovery split has 631 tasks. A previously frozen joint-success semantic panel contributes 28 additional exclusive tasks because two overlap the attempt panel. These tasks were held out from the earlier contribution pilot, but some were exposed to older aggregate analyses. We do not call them untouched by all prior work.

Terra was added after observing the two-model accounting results. Its extension was recorded before extracting the new Terra metrics. It uses the same tasks and is a declared replication extension, not an independent task sample or preregistered primary comparison.

We bootstrap matched tasks with 5,000 draws. We distinguish a ratio of task means from a mean of task ratios. We also examine joint-success subsets, leave-one-repository-out summaries, exclusion of administrative candidates, and reference-patch-size strata. Reference patch size is a demand proxy, not a validated human-difficulty scale.

### 3.2 Cross-harness secondary evidence

An existing Open-SWE-Traces table contains 6,000 runs: 2,000 matched tasks under mini-SWE-agent, OpenHands, and SWE-agent with the same recorded Qwen model. We decompose the call-count differences using its saved operation-kind counts. This corpus was previously analyzed. The new arithmetic is secondary evidence, not new semantic confirmation. Token counts are unavailable; we do not convert character counts into tokens.

### 3.3 Executable validation

We retain all five Flipt tasks in the frozen attempt panel. We reconstruct base, Luna, Gemini, and reference snapshots and apply the independent dataset test patch. Fixed selected test names run in pinned Go 1.20 or 1.24 containers. Source is read-only; work copies are disposable; checks run without network. Dependency preparation and failed setup attempts are logged separately.

These executions validate named properties and benchmark compatibility under declared contexts. They are not full original-harness reruns. In particular, updated tests may depend on new field names or fixtures not stated in the natural-language task. A build failure or missing fixture cannot silently become a universal judgment of repair quality.

On passing submissions, we restore each changed Go source file to its base version and rerun the same checker. Four such interventions test the necessity of a submitted file group. They do not isolate individual agent actions.

### 3.4 DeepSeek continuation pilot

We select three contrasting archived candidate snapshots after inspecting offline outcomes. Soc LLM preflight identifies the user-selected alias as `deepseek-v4.1-flash-1017`. Each snapshot receives fresh public verification, a warm cached canonical observation, or bypass, with two decodes per arm. All arms begin with the same source and public build-cache snapshot. Agents see the public task, requirements, and applied candidate diff. They never see independent evaluator patches, hidden fixtures, or grading logs.

The revised pilot permits eight model calls per episode with the same requested low reasoning setting and 3,072-token response cap. The first four-call pilot had six disk-reserve blocks and one ungraded episode; it is retained as failed protocol development and excluded from balanced outcome comparisons. The revised 18 episodes all complete with grading and usage records. A limit-censored continuation is not the same as an agent choosing to finalize.

We report exact test-patch grading and a separate fixture-complete sensitivity, which supplies reference testdata equally to candidates. No reference production code is added. The fixture context is not silently substituted for the original context.

## 4 Results

### 4.1 Fewer calls can conceal similar amounts of requested work

On the frozen 30 tasks, Gemini averages 54.83 native calls and Luna 17.10. Their ratio is **3.21** [2.82, 3.59]. After decomposition, the means are 60.07 and 50.10 candidate components, giving **1.20** [1.04, 1.37]. Nine of 30 task-level orderings reverse between the two units. The same mechanism appears in discovery: a 2.96 call ratio becomes 1.17 for candidates.

This is not equivalence in effort. Gemini still has more candidates on average, and excluding administrative candidates leaves means of 58.10 versus 44.33. More importantly, reported output tokens average 50,718.6 versus 4,496.7, a ratio of **11.28** [9.62, 13.05]. Nine task-level orderings also reverse between candidate counts and output tokens. Neither native calls nor component counts alone measure generation expenditure.

The pattern persists in the 13 jointly successful confirmation tasks: ratios are 3.37 for calls, 1.26 for candidates, and 10.52 for reported output tokens. Leaving out one repository gives call ratios of 3.09–3.32 and candidate ratios of 1.14–1.25. Demand strata show the same broad unit dependence, but their confirmation sample sizes are small, and one task lacks reference-patch-size metadata.

The Terra extension gives a smaller and less certain contrast: 1.16 [1.07, 1.26] as many calls as Luna, 1.06 [0.95, 1.19] as many candidates, and 1.22 [1.11, 1.33] as many reported output tokens. Eight of 30 call/candidate orderings reverse. This supports checking work granularity beyond the initial Gemini comparison; it does not establish that all systems share the same packaging behavior.

In the frozen harness panel, OpenHands averages 6.70 more calls than mini-SWE-agent, of which 5.67 are edit calls. SWE-agent averages 12.43 more calls, of which 4.10 are edits. These differences identify where the recorded call gap occurs. They do not prove that those edits are redundant or that harness choice alone caused the gap.

### 4.2 Per-role expenditure rankings can be underdetermined

Equal splitting assigns Gemini a larger exploration share of stored output usage than Luna by about 23.6 percentage points. However, allocations consistent with recorded response totals permit the mean full-run difference to range from **−5.6 to +46.4 points**. Both model orderings are feasible. The corresponding ranges are **−30.9 to +23.8 points** for edit and **−15.2 to +8.8 points** for explicit verification.

The ambiguity is not limited to extreme allocations. A command-token-weighted baseline uses `o200k_base` to weight available component commands, then allocates each recorded response total proportionally. Under this convention, the mean edit-share difference changes from **+4.8 points with equal allocation to −19.0 points**. Exploration changes to +31.4 points and explicit verification to +5.9. These are two plausible accounting assumptions with different conclusions, not two measurements of true reasoning purpose.

These are identification bounds, not sampling confidence intervals. They expose uncertainty that a bootstrap around one arbitrary allocation cannot remove. Constructive per-response witnesses conserve every observed total and attain the opposite category rankings under the stated allocation rules. The result concerns operational expenditure association; it does not establish either model's true semantic reasoning allocation.

The telemetry audit finds that all three token fields reconcile on **1,843/2,100 runs**: 696/700 Luna, 529/700 Gemini, and 618/700 Terra. The remaining discrepancies are not assigned to actions. They may reflect missing records or another source-accounting difference; their cause is not established. A role's share of stored usage and its share of recorded full-run usage must have different denominators when they differ.

Available-text completeness also differs. In the frozen tasks, Luna has no available reasoning text in 396 stored responses; Gemini has it in all 1,641, and Terra has none in 387. Retokenizing available generated content gives 89,803 tokens for Luna against 134,901 reported output tokens, 1,506,989 against 1,513,235 for Gemini, and 107,991 against 164,300 for Terra. Provider tokenizers and serialization also differ, so the deficits cannot be labeled precisely as missing reasoning tokens. They do show why available-text attribution must not silently replace the reported usage or be treated as equally complete across configurations.

### 4.3 Executable checks distinguish several meanings of contribution

All five reference patches pass their selected checks. Of ten archived agent patches, three pass in the exact local test-patch context. Across the 20 snapshots, seven fail to build against the updated tests and five reach test failures. These results are scoped compatibility observations, not an accuracy estimate for the entire framework or a new population solve rate.

The file interventions give a sharper statement. Removing three changed source-file groups makes a previously passing checker fail. Removing the fourth detects no loss under that checker. We can therefore identify tested necessity for those three file groups while leaving the fourth's broader value unresolved. Final-patch overlap alone would credit all four; a no-loss result alone would wrongly imply that the fourth is useless.

The evaluation context also changes interpretation. In the readonly task, a selected updated test refers to a fixture absent from the candidate checkout. The initial Luna candidate fails in the exact test-patch context but passes when the same reference testdata fixture is supplied. In a separate earlier configuration case, the reference and a written absent-flag requirement disagree. WorkTrace records these conflicts instead of using one opaque pass/fail value as a universal reward.

The recurrence audit supplies another warning. In the 30-task Gemini panel, 48 literal dedicated-check repeat pairs include 42 with an intervening edit or opaque call. Twelve follow truncated observations and nine follow timeout/interruption screens. These counts overlap. They do not certify any repeat as unnecessary. Luna's bundled and implicit checks are not covered by the same dedicated-call screen, so its low count cannot support a verification-efficiency ranking.

### 4.4 The live pilot measures local reuse savings, not general avoidability

The revised DeepSeek study makes **139 API requests** with complete returned usage and no infrastructure gaps across its 18 episodes. Every arm retains the same production patch on each snapshot. Exact-context passes are 4/6 in each arm; fixture-complete passes are 6/6 in each arm. Only four episodes finish by submission; the others hit the continuation limit. There is no observed repair gain or production-code regression under these checkers.

| Arm | Mean initial check time | Mean continuation input tokens | Mean continuation output tokens | Exact / fixture-complete passes |
|---|---:|---:|---:|---:|
| Fresh execution | 2.152 s | 83,712 | 2,258 | 4/6; 6/6 |
| Warm cache | 0.057 s | 73,068 | 1,821 | 4/6; 6/6 |
| Bypass | 0 s | 65,017 | 2,206 | 4/6; 6/6 |

The measured cache path avoids about 2.09 seconds of initial check time on average. This difference includes source hashing and observation lookup, but assumes an eligible warm cache. Cache-fill setup costs remain separate. The fresh check explicitly uses `-count=1`; the result is not a comparison against Go's default test-result cache.

The token means vary across only three selected task snapshots and two stochastic decodes per cell. They are descriptive, not a reliable token-saving effect. The cache marker changes the prompt, and server caching and scheduling can affect reported input reuse. No monetary bill is measured. Identical scoped outcomes in this pilot do not establish a non-inferiority margin, a safe stopping rule, or the causal utility of the original archived policy's actions.

## 5 Discussion

The main result is a change in what can be concluded. Call counts exaggerate one contrast because systems package requests differently. Candidate counts correct that particular comparison but still fail to represent token expenditure. Equal component allocation produces precise-looking category rankings that the usage records do not identify. Executable checks can ground narrower progress statements, yet their result depends on the property and complete evaluation context.

This changes how the framework should be used. Progression graphs should display shared response bands and distinguish measured usage from allocations. They should mark the first snapshot passing a named checker, while preserving what the agent actually observed. Revisit and repeat edges locate candidates for analysis; they do not define redundancy. Utility remains parameterized by a context and replacement policy.

Successful-run directness can remain a descriptive precision measure if its labels are reliable and its uncertainty is reported. It is not a causal redundancy rate. A failed-run recall needs an independently validated set of required solution units. This study does not manufacture that denominator from a failed final answer.

We recommend the paper lead with the work-unit and attribution findings. The executable and live studies test the boundaries of the proposed interpretation. They currently provide less evidence for a broad story about over-exploration or over-verification. Those patterns should be investigated rather than assumed because TRACE observed analogous thought patterns.

## 6 Related work and scope of novelty

[TRACE](https://aclanthology.org/2026.acl-long.773/) provides the structural motivation. [Graphectory](https://arxiv.org/abs/2512.02393) already offers process graphs, composite-action disaggregation, model/harness analyses, and interventions. [AgentLens](https://arxiv.org/abs/2605.12925) uses task-specific multi-solution process references and decomposable scores. These precedents rule out graph construction or phase labels alone as a strong novelty claim.

[Analyzing and Mitigating Cost-Inefficient Behaviors in Coding Agents](https://arxiv.org/abs/2609.30725) already measures behavior-associated expenditure, including generated content and later context charges. We adapt its tokenizer choice in an available-command weighting sensitivity and separately audit available generated text. Our adaptation does not reproduce its full downstream context/cache charging or source-specific prices, which are not established here. We therefore compare attribution assumptions and coverage, and do not claim empirical superiority over its end-to-end method.

[RedundancyBench](https://arxiv.org/abs/2605.29893) studies contribution labeling for agent steps. [CER](https://arxiv.org/abs/2609.31995) studies contextual early terminal-reward prediction. WorkTrace's context-specific measurements do not establish a novel universal reward model. The most defensible candidate contribution is a measurement procedure with constructive uncertainty bounds and empirical consequences for comparisons, supported by executable examples.

## 7 Limitations and research-loop decision

The operational labels are lexical proxies without independent human semantic validation. Candidate decomposition is not invariant to every program transformation and does not prove branch execution. The primary confirmation panel has 30 tasks, although broader discovery supports its work-unit result. Repository, provider, prompting, and accounting differences limit causal model interpretations. The cross-harness corpus lacks tokens and was previously analyzed. Five executable tasks share one repository, and the three live snapshots were chosen after inspecting outcomes. Updated tests can impose interfaces or fixtures beyond a natural-language task. Two decodes per live cell cannot establish general quality preservation. Warm-cache assumptions and omitted production storage/network costs restrict efficiency claims.

The next decision is not to add more labels. It is to determine whether the measurement contribution adds enough beyond the closest process and cost methods. The current results close substantial implementation and explanatory gaps, but they do not justify calling the broad utility framework fully validated or declaring ACL readiness. A focused submission would need a stronger closest-method comparison and validation on additional task environments, or a correspondingly narrower claim. No acceptance probability is assigned.

## Reproducibility and AI use

All selection rules, amendments, hashes, raw-input references, execution logs, API usage, and derived summaries are retained locally. Downloaded shards, credentials, agent prompts/responses, and private grading artifacts stay outside the tracked compact artifact. Scripts can rebuild the derived summaries from the verified inputs. Soc LLM was used as an experimental coding policy; Codex assisted implementation, analysis, and writing. Archived contribution annotations retain their original machine provenance and are not relabeled as human judgments.
