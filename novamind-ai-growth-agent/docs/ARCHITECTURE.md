# NovaMind V4 — Technical Architecture and Provenance

## V3 lineage and V4 changes
V4 retains the tested V3 `campaigns`, `versions`, `approvals`, `execution_runs`, `deliveries`, `metrics`, `insights`, `agent_runs`, `tool_calls` and `audit_events` model. Original V3 ZIP is retained only in the separate full V4 delivery archive, not in this public source repository. New V4 modules are additive; the V3 CLI remains usable.

## End-to-end process
```
CampaignBrief + validated constraints
    → agent.plan [demo=deterministic / agent=opt-in LLM read-only tools]
    → plan_sessions.PROPOSED + plan_revisions
    → user edits message angles / constraints remain immutable
    → plan_sessions.CONFIRMED (NOT execution approval)
    → content.demo_content | content.llm_content
    → claims and structural review (+ exact-match reviewer evidence lookup)
    → campaign + immutable content VERSION → REVIEW
    → human final content reviewer token → APPROVED | REJECTED
    → dispatch.execute_dry_run (BEGIN IMMEDIATE, atomic local only)
    → deliveries:SYNTHETIC + metrics:SYNTHETIC + HYPOTHESIS insight
    → product telemetry + audit + reviewer feedback memory
```

## Authority boundary
LLM inputs may influence draft planning and message content but NEVER alter `DRY_RUN`, approval requirement, recipient ceiling, actual reviewer identity, evidence attestation authority, SQL execution constraints or customer consent. All side effects are handled by deterministic backend policy. Local token is merely a demo stand-in, not SSO.

## Persisted state
| Table | Scope and invariant |
|---|---|
| plan_sessions | Proposed plan current revision/state; one associated campaign on draft generation |
| plan_revisions | Immutable historical plan JSON, UNIQUE(session,revision) |
| claim_evidence | Exact claimed sentence, reviewer-supplied citation, attested time, expiration |
| reviewer_feedback | Redacted text, version/actor, untrusted preference label |
| product_events | Source-less PIIs suppressed by allowlisted metadata; lifecycle events |
| plans / versions | Plan-to-content link, content hash, audience hash, immutable revision |
| approvals / execution_runs | Approval bound to hashes; local simulation protected by SQLite immediate transaction |
| metrics / insights | Source type SYNTHETIC / HYPOTHESIS, no conversion claims |

## Constraint design
`compile_constraints` currently supports `No live marketing sends` and `Avoid the word X in any CTA` variants. Unsupported prose causes an explicit validation error. CTA term checks are repeated in the Plan contract and content review. This strict narrow design is safer than presenting unbounded constraint understanding with no implementation.

## Evidence safety
`extract_claims` scans quantified performance/certification/endorsement/customer-quantity patterns. For each identified exact sentence, `evidence_for_claim` checks supplied evidence IDs against the local reviewer ledger. No model can insert attestations. This is reviewer provenance, NOT independent validation. Detection is incomplete and may produce false positives and false negatives; launch requires reviewed brand evidence and separate human judgement.

## Memory and untrusted data
`record_feedback` saves reviewer text with basic email/secret redaction; `read_lessons` labels it `REVIEWER_FEEDBACK_NOT_FACT`. Model planning can request that read-only tool. This is not an instruction stream, source of factual product claims, or automatic permission. Full privacy deletion, retention lifecycle and stronger redaction are not implemented.

## Local atomicity vs external delivery
A DB transaction covers claim, local synthetic deliveries, synthetic metrics and completed state. Concurrent local requests produce one execution. This does NOT establish exactly-once delivery over HubSpot or network retries. Production requires durable outbox, idempotency key accepted by provider, suppression checks, reconciliation, timeout and recovery logic.

## Instrumentation and cost
`product_events` contains lifecycle events and source-masked metadata. Time to first approval can be calculated using plan session or campaign start. Human active-time and model dollars remain `null`. The optional LLM SDK can produce tool traces, but online instrumentation/pricing has not been benchmarked.

## UX layer
`ui/v4_dashboard.py` provides stages and tools. It has not had browser automation, accessibility testing, multi-user testing, performance load testing or production security review. Do not treat a code-level UI as production verified.
