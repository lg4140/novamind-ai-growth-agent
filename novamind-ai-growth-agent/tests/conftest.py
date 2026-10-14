import pytest
from dataclasses import replace
from app.config import settings
from app import db,content,dispatch,agent,contacts,evidence,memory_service

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    conf=replace(settings,db_path=tmp_path/'v3.db',output_dir=tmp_path/'outputs',
                 local_demo_review_token='test-demo-reviewer-token',
                 contact_hmac_key='test-hmac-secret',dry_run=True,max_recipients=100)
    for mod in (db,content,dispatch,agent,contacts,evidence,memory_service):
        monkeypatch.setattr(mod,'settings',conf)
    yield conf
