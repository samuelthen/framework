# WorkTrace: A Framework for Structural Analysis of Coding-Agent Work

Revision proposal — 25 October 2026

## 1. Research objective

WorkTrace will provide a common framework for reconstructing, comparing, and explaining how language-model coding agents organize their work. The study will examine how agents explore repositories, revise implementations, return to earlier targets, and verify their solutions, and how these behaviors differ across models and agent harnesses.

The central research question is:

> What structural differences in coding-agent work explain how systems spend their effort and respond to evidence, beyond what final success, trajectory length, and action counts reveal?

The paper will combine a validated framework, matched comparisons across systems, and an investigation of two principal phenomena emerging from those comparisons. The distinction between repetition and redundancy will support the measurement definitions; it will not be the headline contribution. Redundancy will remain one possible property of work alongside exploration, refinement, recovery, evidence reuse, and verification.

## 2. Proposed contributions

1. **A common representation of coding-agent work.** WorkTrace will connect operations to their targets, observable code states, and supporting evidence, enabling comparison across different model outputs and tool interfaces.
2. **A comparative methodology.** The framework will support task-matched cross-model and cross-harness analyses, with explicit checks that observed differences reflect work organization rather than tool formatting or unequal trajectory length.
3. **An explanatory empirical study.** The study will identify and confirm substantial patterns in exploration, revision, and verification, characterize where they occur, and establish what they reveal about agent behavior and effort allocation.

The framework's usefulness will be demonstrated through the comparative conclusions and diagnoses it enables. A downstream control experiment can strengthen a later claim about efficiency improvements, but a new optimization algorithm is not required for the foundational contribution.

## 3. Framework revision

### 3.1 Normalize operations across harnesses

Retain each native tool call and its original arguments and observation. Add a normalized representation of the work performed: operation kind, affected targets, read or search scope, known writes, possible unknown effects, output completeness, and available execution outcome.

Structured editor calls and shell commands must be comparable when they access the same information. Conversely, two reads of the same file must remain distinguishable when they inspect different regions. Preserve call grouping so that differences in how harnesses bundle operations can be examined rather than mistaken for differences in effort.

### 3.2 Separate facts from interpretation

Keep the existing distinction among:

- **Role:** the operation's function in the current work, such as exploration, revision, or verification.
- **Relation:** how it connects to earlier operations, targets, or states.
- **Contribution:** what new evidence or implementation change it establishes, including uncertainty where the log is insufficient.

Rule-computed facts and semantic judgments will have separate provenance. Labels will cite the relevant operations and permit multiple evidence references. Candidate retrieval will assist annotation without restricting every valid judgment to the two candidates currently retrieved.

The revised representation will retain uncertainty about incomplete outputs, unresolved writes, and inferred states. A state-changing command is not automatically a successful change, and a status listing is not a content snapshot.

### 3.3 Connect the two existing graph views

**The object view** will represent investigation: which files, tests, or other work targets the agent visits; what it learns; and why it returns.

**The version view** will represent implementation: how observable code states evolve, which operations produce revisions or restorations, and which checks attach to each state.

Operation IDs will link the views. This allows a return to a file to be interpreted alongside intervening edits and checks, and allows verification on a version to be interpreted by its target and scope. The revision will first strengthen these existing views rather than introduce a larger graph architecture.

### 3.4 Define comparable structural measurements

Primary measurements will cover investigation breadth, return structure, revision sequences, recovery after failures, verification placement, and verification scope. Report distributions and uncertainty in addition to group averages.

Different commands will not automatically count as different verification coverage. A final version will mean the last observed submitted state, not a proven correct or converged solution. Cost measurements will distinguish recorded tokens, tool calls, elapsed time, and character proxies according to what each dataset actually provides.

## 4. Comparative study

### Cross-model comparison

Use the JetBrains sample to compare models under the same harness on matched tasks. Examine how each allocates effort across exploration, implementation, and verification, and whether differences persist across task strata and repeated runs.

### Cross-harness comparison

Use the Open-SWE sample to compare the same Qwen model under mini-swe-agent, OpenHands, and SWE-agent on matched tasks. Examine how tool interfaces and interaction protocols organize investigation, revision, and verification.

These are two complementary comparison panels. Their different task populations do not support a general model-by-harness interaction claim. A later small crossed experiment can test whether the principal patterns transfer to additional model–harness combinations.

### Demonstrating framework usefulness

Compare WorkTrace's conclusions with those supported by final success, total effort, action-type frequencies, simple action sequences, and state-only summaries. The study should establish which structural distinctions change a diagnosis or explain an otherwise unresolved system difference.

For each principal finding, present the aggregate pattern, its distribution across tasks, representative trajectories, counterexamples, and the result of removing the relevant semantic or state information. Match or adjust for task and inspect length and operation-granularity effects. Use task-level uncertainty estimates. Associations with success or cost will be distinguished from causal explanations.

## 5. Two candidate phenomena

These candidates are motivated by the current exploratory results. Their names, direction, and prominence will depend on the revised analysis. Final claims will be tested on tasks not used to select the patterns.

### A. Verification allocation changes as implementation stabilizes

Some models may interleave revisions and diagnostic checks, while others concentrate checks on a stable implementation. The study will distinguish checks that diagnose a failure, validate a relevant edit, cover an additional property, or repeat established evidence.

The explanatory question is whether systems differ in the function and coverage of verification, rather than simply in how often they run commands. Test task dependence, run length, version count, and unequal opportunity for checks on intermediate versus terminal versions. A stronger claim about convergence or marginal benefit would require executable correctness evidence at checkpoints.

### B. Harnesses shape investigation through fragmentation and context reuse

Different harnesses may organize the same model's work into sustained investigation or repeated returns to previously visited targets. The study will determine whether those returns inspect new content, resume an incomplete investigation, reconstruct previously available context, or recover from an unsuccessful approach.

First separate tool-representation effects from residual behavioral differences. Then examine how return structure relates to subsequent edits, evidence acquisition, and effort. An observed return pattern alone will not be interpreted as memory loss. If normalization explains the apparent harness gap, that is a result about interface-induced measurement differences rather than evidence of a reasoning mechanism.

## 6. Validation procedures adapted from RedundancyBench

Adapt and cite [RedundancyBench](https://arxiv.org/pdf/2605.29893v2) for its annotation-guide development, evidence-linked records, independent human judgments followed by adjudication, validation of automated annotation against human references, and separation of localization, retrieval, and classification tasks. These procedures will support WorkTrace's software-work analysis rather than replace its ontology with a generic redundancy taxonomy.

Use a small calibration set to clarify definitions, then freeze the guide before independent evaluation. Sample across models, harnesses, operation types, candidate availability, and difficult state transitions. Target approximately 120–200 operations for the initial human pilot if context-review time permits. Retain original judgments, disagreement, and uncertainty before adjudication.

Evaluate three error sources separately: incorrect facts, missed supporting evidence, and incorrect semantic judgments. Then measure how those errors affect the aggregate structural findings. Keep random and enriched challenge samples separate, preserve runs with no redundancy, and report annotation coverage as well as accuracy. Existing LLM agreement is supporting evidence of stability; it does not substitute for the human reference.

## 7. Optional interactive extension

A small multi-turn sample can test whether the framework handles changing user intent and corrective feedback. Preserve user messages, requirements available at each stage, and the connection between feedback and subsequent work.

Use matched SWE-TaskFlow conditions first if suitable trajectories are available. A reactive benchmark can provide a later boundary test. The extension should examine adaptation, reconstruction, and correction across user turns, rather than serve as a search for a higher redundancy rate. It is secondary to completing the two core comparison panels this week.

## 8. One-week foundation

| Day | Work | Deliverable |
|---|---|---|
| 1 | Restore pilot inputs, pin dependencies, and repair state/write/version failures | Reproducible inputs and passing regression checks |
| 2 | Finalize normalized work units, linked graph fields, and annotation guide | Versioned framework specification and calibration examples |
| 3–4 | Conduct independent human pilot and evaluate facts, retrieval, and labels | Reference annotations, agreement, uncertainty, and component errors |
| 5 | Rebuild matched cross-model and cross-harness comparisons | Comparable structural summaries and baseline comparisons |
| 6 | Investigate candidate phenomena, alternatives, and sensitivity | Initial figures, counterexamples, and uncertainty estimates |
| 7 | Consolidate the argument and define fresh-task confirmation | Research brief, reproducible pilot, and remaining experiment plan |

The end-of-week objective is a trustworthy framework and an initial comparative account of coding-agent work. The human pilot depends on annotator availability, and the analysis depends on restoring the original trace inputs. Missing validation will remain explicit. Existing results will be preserved separately from revised outputs.

## 9. Proposed paper structure

1. Motivation and research questions.
2. WorkTrace: normalized operations, facts, labels, linked graph views, and measurements.
3. Data, comparison design, and validation.
4. Cross-model and cross-harness structural comparisons.
5. Principal phenomena, alternative explanations, and diagnostic value.
6. Optional utility or interactive extension, followed by limitations.

The intended paper claim is that WorkTrace enables a validated structural understanding of how coding agents organize work, and that this understanding reveals consequential differences across systems that ordinary aggregate evaluations miss. The revision must supply evidence for that claim; the proposal does not assume the eventual findings.
