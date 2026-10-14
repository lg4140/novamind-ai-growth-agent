"""Conservative HubSpot adapter boundary.

V3 demonstrates only a local CRM contact-sync preview; neither CRM writes nor
marketing sends are enabled. Source V1/V2 API examples remain in legacy bundles.
"""

def contact_upsert_payload(contacts):
    """Build a request-shaped object in memory for an explicitly synthetic demo.

    DO NOT log/export this payload as it includes personal email addresses.
    """
    return {'inputs': [
        {'id': c['email'], 'idProperty': 'email',
         'properties': {k:c[k] for k in ('email','firstname','lastname','company','persona_segment')}}
        for c in contacts
    ]}


def preview_contact_sync(contacts):
    """No API call, no PII returned."""
    return {'operation':'CRM_CONTACT_SYNC_PREVIEW','source':'CSV_DEMO',
            'records_prepared':len(contacts),'hubspot_api_calls':0,'crm_writes':0}


def sync_contacts(contacts, confirm_live=False):
    if confirm_live:
        raise NotImplementedError('CRM write integration requires verified scopes, consent and sandbox contract tests')
    return preview_contact_sync(contacts)


def send_marketing_email(*_args,**_kwargs):
    raise NotImplementedError('No live marketing sending is supported in NovaMind V3')
