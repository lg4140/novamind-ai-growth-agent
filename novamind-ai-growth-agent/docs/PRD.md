# NovaMind V4 — Product Requirements Document (PRD)
**Version:** V4.0 | **Date:** 2026-10-14 | **Status:** Implemented local prototype with future-only agent and production capabilities explicitly distinguished.

## 1. Executive summary and product hypothesis
NovaMind is a B2B marketing workflow copilot for growth managers at small SaaS and creative-agency-facing companies. A campaign manager defines a measurable goal, audiences, topic and constraints. The system proposes an inspectable plan, records human edits, generates goal-aligned content, flags suspicious claims, gates the immutable content version for review, performs only a consent-free local simulation, and retains feedback for later human-visible planning. Hypothesis: users will save active preparation time without degrading approval quality. **No user research or measured time savings substantiate this yet.**

## 2. Users, recipients and JTBD
| Role | Access/need | Success criterion |
|---|---|---|
| Growth Manager (primary user) | Create campaigns; inspect and edit segment-level plan | Goals and constraints appear in the actual artifacts |
| Content Marketer | Revise blog and email copy by segment | Versioned edits without stale approval reuse |
| Reviewer (local demo role) | Inspect claims and exact content | Can reject unsubstantiated copy and unauthorized dispatch |
| Founder (secondary user) | Evaluate cost, safety and potential value | Clearly labeled synthetic vs verified outcomes |
| Ops Lead / Creative Director / Freelancer | Campaign recipients, **not** product users | Segment-specific messaging (hypotheses, not researched preference) |

## 3. End-to-end journey and state model
`Brief → PROPOSED plan → editable revision → CONFIRMED plan → versioned REVIEW draft → APPROVED or REJECTED → DISPATCHING → COMPLETED`. The durable `plan_sessions` table holds plan revision and associated campaign; `versions` is immutable and stores plan link, content SHA-256, audience SHA-256 and QA. `APPROVED` is possible only after separate reviewer-token verification and passing automated gates. Live sending remains disabled. Revisions after a completed local execution require a new campaign.

## 4. V4 functional requirements and status
| ID | Priority | Requirement | Acceptance / proof | Status |
|---|---|---|---|---|
| FR-01 | P0 | Plan-first create and confirm | Cannot generate without a confirmed plan; versions are persisted | Implemented + tested |
| FR-02 | P0 | Optimistic plan edit | Stale revision rejected; scope and constraints cannot be weakened | Implemented + tested |
| FR-03 | P0 | CTA constraints | Deny blocked term, fail closed on unsupported free text | Implemented for defined patterns |
| FR-04 | P0 | Schema uniqueness and long input | Exactly one angle/segment; long valid topic works downstream | Implemented + tested |
| FR-05 | P0 | Risk-claim detection | Quantified outcomes + SOC 2/ISO etc flagged | Implemented heuristic + tested |
| FR-06 | P0 | Evidence ledger | Exact claim/reviewer/source linked to content version | Implemented as local attestation only |
| FR-07 | P0 | Final content approval | Version/audience/hash checks; local reviewer token | Implemented + tested, no RBAC |
| FR-08 | P0 | Concurrent synthetic dispatch | Exactly one execution, no duplicates | Implemented + tested |
| FR-09 | P1 | Reviewer learning | Feedback redaction, local memory, untrusted source label | Implemented + tested |
| FR-10 | P1 | Product instrumentation | Event trail, elapsed approval time, missing usage explicitly null | Partially implemented; no active-time tracking |
| FR-11 | P1 | Interactive workbench | Plan editing, reviewer action, trace, evidence, metrics | Code delivered; no browser QA study |
| FR-12 | P1 | Agent model planning | Optional `agents` SDK, model-selected read-only tools | Code present; **not run online** |
| FR-13 | P1 | Real agent safety evaluation | Execute actual model/tool trajectories with fault injection | **Not implemented**, 30 scenario definitions only |
| FR-14 | P2 | Verified CRM event integration | Auth + permissions + consent + real metrics | **Not implemented** |
| FR-15 | P2 | Product value/ROI experiment | Controlled manual/V1/V3/V4 comparison | **Not conducted** |

## 5. Behavioral requirements and negative cases
- An unsupported hard/business constraint must return a validation error **before** model generation, never be silently ignored.
- Plan confirmation must **not** authorize dispatch. Final email version approval is separate.
- An LLM suggestion can affect content but cannot grant reviewer identity, attest evidence, or change execution policy.
- A stale plan revision is rejected; a modified content version invalidates earlier approval.
- Synthetic opened/clicked counts are never shown as real customer behavior, conversion or uplift.
- Factual/certification claims missing an exact reviewer-attested reference remain BLOCKED; attestation is not independent fact verification.
- A multi-request local simulation must not produce duplicate deliveries or segment metrics.

## 6. UX details and scope
Tabs: **Brief → Proposed Plan → Draft/Review → Evidence Metrics/Traces → Lessons**. Per-Persona message angles can be edited before plan confirmation, and emails can be edited afterward. Diff view, true rich text, streaming Agent conversations and hosted sessions are future UX backlog, not current features.

## 7. North Star, guardrails and instrumentation
**Proposed North Star:** median Time to Approved Campaign (validated/proposed brief to first approved content version), reported with p75 and source/mode breakdown. V4 records wall-clock approximate elapsed time, not active human editing minutes. **Guardrails:** unapproved dispatch count=0, unsupported claim acceptance count=0 on the explicit eval corpus, reviewer rewrite rate, QA false-positive/negative analysis and corrupted versions count=0. **Unit economics:** API cost/run, AI cost/approved campaign, active human minutes saved; currently missing and must display as unavailable rather than estimated.

## 8. Release acceptance gates
**Local V4 prototype:** deterministic tests all pass, provenance respected, no live external effects, plan- and content-level reviewer gates. **Agent alpha:** connect opted-in model; execute 30 real model scenarios with tool interception and trace-based adjudication; require zero critical safety violations. **Product beta:** usability sessions, measured operator time, brand-approved evidence retrieval, real authentication and permissions. **Production pilot:** consent/opt-out enforcement, validated HubSpot channel and API version, durability/retry/reconciliation, redaction and deletion controls, incident response and monitoring.

## 9. Explicit exclusions and known limitations
No broad semantic natural-language constraint solver. No independent factual verification, automatic web-grounded legal assertions, or automatic promotion of reviewer feedback to facts. No true autonomous observe–act loop after results, no hosted RBAC, no live sends, no verified growth outcomes, no priced unit economics. Reviewer-only locally attested evidence is a workflow signal, not substantiation in law or a replacement for source validation.
