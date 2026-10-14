import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor,as_completed
import pytest
from app.workflow import create_draft,revise_draft,edit_draft,decide,dispatch,inspect
from app.schemas import CampaignContent,CampaignBrief
from app.review import review_content
from app.db import connect,latest_version,get_version,read_metrics,read_tool_trace
from app.dispatch import send_live

GOAL='Increase qualified demo sign-ups for freelance agencies'
TOPIC='AI workflow automation for agencies'
TOKEN='test-demo-reviewer-token'

def create(**kw): return create_draft(GOAL,TOPIC,**kw)

def test_integrated_plan_changes_with_goal_and_kpi():
    a=create()
    b=create_draft('Improve engagement and reading among operations leads',TOPIC,
                    audience=['ops_lead'],primary_kpi='email_engagement')
    d1=inspect(a['campaign_id']);d2=inspect(b['campaign_id'])
    assert d1['plan']['plan_json']!=d2['plan']['plan_json']
    assert d1['version']['content_json']!=d2['version']['content_json']
    assert 'Request a guided workflow demo' in d1['version']['content_json']
    assert 'Explore the practical workflow guide' in d2['version']['content_json']
    assert set(json.loads(d2['version']['content_json'])['newsletters'])=={'ops_lead'}

def test_plan_trace_saved_and_used():
    x=create(audience=['freelancer'])
    r=inspect(x['campaign_id']);p=json.loads(r['plan']['plan_json']);copydata=json.loads(r['version']['content_json'])
    assert len(r['tool_trace'])==3
    assert r['version']['plan_id']==x['plan_id']
    assert p['messaging'][0]['call_to_action']==copydata['newsletters']['freelancer']['cta_text']
    assert x['planner_source']=='DETERMINISTIC_PREVIEW'

def test_review_unverified_numeric_outcome_is_blocked():
    x=create();r=inspect(x['campaign_id'])
    p=json.loads(r['plan']['plan_json']);c=CampaignContent.model_validate_json(r['version']['content_json'])
    c.blog_draft+=' We reduced customer operating costs by 91% using this product.'
    from app.schemas import CampaignPlan
    result=review_content(c,CampaignPlan.model_validate(p))
    assert not result.passed and result.claim_status=='NEEDS_EVIDENCE'
    assert result.flagged_claims

def test_invalid_reviewer_token_denied():
    x=create()
    with pytest.raises(PermissionError):decide(x['campaign_id'],'arbitrary-email','APPROVED')

def test_no_token_blank_denied():
    x=create()
    with pytest.raises(PermissionError):decide(x['campaign_id'],'','APPROVED')

def test_unapproved_execution_denied():
    x=create()
    with pytest.raises(PermissionError):dispatch(x['campaign_id'],'fake')

def test_approved_local_execution_only():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED');d=dispatch(x['campaign_id'],a['approval_id'])
    assert d['live_emails_sent']==0 and d['synthetic_recipients_prepared']==6
    with connect() as c:
        assert c.execute('SELECT COUNT(*) FROM deliveries').fetchone()[0]==6
        assert c.execute('SELECT COUNT(*) FROM metrics').fetchone()[0]==3
        assert c.execute('SELECT COUNT(*) FROM execution_runs').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM insights').fetchone()[0]==1
    for m in d['synthetic_metrics']:
        assert m['clicked']<=m['opened']<=m['recipient_count']
        assert m['source_type']=='SYNTHETIC'
        assert m['simulated_deliveries']==m['recipient_count']

def test_repeated_execution_does_not_duplicate_metrics():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED');dispatch(x['campaign_id'],a['approval_id'])
    with pytest.raises(PermissionError):dispatch(x['campaign_id'],a['approval_id'])
    assert len(read_metrics(x['campaign_id']))==3

def test_concurrent_dispatch_only_one_wins():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED')
    def worker(_):
        try:
            return dispatch(x['campaign_id'],a['approval_id'])['execution_id']
        except PermissionError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(worker,range(8)))
    assert len([r for r in results if r])==1
    with connect() as c:
        assert c.execute('SELECT COUNT(*) FROM execution_runs').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM deliveries').fetchone()[0]==6
        assert c.execute('SELECT COUNT(*) FROM metrics').fetchone()[0]==3

def test_reject_then_no_execution():
    x=create();a=decide(x['campaign_id'],TOKEN,'REJECTED')
    with pytest.raises(PermissionError):dispatch(x['campaign_id'],a['approval_id'])

def test_revision_invalidates_prior_approval():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED')
    r=revise_draft(x['campaign_id'],goal='Improve educational newsletter engagement for creative leads',
                   audience=['creative_director'],primary_kpi='email_engagement')
    assert r['new_version_id']!=x['version_id']
    with pytest.raises(PermissionError):dispatch(x['campaign_id'],a['approval_id'])

def test_human_edit_needs_fresh_approval():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED')
    v=inspect(x['campaign_id'])['version'];content=json.loads(v['content_json'])
    content['newsletters']['freelancer']['subject']='Practical starter checklist for one workflow'
    e=edit_draft(x['campaign_id'],content)
    assert e['version_id']!=x['version_id']
    with pytest.raises(PermissionError):dispatch(x['campaign_id'],a['approval_id'])

def test_changed_audience_blocks_execution(monkeypatch):
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED')
    import app.workflow as w
    original=w.load_contacts
    def altered():
        c=original();c[0]['email']='changed.address@example.net';return c
    monkeypatch.setattr(w,'load_contacts',altered)
    with pytest.raises(PermissionError,match='Audience changed'):
        dispatch(x['campaign_id'],a['approval_id'])

def test_tampered_content_hash_denies(monkeypatch):
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED')
    with connect(immediate=True) as c:
        c.execute('UPDATE versions SET content_json=content_json||? WHERE id=?',(' ',x['version_id']))
    with pytest.raises(PermissionError,match='Content integrity'):
        dispatch(x['campaign_id'],a['approval_id'])

def test_invalid_topic_rejected():
    with pytest.raises(ValueError):create_draft('Long enough goal','x')

def test_duplicate_audience_rejected():
    with pytest.raises(ValueError):create(audience=['freelancer','freelancer'])

def test_nonexistent_persona_rejected():
    with pytest.raises(ValueError):create(audience=['unknown'])

def test_reviewer_cannot_approve_unverified_claim():
    x=create();c=json.loads(inspect(x['campaign_id'])['version']['content_json'])
    c['newsletters']['freelancer']['body']+=' We increase team revenue by 82% in one week.'
    rev=edit_draft(x['campaign_id'],c)
    assert rev['review']['passed'] is False
    with pytest.raises(PermissionError,match='Quality'):
        decide(x['campaign_id'],TOKEN,'APPROVED')

def test_live_email_send_unavailable():
    with pytest.raises(NotImplementedError):send_live()
    from app.hubspot_client import sync_contacts,send_marketing_email
    assert sync_contacts([])["crm_writes"]==0
    with pytest.raises(NotImplementedError):sync_contacts([],confirm_live=True)
    with pytest.raises(NotImplementedError):send_marketing_email()

def test_after_completion_edit_denied():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED');dispatch(x['campaign_id'],a['approval_id'])
    c=json.loads(inspect(x['campaign_id'])['version']['content_json'])
    with pytest.raises(ValueError,match='immutable'):edit_draft(x['campaign_id'],c)

def test_metrics_source_is_explicit():
    x=create(audience=['freelancer']);a=decide(x['campaign_id'],TOKEN,'APPROVED');dispatch(x['campaign_id'],a['approval_id'])
    data=read_metrics(x['campaign_id'])
    assert len(data)==1 and data[0]['source_type']=='SYNTHETIC'

def test_campaign_goal_must_be_meaningful():
    with pytest.raises(ValueError):create_draft('short',TOPIC)

def test_blog_meets_target_word_count():
    x=create();v=inspect(x['campaign_id'])['version']
    c=CampaignContent.model_validate_json(v['content_json'])
    assert 400 <= len(c.blog_draft.split()) <= 600

def test_numeric_revenue_claim_in_email_rejected():
    x=create();d=inspect(x['campaign_id']);c=json.loads(d['version']['content_json'])
    c['newsletters']['ops_lead']['subject']='Guaranteed 30% ROI from your workflow'
    r=edit_draft(x['campaign_id'],c)
    assert r['review']['claim_status']=='NEEDS_EVIDENCE'

def test_marketing_guarantee_without_number_flagged():
    x=create();c=json.loads(inspect(x['campaign_id'])['version']['content_json'])
    c['newsletters']['ops_lead']['body']+=' We guarantee increased revenue with zero risk.'
    r=edit_draft(x['campaign_id'],c)
    assert r['review']['flagged_claims']

def test_dropped_goal_makes_quality_fail():
    x=create();c=json.loads(inspect(x['campaign_id'])['version']['content_json'])
    c['blog_draft']=c['blog_draft'].replace(GOAL,'Marketing effort exists')
    r=edit_draft(x['campaign_id'],c)
    assert r['review']['checks']['goal_trace_in_content'] is False

def test_removing_selected_newsletter_fails_review():
    x=create(audience=['freelancer'])
    c=json.loads(inspect(x['campaign_id'])['version']['content_json'])
    c['newsletters']={}
    r=edit_draft(x['campaign_id'],c)
    assert not r['review']['structural_pass']

def test_invalid_email_body_rejected_by_schema():
    x=create();c=json.loads(inspect(x['campaign_id'])['version']['content_json'])
    c['newsletters']['freelancer']['body']='hi'
    with pytest.raises(ValueError):edit_draft(x['campaign_id'],c)

def test_audit_does_not_include_raw_emails_or_review_token():
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED');dispatch(x['campaign_id'],a['approval_id'])
    details=' '.join(x['detail'] for x in inspect(x['campaign_id'])['audit'])
    assert TOKEN not in details
    assert '@' not in details

def test_readonly_tools_do_not_store_contact_addresses():
    x=create();trace=read_tool_trace(cid=x['campaign_id'])
    assert len(trace)==3 and all(t['status']=='OK' for t in trace)
    assert all('@' not in t['result_summary'] for t in trace)

def test_no_execution_if_dry_run_flag_off(monkeypatch,isolated):
    from dataclasses import replace
    import app.dispatch as d
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED')
    monkeypatch.setattr(d,'settings',replace(isolated,dry_run=False))
    with pytest.raises(PermissionError,match='DRY_RUN'):
        dispatch(x['campaign_id'],a['approval_id'])

def test_history_marks_unverified_conversions():
    from app.db import read_history
    x=create();a=decide(x['campaign_id'],TOKEN,'APPROVED');dispatch(x['campaign_id'],a['approval_id'])
    h=read_history()
    assert all(not item['verified_conversion_evidence'] for item in h)
    assert any(item['metric_source']=='SYNTHETIC' for item in h)
