"""Conservative deterministic screening. Flag unsubstantiated performance claims.

Not a factual verifier: without approved evidence store, numerical outcome claims block approval.
"""
import re
from .schemas import ReviewResult, CampaignPlan

# Conservative false positives are resolved by editing copy, not bypassing evidence policy.
PERFORMANCE = re.compile(r'\b(roi|return on investment|revenue|sales|cost|costs|profits?|margins?|'
                         r'productivity|efficien\w*|time sav\w*|hours? sav\w*|conversion|churn|'
                         r'growth|lift|increase\w*|reduc\w*|boost\w*)\b', re.I)
QUANT = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|percent\b|percentage points?\b|x\b|times\b)|\b\d+(?:\.\d+)?%')
GUARANTEE = re.compile(r'\b(guarantee(?:d|s)?|proven to|risk.free profit|double your revenue)\b', re.I)

from .evidence import extract_claims, evidence_for_claim
from .constraints import cta_violations

def find_risky_claims(content):
    """Backwards-compatible name for rule-driven claim extraction."""
    return extract_claims(content)

def review_content(content, plan:CampaignPlan):
    issues=[]
    wc=len(content.blog_draft.split())
    checks={
        'blog_400_600_words':400<=wc<=600,
        'exact_selected_audience':set(content.newsletters)==set(plan.target_segments),
        'goal_trace_in_content':plan.goal.lower() in content.blog_draft.lower(),
        'topic_matches_plan':content.topic==plan.topic,
        'subject_and_cta_present':all(len(n.body.split())>=22 and n.cta_text.strip() for n in content.newsletters.values()),
        'cta_plan_alignment':all((m.persona in content.newsletters and content.newsletters[m.persona].cta_text==m.call_to_action) for m in plan.messaging),
        'cta_constraints':all(not cta_violations(n.cta_text,plan.constraint_policy) for n in content.newsletters.values()),
    }
    for k,v in checks.items():
        if not v: issues.append(k+' failed')
    extracted=extract_claims(content)
    unresolved=[claim for claim in extracted if not evidence_for_claim(claim,content.evidence_refs)]
    if unresolved:
        issues.append(f'{len(unresolved)} potentially unsupported claim(s) need exact evidence or rewrite')
    if extracted and not unresolved:
        issues.append('All flagged claims have LOCAL REVIEWER attestations; no independent verification performed')
    score=max(0,100-10*sum(not v for v in checks.values())-25*bool(unresolved))
    structural=all(checks.values())
    status=('NEEDS_EVIDENCE' if unresolved else
            'REVIEWER_ATTESTED' if extracted else 'CLEAR_BY_RULES')
    return ReviewResult(passed=structural and not unresolved and score>=80,
                        structural_pass=structural,claim_status=status,
                        score=score,issues=issues,checks=checks,flagged_claims=unresolved,
                        note='Pattern screening + optional LOCAL reviewer attestation, NOT independent factual/legal certification.')
