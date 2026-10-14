"""Product telemetry: no synthetic lift, inferred token usage or invented costs."""
import json
from datetime import datetime
from .db import connect,uid,now

VALID_EVENTS={'brief_submitted','plan_ready','plan_confirmed','draft_ready','human_edit_started',
              'human_edit_completed','approval_requested','approval_decided','dry_run_completed',
              'workflow_failed','reviewer_feedback_saved'}


def event(name,campaign_id=None,meta=None):
    if name not in VALID_EVENTS:raise ValueError('Unsupported telemetry event')
    clean={k:v for k,v in (meta or {}).items() if k in {'status','mode','revision','source','time_ms'}}
    with connect(immediate=True) as c:
        c.execute('INSERT INTO product_events VALUES(?,?,?,?,?)',
                  (uid('evt'),campaign_id,name,now(),json.dumps(clean)))


def product_event_summary(campaign_id):
    with connect() as c:
        rows=c.execute('SELECT event,occurred_at,meta_json FROM product_events WHERE campaign_id=? ORDER BY occurred_at,id',(campaign_id,)).fetchall()
    data=[dict(r) for r in rows]
    times={r['event']:datetime.fromisoformat(r['occurred_at']) for r in data}
    # No active human time unless instrumentation actually observes editing sessions.
    with connect() as c:
        ps=c.execute('SELECT created_at FROM plan_sessions WHERE campaign_id=? LIMIT 1',(campaign_id,)).fetchone()
        legacy=c.execute('SELECT created_at FROM campaigns WHERE id=?',(campaign_id,)).fetchone()
    start=datetime.fromisoformat(ps['created_at'] if ps else legacy['created_at']) if legacy else None
    approved=next((datetime.fromisoformat(r['occurred_at']) for r in data if r['event']=='approval_decided' and json.loads(r['meta_json']).get('status')=='APPROVED'),None)
    full=(approved-start).total_seconds() if approved and start else None
    t=(times['approval_decided']-times['draft_ready']).total_seconds() if 'approval_decided' in times and 'draft_ready' in times else None
    return {'events':data,'draft_to_approval_seconds':round(t,3) if t is not None else None,
            'time_to_approved_campaign_seconds':round(full,3) if full is not None else None,
            'human_active_minutes':None,'agent_cost_usd':None,
            'note':'Times measure elapsed wall-clock between database events (no human active-time or actual model-cost measurement).'}
