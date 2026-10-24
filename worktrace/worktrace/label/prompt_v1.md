You are labeling one tool operation from a coding agent's trajectory.

Issue:
{issue}

Current operation {op_id} (turn {turn}):
Agent message: {message}
Command: {command}
Exit code: {exit_code}
Result:
{result}

Candidate A, latest operation on the same object ({object}):
{cand_a}

Candidate B, latest operation of the same kind with the same output:
{cand_b}

Facts: kinds={kinds}; mixed={mixed}; write={write}
{facts_vs}
(Long results are shortened to their first and last {n} characters, marked [...].)

Return JSON only:
{{"purpose": "<few words from what the agent stated, or 'unspecified'>",
 "role": "initial | explore | verify | revise | branch_out | final",
 "relation": "unmatched | revisits | reproduces | uncertain",
 "matched_op": "<op id of candidate A or B, or null>",
 "contribution": "distinct | non_distinct | uncertain",
 "evidence_refs": ["<op_id>", ...],
 "evidence": "<one sentence>"}}

Rules:
- Judge contribution for every operation, including unmatched ones.
- relation "reproduces": the result is equivalent to the chosen candidate, and nothing
  relevant changed in between. For reads and searches, "this object written since" must
  be no; for runs, "any code written since" must be no.
- relation "revisits": same target as the candidate, but a new purpose or a different result.
- relation "unmatched": neither candidate is a true earlier match (or there are none).
- relation "uncertain": the facts needed for the comparison are unknown or the log is incomplete.
- distinct: the result established something new for the issue, such as new code,
  a new error, a ruled-out cause, or a check on changed code. Cite the current operation.
- non_distinct: the result only repeats what the matched operation established.
  Cite BOTH the current and the matched operation. Not seeing anything new is not enough.
- uncertain contribution: the trace does not let you tell.
- For a mixed operation, judge the whole operation: if any part is distinct, it is distinct.
- Do not invent a purpose the agent did not state. Facts are hints, not proof.
- Do not use the final patch to judge this operation.
