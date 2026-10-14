"""SQLite store with transactional execution and version-bound approvals.

Fresh V3 database: the V2 file is retained in legacy but never silently migrated.
"""
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import settings


def uid(prefix):
    return prefix + '_' + uuid.uuid4().hex[:16]

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect(immediate=False):
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.db_path, timeout=15, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=15000')
    try:
        c.execute('BEGIN IMMEDIATE' if immediate else 'BEGIN')
        yield c
        c.execute('COMMIT')
    except Exception:
        if c.in_transaction:
            c.execute('ROLLBACK')
        raise
    finally:
        c.close()


def init_db():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.db_path) as c:
        c.execute('PRAGMA foreign_keys=ON')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS campaigns(
          id TEXT PRIMARY KEY, brief_json TEXT NOT NULL,
          status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plans(
          id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
          plan_json TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS versions(
          id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
          plan_id TEXT NOT NULL REFERENCES plans(id), revision INTEGER NOT NULL,
          sha256 TEXT NOT NULL, audience_sha256 TEXT NOT NULL,
          content_json TEXT NOT NULL, generation_mode TEXT NOT NULL,
          review_json TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(campaign_id, revision));
        CREATE TABLE IF NOT EXISTS approvals(
          id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
          version_id TEXT NOT NULL REFERENCES versions(id), actor_id TEXT NOT NULL,
          decision TEXT NOT NULL, content_sha256 TEXT NOT NULL,
          audience_sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS execution_runs(
          id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
          version_id TEXT NOT NULL REFERENCES versions(id),
          approval_id TEXT NOT NULL REFERENCES approvals(id),
          status TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT,
          UNIQUE(campaign_id,version_id));
        CREATE TABLE IF NOT EXISTS deliveries(
          id TEXT PRIMARY KEY, execution_id TEXT NOT NULL REFERENCES execution_runs(id),
          recipient_hash TEXT NOT NULL, persona TEXT NOT NULL,
          status TEXT NOT NULL, source_type TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(execution_id,recipient_hash));
        CREATE TABLE IF NOT EXISTS metrics(
          id TEXT PRIMARY KEY, execution_id TEXT NOT NULL REFERENCES execution_runs(id),
          campaign_id TEXT NOT NULL REFERENCES campaigns(id), persona TEXT NOT NULL,
          recipient_count INTEGER NOT NULL, simulated_deliveries INTEGER NOT NULL,
          opened INTEGER NOT NULL, clicked INTEGER NOT NULL, unsubscribed INTEGER NOT NULL,
          source_type TEXT NOT NULL, measured_at TEXT NOT NULL,
          UNIQUE(execution_id,persona));
        CREATE TABLE IF NOT EXISTS insights(
          id TEXT PRIMARY KEY, execution_id TEXT NOT NULL REFERENCES execution_runs(id) UNIQUE,
          evidence_type TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS agent_runs(
          id TEXT PRIMARY KEY, campaign_id TEXT REFERENCES campaigns(id),
          planner_source TEXT NOT NULL, status TEXT NOT NULL,
          input_summary TEXT NOT NULL, error TEXT, started_at TEXT NOT NULL,
          finished_at TEXT);
        CREATE TABLE IF NOT EXISTS tool_calls(
          id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES agent_runs(id),
          tool_name TEXT NOT NULL, status TEXT NOT NULL, latency_ms INTEGER NOT NULL,
          result_summary TEXT NOT NULL, at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_events(
          id TEXT PRIMARY KEY, campaign_id TEXT REFERENCES campaigns(id),
          action TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL, at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS claim_evidence(
          id TEXT PRIMARY KEY, exact_claim TEXT NOT NULL,
          normalized_claim TEXT NOT NULL, source_reference TEXT NOT NULL,
          source_type TEXT NOT NULL, attestor TEXT NOT NULL,
          attested_at TEXT NOT NULL, expires_at TEXT);
        CREATE TABLE IF NOT EXISTS plan_sessions(
          id TEXT PRIMARY KEY, brief_json TEXT NOT NULL,plan_json TEXT NOT NULL,
          plan_revision INTEGER NOT NULL,status TEXT NOT NULL,
          planner_source TEXT NOT NULL,agent_run_id TEXT NOT NULL REFERENCES agent_runs(id),
          campaign_id TEXT REFERENCES campaigns(id),created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plan_revisions(
          id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES plan_sessions(id),
          revision INTEGER NOT NULL,plan_json TEXT NOT NULL,created_at TEXT NOT NULL,
          UNIQUE(session_id,revision));
        CREATE TABLE IF NOT EXISTS product_events(
          id TEXT PRIMARY KEY,campaign_id TEXT REFERENCES campaigns(id),event TEXT NOT NULL,
          occurred_at TEXT NOT NULL,meta_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviewer_feedback(
          id TEXT PRIMARY KEY,campaign_id TEXT NOT NULL REFERENCES campaigns(id),
          version_id TEXT NOT NULL REFERENCES versions(id),actor TEXT NOT NULL,
          feedback TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_feedback_campaign ON reviewer_feedback(campaign_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_versions_campaign ON versions(campaign_id,revision);
        CREATE INDEX IF NOT EXISTS idx_metrics_campaign ON metrics(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_audit_campaign ON audit_events(campaign_id,at);
        ''')

def audit(action, detail, campaign_id=None, actor='system', conn=None):
    args = (uid('aud'), campaign_id, action, actor, detail[:1200], now())
    if conn is not None:
        conn.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?)', args)
    else:
        with connect(immediate=True) as c:
            c.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?)', args)

def create_campaign(brief, plan, plan_source, content, generation_mode, review, fingerprint):
    """All authoritative state is inserted atomically; no half-finished campaign."""
    cid, pid, vid = uid('cmp'), uid('plan'), uid('ver')
    payload = content.model_dump_json()
    sha = hashlib.sha256(payload.encode()).hexdigest()
    when = now()
    with connect(immediate=True) as c:
        c.execute('INSERT INTO campaigns VALUES(?,?,?,?,?)', (cid, brief.model_dump_json(), 'REVIEW', when, when))
        c.execute('INSERT INTO plans VALUES(?,?,?,?,?)', (pid, cid, plan.model_dump_json(), plan_source, when))
        c.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (vid,cid,pid,1,sha,fingerprint,payload,generation_mode,review.model_dump_json(),when))
        audit('CAMPAIGN_CREATED', 'plan-driven version='+vid, cid, conn=c)
    return cid,pid,vid

def row_one(sql, args):
    with connect() as c:
        r = c.execute(sql,args).fetchone()
    if not r:
        raise KeyError('Record not found')
    return dict(r)

def campaign(cid):
    return row_one('SELECT * FROM campaigns WHERE id=?',(cid,))

def latest_version(cid):
    return row_one('SELECT * FROM versions WHERE campaign_id=? ORDER BY revision DESC LIMIT 1',(cid,))

def get_version(vid):
    return row_one('SELECT * FROM versions WHERE id=?',(vid,))

def get_plan(pid):
    return row_one('SELECT * FROM plans WHERE id=?',(pid,))

def list_campaigns(limit=50):
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM campaigns ORDER BY created_at DESC LIMIT ?',(limit,))]

def save_revision(cid, brief, plan, plan_source, content, mode, review, fingerprint):
    pid, vid, when = uid('plan'), uid('ver'), now()
    payload = content.model_dump_json()
    sha = hashlib.sha256(payload.encode()).hexdigest()
    with connect(immediate=True) as c:
        row=c.execute('SELECT status FROM campaigns WHERE id=?',(cid,)).fetchone()
        if row is None: raise KeyError('Unknown campaign')
        if row['status'] in ('COMPLETED','DISPATCHING'): raise ValueError('Executed campaign immutable')
        rev = c.execute('SELECT COALESCE(MAX(revision),0)+1 FROM versions WHERE campaign_id=?',(cid,)).fetchone()[0]
        c.execute('INSERT INTO plans VALUES(?,?,?,?,?)',(pid,cid,plan.model_dump_json(),plan_source,when))
        c.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (vid,cid,pid,rev,sha,fingerprint,payload,mode,review.model_dump_json(),when))
        c.execute("UPDATE campaigns SET status='REVIEW',brief_json=?,updated_at=? WHERE id=?",(brief.model_dump_json(),when,cid))
        audit('REVISION',f'new version {vid}; prior approvals invalidated',cid,conn=c)
    return pid,vid

def approve(cid, version_id, reviewer_token, decision):
    """Local demo reviewer identity is bound to a secret, not a typed email string.
    This is NOT hosted authentication/RBAC; live emailing is disabled.
    """
    import hmac
    if not settings.local_demo_review_token or not reviewer_token or not hmac.compare_digest(
            reviewer_token,settings.local_demo_review_token):
        raise PermissionError('Local reviewer token missing or invalid')
    if decision not in ('APPROVED','REJECTED'):
        raise ValueError('Invalid decision')
    aid=uid('apr')
    with connect(immediate=True) as c:
        row=c.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone()
        ver=c.execute('SELECT * FROM versions WHERE id=? AND campaign_id=?',(version_id,cid)).fetchone()
        latest=c.execute('SELECT * FROM versions WHERE campaign_id=? ORDER BY revision DESC LIMIT 1',(cid,)).fetchone()
        if not row or not ver or not latest: raise KeyError('Unknown campaign or version')
        if row['status']!='REVIEW' or latest['id']!=version_id:
            raise PermissionError('Only current REVIEW version may be approved')
        if decision=='APPROVED' and not json.loads(ver['review_json'])['passed']:
            raise PermissionError('Quality checks not passed')
        c.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?)',
                 (aid,cid,version_id,settings.local_demo_reviewer_id,decision,ver['sha256'],ver['audience_sha256'],now()))
        c.execute('UPDATE campaigns SET status=?,updated_at=? WHERE id=?',
                  (decision,now(),cid))
        audit('APPROVAL_DECISION',f'{decision} version={version_id}',cid,
              actor=settings.local_demo_reviewer_id,conn=c)
    return aid

def audits(cid):
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM audit_events WHERE campaign_id=? ORDER BY at,id',(cid,))]

def read_metrics(cid):
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM metrics WHERE campaign_id=? ORDER BY persona',(cid,))]

def read_history(limit=20):
    """Return data source labels. Never present synthetic results as verified conversion evidence."""
    with connect() as c:
        rs = c.execute('''SELECT c.id, c.status, c.brief_json, MAX(m.source_type) AS metric_source
                            FROM campaigns c LEFT JOIN metrics m ON m.campaign_id=c.id
                            GROUP BY c.id ORDER BY c.created_at DESC LIMIT ?''',(limit,)).fetchall()
    out=[]
    for r in rs:
        b=json.loads(r['brief_json'])
        out.append({'campaign_id':r['id'],'status':r['status'],'goal':b['goal'],
                    'topic':b['topic'],'primary_kpi':b['primary_kpi'],
                    'metric_source':r['metric_source'] or 'NONE',
                    'verified_conversion_evidence':False})
    return out

def create_agent_run(source, summary, cid=None):
    run=uid('run')
    with connect(immediate=True) as c:
        c.execute('INSERT INTO agent_runs VALUES(?,?,?,?,?,?,?,?)',
                  (run,cid,source,'RUNNING',summary[:600],None,now(),None))
    return run

def end_agent_run(run,status,error=None):
    with connect(immediate=True) as c:
        c.execute('UPDATE agent_runs SET status=?,error=?,finished_at=? WHERE id=?',
                  (status,str(error)[:400] if error else None,now(),run))

def log_tool(run,name,status,latency_ms,summary):
    with connect(immediate=True) as c:
        c.execute('INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)',
                  (uid('tool'),run,name,status,max(0,int(latency_ms)),str(summary)[:300],now()))

def read_tool_trace(cid=None,run=None):
    with connect() as c:
        if run:
            rows=c.execute('SELECT * FROM tool_calls WHERE run_id=? ORDER BY at,id',(run,)).fetchall()
        elif cid:
            rows=c.execute('''SELECT t.* FROM tool_calls t JOIN agent_runs a ON t.run_id=a.id
                              WHERE a.campaign_id=? ORDER BY t.at,t.id''',(cid,)).fetchall()
        else: rows=[]
    return [dict(r) for r in rows]
