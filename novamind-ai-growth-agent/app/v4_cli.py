"""V4 additions: separate plan confirmation and draft generation.

Existing `python -m app.main ...` remains backwards-compatible for V3 workflows.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
from .schemas import CampaignBrief
from .stateful import propose,revise_plan,confirm_plan,generate_from_confirmed,session_status,retry_export
from .evidence import attest_claim
from .memory_service import record_feedback,read_lessons
from .telemetry import product_event_summary


def main(argv=None):
    p=argparse.ArgumentParser(description='NovaMind V4 plan-first product workflows (no live sending)')
    sp=p.add_subparsers(dest='cmd',required=True)
    s=sp.add_parser('propose');s.add_argument('--goal',required=True);s.add_argument('--topic',required=True)
    s.add_argument('--audience',default='ops_lead,creative_director,freelancer')
    s.add_argument('--kpi',default='qualified_demo_signups');s.add_argument('--planner',choices=['demo','agent'],default='demo')
    s.add_argument('--constraint',action='append',default=[])
    s=sp.add_parser('edit-plan');s.add_argument('--session',required=True);s.add_argument('--plan-file',required=True);s.add_argument('--expected-revision',type=int,required=True)
    s=sp.add_parser('confirm-plan');s.add_argument('--session',required=True);s.add_argument('--revision',type=int,required=True)
    s=sp.add_parser('generate');s.add_argument('--session',required=True);s.add_argument('--mode',choices=['demo','llm'],default='demo')
    s=sp.add_parser('plan-status');s.add_argument('--session',required=True)
    s=sp.add_parser('retry-export');s.add_argument('--campaign',required=True)
    s=sp.add_parser('attest-claim');s.add_argument('--claim',required=True);s.add_argument('--source',required=True)
    s=sp.add_parser('feedback');s.add_argument('--campaign',required=True);s.add_argument('--version',required=True);s.add_argument('--text',required=True)
    sp.add_parser('lessons')
    s=sp.add_parser('telemetry');s.add_argument('--campaign',required=True)
    a=p.parse_args(argv)
    if a.cmd=='propose':
        value=propose(CampaignBrief(goal=a.goal,topic=a.topic,audience=a.audience.split(','),primary_kpi=a.kpi,
                     constraints=a.constraint or ['No live marketing sends']).model_dump(),a.planner)
    elif a.cmd=='edit-plan':value=revise_plan(a.session,json.loads(Path(a.plan_file).read_text()),a.expected_revision)
    elif a.cmd=='confirm-plan':value=confirm_plan(a.session,a.revision)
    elif a.cmd=='generate':value=generate_from_confirmed(a.session,a.mode)
    elif a.cmd=='plan-status':value=session_status(a.session)
    elif a.cmd=='retry-export':value=retry_export(a.campaign)
    elif a.cmd=='lessons':value=read_lessons()
    elif a.cmd=='telemetry':value=product_event_summary(a.campaign)
    else:
        token=os.getenv('LOCAL_REVIEW_TOKEN_INPUT') or getpass.getpass('Local reviewer token: ')
        if a.cmd=='attest-claim':value={'evidence_id':attest_claim(a.claim,a.source,token)}
        else:value=record_feedback(a.campaign,a.version,a.text,token)
    print(json.dumps(value,indent=2,ensure_ascii=False))
    return value

if __name__=='__main__': main()
