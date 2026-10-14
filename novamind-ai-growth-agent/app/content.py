"""Plan-driven content; offline copy is synthetic and goal-sensitive, LLM copy is opt-in."""
import json
import os
from .config import settings
from .schemas import CampaignContent, Newsletter, LLMCampaignContent

PARAGRAPHS = [
 'Before adopting new workflow software, an agency should map current responsibilities, approval paths, and repetitive coordination work. A clear baseline makes it possible to see where a small trial might be worthwhile and where human decision-making is essential.',
 'Start by choosing one recurring activity with a well-defined beginning and end. Record who owns each handoff, what information is needed, and how a failed step will be corrected. A narrow pilot is easier to evaluate than a broad automation promise.',
 'Content for different roles should recognize that people care about different outcomes. An operations manager may ask about predictable handoffs. A creative leader may want fewer interruptions without losing editorial control. A solo operator may prefer minimal configuration and reversible experiments.',
 'Write down assumptions before collecting data. If a potential benefit comes from a fictional demonstration or a small synthetic sample, it belongs in a hypothesis register, not in an outcome claim. The team should request verifiable product information before making a factual assertion.',
 'An email call to action needs to match the reason that a recipient is hearing from the company. If the goal concerns demonstration requests, ask readers whether they want a workflow demonstration. If the goal concerns learning, offer a helpful explanation or practical checklist instead.',
 'Human review is a meaningful part of campaign quality rather than an administrative afterthought. Reviewers should see the full message, selected audience, known uncertainties, and exact version. Changes made after approval require another review, even if the changes look small.',
 'Keep campaign operations separate from customer behavior. A locally prepared message is not a delivered email. A generated open or click event is not a real person engaging. The dashboard must label these categories and prevent synthetic examples from being counted as verified business performance.',
 'Use a small number of transparent measures. A campaign-preparation time measure can show whether the workflow saves operator effort, while revision counts help reveal where the writing needs improvement. The business outcome must still be validated using real, consented events.',
 'If the pilot produces mixed results, report the limitations instead of presenting a success story. Investigate sample size, event definitions, missing data, and differences in contact selection before suggesting another test. An informed next experiment is often more valuable than an exaggerated conclusion.',
 'A credible rollout plan should also specify when to stop. Record errors, reviewer feedback, tool costs, and decision points. Use the saved evidence to revise the next campaign brief, while keeping the model away from unauthorized sends or other irreversible changes.',
]

def demo_content(brief,plan):
    """Topic + goal + KPI + selected persona messaging actively change copy."""
    perspective=' '.join(f'For {m.persona.replace("_"," ")}, prioritize {m.customer_problem}.' for m in plan.messaging)
    lead=(f'Topic: {brief.topic}. Campaign objective: {brief.goal}. The primary KPI is '
          f'{brief.primary_kpi}. This is an illustrative planning brief, not evidence of customer outcomes. '
          f'{perspective} The tone is {brief.brand_voice}.')
    draft=lead+'\n\n'+'\n\n'.join(PARAGRAPHS)
    nl={}
    for m in plan.messaging:
        nl[m.persona]=Newsletter(
          subject=(f'{brief.topic}: {m.customer_problem}')[:150].rstrip(' :,-'),
          preview_text=(f'{m.value_proposition}. A practical, reviewer-guided introduction.')[:250].rstrip(' ,;'),
          body=(f'Hello,\n\nOur campaign objective is {brief.goal}. '
                f'If {m.customer_problem} is a recurring challenge, consider a reversible pilot. '
                f'{m.value_proposition}. First document the baseline, check your team\'s consent '
                f'and existing tools, then review a single workflow with a responsible owner. '
                f'No outcome is promised and no customer result is being asserted.\n\n'
                f'Next step: {m.call_to_action}.'),
          cta_text=m.call_to_action)
    return CampaignContent(topic=plan.topic,blog_title=f'{brief.topic}: a practical, evidence-aware campaign guide',
       blog_outline=['Define audience problems','Set measurable campaign intent','Pilot a safe workflow',
                     'Review evidence and adjust'],blog_draft=draft,newsletters=nl)

def llm_content(brief,plan):
    if not settings.api_key:raise RuntimeError('OPENAI_API_KEY is required for LLM content')
    from openai import OpenAI
    client=OpenAI(api_key=settings.api_key)
    response=client.responses.parse(model=settings.openai_model,
         input=[{'role':'system','content':(
            'You write for a fictional B2B startup. Use the exact approved campaign plan. '
            'Write a 400–600 word blog, a tailored newsletter for every selected persona and NO other persona. '
            'Blog must mention campaign goal verbatim. CTA text must match the plan exactly. '
            'Avoid invented features, statistics, ROI, client stories, prices, and product claims. '
            'Real campaign results and approvals do not exist.')},
            {'role':'user','content':json.dumps({'brief':brief.model_dump(),'plan':plan.model_dump()},ensure_ascii=False)}],
         text_format=LLMCampaignContent,max_output_tokens=4000)
    if response.output_parsed is None:raise RuntimeError('Model did not return valid structured output')
    p=response.output_parsed
    if len({x.persona for x in p.newsletters})!=len(p.newsletters):raise ValueError('Duplicate persona in LLM content')
    result=CampaignContent(topic=p.topic,blog_title=p.blog_title,blog_outline=p.blog_outline,
       blog_draft=p.blog_draft,newsletters={n.persona:Newsletter.model_validate(n.model_dump(exclude={'persona'})) for n in p.newsletters})
    return result

def store_json(campaign_id,version_id,content,mode):
    """Optional export: database is canonical, partial file is never presented as authoritative."""
    settings.output_dir.mkdir(parents=True,exist_ok=True)
    dest=settings.output_dir/f'{campaign_id}_{version_id}.json'
    tmp=dest.with_suffix('.tmp')
    payload={'source':mode,'campaign_id':campaign_id,'version_id':version_id,'content':content.model_dump()}
    tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    os.replace(tmp,dest)
    return dest
