# V4 Evidence Governance & Claim Review

## Why a provenance label is not proof
V3 stored `CSV_DEMO` and `NO_CAMPAIGN_HISTORY` evidence labels. V4 adds a reviewer-attested exact-text claim registry. Neither mechanism guarantees a claim is factual; no verified external identity, independent documentary assessment or live lookup was used.

## Registry fields and policy
Each `claim_evidence` row has ID, exact claim, normalized claim, source reference, `LOCAL_REVIEWER_ATTESTATION`, reviewer ID, timestamp and optional expiry. Only holders of the local demo reviewer token can insert a row. Sentence matching is exact after whitespace/case normalization to avoid citation laundering across different statements.

## Risk-screening classes
- Quantified outcomes tied to revenue, cost, productivity, ROI or conversion.
- Guarantees such as `guarantee`, `proven to` or impossible zero-risk profit promises.
- SOC 2 / ISO 27001 / HIPAA / GDPR credential assertions.
- Claimed regulatory approval, endorsement, customer volume and market leadership.

## Decision flow
1. Extract conservative suspicious sentences from blog/email fields.
2. Check whether each flagged sentence has an exact currently valid, reviewer-attested citation ID attached to the content version.
3. If ANY flagged claim lacks a citation: `NEEDS_EVIDENCE`, `passed=false`, no approval.
4. If all flagged claims have attestations: `REVIEWER_ATTESTED`; final human review is still required. **This is not `VERIFIED`**.
5. Any edit yields a new immutable version and invalidates earlier content approval.

## Limits and future work
Regex cannot detect all implied product claims, nuanced AI hallucinations, misleading paraphrases, or jurisdiction-dependent marketing law. Reviewer attestation is not a legal safe harbor. Future beta should use an approved Product Facts Library with validity dates, official source URLs, claim-level entailment, review escalation, human evidence check, deletions and access governance. Real high-risk compliance copy should undergo appropriate specialist review.
