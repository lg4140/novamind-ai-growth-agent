"""Single SQLite transaction covers claim, synthetic deliveries, metrics and completion.

No live email endpoint is reachable from this module. No network side effects.
"""
import hashlib
import hmac
import json
from .config import settings
from .contacts import audience_fingerprint
from .db import connect,uid,now,audit
from .analytics import synthetic_metrics,hypothesis_summary


def execute_dry_run(cid,approval_id,contacts):
    if not settings.dry_run:
        raise PermissionError('V4 supports local dry-run only; DRY_RUN must remain true')
    with connect(immediate=True) as c:
        cr=c.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone()
        if cr is None:raise KeyError('Campaign not found')
        if cr['status']!='APPROVED':raise PermissionError('Campaign not in APPROVED state')
        ver=c.execute('SELECT * FROM versions WHERE campaign_id=? ORDER BY revision DESC LIMIT 1',(cid,)).fetchone()
        apr=c.execute('''SELECT * FROM approvals WHERE id=? AND campaign_id=? AND version_id=?
                           AND decision='APPROVED' ''',(approval_id,cid,ver['id'])).fetchone()
        if apr is None:raise PermissionError('Missing matching approval')
        if apr['content_sha256']!=ver['sha256'] or apr['audience_sha256']!=ver['audience_sha256']:
            raise PermissionError('Approval digest mismatch')
        actual=hashlib.sha256(ver['content_json'].encode()).hexdigest()
        if actual!=ver['sha256']:raise PermissionError('Content integrity mismatch')
        if not json.loads(ver['review_json'])['passed']:
            raise PermissionError('Quality review not passed')
        b=json.loads(cr['brief_json'])
        audience=set(b['audience'])
        filtered=[x for x in contacts if x['persona_segment'] in audience]
        if not filtered:raise ValueError('No selected recipients')
        if len(filtered)>settings.max_recipients:raise PermissionError('Selected recipient ceiling exceeded')
        if audience_fingerprint(contacts,audience)!=ver['audience_sha256']:
            raise PermissionError('Audience changed since version review')
        if not settings.contact_hmac_key or settings.contact_hmac_key=='':
            raise PermissionError('Missing recipient HMAC key')
        # Exclusive transaction makes check/claim/writes serial even across processes.
        c.execute("UPDATE campaigns SET status='DISPATCHING',updated_at=? WHERE id=? AND status='APPROVED'",(now(),cid))
        exid=uid('exe')
        c.execute('INSERT INTO execution_runs VALUES(?,?,?,?,?,?,?)',
                 (exid,cid,ver['id'],approval_id,'DISPATCHING',now(),None))
        for contact in filtered:
            pseudonym=hmac.new(settings.contact_hmac_key.encode(),contact['email'].encode(),hashlib.sha256).hexdigest()
            c.execute('INSERT INTO deliveries VALUES(?,?,?,?,?,?,?)',
                      (uid('del'),exid,pseudonym,contact['persona_segment'],'SIMULATED_PREPARED','SYNTHETIC',now()))
        groups={p:sum(x['persona_segment']==p for x in filtered) for p in audience}
        rows=synthetic_metrics(cid,groups)
        for x in rows:
            c.execute('INSERT INTO metrics VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (uid('met'),exid,cid,x['persona'],x['recipient_count'],x['simulated_deliveries'],
                       x['opened'],x['clicked'],x['unsubscribed'],'SYNTHETIC',now()))
        summary=hypothesis_summary(rows)
        c.execute('INSERT INTO insights VALUES(?,?,?,?,?)',(uid('ins'),exid,'HYPOTHESIS',summary,now()))
        c.execute("UPDATE execution_runs SET status='COMPLETED',completed_at=? WHERE id=?",(now(),exid))
        c.execute("UPDATE campaigns SET status='COMPLETED',updated_at=? WHERE id=?",(now(),cid))
        audit('DRY_RUN_COMPLETED',f'execution={exid}; recipients={len(filtered)}; live_send=0',cid,conn=c)
        c.execute('INSERT INTO product_events VALUES(?,?,?,?,?)',
                  (uid('evt'),cid,'dry_run_completed',now(),'{}'))
    return {'campaign_id':cid,'execution_id':exid,'mode':'LOCAL_DRY_RUN',
            'synthetic_recipients_prepared':len(filtered),'live_emails_sent':0,
            'synthetic_metrics':rows,'analysis':summary}

def send_live(*args,**kwargs):
    raise NotImplementedError('Live marketing send is disabled in V4')
