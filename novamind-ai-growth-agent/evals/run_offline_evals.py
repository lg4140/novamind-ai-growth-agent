"""Executes actual deterministic product tests and captures independent JUnit evidence.

DO NOT use this result as an LLM Agent evaluation rate.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'
OUT.mkdir(exist_ok=True)
XML=OUT/'offline_pytest_junit.xml'
RUN=OUT/'offline_engineering_results.json'
cmd=[sys.executable,'-m','pytest','tests/test_product_workflow.py','tests/test_v4.py','-q',f'--junitxml={XML}']
p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
if not XML.exists():
    raise RuntimeError('No test runner XML was produced; refusing to record a fabricated result.\n'+p.stdout)
root=ET.parse(XML).getroot()
tests=[]
for tc in root.findall('.//testcase'):
    status='FAIL' if tc.find('failure') is not None else 'ERROR' if tc.find('error') is not None else 'SKIPPED' if tc.find('skipped') is not None else 'PASS'
    tests.append({'test_id':tc.get('name'),'status':status,'duration_seconds':float(tc.get('time','0')),
                  'evidence':'reports/offline_pytest_junit.xml'})
report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'execution_type':'DETERMINISTIC_OFFLINE_PYTEST_NOT_LLM_AGENT',
        'command':' '.join(cmd),'exit_code':p.returncode,
        'passed':sum(t['status']=='PASS' for t in tests),
        'failed':sum(t['status'] in ('FAIL','ERROR') for t in tests),
        'skipped':sum(t['status']=='SKIPPED' for t in tests),
        'tests':tests,'stdout':p.stdout[-4000:],
        'model_agent_evals_executed':0,'real_hubspot_integrations_executed':0,
        'real_customer_conversions_verified':0}
RUN.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('tests','stdout')},indent=2))
if p.returncode:sys.exit(p.returncode)
