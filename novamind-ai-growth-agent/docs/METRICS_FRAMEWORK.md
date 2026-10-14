# V4 Product & Agent Metrics Specification

## North Star
**Time to Approved Campaign (TAC)**: `approval_decided_at(first APPROVED) - brief/proposal_started_at` (wall-clock). Use median/p75, report manual vs AI mode, goal complexity and human-review wait time separately. V4 can compute this elapsed metric from `plan_sessions`/`campaigns` and approval events. Active human time is NOT currently measured.

## Guardrails
Unauthorized effects (target 0), stale-approval acceptance (target 0), unresolved-claim approval count (target 0 on evaluated corpus), quality false negative / false positive rate on human-rated content, source-provenance errors (target 0). Do not use a synthetic open rate as the product North Star.

## Operational agent metrics (future instrumentation)
Model tool-selection accuracy, task completion, retry correctness, trace coverage, p50/p95 tool duration, token cost per accepted plan and per approved campaign, number of human corrective interventions, agent-turn distribution. Optional online tools have not been benchmarked in V4.

## Business outcomes (future, not current)
Qualified demo signups from verified conversion events, agreed attribution window, consented contacts and adequately powered A/B tests. `SYNTHETIC` events are exclusively for testing software paths, not measured business lift.

## Current event names
`draft_ready`, `human_edit_completed`, `approval_decided`, `dry_run_completed`, `reviewer_feedback_saved`. Some other names have defined schemas but not instrumented call sites. Missing fields, such as USD model usage or active human minutes, must remain null.
