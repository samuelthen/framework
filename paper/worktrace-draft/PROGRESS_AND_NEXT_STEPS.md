# Progress and next steps: solution contribution and coverage

Status checked: 26 October 2026. This supersedes the measurement priorities in the older foundation plan; it does not change the manuscript, saved labels, or frozen analysis outputs.

## Current position

WorkTrace is an implemented exploratory framework with large comparison panels, saved analyses, graphs, and a draft. The proposed solution contribution/coverage framework has definitions but no implemented reference construction, independently adjudicated labels, or computed metric results.

Verified today:

- The draft describes 6,300 cross-model runs and 6,000 cross-harness runs. Saved paired analyses and sensitivity tables exist. Current headline patterns are final-version checking and target revisits, not independently established excessive work.
- Existing semantic-label pilots contain 1,432 and 4,018 operation records. They use the previous novelty/reproduction construct and cannot be reused as direct solution contribution ground truth.
- The 200-row human packet has zero populated first-reviewer, second-reviewer, or adjudicated contribution fields.
- All seven checks in audit/reproduce_reliability.py still fail on this checkout. No estimate of real-data error frequency follows from these challenge cases.
- Full original traces are not available for every saved aggregate. Recoverability must be checked before selecting the pilot. Do not treat 80-character command summaries as full observations.

## Scientific gap relative to TRACE

TRACE links structural patterns to intermediate correctness, prefix helpfulness, and a limited stopping experiment. WorkTrace currently has structural patterns and outcome associations. The missing bridge is validated action-to-solution attribution and solution progress over code states. A new graph design or additional large unvalidated label batch will not supply that bridge.

## Measurement specification to freeze

For each trajectory, retain P_tau = contributing actions / performed actions, Q_tau as the same density used for failures, and R_tau = achieved reference requirements / total reference requirements. Compute per-run scores before outcome-conditioned means. Preserve uncertainty and its denominator coverage. Do not call Q conventional recall.

Define solution requirements independently of the evaluated agent outputs, using the issue, executable behavior, and an accepted fix as evidence. Permit different valid implementations. Separate newly achieved repair requirements from already satisfied preservation constraints, or report initial coverage explicitly; otherwise baseline behavior can inflate apparent progress. Reference patch line matching is not the definition.

For every positive contribution label, record action ID, supported requirement ID, concrete contributed content, evidence location, and validity after later edits. Negative-only searches receive no direct contribution credit under the user's definition. Retain uncertain labels when evidence is incomplete. Action granularity, compound calls, repeated support, and final versus peak validity need fixed rules shared by all systems.

Primary coverage uses simultaneously valid terminal requirements. Peak coverage is separate. A read can support diagnosis without implementing a required behavior; distinguish epistemic support from achieved implementation requirements.

## Ordered work

1. Repair state identity, branch changes, write targets, unknown side effects, failed restores, partial restores, and truncated-observation merges. Pass the seven regression checks; add ordinary regression coverage for the fixes and rebuild affected summaries. Passing seven probes alone is not full real-run validation.
2. Recover complete inputs for a small matched pilot: task specification, tool arguments and outputs, initial repository revision, code changes, final patch, and verified outcome. Mark missing fields before annotation; record exclusions.
3. Construct requirements and an annotation guide on development tasks. Use two independent reviewers, keep original judgments, and adjudicate. Freeze guide before held-out annotation. Hide model/harness identity where possible. Retrospective contribution annotation needs the correct solution and full trace; do not reuse the older prefix-only justification protocol for this different construct.
4. Evaluate whether requirements and contribution can be applied consistently on held-out tasks. Report agreement, disagreement types, unknown share, annotation effort, and automated labels against the independent reference. Reference-unit construction disagreements matter as well as action-label disagreements.
5. Implement per-run P/Q/R and state-dependent coverage curves. Check command-equivalent routes, split/merged calls, irrelevant detours, valid alternative repairs, and undone changes. These are diagnostics, not independent population evidence.
6. Compare with binary success, total calls, exact repetition, target revisits, and state-blind contribution attribution. Show specific diagnoses changed by semantic or state information, then aggregate only over the assessable sample.
7. Run a matched comparison. Initially hold model fixed and compare two harnesses, or hold harness fixed and compare two models. Outcome conditioning changes task composition: report both-success, both-failure, and discordant task outcomes, plus success rate and effort. Reserve fresh tasks for confirmation after exploratory phenomena are selected.

## Two candidate phenomena

- Successful systems can achieve comparable solution requirements with different direct contribution density. Determine whether this difference survives command granularity and task matching.
- Failed runs may never establish key requirements, or may establish them and later invalidate them. Compare terminal and peak coverage to identify which pattern occurs and in which system.

These replace neither the saved findings nor their names until measured. Existing final-version checking and target revisit patterns can be used to select questions, but should be related to P/Q/R only after independent annotation.

## One-week foundation

| Day | Deliverable |
| --- | --- |
| 1 | State repairs, passing challenge checks, trace-availability inventory |
| 2 | Three development tasks, accepted requirements, action guide, working scorer |
| 3–4 | Independent annotation and adjudication on task-separated matched runs |
| 5 | Agreement, uncertainty, score diagnostics, baseline and state-blind comparisons |
| 6 | First matched comparison, progress curves, counterexamples, revised hypotheses |
| 7 | Draft revision with actual pilot results and remaining confirmation study |

A target is three development tasks with two runs each, followed by up to twelve held-out tasks with two runs each: at most thirty fully reviewed runs. Feasibility depends on context recovery and independent reviewers. If completion time is insufficient, report a smaller feasibility pilot with its actual coverage; do not replace missing human validation with model self-agreement. Enriched outcome sampling supports method development, not representative population estimates.

The week should establish whether the measurement works. Broader claims need more independent tasks and fresh confirmation. A small checkpoint/continuation experiment would supply a TRACE-like utility test if executable states are recoverable. Claims about safe execution-cost reduction require such interventions; an optimization algorithm is not required for a measurement study.

## Concrete completion gates

- Every evaluated task has an auditable, alternative-aware solution reference.
- Every credited action has evidence and a requirement link; unknowns are visible.
- Independent reviewers can reproduce the construct with documented disagreement.
- Corrected state tracking changes or preserves the reported patterns transparently.
- The measures distinguish meaningful cases that simple baselines miss.
- Model/harness findings survive task matching, granularity checks, and uncertainty reporting.

No precision/recall values, validation passes, or newly confirmed phenomena were produced by this status review.
