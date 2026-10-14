"""V4 offline contract/security/regression tests. No LLM or HubSpot access."""
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from app.schemas import CampaignBrief,CampaignPlan,CampaignContent
from app.constraints import compile_constraints
from app.stateful import propose,revise_plan,confirm_plan,generate_from_confirmed,session_status,retry_export
from app.orchestrator import next_action
from app.evidence import attest_claim,extract_claims
from app.memory_service import record_feedback,read_lessons
from app.telemetry import product_event_summary
from app.workflow import edit_draft,inspect,decide,dispatch
from app.db import connect
from app.config import settings

GOAL='Increase qualified demo signups among freelancers'
TOPIC='AI workflow automation for small teams'
TOKEN='test-demo-reviewer-token'

def make_brief(**kw):
    return CampaignBrief(goal=GOAL,topic=TOPIC,audience=['freelancer'],**kw).model_dump()

def make_draft():
    s=propose(make_brief())
    confirm_plan(s['session_id'],s['revision'])
    return generate_from_confirmed(s['session_id'])

def test_plan_proposal_is_separate_from_content():
    s=propose(make_brief())
    assert s['content_created'] is False and s['status']=='PROPOSED'
    with connect() as c:assert c.execute('SELECT COUNT(*) FROM campaigns').fetchone()[0]==0
    assert next_action('PROPOSED').action=='WAIT_FOR_PLAN_CONFIRMATION'

def test_confirm_is_required():
    s=propose(make_brief())
    with pytest.raises(PermissionError):generate_from_confirmed(s['session_id'])

def test_plan_edit_revision_then_confirm():
    s=propose(make_brief())
    plan=s['plan'];plan['messaging'][0]['customer_problem']='disorganized approvals and repetitive admin'
    e=revise_plan(s['session_id'],plan,s['revision'])
    assert e['revision']==2
    with pytest.raises(PermissionError):confirm_plan(s['session_id'],1)
    confirm_plan(s['session_id'],2)
    d=generate_from_confirmed(s['session_id'])
    assert 'disorganized approvals' in inspect(d['campaign_id'])['version']['content_json']
    assert session_status(s['session_id'])['status']=='DRAFTED'

def test_cannot_weaken_plan_constraints_or_change_scope():
    s=propose(make_brief(constraints=['Avoid the word demo in any CTA']))
    p=s['plan'];p['constraint_policy']={'block_cta_terms':[],'no_live_send':True}
    with pytest.raises(ValueError):revise_plan(s['session_id'],p,1)
    p=s['plan'];p['target_segments']=['ops_lead']
    with pytest.raises(ValueError):revise_plan(s['session_id'],p,1)

def test_duplicate_message_angles_rejected_by_schema():
    s=propose(make_brief());p=s['plan'];p['messaging'].append(p['messaging'][0])
    with pytest.raises(ValueError,match='exactly one'):CampaignPlan.model_validate(p)

def test_constraints_actually_change_cta():
    s=propose(make_brief(constraints=['Avoid the word demo in any CTA']))
    assert 'demo' not in s['plan']['messaging'][0]['call_to_action'].lower()
    confirm_plan(s['session_id'],1);result=generate_from_confirmed(s['session_id'])
    assert result['review']['checks']['cta_constraints']
    assert 'demo' not in json.loads(inspect(result['campaign_id'])['version']['content_json'])['newsletters']['freelancer']['cta_text'].lower()

def test_unsupported_freeform_constraint_fails_closed():
    with pytest.raises(ValueError,match='Unsupported constraint'):
        CampaignBrief.model_validate(make_brief()|{'constraints':['Optimize my business in secret']})

def test_no_override_approval_required():
    s=propose(make_brief());p=s['plan'];p['approval_required']=False
    with pytest.raises(ValueError):revise_plan(s['session_id'],p,1)

def test_plan_generation_is_at_most_once_even_concurrent():
    s=propose(make_brief());confirm_plan(s['session_id'],1)
    def run(_):
        try:return generate_from_confirmed(s['session_id'])['campaign_id']
        except PermissionError:return None
    with ThreadPoolExecutor(max_workers=5) as pool:result=list(pool.map(run,range(5)))
    assert len([x for x in result if x])==1
    with connect() as c:assert c.execute('SELECT COUNT(*) FROM campaigns').fetchone()[0]==1

def test_confirmed_plan_not_editable():
    s=propose(make_brief());confirm_plan(s['session_id'],1)
    with pytest.raises(ValueError):revise_plan(s['session_id'],s['plan'],1)

def test_long_valid_topic_does_not_break_downstream_schema():
    s=propose(make_brief()|{'topic':'AI '+'workflows '*19})
    confirm_plan(s['session_id'],1)
    result=generate_from_confirmed(s['session_id'])
    assert result['review']['structural_pass']
    assert len(CampaignContent.model_validate_json(inspect(result['campaign_id'])['version']['content_json']).newsletters['freelancer'].subject)<=150

def test_claim_detector_flags_certification_and_endorsement():
    d=make_draft();obj=json.loads(inspect(d['campaign_id'])['version']['content_json'])
    obj['newsletters']['freelancer']['body']+=' We are SOC 2 Type II certified and approved by major regulators.'
    edited=edit_draft(d['campaign_id'],obj)
    assert edited['review']['claim_status']=='NEEDS_EVIDENCE'
    assert not edited['review']['passed']
    with pytest.raises(PermissionError):decide(d['campaign_id'],TOKEN,'APPROVED')

def test_claim_detector_flags_customer_quantity():
    d=make_draft();obj=json.loads(inspect(d['campaign_id'])['version']['content_json'])
    obj['newsletters']['freelancer']['body']+=' Trusted by thousands of agencies.'
    assert extract_claims(CampaignContent.model_validate(obj))

def test_evidence_requires_review_token_and_matching_quote():
    with pytest.raises(PermissionError):attest_claim('We are SOC 2 certified','Source A legal paperwork','bad')
    d=make_draft();obj=json.loads(inspect(d['campaign_id'])['version']['content_json'])
    claim='We are SOC 2 Type II certified'
    obj['newsletters']['freelancer']['body']+=' '+claim+'.'
    ref=attest_claim(claim,'Internal control attestation - NOT independently verified',TOKEN)
    obj['evidence_refs']=[ref]
    changed=edit_draft(d['campaign_id'],obj)
    assert changed['review']['claim_status']=='REVIEWER_ATTESTED'
    assert changed['review']['passed']

def test_nonmatching_evidence_does_not_clear_claim():
    d=make_draft();obj=json.loads(inspect(d['campaign_id'])['version']['content_json'])
    obj['newsletters']['freelancer']['body']+=' We are SOC 2 Type II certified.'
    obj['evidence_refs']=[attest_claim('We are ISO 27001 certified','Internal control attestation document',TOKEN)]
    edited=edit_draft(d['campaign_id'],obj)
    assert not edited['review']['passed']

def test_feedback_redacts_email_and_is_memory_not_fact():
    d=make_draft();v=d['version_id']
    result=record_feedback(d['campaign_id'],v,'Please avoid claims in customer@example.net and keep messages concise',TOKEN)
    memory=read_lessons()
    assert result['stored_redacted'] and memory[0]['trusted_instruction'] is False
    assert 'customer@example.net' not in memory[0]['feedback']

def test_feedback_requires_reviewer_token():
    d=make_draft()
    with pytest.raises(PermissionError):record_feedback(d['campaign_id'],d['version_id'],'Needs shorter subject','invalid')

def test_policy_orchestrator_explicitly_requires_review():
    assert next_action('CONFIRMED').action=='GENERATE_DRAFT'
    assert next_action('REVIEW',unresolved_claims=2).action=='WAIT_FOR_EVIDENCE'
    assert next_action('REVIEW',quality_passed=False,revision_count=2).action=='REPLAN_OR_ESCALATE'
    assert next_action('APPROVED').action=='EXECUTE_DRY_RUN'
    assert not next_action('APPROVED').safe_to_send_live

def test_pipeline_still_requires_final_approval_after_plan_confirm():
    d=make_draft()
    with pytest.raises(PermissionError):dispatch(d['campaign_id'],'fake')
    a=decide(d['campaign_id'],TOKEN,'APPROVED')
    end=dispatch(d['campaign_id'],a['approval_id'])
    assert end['live_emails_sent']==0
    assert len(end['synthetic_metrics'])==1

def test_product_telemetry_does_not_invent_cost_or_human_time():
    d=make_draft();a=decide(d['campaign_id'],TOKEN,'APPROVED')
    report=product_event_summary(d['campaign_id'])
    assert report['agent_cost_usd'] is None and report['human_active_minutes'] is None
    assert any(x['event']=='draft_ready' for x in report['events'])
    assert any(x['event']=='approval_decided' for x in report['events'])

def test_export_can_be_retried_from_canonical_db():
    d=make_draft();out=retry_export(d['campaign_id'])
    assert out['export_status']=='EXPORTED'
