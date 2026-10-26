# Evaluation of the proposed agent precision/recall idea

Date: 26 October 2026. Status: research proposal, not a new result or validated metric. No manuscript claims or experiment outputs were changed.

## Interpretation of the idea

The user proposes two dimensions: task completion relative to expenditure, and the fraction of actions that gain useful information. The scientific question is whether systems achieve higher success by converting effort into task progress effectively, or by using more effort with substantial unproductive work.

This can be a substantive comparative question. The precision/recall analogy is incomplete. Standard precision and recall use true positives, false positives, and false negatives over a specified target population. Cost versus solve rate is a success–cost tradeoff, while useful-action share concerns process composition. These are different units and should not be combined into an F-score.

## Recommended formulation

1. **Outcome under budget:** S_m(B) is the solve probability when system m is actually run with a defined budget B. Compare systems on matched tasks and plot a budget–success curve. This avoids an arbitrary fixed ratio that treats a cheap, low-success agent as best for every application.
2. **Productive-work share:** for action costs c_t and independently assessed contribution labels u_t in {0,1}, report sum(c_t u_t)/sum(c_t). This describes where cost went under the annotation criterion. It does not measure value gained per dollar or prove that every productive action was cost-effective. Where per-action costs are unavailable, use explicitly named normalized operation shares. Report unknown contributions and their cost share separately; do not silently classify them as nonproductive.
3. **Attribution of the remaining work:** separate repeated evidence, novel task-irrelevant investigation, execution failure, and uncertain work. An unproductive action is not automatically evidentially redundant. A reasonable failed probe may have low realized gain while remaining justified prospectively.

Useful contribution includes task-relevant negative evidence, relevant code changes, necessary preparation, and justified confidence gains. It is not restricted to positive findings or fact novelty. A visit to a file absent from the final patch can eliminate a plausible cause. Conversely, a new irrelevant fact can be novel without advancing the task.

A literal recall measure would require an independently defined reference set of required behaviors or evidence obligations. The denominator cannot be the set the agent happened to collect. Software tasks permit alternative valid solutions and different justified search paths. Such recall would therefore be reference-conditional, with coverage and reference-construction errors reported. It should not penalize all omissions from a single gold trajectory.

## Why this does not by itself define redundancy

A small productive-work share does not distinguish duplicated evidence from irrelevant new evidence. A high share does not establish that the total budget was justified: all actions may contribute a little while remaining much more expensive than another strategy. Solve rate and action-level contribution must be reported together. Competence, search effort, justified uncertainty reduction, and avoidable repetition are separable.

The strongest paper contribution would be a validated state-aware measure of task progress that explains matched system cost differences and improves diagnosis beyond cost, length, repeats, and existing graph summaries. Naming two existing dimensions precision and recall is not sufficient novelty.

## Existing data and first test

Saved runs support final success versus recorded cost/proxy plots. They do not generally reveal the earliest correct intermediate patch or the result of an adaptive early-stop policy. A completion-cost profile may count successful recorded runs that finished within B, but must not be described as solve probability under an experimentally imposed budget B. Failed runs must remain in the denominator. Restricting evaluation to runs whose observed cost is below B would select on an outcome of the trajectory.

For a feasibility test, inspect a small number of matched tasks with equal final outcomes and large effort differences, where context is complete. Annotate task contribution, negative evidence, repeated evidence, task-irrelevant novelty, and uncertainty. Check whether the proposed attribution explains the effort gap beyond action counts and graph summaries. This selected-case pilot cannot estimate prevalence. Confirm subsequent comparisons on a representative held-out task sample.

Normalize interface granularity and keep mixed-call components traceable. A harness with one compound call should not gain apparent precision merely by packaging several operations together. Recover real per-action costs before claiming monetary attribution.

## Primary sources checked

- [AI Agents That Matter](https://arxiv.org/html/2407.01502v1), especially Sections 2.1–2.3 and the cost/accuracy comparison and Pareto discussion. This establishes that joint cost–success evaluation is existing work, not a novelty claim by itself.
- [scikit-learn precision/recall reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html), for the standard TP/(TP+FP) and TP/(TP+FN) definitions.
- Prior local reading notes on CoTJudger and CAID remain relevant to state-sensitive progress attribution. No fresh full reading of those PDFs was needed for this note.
