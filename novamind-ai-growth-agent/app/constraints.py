"""Conservative, typed business-constraint compiler and execution-time checks.

Free-text constraints are NOT silently assumed to be enforceable. Unsupported input
raises and must be reformulated with an implemented rule. Local dry-run policy
is unconditional and cannot be relaxed by an LLM or a user instruction.
"""
import re
from pydantic import BaseModel, Field, field_validator, model_validator

class ConstraintPolicy(BaseModel):
    block_cta_terms: list[str] = Field(default_factory=list)
    no_live_send: bool = True

    @model_validator(mode='after')
    def cannot_enable_live_send(self):
        if not self.no_live_send:
            raise ValueError('Live sending is prohibited by backend policy')
        return self

    @field_validator('block_cta_terms')
    @classmethod
    def clean_terms(cls, v):
        cleaned=[s.strip().lower() for s in v]
        if not all(1<=len(x)<=45 and re.fullmatch(r'[a-z0-9][\w -]*',x) for x in cleaned):
            raise ValueError('CTA blocked terms must be 1-45 simple characters')
        if len(set(cleaned))!=len(cleaned):
            raise ValueError('Duplicate blocked terms')
        return cleaned

SUPPORTED = re.compile(r'^(?:avoid|do not use|don\'t use|exclude)\s+(?:the\s+)?(?:word\s+)?["\']?([\w -]+?)["\']?\s+in\s+(?:any\s+)?(?:the\s+)?cta(?:s)?$', re.I)


def compile_constraints(constraints):
    terms=[]
    for text in constraints:
        cleaned=text.strip().rstrip('.').strip()
        if cleaned.lower() in {'no live marketing sends','no live sends','dry run only'}:
            continue
        match=SUPPORTED.fullmatch(cleaned)
        if match:
            term=match.group(1).strip().strip('"\' ').lower()
            terms.append(term)
        else:
            raise ValueError('Unsupported constraint; explicitly implement or rephrase before planning: '+cleaned[:100])
    return ConstraintPolicy(block_cta_terms=terms)


def cta_violations(cta, policy):
    words=cta.lower()
    failures=[]
    for term in policy.block_cta_terms:
        if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)', words):
            failures.append(f'cta_contains_prohibited_term:{term}')
    return failures


def compliant_cta(candidate, policy):
    if not cta_violations(candidate,policy):return candidate
    alternate='Explore a practical workflow guide'
    if cta_violations(alternate,policy):
        raise ValueError('No implemented CTA fallback satisfies all blocked terms; reviewer must propose valid copy')
    return alternate


def assert_plan_constraints(plan):
    for item in plan.messaging:
        errors=cta_violations(item.call_to_action,plan.constraint_policy)
        if errors:
            raise ValueError('; '.join(errors))
