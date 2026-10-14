"""Review-derived learning. Feedback is evidence of reviewer preference, not truth.

Stored feedback is never promoted to a system instruction or automatically made
into factual product claims. Read-only history is scoped to this local demo DB.
"""
import hmac
import re
from .db import connect,init_db,uid,now
from .config import settings


def redact_free_text(text):
    text=re.sub(r'[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]', text)
    text=re.sub(r'\b(?:sk-[a-zA-Z0-9_\-]{12,}|Bearer\s+\S+)\b','[REDACTED_SECRET]',text)
    return text[:1200]


def record_feedback(campaign_id, version_id, feedback, reviewer_token):
    init_db()
    if not (settings.local_demo_review_token and reviewer_token and
            hmac.compare_digest(reviewer_token,settings.local_demo_review_token)):
        raise PermissionError('Reviewer token required')
    if not 5<=len(feedback.strip())<=2000:raise ValueError('Feedback must be 5-2000 chars')
    safe=redact_free_text(feedback.strip())
    ref=uid('fbk')
    with connect(immediate=True) as c:
        ver=c.execute('SELECT 1 FROM versions WHERE id=? AND campaign_id=?',(version_id,campaign_id)).fetchone()
        if not ver:raise KeyError('Unknown campaign/version')
        c.execute('INSERT INTO reviewer_feedback VALUES(?,?,?,?,?,?)',
                  (ref,campaign_id,version_id,settings.local_demo_reviewer_id,safe,now()))
        c.execute('INSERT INTO product_events VALUES(?,?,?,?,?)',
                  (uid('evt'),campaign_id,'reviewer_feedback_saved',now(),'{}'))
    return {'feedback_id':ref,'stored_redacted':safe != feedback.strip(),'source':'REVIEWER_FEEDBACK_NOT_FACT'}


def read_lessons(limit=10):
    init_db()
    with connect() as c:
        rows=c.execute('''SELECT f.id,f.campaign_id,f.version_id,f.feedback,f.created_at
            FROM reviewer_feedback f ORDER BY created_at DESC LIMIT ?''',(max(1,min(limit,30)),)).fetchall()
    return [dict(r)|{'source_type':'REVIEWER_FEEDBACK_NOT_FACT','trusted_instruction':False} for r in rows]
