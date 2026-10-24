You are labeling one tool operation from a coding agent's trajectory.

Issue:
{issue}

Earlier operations (most recent last):
{history}

Current operation {op_id} (turn {turn}):
Agent message: {message}
Command: {command}
Exit code: {exit_code}
Result:
{result}
(Long results are shortened, marked [...].)

Return JSON only:
{{"purpose": "<few words from what the agent stated, or 'unspecified'>",
 "role": "initial | explore | verify | revise | branch_out | final",
 "relation": "unmatched | revisits | reproduces | uncertain",
 "matched_op": "<op id of the earlier operation it repeats, or null>",
 "contribution": "distinct | non_distinct | uncertain",
 "evidence_refs": ["<op_id>", ...],
 "evidence": "<one sentence>"}}

Rules:
- relation "reproduces": the result is equivalent to an earlier operation and nothing relevant changed in between.
- relation "revisits": same target as an earlier operation, but a new purpose or a different result.
- relation "unmatched": no earlier operation shown has the same target.
- distinct: the result established something new for the issue. Cite the current operation.
- non_distinct: the result only repeats what an earlier operation established. Cite BOTH operations.
- uncertain: the trace does not let you tell.
