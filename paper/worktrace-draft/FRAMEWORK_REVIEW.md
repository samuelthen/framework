# 4 Framework for Analysing Coding Agent Work and Resource Use

*Author review revision, 27 October 2026. This section follows TRACE's four-stage organisation. Component annotation and work graphs exist. Response-ledger allocation and region aggregation are now implemented; empirical per-response usage is not yet recovered locally. Author notes distinguish implementation from validated results.*

We introduce **WorkTrace**, a framework for analysing how coding agents explore repositories, change code, and verify solutions. The framework connects work progression to direct solution contribution and resource expenditure. It asks where agents spend effort, what that work establishes, and whether systems reach accepted solutions through different combinations of action frequency and inference expenditure.

Following [TRACE](https://aclanthology.org/2026.acl-long.773/), WorkTrace proceeds through four stages: **(1) Trajectory Collection**, **(2) Action Decomposition and Label Inference**, **(3) Progression Graph Construction**, and **(4) Work Pattern Induction and Resource Analysis**. TRACE tracks proposed answers within reasoning traces. WorkTrace tracks external actions, which can support a solution without stating a complete answer. Code changes also require us to distinguish evidence about earlier implementations from evidence about the submitted implementation.

## 4.1 Stage 1 Trajectory Collection

For each task, we collect the task description, tool calls, observations, code changes, final submission, and recorded outcome. Each action retains its position, arguments, output, and available execution status. We distinguish the output available to the agent from any longer raw output retained by the dataset. Missing or truncated observations remain marked throughout the analysis.

We distinguish three units: a **model response**, a **native tool operation**, and an assessable **work component**. One response can issue several operations, and one operation can contain several searches, edits, or checks. Component decomposition retains coherent pipelines, quoted programs and control constructs where necessary. Malformed commands remain opaque attempts. Reviewers assess execution separately; a successful parent call does not establish that every conditional branch ran.

Each component links to its generating response. A separate response ledger records input tokens, cached-input tokens, output tokens, reported reasoning details and available monetary cost. We retain responses without tool calls and compare response sums with run totals. Duplicate source response identifiers require reconciliation. Missing usage is null, not zero.

Resource fields remain separate. Cached-input tokens are not added to input totals. Reasoning details are not added to output without checking source accounting. Recorded usage and historical cost do not establish standardized internal compute or tool runtime. Text characters remain text-volume proxies where tokens are unavailable.

For contribution annotation, we construct a task reference from the stated requirements and accepted solution evidence. Requirements describe the behaviour to establish or preserve. They do not prescribe a command sequence or require the reference patch's exact implementation. We separate repair requirements from properties already satisfied in the initial repository. Reference conflicts remain unresolved until reviewed.

## 4.2 Stage 2 Action Decomposition and Label Inference

We describe each component through three fields: **role**, **relation**, and **contribution**. The role identifies exploration, editing, verification, or administration. The relation connects the component to earlier work, including a target revisit, repeated observation, revision, or return to an earlier code state. We do not spread a native call's strongest contribution label across its components.

Contribution concerns the action's support for a correct solution. We assign one of three labels:

- **Direct:** the action establishes solution-bearing information, implements a valid repair requirement, or verifies a defined property of the solution.
- **Non-direct:** the available evidence establishes no direct contribution under the annotation rules, such as an irrelevant search, discarded change, or repeated inspection without an additional supported contribution.
- **Uncertain:** incomplete observations, unclear support, or unresolved code state prevent a reliable judgment.

Every direct label cites the contributed content, the supported requirement, and the relevant observation or code change. For exploration, the annotation links information to a subsequent implementation or check. For editing, it identifies the supported change and whether that change survives. For verification, it identifies the checked property and the code state to which the result applies. Visiting a file later edited is insufficient evidence by itself.

These labels measure retrospective solution contribution. A search that only rules out an irrelevant file receives no direct credit. An absence that establishes a missing requirement can contribute when it supports a specific surviving repair. Uncertain support remains separate from established non-contribution.

The earlier WorkTrace labels, `distinct` and `non_distinct`, describe novelty relative to retrieved evidence. We retain them as separate fields. New information and direct solution contribution answer different questions and require separate annotations.

**Response usage allocation.** Let \(T_{t,m}\) be response \(t\)'s recorded usage for resource field \(m\), and let \(C_t\) contain all components it generated. Our baseline allocates equal shares:

\[
\widehat{T}_{c,m}=\frac{T_{t,m}}{|C_t|},\qquad c\in C_t.
\]

These are **allocated response tokens**, not measured component-specific reasoning. A singleton receives its full response-associated usage. Generated but failed or unexecuted commands retain their inference allocation, since producing them still consumes model output. This denominator differs from performed-component precision.

Responses without tool components enter an unassigned response bucket. This preserves planning, interpretation and final-answer expenditure rather than silently charging it to the nearest action. Later episode links can connect result interpretation to earlier checks, but cannot charge a response twice. Mixed-purpose inference remains explicit.

## 4.3 Stage 3 Progression Graph Construction

WorkTrace organises each trajectory through two linked views. Shared action identifiers connect both views to the recorded evidence.

**Target view.** Nodes represent addressed files or other work targets. Directed edges follow the action sequence. Consecutive actions on the same target form self-loops; later returns connect previously visited targets. The contribution annotation distinguishes returns that support the solution from those that repeat or abandon work.

**Version view.** Nodes represent observed or inferred code states. Edits connect successive states, and checks attach to the state on which they run. A restore connects to an earlier state only when the available evidence supports that identity. Unknown side effects or incomplete observations preserve uncertainty rather than establish state equality.

**Component-versus-version view.** Our primary trajectory figure places component order on the horizontal axis and distinct code versions on the vertical axis. Each point represents a work component. Exploration and verification remain on their execution-version row; an edit occupies the transition between its before and after states. Vertical position identifies a state, not its quality. A supported restore returns to the earlier state's row while preserving the later occurrence in time. Point shape denotes action type: circle for exploration, diamond for editing, square for verification and triangle for administration. One solid color denotes contribution: green for direct, orange for non-direct and gray for uncertain. Borders carry no additional meaning. Linked attributes retain response ID, input tokens, cached-input tokens, output tokens and attribution method. An aligned table can display these attributes without crowding the graph. This view complements the underlying target and version graphs.

**Evaluated version outcomes.** We propose annotating recoverable versions with independent final-benchmark outcomes. A PASS requires evaluation of that exact complete snapshot under the same task protocol and environment; a local passing check or the final run outcome cannot establish an intermediate PASS. Preserve fail, timeout, infrastructure error, untested and unreconstructable states separately. Highlight every confirmed passing version and mark the earliest evaluated passing occurrence. Only complete coverage of preceding states establishes that it was the earliest passing state. The checkpoint evaluation adapter and empirical outcome overlays remain pending. The evaluated-outcome illustration is synthetic; archived trajectory examples use inferred native-call states with untested intermediate outcomes.

We propose adding **support links** from actions to requirements and **invalidation links** from changes to earlier evidence. For example, a passing test supports the implementation it tested. A later change to the relevant code can invalidate that support. These links would distinguish progress that survives into the submission from progress later undone. The contribution pilot records support judgments; automated construction of these links remains future work.

**Resource regions.** A graph region groups work by role, version context, target, or contribution. Each component has one accounting region within a partition; mixed or unknown targets remain explicit. Region expenditure is

\[
\widehat{T}_{G,m}=\sum_{c\in G}\widehat{T}_{c,m}.
\]

If a region contains every component from a response, that response's regional total is recorded response-associated usage. A partial-response share remains allocated. Summaries distinguish these amounts and show missing-usage coverage. Average allocated usage per component is reported only when usage is complete. Alternative graph views partition the same ledger; their totals must not be added together.

Model generation context is kept separate from component execution state. An edit can carry expenditure on a transition, but its post-edit version is not automatically the state the model saw while generating it. Unknown context remains an unknown region.

For visualization, component shape denotes role and solid color denotes contribution. Keep sizes fixed in the primary sequence figure so shape remains legible; report input/cache/output in a linked table. An optional resource view can scale glyph area or edge width by one explicitly named field. A region label shows component count, total usage, average allocation and attribution method. Unknown usage remains explicitly missing rather than becoming a zero-size symbol. Version-level PASS/FAIL/UNTESTED labels remain separate from action contribution colors. A version node can show a role breakdown of its associated work.

## 4.4 Stage 4 Work Pattern Induction and Resource Analysis

We compare models under a shared harness and harnesses under a fixed model. Comparisons pair runs by task and report recorded success and effort alongside contribution. Graphs locate where work occurs; contribution labels establish what that work supports.

**Successful-run precision.** Let \(A_\tau\) be the included work components in trajectory \(\tau\), and let \(D_\tau\) contain those with direct contribution labels. Known unexecuted candidates are excluded here. For a successful run,

\[
P_\tau = \frac{|D_\tau|}{|A_\tau|},
\qquad
P_{\mathrm{success}} = \mathbb{E}[P_\tau\mid Y_\tau=1].
\]

Here, \(Y_\tau\) is the recorded task outcome. The score measures the share of performed actions that directly supports the accepted solution. It does not compare actions with a predefined trajectory. With \(U_\tau\) uncertain actions, we report label bounds:

\[
P_\tau \in \left[
\frac{|D_\tau|}{|A_\tau|},
\frac{|D_\tau|+|U_\tau|}{|A_\tau|}
\right].
\]

These bounds cover unresolved contribution labels, not systematic annotation errors or differences in call packaging.

We also report precision separately for exploration and verification, averaging per-run scores across complete paired role comparisons. Runs with no role denominator are reported rather than scored zero.

**Resource allocation.** Report total associated/allocated expenditure and average expenditure per component in each region. Input-context processing and output generation remain separate. Compare equal-share allocation with a sensitivity that keeps heterogeneous responses in a mixed bucket. This tests whether conclusions depend on distributing shared inference among purposes.

An optional expenditure-weighted measure supplements component precision. For one complete resource ledger, let \(B_D\), \(B_N\) and \(B_U\) be expenditure allocated to direct, non-direct and uncertain or unassigned work:

\[
P^{(m)}_{\mathrm{expenditure}}\in
\left[\frac{B_D}{B_D+B_N+B_U},
\frac{B_D+B_U}{B_D+B_N+B_U}\right].
\]

This is an allocation-dependent expenditure share. It is undefined for zero totals or incomplete usage and does not estimate safely removable cost.

**Optional reference requirement coverage.** For tasks with an independent correct reference, let \(\mathcal R_i\) contain the repair requirements and \(H_\tau\subseteq\mathcal R_i\) the requirements achieved together in the submitted state. We propose

\[
R_\tau = \frac{|H_\tau|}{|\mathcal R_i|},
\qquad
R_{\mathrm{failure}} = \mathbb{E}[R_\tau\mid Y_\tau=0].
\]

This is a reference-conditional recall measure. Reading about a requirement does not achieve it. A failed run can receive partial credit when its final implementation satisfies some verified requirements. Runs without an adequate reference remain unscored. Preservation requirements and peak progress are reported separately.

**Pattern analysis.** We examine work frequency, contribution and expenditure by role, version and trajectory position. A system may perform more checks yet spend less inference on each. Repeated context processing can make individually short responses expensive. Inspect repeated checking of the same property on unchanged relevant state and its allocated expenditure, separating new coverage, confidence gains, environment failures and uncertainty. A fixed self-loop intervention is evaluated separately with prefix-only information and actual task outcomes. Retrospective contribution alone cannot establish safe suppression.

**Post-pass expenditure.** For replayable trajectories, locate the first independently confirmed passing occurrence and partition subsequent expenditure by role and contribution. The edit creating that state belongs to reaching it; later work can include direct confirmation, additional edits and regressions. Report later edit counts and evaluated pass-to-fail/recovery transitions. A response spanning the boundary retains an allocated split plus a mixed-boundary sensitivity. No-tool responses remain ordered ledger entries; unresolved boundary association remains unknown. These are retrospective spending measures, not prospective stopping guarantees or automatically removable cost. Code-version correctness and contribution to the final accepted implementation remain distinct judgments.

---

## Author review notes

1. **Implementation:** response-ledger extraction, equal-share allocation, mixed-response sensitivity, expenditure bounds, regional totals and graph-overlay data export now exist. The existing graph viewer has not yet been wired to the overlay.
2. **Data:** empirical per-response usage is not verified locally. Existing component labels and historical results are unchanged; they gain no token values until source responses are recovered and reconciled. Missing usage remains null.
3. **Annotation:** two blinded same-family model-coded component passes exist. Human accuracy, disputed requirements and complete role certainty remain unresolved. No new model ranking is claimed.
4. **Graphs:** the original seven audit probes and additional restore-scope checks pass. State identity remains conservative inference rather than a complete verified snapshot. Automated requirement/invalidation graphs are still incomplete. A component-versus-version illustration now exists, with synthetic PASS highlights; no real intermediate checkpoint outcome has been established locally.
5. **Paper boundary:** normalized property coverage, component-scored harness confirmation and live control remain pending. Failed-run recall is an optional reference-dependent extension. Allocation-dependent expenditure is not safely removable execution cost.

The executable study brief is `CODEX_FRAMEWORK_VALIDATION.md` at the repository root. It specifies response recovery, independent checkpoint evaluation, post-pass accounting, fixed comparison samples, outputs and evidence boundaries.
