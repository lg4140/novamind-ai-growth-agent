"""Local claims registry, intentionally NOT a web fact checker.

Reviewer attestations are user-provided provenance; they do not constitute
independent third-party verification. The model cannot self-register evidence.
"""
import re
from datetime import datetime, timezone
from .db import connect, uid, now, init_db
from .config import settings

TRIGGER_PATTERNS = (
    r'\b(?:soc\s*2(?:\s*type\s*(?:i{1,3}|[123]))?|iso\s*27001|hipaa|gdpr)\s*(?:certif\w*|compliant|approved|verified|accredited)\b',
    r'\b(?:certified|accredited|endorsed|approved)\s+by\s+\w+',
    r'\b(?:trusted|used|chosen|recommended)\s+by\s+(?:over\s+)?(?:\d[\d,]*|thousands?|millions?)\b',
    r'\b(?:industry.leading|number\s*one|#1|market.leader)\b',
    r'\b(?:guarantee(?:d|s)?|proven\s+to|risk.free\s+profit|double\s+your\s+revenue)\b',
)
PERFORMANCE = re.compile(r'\b(?:roi|return on investment|revenue|sales|costs?|profits?|margins?|productivity|efficien\w*|time sav\w*|hours? sav\w*|conversion|churn|growth|lift|increas\w*|reduc\w*|boost\w*)\b', re.I)
QUANTITY = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|percent\b|percentage points?\b|x\b|times\b)|\b\d+(?:\.\d+)?%', re.I)
PATTERNS = [re.compile(pattern,re.I) for pattern in TRIGGER_PATTERNS]


def extract_claims(content):
    """Conservative pattern detection; not comprehensive NLP/factual validation."""
    pieces=[content.blog_title,content.blog_draft]
    pieces += [f'{x.subject}. {x.preview_text}. {x.body}. {x.cta_text}' for x in content.newsletters.values()]
    found=[]
    for text in pieces:
        for part in re.split(r'[.!?\n]+',text):
            sentence=' '.join(part.split()).strip()
            if sentence and (any(p.search(sentence) for p in PATTERNS) or
                             (PERFORMANCE.search(sentence) and QUANTITY.search(sentence))):
                if sentence not in found: found.append(sentence[:300])
    return found


def normalize_claim(s):
    return ' '.join(s.casefold().split()).strip().rstrip('.')


def attest_claim(claim_text, source_reference, reviewer_token, expires_at=None):
    """Attest exact quoted claim + provenance. This is LOCAL reviewer judgement only."""
    import hmac
    if (not settings.local_demo_review_token or not reviewer_token or
        not hmac.compare_digest(reviewer_token,settings.local_demo_review_token)):
        raise PermissionError('Valid local reviewer token required to attest claim')
    if not (10 <= len(claim_text.strip()) <= 300):
        raise ValueError('Provide the exact full claim sentence (10–300 chars)')
    if not (8 <= len(source_reference.strip()) <= 1000):
        raise ValueError('Source reference must be a nonempty identifiable citation (8–1000 chars)')
    if expires_at and datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError('Evidence cannot already be expired')
    init_db()
    ref=uid('evd')
    with connect(immediate=True) as c:
        c.execute('''INSERT INTO claim_evidence
          (id,exact_claim,normalized_claim,source_reference,source_type,attestor,attested_at,expires_at)
          VALUES(?,?,?,?,?,?,?,?)''',(ref,claim_text.strip(),normalize_claim(claim_text),source_reference.strip(),
          'LOCAL_REVIEWER_ATTESTATION',settings.local_demo_reviewer_id,now(),expires_at))
    return ref


def evidence_for_claim(claim, refs):
    """Exact-match only, no substring citation laundering."""
    if not refs:return None
    placeholders=','.join('?' for _ in refs)
    with connect() as c:
        rows=c.execute(f'SELECT * FROM claim_evidence WHERE id IN ({placeholders})',tuple(refs)).fetchall()
    for row in rows:
        if row['normalized_claim'] != normalize_claim(claim):continue
        if row['expires_at'] and datetime.fromisoformat(row['expires_at']).replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            continue
        return {'evidence_id':row['id'],'source_type':row['source_type'],'source_reference':row['source_reference']}
    return None
