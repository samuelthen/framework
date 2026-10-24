You are labeling one code change made by a coding agent. This is an add-on label: it does not replace any
other label of this operation.

Issue:
{issue}

Earlier code changes in this run (oldest first):
{history}

Latest test or script run on the code before this change:
{last_run}

Current operation {op_id} (turn {turn}), a code change:
Agent message: {message}
Command: {command}
Exit code: {exit_code}
Result:
{result}

Facts: files written by this change={files}; files written by earlier changes={prev_files}; latest run failed={last_failed}
Support-candidate files written by this change={support} (rule hint: a new file that is deleted later in the run or
absent from the final submission diff)
(Long texts are shortened to their first and last {n} characters, marked [...].)

Return JSON only:
{{"version_move": "correct | branch_out | support | sidetrack | uncertain",
 "evidence_refs": ["<op_id>", ...],
 "evidence": "<one sentence>"}}

Definitions:
- correct: continues the current approach to the issue. It fixes, completes or refines an earlier change, or
  responds to a failure or observation, in the same place and with the same strategy.
- branch_out: tries a different approach to the issue: a different strategy, a different place in the code
  for the fix, or undoing and redoing the fix another way.
- support: serves the fix but is not part of it, such as a reproduction or debug script, temporary prints, or
  a scratch test file.
- sidetrack: irrelevant to the issue, such as formatting unrelated code or editing unrelated files.
- uncertain: the log does not let you tell.

Rules:
- The first change of the run has no earlier approach: if it is part of the fix, label it correct.
- The support-candidate hint is a rule fact, not a label: decide from what the change does.
- Judge from what the agent stated and what the command does. Facts are hints, not proof.
- Cite the current operation, and the earlier change it continues or departs from if there is one.
- Apart from the support-candidate hint, do not use the final patch or whether the run was resolved.
