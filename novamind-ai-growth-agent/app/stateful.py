"""Checkpointed human-AI collaboration on a proposed plan BEFORE content creation.

Plan acceptance does not authorize sending. Approval of immutable content remains
separate and is always required for local dry-run dispatch.
"""
import hashlib
import json
from .schemas import CampaignBrief, CampaignPlan
from .agent import plan as compile_plan
from .contacts import load_contacts, audience_fingerprint
from .content import demo_content, llm_content, store_json
from .review import review_content
from .db import connect,init_db,now,uid,audit,log_tool


def _row(session):
    with connect() as c:
        r=c.execute('SELECT * FROM plan_sessions WHERE id=?',(session,)).fetchone()
    if r is None:raise KeyError('Unknown plan session')
    return dict(r)


def propose(brief_data,planner='demo'):
    """Create resumable proposed plan without producing/sending content."""
    init_db()
    brief=CampaignBrief.model_validate(brief_data)
    p,agent_run,source=compile_plan(brief,load_contacts(),planner)
    session=uid('psn');now_utc=now()
    with connect(immediate=True) as c:
        c.execute('''INSERT INTO plan_sessions(id,brief_json,plan_json,plan_revision,status,
              planner_source,agent_run_id,campaign_id,created_at,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?)''',
              (session,brief.model_dump_json(),p.model_dump_json(),1,'PROPOSED',source,agent_run,None,now_utc,now_utc))
        c.execute('INSERT INTO plan_revisions VALUES(?,?,?,?,?)',
                  (uid('prv'),session,1,p.model_dump_json(),now_utc))
    return {'session_id':session,'revision':1,'status':'PROPOSED','plan':p.model_dump(),
            'planner_source':source,'agent_run_id':agent_run,'content_created':False}


def revise_plan(session_id,plan_data,expected_revision=None):
    """Optimistic revision: user may edit messaging/steps, not change scope or policy."""
    init_db()
    new=CampaignPlan.model_validate(plan_data)
    with connect(immediate=True) as c:
        current=c.execute('SELECT * FROM plan_sessions WHERE id=?',(session_id,)).fetchone()
        if current is None:raise KeyError('Unknown plan session')
        if current['status']!='PROPOSED':raise ValueError('Plan cannot be edited after confirmation')
        if expected_revision is not None and current['plan_revision']!=expected_revision:
            raise ValueError('Stale plan revision; refresh before editing')
        brief=CampaignBrief.model_validate_json(current['brief_json'])
        if new.goal!=brief.goal or new.topic!=brief.topic or new.primary_kpi!=brief.primary_kpi:
            raise ValueError('Plan cannot override user goal, topic, or KPI')
        if new.target_segments!=brief.audience:
            raise ValueError('Plan audience must equal brief audience')
        from .constraints import compile_constraints
        if new.constraint_policy!=compile_constraints(brief.constraints):
            raise ValueError('Plan cannot weaken or alter compiled user constraints')
        revision=current['plan_revision']+1; t=now()
        c.execute('UPDATE plan_sessions SET plan_json=?,plan_revision=?,updated_at=? WHERE id=?',
                  (new.model_dump_json(),revision,t,session_id))
        c.execute('INSERT INTO plan_revisions VALUES(?,?,?,?,?)',
                  (uid('prv'),session_id,revision,new.model_dump_json(),t))
    return {'session_id':session_id,'revision':revision,'status':'PROPOSED','plan':new.model_dump()}


def confirm_plan(session_id,expected_revision):
    init_db()
    with connect(immediate=True) as c:
        row=c.execute('SELECT status,plan_revision FROM plan_sessions WHERE id=?',(session_id,)).fetchone()
        if row is None:raise KeyError('Unknown session')
        if row['status']!='PROPOSED' or row['plan_revision']!=expected_revision:
            raise PermissionError('Plan changed or already confirmed')
        c.execute("UPDATE plan_sessions SET status='CONFIRMED',updated_at=? WHERE id=?",(now(),session_id))
    return {'session_id':session_id,'revision':expected_revision,'status':'CONFIRMED',
            'note':'Plan confirmation is not a campaign/send approval.'}


def generate_from_confirmed(session_id,mode='demo'):
    init_db()
    session=_row(session_id)
    if session['status']!='CONFIRMED':raise PermissionError('Plan must be confirmed before draft generation')
    brief=CampaignBrief.model_validate_json(session['brief_json'])
    plan=CampaignPlan.model_validate_json(session['plan_json'])
    if mode not in ('demo','llm'):raise ValueError('mode must be demo or llm')
    content=demo_content(brief,plan) if mode=='demo' else llm_content(brief,plan)
    review=review_content(content,plan)
    # Recheck state while holding an exclusive transaction; exactly one generation commits.
    cid,pid,vid=uid('cmp'),uid('plan'),uid('ver');t=now()
    body=content.model_dump_json();sha=hashlib.sha256(body.encode()).hexdigest()
    fp=audience_fingerprint(load_contacts(),brief.audience)
    with connect(immediate=True) as c:
        row=c.execute('SELECT * FROM plan_sessions WHERE id=?',(session_id,)).fetchone()
        if row['status']!='CONFIRMED' or row['plan_revision']!=session['plan_revision']:
            raise PermissionError('Plan no longer in confirmed state')
        c.execute('INSERT INTO campaigns VALUES(?,?,?,?,?)',(cid,brief.model_dump_json(),'REVIEW',t,t))
        c.execute('INSERT INTO plans VALUES(?,?,?,?,?)',(pid,cid,plan.model_dump_json(),row['planner_source'],t))
        c.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (vid,cid,pid,1,sha,fp,body,'SYNTHETIC_DEMO' if mode=='demo' else 'OPENAI_LLM',review.model_dump_json(),t))
        c.execute("UPDATE plan_sessions SET status='DRAFTED',campaign_id=?,updated_at=? WHERE id=?",(cid,t,session_id))
        c.execute('UPDATE agent_runs SET campaign_id=? WHERE id=?',(cid,row['agent_run_id']))
        audit('PLAN_CONFIRMED_DRAFT',f'session={session_id}; plan_rev={row["plan_revision"]}',cid,conn=c)
        c.execute('INSERT INTO product_events VALUES(?,?,?,?,?)',
                  (uid('evt'),cid,'draft_ready',t,json.dumps({'session_id':session_id,'mode':mode})))
    try:
        export=store_json(cid,vid,content,mode)
        path=str(export)
    except OSError:
        # DB is authoritative. A failed export can be retried independently.
        path=None
    return {'session_id':session_id,'campaign_id':cid,'plan_id':pid,'version_id':vid,
            'status':'REVIEW','review':review.model_dump(),'content_path':path,
            'export_status':'EXPORTED' if path else 'RETRY_REQUIRED'}


def session_status(session_id):
    r=_row(session_id)
    return {'session_id':session_id,'revision':r['plan_revision'],'status':r['status'],
            'campaign_id':r['campaign_id'],'brief':json.loads(r['brief_json']),
            'plan':json.loads(r['plan_json'])}


def retry_export(cid):
    from .db import latest_version, campaign
    from .schemas import CampaignContent
    init_db();campaign(cid);v=latest_version(cid)
    mode=v['generation_mode']
    path=store_json(cid,v['id'],CampaignContent.model_validate_json(v['content_json']),mode)
    return {'campaign_id':cid,'path':str(path),'export_status':'EXPORTED'}
