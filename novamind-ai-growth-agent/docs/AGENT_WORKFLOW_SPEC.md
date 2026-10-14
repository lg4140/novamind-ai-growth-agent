# V4 Agent Workflow, State, Tools & Recovery Specification

## State graph
`PROPOSED (edit in place with immutable revision history) → CONFIRMED → DRAFTED/REVIEW → APPROVED | REJECTED → DISPATCHING → COMPLETED`. `FAILED` is a controller recommendation state, not a fully checkpointed LLM execution engine. `plan_sessions` is persisted separately from campaign content; optimistic revision checks reject stale proposals.

## Planner choice
`planner=demo` creates a deterministic `CampaignPlan` using CSV counts, history and policy. It does NOT autonomously select tools. `planner=agent` uses OpenAI Agents SDK and four read-only tools: audience counts, local campaign history, execution policy, redacted reviewer lessons. Integration code exists but has not been run online. Tools have no ability to write evidence, approve content, or dispatch.

## Structured contracts
`CampaignBrief` validates goal/topic/KPI, unique allowed audiences and supported constraints; `CampaignPlan` covers EXACTLY one message angle per selected Persona, matching business inputs and approved constraint policy; `CampaignContent` enforces typed newsletter fields and optional reviewer-attested evidence IDs.

## Deterministic next-action controller
`next_action(PROPOSED)` waits for human plan confirmation; `CONFIRMED` allows content generation; `REVIEW + unresolved claims` requests evidence; after revision budget exhausted it requests replan/escalation; `APPROVED` only proposes local DRY_RUN, and backend independently enforces all hashes and tokens; terminal states HALT. The controller is a decision helper, not a deployed autonomous loop.

## Partial failure and restoration
Plan sessions are durable in SQLite; user can re-open a proposed or confirmed session. Exactly one draft is committed per confirmed plan session even with concurrent requests. JSON export is optional; canonical content is in the DB and can be re-exported using `retry-export`. External network retries and resumable multi-turn LLM sessions are NOT supported in V4.

## Critical negative cases
- Unsupported constraints fail closed.
- A malformed/duplicated message plan fails schema validation.
- A stale plan cannot be confirmed or overwritten.
- A confirmed plan does not waive final content approval.
- User-provided reviewer feedback is untrusted, not prompt authority.
- Failed structural or unverified claim checks block content approval.
- Synthetic engagement never becomes real conversion evidence.
