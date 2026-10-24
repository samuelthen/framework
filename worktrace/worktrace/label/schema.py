"""Pydantic models for LLM labels (B.4, D.4)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class Label(BaseModel):
    purpose: str = "unspecified"
    role: Literal["initial", "explore", "verify", "revise", "branch_out", "final"]
    relation: Literal["unmatched", "revisits", "reproduces", "uncertain"]
    matched_op: Optional[str] = None
    contribution: Literal["distinct", "non_distinct", "uncertain"]
    evidence_refs: list[str] = []
    evidence: str = ""

    @field_validator("matched_op", mode="before")
    @classmethod
    def _null(cls, v):
        return None if v in ("null", "", "None") else v


def evidence_rule_errors(lab: Label, op_id: str, candidates: set[str]) -> list[str]:
    """B.4: reproduces / non_distinct must cite both the current and the matched op; matched op must be a candidate."""
    errs = []
    if lab.matched_op is not None and lab.matched_op not in candidates:
        errs.append(f"matched_op {lab.matched_op} is not one of the candidates {sorted(candidates)}")
    if lab.relation in ("reproduces", "revisits") and lab.matched_op is None:
        errs.append(f"relation {lab.relation} requires matched_op")
    if lab.relation == "reproduces" or lab.contribution == "non_distinct":
        if lab.matched_op is None:
            errs.append("non_distinct/reproduces requires a matched_op")
        elif not {op_id, lab.matched_op} <= set(lab.evidence_refs):
            errs.append("non_distinct/reproduces must cite both the current and the matched operation in evidence_refs")
    if lab.contribution == "distinct" and op_id not in lab.evidence_refs:
        errs.append("distinct must cite the current operation")
    return errs
