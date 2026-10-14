"""Strict, low-dependency segmentation data ingestion."""
import csv
import hashlib
import json
import re
from .config import settings
from .schemas import PERSONAS


def load_contacts(path=None):
    path = path or settings.contacts_path
    required = {'email', 'firstname', 'lastname', 'company', 'persona_segment'}
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'CSV missing fields: {sorted(required - set(reader.fieldnames or []))}')
        contacts = []
        emails = set()
        for rownum, source in enumerate(reader, 2):
            row = {k: (source.get(k) or '').strip() for k in required}
            email = row['email'].lower()
            if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
                raise ValueError(f'Invalid email on row {rownum}')
            if email in emails:
                raise ValueError(f'Duplicate email on row {rownum}')
            if row['persona_segment'] not in PERSONAS:
                raise ValueError(f'Unknown persona on row {rownum}')
            if any(not row[key] for key in required):
                raise ValueError(f'Empty required field on row {rownum}')
            row['email'] = email
            emails.add(email)
            contacts.append(row)
    return contacts


def segment_counts(contacts):
    return {p: sum(c['persona_segment'] == p for c in contacts) for p in PERSONAS}


def audience_fingerprint(contacts, audience):
    """Immutable digest of the exact selected email/persona recipients, not identities."""
    subset = sorted((c['email'], c['persona_segment']) for c in contacts
                    if c['persona_segment'] in set(audience))
    payload = json.dumps(subset, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
