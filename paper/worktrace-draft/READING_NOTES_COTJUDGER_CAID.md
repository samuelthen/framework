# Inspiration from CoTJudger and CAID/PACE

Date: 26 October 2026. These notes propose research changes. They report no new experiment, annotation, or validated WorkTrace finding. These notes are now incorporated into the manuscript's related work, proposed evidence assessment, and one-week pilot.

## Sources and reading depth

1. **Li et al., CoTJudger: A Graph-Driven Framework for Automatic Evaluation of Chain-of-Thought Efficiency and Redundancy in LRMs.** Findings ACL 2026, 41837–41863. [Official record](https://aclanthology.org/2026.findings-acl.2077/). Local source: `/Users/samuelthen/Downloads/2026.findings-acl.2077.pdf`.
   - Read the main method, experiments, findings, and limitations. Read Appendix B and the relevant validation and graph-building prompts. Visually inspected PDF pages 3–4 and 11–12, including Table 3.
2. **Lee and Yu, Valid ≠ Necessary: Diagnosing Latent Inefficiency in Chain-of-Thought.** Findings ACL 2026, 38998–39014. [Official record](https://aclanthology.org/2026.findings-acl.1942/). Local source: `/Users/samuelthen/Downloads/2026.findings-acl.1942.pdf`.
   - Read the method, controlled perturbations, experimental controls, ablations, discussion, and limitations. Read construction and parameter details and Appendix F. Visually inspected PDF pages 5 and 8–9, including Tables 2–4.

## Main recommendation

Test whether connecting operations to state-specific evidence and visible decisions makes cross-model and cross-harness differences easier to explain. Preserve the current target and version graphs. Pilot the additional evidence links before building a large automatic dependency graph.

The uncertainty worth resolving is concrete: does additional checking collect new evidence, or repeat evidence already available? Do target revisits answer new questions, or reconstruct information already obtained? The answer changes how we interpret the observed system differences. A new graph alone is not sufficient evidence of value.

## What to borrow from CoTJudger

### Dependency links rather than sequence links alone

Sections 4.4–4.5 construct logical relations, normalize semantic repetition, and validate candidate paths. WorkTrace currently has target transitions and inferred version transitions. Those are not the same as evidence dependencies.

A useful extension would record:

- Which question an observation addresses.
- Which visible decision or edit the observation supports.
- Which claim a check tests.
- Which relevant change invalidates earlier evidence.

Links must distinguish explicit support in the visible trace from an annotator's inference. Unobservable use remains unknown. Do not claim that these links reveal hidden reasoning or prove causal dependence.

### Do not transfer the shortest-path necessity claim directly

CoTJudger's graph rules permit affirmative verification nodes to be bypassed. GPT-5 then validates candidate paths. The resulting SEP is a retrospective sufficient path within that graph construction. It is not a direct experiment on what an agent could safely omit when uncertain.

For software agents, several observations may jointly support an edit. The useful object may be a supporting subgraph rather than one path. Code, tests, configuration, and environment can change. A negative check can reasonably eliminate an alternative even if it is absent from the final successful path.

Keep separate labels for retrospective solution support and prospective justification given the information available at the time. The paper's own limitations identify interactive tool use and external state as future work.

### Validate components separately

Appendix B reports repeated-pipeline consistency and a masked-answer regeneration test after SEP rewriting. These are useful procedural precedents. They are not an independent human oracle for whether every omitted step was unnecessary. WorkTrace should separately evaluate state identity, evidence matching, support links, and downstream diagnostic value.

## What to borrow from CAID/PACE

### Separate novelty from task relevance

CAID combines local similarity, goal alignment, information density, and contextual change. The useful transfer is the separation of dimensions. WorkTrace's distinct/non-distinct label alone cannot represent novel but task-irrelevant exploration.

For coding agents, score task progress against an open question or code property. Do not treat embedding similarity to the issue text as a reliable oracle. A low-overlap source file may be crucial. A one-token code change may matter despite a very similar embedding.

### Use controlled contrast cases

RIV-GSM8K injects duplication, paraphrase, decomposition, circular reasoning, and irrelevant material. Its role is controlled diagnosis. Human inspection found some generated cases invalid, so injected material still needs checking.

A software counterpart should include both redundant and necessary contrasts:

1. Equivalent deterministic evidence collected with different command wording, on the same relevant state.
2. The same command after a relevant code change.
3. Another check on the same code version that tests a genuinely new property.
4. A new file inspection that resolves a plausible open question.
5. A new but unjustified detour, under an independently stated task criterion.

Do not automatically label a negative search or a file absent from the final patch as unnecessary. Controlled examples test a specific distinction. They do not establish natural prevalence or real agent savings.

### Preserve the distinction between compression and action removal

PACE distinguishes PRUNE, MERGE, and KEEP. Its ablation reports a 5.38-point accuracy reduction for removal based on low semantic progress. The full method merges selected content and reports a 0.91-point reduction on GSM8K, alongside token reduction. These are answer-regeneration results, not proof of identical continuations.

For WorkTrace, compressing a tool observation, reusing earlier evidence, batching inspections, omitting a tool call, and stopping the agent are different interventions. The first may preserve information even when the original action was necessary. Report each outcome separately and include analysis overhead in any cost claim.

### Use simple controls

PACE compares selective processing with random pruning and substitutes PRM scorers within the same pipeline. WorkTrace should likewise compare the full evidence representation against exact repetition, target/version summaries, and a state-blind evidence matcher. A later continuation study should use a comparable cost budget and prevent future patch or final-test leakage.

## Two hypotheses to test, not findings to declare

1. **Verification scope saturation:** checks continue while the set of task-relevant properties checked grows little. Alternatives include justified stochastic repetition, additional environments, and checks of independent properties.
2. **Evidence reacquisition:** a system returns to previously obtained evidence without a relevant state change. Alternatives include new ranges, different questions, missing context, and interface-dependent target normalization.

The first extends the observed final-version checking pattern. The second can explain part of the observed harness revisit gap. Neither should be selected merely to reproduce another paper's terminology.

## First informative experiment within one week

After repairing the state-tracking failures, select a small task-separated set of complete verification and exploration episodes across both comparison sets. About 30 episodes is a reasonable annotation-design pilot, not a powered final study.

Have independent readers mark question/claim, relevant state, evidence added, task relevance, visible decision support, and uncertainty. Compare exact-repeat signals, the current target/version representation, and the proposed evidence links on the same cases. Include the controlled contrast cases above. Keep a separate untouched task sample for later confirmation.

Continue with the new layer if readers can judge it consistently and it changes useful diagnoses beyond simpler summaries. If the context does not support reliable judgments, improve evidence capture or narrow the claimed construct before scaling annotation.

## Current-data constraint

Some natural examples retain commands, observations, and agent text. The full raw trajectory collection is absent. The scale reconciliation writer stores command prefixes of only 80 characters (`worktrace/scripts/v2_reconcile.py`), so exact test selection cannot be reconstructed reliably for every scale check from that table. Use complete examples first and recover raw traces for cases requiring missing scope information.

## Contribution boundary

Both papers already establish that graph structure and step utility are useful subjects of study. “A graph plus a redundancy score” is not a sufficient novelty claim for WorkTrace. A stronger contribution would demonstrate that changing external state and evidence dependencies alter judgments of useful work, and that these distinctions explain matched system differences. This is a proposed direction; novelty and explanatory value remain to be established.

## Current implementation check: 26 October 2026

The current `prompt_v1.md` already defines a newly ruled-out cause as a distinct contribution (lines 40–41). The required change is structured, state-sensitive tracking of negative evidence and its question, not adding a negative-evidence instruction that is already present.

`Label` currently records purpose, role, relation, one matched operation, contribution, and evidence references. It has no separate question ID, result type, scope record, or task-justification field. `fill_prompt` provides the issue, current operation, and two candidates rather than a running record of open questions and established evidence. The validator disallows matches outside those candidates. These are concrete boundaries of the current implementation.

The seven read-only audit probes in `audit/reproduce_reliability.py` were rerun during this check. All seven still fail. State correctness must precede stronger unchanged-state or repeated-evidence claims. No framework code or frozen results were changed in this check.
