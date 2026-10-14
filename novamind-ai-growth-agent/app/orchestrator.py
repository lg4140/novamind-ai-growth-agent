"""Deterministic product policy controller around an optional planning LLM.

This is NOT an autonomous free-running agent; it yields explicit next actions
based on observed state and limits. The LLM cannot waive approvals.
"""
from pydantic import BaseModel,Field
from typing import Literal

Status=Literal['PROPOSED','CONFIRMED','REVIEW','APPROVED','REJECTED','COMPLETED','FAILED']
Action=Literal['WAIT_FOR_PLAN_CONFIRMATION','GENERATE_DRAFT','WAIT_FOR_EVIDENCE',
               'WAIT_FOR_CONTENT_REVIEW','EXECUTE_DRY_RUN','HALT','REPLAN_OR_ESCALATE']

class Decision(BaseModel):
    action: Action
    explanation: str
    safe_to_send_live: bool = False
    remaining_revision_budget: int = Field(ge=0)


def next_action(status:Status,quality_passed=None,unresolved_claims=0,
                revision_count=0,max_revisions=2):
    remaining=max(0,max_revisions-revision_count)
    if status=='PROPOSED':return Decision(action='WAIT_FOR_PLAN_CONFIRMATION',explanation='Plan is editable; no content or send approved',remaining_revision_budget=remaining)
    if status=='CONFIRMED':return Decision(action='GENERATE_DRAFT',explanation='Plan was confirmed; prepare draft and independent quality checks',remaining_revision_budget=remaining)
    if status=='REVIEW':
        if unresolved_claims:return Decision(action='WAIT_FOR_EVIDENCE',explanation='Claims need supporting reviewer-attested citations or a rewrite',remaining_revision_budget=remaining)
        if quality_passed is False and not remaining:return Decision(action='REPLAN_OR_ESCALATE',explanation='Revision budget exhausted; require human intervention',remaining_revision_budget=0)
        return Decision(action='WAIT_FOR_CONTENT_REVIEW',explanation='Human must review exact content/version even if automated QA passes',remaining_revision_budget=remaining)
    if status=='APPROVED':return Decision(action='EXECUTE_DRY_RUN',explanation='Backend must re-check token-bound approval, version and audience fingerprints',remaining_revision_budget=remaining)
    return Decision(action='HALT',explanation='Terminal or failed state requires human intervention to start new work',remaining_revision_budget=remaining)
