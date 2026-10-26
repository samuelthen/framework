"""Prefix-only check suppression prototype, not a deployed agent intervention.

Runtime adapters must supply a complete relevant-content snapshot and an assessed
property using information available before the request. Inferred version IDs
and retrospective contribution labels are not accepted state evidence.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    property_id: str | None
    state_digest: str | None
    scope_complete: bool = False
    deterministic: bool = False
    dedicated_verification: bool = True
    state_basis: str = 'unknown'


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str


class PropertyStatePolicy:
    """Suppress the kth consecutive repeat candidate; continue the agent.

    k=1 suppresses the first repeat of established deterministic support. k=2
    permits one completed repeat first. New properties/relevant edits reset the
    streak; unknown scope/state/result always permits further work.
    """
    def __init__(self,k):
        if k not in (1,2,3):raise ValueError('calibration candidates are k=1,2,3')
        self.k=k;self.support={};self.completed_repeats=0

    def eligible(self,r):
        return (r.dedicated_verification and r.property_id is not None and r.state_digest is not None
                and r.scope_complete and r.deterministic and r.state_basis=='content_snapshot')

    def decide(self,r):
        if not self.eligible(r):
            self.completed_repeats=0
            return Decision(True,'unknown_or_ineligible_allow')
        if self.support.get(r.property_id)!=r.state_digest:
            self.completed_repeats=0
            return Decision(True,'new_property_or_relevant_state_allow')
        if self.completed_repeats+1>=self.k:
            return Decision(False,'repeated_support_threshold_suppress_check_continue_agent')
        return Decision(True,'repeat_below_threshold')

    def observe(self,r,*,completed,passed,property_assessed):
        # Called only after actual execution, never after a suppressed request.
        if not self.eligible(r) or not completed or not passed or not property_assessed:
            self.support.pop(r.property_id,None)
            self.completed_repeats=0
            return
        repeated=self.support.get(r.property_id)==r.state_digest
        self.completed_repeats=self.completed_repeats+1 if repeated else 0
        self.support[r.property_id]=r.state_digest

    def on_edit(self,affected_properties=None):
        if affected_properties==[]:return  # explicitly irrelevant edit
        self.completed_repeats=0
        if affected_properties is None:self.support.clear()
        else:
            for p in affected_properties:self.support.pop(p,None)


class CheckCountCap:
    """Simple comparator, same dedicated-check eligibility; no property knowledge."""
    def __init__(self,max_checks):
        if max_checks<1:raise ValueError('positive cap required')
        self.max_checks=max_checks;self.attempts=0

    def decide(self,r):
        return Decision(not r.dedicated_verification or self.attempts<self.max_checks,'simple_check_count_cap')

    def observe(self,r,**_):
        self.attempts+=int(r.dedicated_verification)


class Unrestricted:
    def decide(self,r):return Decision(True,'unrestricted')
    def observe(self,r,**_):pass
