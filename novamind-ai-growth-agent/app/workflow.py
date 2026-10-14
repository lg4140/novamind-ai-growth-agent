"""Unified V3 workflow: the actual Plan changes the draft and the stored campaign state."""
import hashlib
import json
from .schemas import CampaignBrief, CampaignContent, CampaignPlan
from .contacts import load_contacts,audience_fingerprint,segment_counts
from .agent import plan as build_plan
from .content import demo_content,llm_content,store_json
from .review import review_content
from .dispatch import execute_dry_run
from .telemetry import event, product_event_summary
from .db import (init_db,create_campaign,save_revision,latest_version,campaign,get_plan,
                 get_version,approve,list_campaigns,read_metrics,audits,read_tool_trace,connect)

def create_draft(goal,topic,mode='demo',planner='demo',audience=None,primary_kpi='qualified_demo_signups',brand_voice=None):
    init_db()
    contacts=load_contacts()
    brief=CampaignBrief(goal=goal,topic=topic,primary_kpi=primary_kpi,
             audience=audience if audience is not None else ['ops_lead','creative_director','freelancer'],
             brand_voice=brand_voice or 'practical, precise, evidence-aware')
    p,run,source=build_plan(brief,contacts,planner)
    content=demo_content(brief,p) if mode=='demo' else llm_content(brief,p) if mode=='llm' else None
    if content is None:raise ValueError('mode must be demo or llm')
    review=review_content(content,p)
    cid,pid,vid=create_campaign(brief,p,source,content,'SYNTHETIC_DEMO' if mode=='demo' else 'OPENAI_LLM',review,
                               audience_fingerprint(contacts,brief.audience))
    # Trace linkage: planning is stored, and output is used; no invented agent autonomy in demo.
    with connect(immediate=True) as c:
        c.execute('UPDATE agent_runs SET campaign_id=? WHERE id=?',(cid,run))
    event('draft_ready',cid,{'mode':mode})
    try:
        path=store_json(cid,vid,content,mode)
    except OSError:
        path=None
    return {'campaign_id':cid,'plan_id':pid,'version_id':vid,'planner_source':source,
            'agent_run_id':run,'status':'REVIEW','review':review.model_dump(),
            'audience':brief.audience,'counts':segment_counts(contacts),'content_path':str(path) if path else None,
            'export_status':'EXPORTED' if path else 'RETRY_REQUIRED'}

def revise_draft(cid,goal=None,audience=None,primary_kpi=None,mode='demo',planner='demo'):
    init_db()
    old=campaign(cid)
    existing=CampaignBrief.model_validate_json(old['brief_json'])
    new=existing.model_copy(update={'goal':goal or existing.goal,
                          'audience':audience if audience is not None else existing.audience,
                          'primary_kpi':primary_kpi or existing.primary_kpi})
    new=CampaignBrief.model_validate(new.model_dump())
    contacts=load_contacts()
    p,run,source=build_plan(new,contacts,planner)
    content=demo_content(new,p) if mode=='demo' else llm_content(new,p) if mode=='llm' else None
    if content is None:raise ValueError('mode must be demo or llm')
    review=review_content(content,p)
    pid,vid=save_revision(cid,new,p,source,content,'SYNTHETIC_DEMO' if mode=='demo' else 'OPENAI_LLM',
                         review,audience_fingerprint(contacts,new.audience))
    with connect(immediate=True) as c:
        c.execute('UPDATE agent_runs SET campaign_id=? WHERE id=?',(cid,run))
    path=store_json(cid,vid,content,mode)
    return {'campaign_id':cid,'plan_id':pid,'new_version_id':vid,'review':review.model_dump(),
            'status':'REVIEW','content_path':str(path)}

def edit_draft(cid,content_dict):
    """Human edit creates a fresh immutable version, invalidating prior approvals."""
    init_db()
    old=campaign(cid)
    brief=CampaignBrief.model_validate_json(old['brief_json'])
    v=latest_version(cid)
    plan=CampaignPlan.model_validate_json(get_plan(v['plan_id'])['plan_json'])
    content=CampaignContent.model_validate(content_dict)
    review=review_content(content,plan)
    pid,vid=save_revision(cid,brief,plan,'HUMAN_EDIT_OF_PLAN',content,'HUMAN_EDIT',review,
                         audience_fingerprint(load_contacts(),brief.audience))
    event('human_edit_completed',cid,{'revision':int(v['revision'])+1})
    path=store_json(cid,vid,content,'human_edit')
    return {'campaign_id':cid,'version_id':vid,'plan_id':pid,'review':review.model_dump(),'content_path':str(path)}

def decide(cid,reviewer_token,decision):
    init_db()
    v=latest_version(cid)
    aid=approve(cid,v['id'],reviewer_token,decision)
    event('approval_decided',cid,{'status':decision})
    return {'campaign_id':cid,'version_id':v['id'],'decision':decision,'approval_id':aid}

def dispatch(cid,approval_id):
    init_db()
    return execute_dry_run(cid,approval_id,load_contacts())

def inspect(cid):
    init_db()
    c=campaign(cid)
    v=latest_version(cid)
    p=get_plan(v['plan_id'])
    return {'campaign':c,'version':v,'plan':p,'metrics':read_metrics(cid),
            'product_telemetry':product_event_summary(cid),
            'audit':audits(cid),'tool_trace':read_tool_trace(cid=cid)}
