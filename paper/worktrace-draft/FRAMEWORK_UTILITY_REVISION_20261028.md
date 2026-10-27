# WorkTrace: context-specific progress, evidence and expenditure

Revision after seven local audit rounds. This specification supplements the existing framework review without replacing its user edits. The local findings and scope are recorded in [RESULTS.md](../../results/utility_audit_20261028/RESULTS.md).

**Subsequent empirical revision:** the [measurement paper](WORKTRACE_MEASUREMENT_PAPER_20261028.md) now tests work units and response accounting on 2,100 archived runs, five executable tasks, four source-file interventions and a complete 18-episode DeepSeek pilot. Two changes are required: use candidate-component counts alongside native calls, and report feasible attribution bounds whenever a response spans components. The pilot establishes a local warm-cache time saving; it does not validate a universal action reward or safe check removal. The existing three contribution labels remain descriptive and unchanged.

## Research question

Coding agents can reach the same outcome with different amounts of exploration, editing and verification. WorkTrace asks **which work changes the implementation, which work establishes useful evidence, and how much each kind of work costs**. It uses these measurements to locate candidate inefficiencies for model and harness comparisons. A later intervention tests whether a candidate can be removed or replaced safely.

The local pilot establishes measurement corrections and scoped examples. It does not yet establish a causal redundancy rate or a general model ranking.

## 1. Extract work components and response expenditure

Preserve three units: model response, native tool call and work component. Split a compound call into components while retaining their shared call and response IDs. Record execution status separately from the requested command. A requested check, a completed check and an observed result are distinct events.

For each component, record:

| Field | Required content |
|---|---|
| Identity | Run, response, native call, component order and source location |
| Action type | Exploration, edit, verification or administration |
| Target | File, symbol, requirement, test or delivered artifact; unknown if unresolved |
| Execution | Performed, not executed or unresolved; timeout and infrastructure status separately |
| Observation | Raw result, agent-visible result, truncation, completion and provenance |
| Contribution annotation | Direct, Indirect or Uncertain; retain the original fine label and reason |
| State | Relevant pre/post file hashes, checker dependencies and environment; distinguish inferred from reconstructed states |
| Evaluation context | Property ID, requirement source, checker version and preservation conditions |
| Result | Observed property outcome and its scope; build failure and unknown remain distinct from semantic failure |
| Evidence novelty | New valid assertion, valid re-observation, recovery of unavailable evidence, or unresolved |
| Resource | Response input, cached input, output, reported reasoning, USD and tool time, with source and missingness |
| Utility status | Descriptive only, scoped executable measurement, or controlled continuation estimate |

Use shape for action type and one color for the three contribution labels. Contribution color does not encode causal utility. Broad **Indirect** includes diagnostic and operational work as well as work without demonstrated final-solution contribution; it is not a zero-reward label.

Measure usage once per response. For a response with several components, retain shared usage; an optional equal split is an explicitly labeled estimate. Show the shared response as a graph band. Separate input, cached input and output. Keep no-tool responses and unlocalized run/response residuals visible. Reconcile every metric before reporting a percentage of total run expenditure.

## 2. Construct progression graphs at observed state boundaries

Use component order on the horizontal axis. Use implementation state on the vertical axis. A formatter, restore or compound edit can create an intermediate state; add a boundary only when the trace or reconstruction supports it. A write to a disposable probe is not automatically a new project implementation. Use a separate target view for movement among files or symbols.

Keep these relations distinct:

- **Initial/revisit:** relation to a previously inspected target.
- **Exact repeat:** equality of the recorded command string.
- **State match:** equality of the dependencies relevant to a named checker.
- **Evidence reuse eligibility:** a complete prior result remains valid under the current checker and context.

An exact repeat is a recurrence cue. An inferred version match is weaker than a dependency match. Neither is proof of redundancy.

Attach each evaluation marker to its exact snapshot and checker. Label a local result “passes selected check X.” Mark “passes final evaluation” only after running that independent final evaluator. Preserve later edits so that a trajectory can show quality gain, loss or unchanged scoped behavior.

**Observed example:** task 03 passes the selected patched `TestErrorUnaryInterceptor` after the literal edit and before formatting. Formatting changes an import order. The original agent's two test requests timed out, so the offline pass cannot be inserted into its knowledge state.

## 3. Measure implementation progress and evidence separately

Define a context \(c\) before scoring: the requirement set, preservation conditions, checker suite, environment, budget and outcome priority. Store conflicting requirement and evaluator results separately. Do not resolve a conflict by silently choosing whichever makes a model look better.

### Implementation progress

Let \(q_{c,k}(s)\) be the observed outcome of property \(k\) on snapshot \(s\). Its values include pass, fail, build failure and unknown. For an edit, compare the same independent checker before and after:

\[
g_{i,k}(c)=q_{c,k}(s_{i+1})-q_{c,k}(s_i).
\]

Use numeric subtraction only for comparable, observed binary outcomes. Otherwise report the categorical transition. Keep requirement gains and preservation losses as a vector. A test does not exhaust correctness. A formatter can improve a declared formatting property while leaving tested behavior unchanged.

**Observed example:** task 04's submitted patch passes all five authored requirement diagnostics but fails the selected patched configured-case test. The reference passes the selected tests but fails the absent-flag diagnostic. This is a context conflict, not a calibrated 5/5 versus 4/5 utility ranking.

### Evidence gain

Represent a piece of evidence as a scoped assertion: property, relevant state, checker, outcome, observation availability and provenance. Let \(K_i(c)\) contain valid assertions already available to the agent. Record which assertions the new observation adds to \(K_i(c)\).

For verification, a complete failure can add useful diagnostic evidence. A repeat after an implementation change checks a new state. A repeat after a timeout can recover missing evidence. A complete repeat of the same valid assertion has no *new assertion* under this representation, but its decision value remains unresolved—for example, it could test a suspected flaky result.

For exploration, record the actual finding and its scope. A failed search can establish that a symbol is absent under a particular query and snapshot. A file read can reveal an incompatible implementation. This receives evidence credit when it establishes a relevant fact; it does not receive direct final-patch credit merely because it happened. Reading a file does not prove that the file is useless for every correct solution.

Link a fact to a named repair decision when the trace supports that link. A later action matching the fact is a retrospective association; it does not establish that the observation caused the decision. Fact counts alone can reward irrelevant browsing, so do not use them as a universal reward.

The pilot has not validated an automatic exploration-utility checker. Record this field as unresolved where relevance or inference cannot be checked.

## 4. Test avoidability and decision utility

Progress, evidence novelty and directness are measurable proxies with different meanings. **Causal utility asks what changes when an action is executed, replaced by valid evidence reuse, or bypassed.**

At an eligible checkpoint, compare continuations from the same prefix under a fixed budget:

- Fresh execution: run the action and return its observation.
- Valid reuse: return the corresponding cached observation with a reuse marker and provenance.
- Bypass, when relevant: omit the action and resume under an explicit policy.

The reuse and bypass arms answer different questions. Preserving evidence while avoiding execution is not the same as removing evidence from the agent.

Let \(J_c\) combine independently measured final quality, expenditure and time under declared context weights. The utility of fresh execution relative to replacement \(b\) is:

\[
U_i(c;b)=\mathbb{E}[J_c(\text{continue after fresh }a_i)]-
         \mathbb{E}[J_c(\text{continue after }b)].
\]

Report the quality and cost differences separately before an optional scalar. State the weights, normalization and uncertainty if a scalar is used. Account for inspection, hashing, cache lookup, checker execution, model generation and later context costs. Replicate stochastic continuations; one continuation cannot establish a reliable general utility estimate.

No continuation experiment was run in this pilot. All causal utility values remain unresolved. A deterministic local checker can validate a property without establishing downstream decision utility.

## 5. Require scoped validity and net benefit for evidence reuse

An evidence record is reusable only if the checker, relevant dependencies, environment, working directory and property context match; the previous observation is complete; and the checker is suitable for deterministic, side-effect-free reuse. Hashing a declared dependency set does not prove that the set is complete. Preserve failed checks as failures. Do not treat timeouts, truncation or infrastructure errors as complete test certificates.

Compute the local execution benefit as:

\[
S_{\mathrm{tool}}=T_{\mathrm{fresh}}-
(T_{\mathrm{dependency\ validation}}+T_{\mathrm{lookup}}+T_{\mathrm{return}}).
\]

This measures tool time only. It becomes an end-to-end benefit only after measuring the continuation and all relevant expenditure.

**Observed examples:** the exact patch-artifact checker is cheaper to rerun than to hash and reuse. A scoped Go test with explicit `-count=1` is more expensive to rerun in the local experiment. Go build caching remains enabled. These results do not certify any original trajectory cache hit or establish an advantage over Go's existing test-result cache.

This is application-level evidence memoization. It does not reuse an LLM's neural KV state.

## 6. Report candidate inefficiencies and validate patterns

Report three levels of claim:

| Level | Valid claim | Required evidence |
|---|---|---|
| Descriptive | Repeated attention, low directness, costly verification region, missing evidence | Trace, annotation uncertainty and reconciled expenditure |
| Scoped executable | No tested behavior gain, new diagnostic fact, unchanged check with measured local reuse benefit | Reconstructed states, declared independent checker, scoped validity and measured overhead |
| Controlled | Execution or evidence can be replaced with lower cost while preserving quality under context \(c\) | Paired continuations, independent outcomes and uncertainty |

Use the first two levels to select candidates for the third. A fixed loop threshold is a candidate policy to evaluate; it is not a definition of over-verification. Low directness or many inspected files alone cannot establish over-exploration.

For successful-run precision, retain the descriptive Direct/performed-action ratio and its uncertainty bounds. Cost-weighted directness remains an allocation-dependent expenditure share. A failed-run recall requires independently validated required solution units; without them, do not report recall.

Compare models on matched tasks with task-level uncertainty and outcome stratification. Compare harnesses only when the data contain distinct harness conditions. Difficulty analysis requires an external task-demand measure or an explicit operational definition; do not use a model's own cost as both difficulty and the effect being explained.

The next experiment should test a small set of eligible fresh-versus-reuse continuations before expanding sample size. Continue if the property scope is defensible and the experiment can distinguish reduced execution cost from changed agent behavior. Revise the checker or context if validity conflicts dominate. The present pilot supplies such a conflict and therefore strengthens the protocol before a larger comparison.
