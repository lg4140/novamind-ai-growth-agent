"""V4 local Streamlit workbench (reviewable workflow; NOT hosted auth or live CRM)."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from app.db import init_db,list_campaigns,connect
from app.schemas import CampaignBrief,PERSONAS
from app.stateful import propose,revise_plan,confirm_plan,generate_from_confirmed,session_status,retry_export
from app.workflow import inspect,edit_draft,decide,dispatch
from app.evidence import attest_claim
from app.memory_service import record_feedback,read_lessons
from app.orchestrator import next_action

st.set_page_config(page_title='NovaMind V4 | Growth Agent',layout='wide')
st.title('NovaMind V4 · Evidence-Aware Growth Copilot')
st.caption('LOCAL DEMONSTRATION — PLAN CONFIRMATION ≠ SEND APPROVAL — NO LIVE EMAIL — SYNTHETIC METRICS — Reviewer token is not SSO/RBAC')
init_db()

def sessions():
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT id,status,plan_revision,updated_at FROM plan_sessions ORDER BY created_at DESC LIMIT 100')]

def safe_run(fn):
    try: return fn()
    except Exception as exc:
        st.error(f'{type(exc).__name__}: {exc}')
        return None

t1,t2,t3,t4,t5=st.tabs(['1 · Create brief','2 · Plan & revise','3 · Draft & review','4 · Metrics & traces','5 · Lessons'])
with t1:
    st.subheader('Describe a business goal before generating content')
    with st.form('brief'):
        goal=st.text_area('Goal','Increase qualified demo signups among creative agencies')
        topic=st.text_input('Topic','AI workflow automation for small studios')
        audience=st.multiselect('Selected recipient personas',list(PERSONAS),default=list(PERSONAS))
        kpi=st.text_input('Primary KPI','qualified_demo_signups')
        brand=st.text_input('Brand voice','practical, precise, evidence-aware')
        constraints=st.text_area('Supported constraints (one per line)','No live marketing sends\nAvoid the word guaranteed in any CTA')
        planner=st.selectbox('Planning mode',['demo','agent'],help='demo is deterministic, agent uses model-selected read-only tools and needs configured credentials')
        if st.form_submit_button('Propose plan (no content yet)',type='primary'):
            def call():
                b=CampaignBrief(goal=goal,topic=topic,audience=audience,primary_kpi=kpi,brand_voice=brand,
                    constraints=[x.strip() for x in constraints.splitlines() if x.strip()])
                return propose(b.model_dump(),planner=planner)
            response=safe_run(call)
            if response:
                st.session_state['session']=response['session_id']
                st.success('Plan proposed; no content created, no approval granted')
                st.json(response)

slist=sessions()
ssids=[s['id'] for s in slist]
current_session=st.sidebar.selectbox('Plan session',ssids,index=ssids.index(st.session_state.get('session')) if st.session_state.get('session') in ssids else 0) if ssids else None
campaigns=list_campaigns()
cids=[r['id'] for r in campaigns]
current_campaign=st.sidebar.selectbox('Campaign',cids,index=cids.index(st.session_state.get('campaign')) if st.session_state.get('campaign') in cids else 0) if cids else None

with t2:
    st.subheader('Proposed plan — version-controlled and editable')
    if not current_session:st.info('Create a brief first.')
    else:
        session=session_status(current_session);p=session['plan'];st.write('State:',session['status'],' · Revision:',session['revision'])
        st.json({'goal':p['goal'],'topic':p['topic'],'segments':p['target_segments'],
                 'assumptions':p['assumptions'],'evidence_refs':p['evidence_refs'],
                 'compiled_constraints':p['constraint_policy']})
        decision=next_action('PROPOSED' if session['status']=='PROPOSED' else 'CONFIRMED' if session['status']=='CONFIRMED' else 'REVIEW')
        st.caption('Next step: '+decision.action+' — '+decision.explanation)
        if session['status']=='PROPOSED':
            with st.form(f'edit_plan_{current_session}_{session["revision"]}'):
                angles=[]
                for i,m in enumerate(p['messaging']):
                    st.markdown('**'+m['persona']+'**')
                    problem=st.text_input('Customer problem',m['customer_problem'],key=f'prob{i}')
                    val=st.text_area('Value proposition',m['value_proposition'],key=f'val{i}')
                    cta=st.text_input('Call to action',m['call_to_action'],key=f'cta{i}')
                    angles.append(dict(persona=m['persona'],customer_problem=problem,value_proposition=val,call_to_action=cta))
                if st.form_submit_button('Save revised plan'):
                    change=p|{'messaging':angles}
                    r=safe_run(lambda:revise_plan(current_session,change,session['revision']))
                    if r:st.success('Revised; prior plan version no longer current');st.rerun()
            if st.button('Confirm this plan version',type='primary'):
                r=safe_run(lambda:confirm_plan(current_session,session['revision']))
                if r:st.success('Plan confirmed; no campaign approval granted');st.rerun()
        elif session['status']=='CONFIRMED':
            mode=st.selectbox('Content generation mode',['demo','llm'])
            if st.button('Generate draft from confirmed plan',type='primary'):
                r=safe_run(lambda:generate_from_confirmed(current_session,mode))
                if r:st.session_state['campaign']=r['campaign_id'];st.success('Created reviewable content version');st.rerun()
        else:
            st.info('This plan has already created a campaign. Editing a plan requires a new session; content changes create a new immutable draft version.')

with t3:
    st.subheader('Review the exact version before approval')
    if not current_campaign:st.info('Generate a draft from a confirmed plan first.')
    else:
        result=inspect(current_campaign);v=result['version'];content=json.loads(v['content_json']);review=json.loads(v['review_json'])
        st.write('Campaign status:',result['campaign']['status'],' · Content revision:',v['revision'],' · Version ID:',v['id'])
        a,b,c=st.columns(3);a.metric('Structural quality','PASS' if review['structural_pass'] else 'FAIL');b.metric('Claims',review['claim_status']);c.metric('Eligible for review','YES' if review['passed'] else 'NO')
        for item in review['issues']:st.warning(item)
        st.caption('A reviewer attestation means someone supplied a reference; it is NOT third-party factual verification.')
        with st.form(f'edit_content_{v["id"]}'):
            reftext=st.text_input('Attached local evidence IDs (comma-separated)',','.join(content.get('evidence_refs',[])))
            blog_title=st.text_input('Blog title',content['blog_title'])
            blog=st.text_area('Blog body',content['blog_draft'],height=210)
            emails={}
            for persona,msg in content['newsletters'].items():
                with st.expander('Newsletter / '+persona,expanded=True):
                    sub=st.text_input('Subject',msg['subject'],key='subject_'+persona+v['id'])
                    pre=st.text_input('Preview text',msg['preview_text'],key='preview_'+persona+v['id'])
                    body=st.text_area('Email body',msg['body'],height=130,key='body_'+persona+v['id'])
                    cta=st.text_input('CTA',msg['cta_text'],key='msg_cta_'+persona+v['id'])
                    emails[persona]=dict(subject=sub,preview_text=pre,body=body,cta_text=cta)
            if st.form_submit_button('Save new immutable content version'):
                updated=content|{'blog_title':blog_title,'blog_draft':blog,'newsletters':emails,
                                 'evidence_refs':[x.strip() for x in reftext.split(',') if x.strip()]}
                r=safe_run(lambda:edit_draft(current_campaign,updated))
                if r:st.success('New version generated; all previous approvals invalidated');st.rerun()
        st.divider()
        token=st.text_input('Local reviewer token',type='password',key='reviewer_local')
        claim_text=st.text_input('Evidence claim sentence (exact text, optional)')
        evidence_source=st.text_input('Source reference / reviewer attestation (not independent verification)')
        if st.button('Register local reviewer evidence'):
            r=safe_run(lambda:attest_claim(claim_text,evidence_source,token))
            if r:st.success(f'Evidence ID: {r}. Add this ID to content.evidence_refs in a new revision to request exact-match clearance.')
        feedback=st.text_area('Reviewer feedback (will be redacted for email patterns)')
        if st.button('Save reviewer feedback'):
            r=safe_run(lambda:record_feedback(current_campaign,v['id'],feedback,token))
            if r:st.success('Review note saved')
        left,right=st.columns(2)
        if left.button('Approve current version'):
            r=safe_run(lambda:decide(current_campaign,token,'APPROVED'))
            if r:st.session_state['approval_'+current_campaign]=r['approval_id'];st.success('Approved exactly this version')
        if right.button('Reject current version'):
            r=safe_run(lambda:decide(current_campaign,token,'REJECTED'))
            if r:st.warning('Rejected; no dispatch permitted')
        aid=st.text_input('Approval ID',value=st.session_state.get('approval_'+current_campaign,''))
        if st.button('Execute LOCAL DRY-RUN only'):
            r=safe_run(lambda:dispatch(current_campaign,aid))
            if r:st.json(r);st.success('0 live emails sent')

with t4:
    st.subheader('Business evidence and auditability')
    if not current_campaign:st.info('Create a campaign first.')
    else:
        r=inspect(current_campaign)
        st.caption('All engagement records here are SYNTHETIC; no conversion or live email was measured.')
        st.markdown('#### Metric provenance');st.dataframe(r['metrics'],use_container_width=True)
        st.markdown('#### Planner and tools');st.dataframe(r['tool_trace'],use_container_width=True)
        st.markdown('#### Product events');st.json(r['product_telemetry'])
        st.markdown('#### Approval and workflow audit');st.dataframe(r['audit'],use_container_width=True)
        if st.button('Retry content export from database'):
            r2=safe_run(lambda:retry_export(current_campaign))
            if r2:st.success('Exported: '+r2['path'])

with t5:
    st.subheader('Human feedback memory is NOT factual product evidence')
    st.dataframe(read_lessons(20),use_container_width=True)
    st.info('Feedback is historical reviewer preference. Treat as untrusted data; it never grants tool permissions or proves customer outcomes.')
