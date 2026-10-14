"""Typed product contracts. Proposal data is not an authority to execute actions."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .constraints import ConstraintPolicy, compile_constraints, assert_plan_constraints

Persona = Literal['ops_lead', 'creative_director', 'freelancer']
PERSONAS = ('ops_lead', 'creative_director', 'freelancer')

class CampaignBrief(BaseModel):
    goal: str = Field(min_length=10, max_length=500)
    topic: str = Field(min_length=3, max_length=200)
    primary_kpi: str = Field(default='qualified_demo_signups', min_length=3, max_length=80)
    audience: list[Persona] = Field(default_factory=lambda: list(PERSONAS))
    constraints: list[str] = Field(default_factory=lambda: ['No live marketing sends'])
    # Any unsupported natural-language constraint is rejected rather than silently ignored.
    brand_voice: str = Field(default='practical, precise, evidence-aware', max_length=200)

    @model_validator(mode='after')
    def validate_constraints(self):
        compile_constraints(self.constraints)
        return self

    @field_validator('audience')
    @classmethod
    def validate_audience(cls, v):
        if not v or len(v) != len(set(v)):
            raise ValueError('Audience must be nonempty and contain unique personas')
        return v

class MessageAngle(BaseModel):
    persona: Persona
    customer_problem: str = Field(min_length=5)
    value_proposition: str = Field(min_length=10)
    call_to_action: str = Field(min_length=5)

class CampaignPlan(BaseModel):
    goal: str
    topic: str
    primary_kpi: str
    target_segments: list[Persona] = Field(min_length=1)
    messaging: list[MessageAngle] = Field(min_length=1)
    steps: list[str] = Field(min_length=3)
    assumptions: list[str]
    evidence_refs: list[str]
    risks: list[str]
    approval_required: bool = True
    constraint_policy: ConstraintPolicy = Field(default_factory=ConstraintPolicy)

    @model_validator(mode='after')
    def align(self):
        if set(self.target_segments) != {m.persona for m in self.messaging}:
            raise ValueError('Messaging must cover selected personas exactly once')
        if len(set(self.target_segments)) != len(self.target_segments):
            raise ValueError('Duplicate personas in plan')
        if len(self.messaging)!=len(self.target_segments):
            raise ValueError('Messaging must contain exactly one angle per selected persona')
        if not self.approval_required:
            raise ValueError('Approval cannot be disabled by plan')
        assert_plan_constraints(self)
        return self

class AgentPlanProposal(BaseModel):
    """LLM-only content; backend binds actual business contract and policy."""
    messaging: list[MessageAngle]
    steps: list[str]
    assumptions: list[str]
    evidence_refs: list[str]
    risks: list[str]

class Newsletter(BaseModel):
    subject: str = Field(min_length=5, max_length=150)
    preview_text: str = Field(min_length=5, max_length=250)
    body: str = Field(min_length=30)
    cta_text: str = Field(min_length=3, max_length=100)

class CampaignContent(BaseModel):
    topic: str
    blog_title: str = Field(min_length=5)
    blog_outline: list[str] = Field(min_length=3, max_length=8)
    blog_draft: str = Field(min_length=150)
    newsletters: dict[Persona, Newsletter]
    evidence_refs: list[str] = Field(default_factory=list)

class LLMNewsletter(BaseModel):
    persona: Persona
    subject: str
    preview_text: str
    body: str
    cta_text: str

class LLMCampaignContent(BaseModel):
    topic: str
    blog_title: str
    blog_outline: list[str]
    blog_draft: str
    newsletters: list[LLMNewsletter]

class ReviewResult(BaseModel):
    passed: bool
    structural_pass: bool
    claim_status: Literal['CLEAR_BY_RULES', 'NEEDS_EVIDENCE', 'REVIEWER_ATTESTED']
    score: int = Field(ge=0, le=100)
    issues: list[str]
    checks: dict[str, bool]
    flagged_claims: list[str]
    note: str = 'Rule screening is not a factual, legal or compliance verification.'
