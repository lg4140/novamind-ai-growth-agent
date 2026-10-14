# V4 Unit Economics — Measurement Spec, Not a Financial Claim

## Economic hypothesis
NovaMind may reduce growth-manager active preparation time by reusing plan templates, assisted edits and centralized review. No real operator timings or payment data exist yet. An Agent may also increase API and review costs; test marginal value against deterministic V3.

## Cost model
`Total_cost_per_approved_campaign = model_input_cost + model_output_cost + tool_service_cost + infrastructure_cost + human_review_time_cost + failure_retry_cost`.

## Required raw fields
Agent model/version, measured prompt/completion tokens, verified billed USD rate and currency, tool calls/duration, review active minutes (measured), number of content revision cycles, task status and accepted output. Never present estimates as invoices or leave unlabeled sample prices in the report.

## Study design
Recruit willing workflow testers, hold Task brief and brand facts constant, randomize or counterbalance manual/V1/V3/V4 order, capture screen/active-time separately from approval waiting time. Have blinded reviewers score factuality, persona relevance and actionability. Only compute confidence intervals after collecting observations.

## Status
`app.telemetry.product_event_summary` records event timestamps and elapsed approval time, but returns `human_active_minutes=null` and `agent_cost_usd=null`. No real cost savings, conversion growth or ROI can be claimed.
