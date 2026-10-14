"""V3-compatible CLI. Run from root: python -m app.main create ..."""
import argparse
import getpass
import json
import os
from .workflow import create_draft,revise_draft,edit_draft,decide,dispatch,inspect
from .db import init_db,list_campaigns

def main(argv=None):
    p=argparse.ArgumentParser(description='NovaMind AI Growth Agent V4 (legacy-compatible, local-only safety)')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('create');s.add_argument('--goal',required=True);s.add_argument('--topic',required=True)
    s.add_argument('--mode',choices=['demo','llm'],default='demo')
    s.add_argument('--planner',choices=['demo','agent'],default='demo')
    s.add_argument('--audience',default='ops_lead,creative_director,freelancer')
    s.add_argument('--kpi',default='qualified_demo_signups')
    s=sub.add_parser('revise');s.add_argument('--campaign',required=True);s.add_argument('--goal');s.add_argument('--audience');s.add_argument('--kpi')
    s.add_argument('--mode',choices=['demo','llm'],default='demo');s.add_argument('--planner',choices=['demo','agent'],default='demo')
    s=sub.add_parser('edit');s.add_argument('--campaign',required=True);s.add_argument('--content-file',required=True)
    s=sub.add_parser('approve');s.add_argument('--campaign',required=True);s.add_argument('--decision',choices=['APPROVED','REJECTED'],required=True)
    s=sub.add_parser('send');s.add_argument('--campaign',required=True);s.add_argument('--approval',required=True)
    s=sub.add_parser('show');s.add_argument('--campaign',required=True)
    sub.add_parser('list')
    a=p.parse_args(argv)
    if a.command=='create':
        value=create_draft(a.goal,a.topic,mode=a.mode,planner=a.planner,audience=a.audience.split(','),primary_kpi=a.kpi)
    elif a.command=='revise':
        value=revise_draft(a.campaign,goal=a.goal,audience=a.audience.split(',') if a.audience else None,
                           primary_kpi=a.kpi,mode=a.mode,planner=a.planner)
    elif a.command=='edit':
        with open(a.content_file,encoding='utf8') as f: data=json.load(f)
        value=edit_draft(a.campaign,data.get('content',data))
    elif a.command=='approve':
        # Terminal password entry avoids putting the token in shell history.
        token=os.getenv('LOCAL_REVIEW_TOKEN_INPUT') or getpass.getpass('Enter reviewer token: ')
        value=decide(a.campaign,token,a.decision)
    elif a.command=='send':value=dispatch(a.campaign,a.approval)
    elif a.command=='show':value=inspect(a.campaign)
    else:
        init_db();value=list_campaigns()
    print(json.dumps(value,indent=2,ensure_ascii=False,default=str))
    return value
if __name__=='__main__':main()
