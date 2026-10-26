# Component contribution review, v2

Scope: the frozen evaluation tasks 03–10, two submitted trajectories each. This
is retrospective assessment, using the issue, requirements, complete agent-visible
trace and submitted patch. Recorded resolved is dataset provenance, not a new
execution check or proof of every stated requirement.

Use one contribution label for every role: `direct`, `non_direct`, `uncertain`.
Roles are `exploration`, `edit`, `verification`, `administration`.

Direct requires specific observed content implementing or supporting a solution
requirement or relevant regression property, with evidence connecting it to the
solution. A relevant filename, successful outcome, passing command, or different
command string is insufficient. A baseline failure can contribute when it
reveals a defect used in the repair. Negative-only unrelated searches get no
direct credit under this retrospective definition.

Non-direct requires supported absence of direct solution contribution under
the guide, with a separate reason, such as `repeated_support`, `unused_context`,
`discarded_edit`, `unrelated_check`, `administration` or `scaffolding`.
Missing evidence is uncertain, not evidence of non-contribution.

## Units and execution

The inventory is a mechanical candidate decomposition. Independent shell work
segments are separate; pipelines, quoted inline programs, heredocs, substitutions
and control constructs stay together. Directory changes provide context.
Malformed shell is one opaque attempted action. This is a pragmatic component
unit, not a packaging-free elementary reasoning unit.

Every component needs its own judgment; never copy a call's strongest label to
all its parts. Shared output must be attributed from visible boundaries/content.
If a component remains internally mixed, inseparable or lacks execution evidence,
mark uncertain with the reason. Commands behind short circuits are not proven
executed by the exit code of the last command. A known unexecuted branch must be
flagged; uncertain execution remains visible and cannot earn certain direct credit.
Submission signals are administrative attempts, retained for comparability with
the legacy denominator; also report a sensitivity excluding submission actions.

## Verification

Use the same contribution labels. Add `reason`, `property_checked`,
`earlier_check_ids`, `relevant_state_changed` (changed/unchanged/uncertain),
`verification_gain`, and specific evidence. Direct verification adds supported
evidence, reveals a defect used in repair, or supplies justified additional
confidence. Non-direct verification adds no supported contribution, such as
repeating established deterministic evidence on unchanged relevant code.
Property/state/result/contribution that cannot be established is uncertain.

Verification precision is direct verification components / all verification
components. Report non-direct and uncertain shares too, per run and pooled.
Never rename these labels to a second low-contribution terminology.

## Requirements and links

Distinguish repair obligations from already-present behavior to preserve. Allow
valid alternative implementations; do not treat the reference patch as an exact
route. Record source conflicts and uncertain scope. An accepted outcome cannot
resolve conflicting requirements. Record support and invalidation links only
where a cited trace establishes them; an empty link list makes no absence claim.

## Blinding and interpretation

Reviewers B and C read anonymous X/Y commands, observations and final patches,
without the other pass's component labels, legacy labels or the model key. C
receives the frozen reviewed requirement sheets. Run lengths and style can weaken
blinding. Within each pass, two Codex workers cover disjoint task groups. There
are now two blinded component judgments per candidate, from the same model
family. The first-pass guide snapshot preserves the earlier metadata before C
was added; contribution rules did not change between these passes. Legacy Claude
annotations cover native calls and supply historical context separately.

Keep each reviewer's original labels and all disagreements. Conservative
cross-review bounds mark disagreements uncertain, without claiming semantic
consensus. Verification-role disputes remain uncertain in the candidate
verification union. A candidate is excluded as unexecuted only when both passes
agree; direct agreement also requires a shared requirement link. Human validation
and actual task-test execution remain separate missing evidence.
