# V4 Claim Verification Contract

Rule-based risk extraction is implemented in `app/evidence.py`: quantified marketing outcomes, guarantee terms, certifications (SOC 2 / ISO 27001), regulatory endorsements and customer volume. Content includes `evidence_refs`; each claim must match a reviewer-attested sentence in `claim_evidence` without expiry, or approval is blocked.

This is deliberately called **claim screening + reviewer provenance**, not independent truth verification. A source reference entered by a reviewer is not automatically checked against the official source. A launch-quality system must verify source authenticity, date, relevance, claim entailment and legal compliance under human oversight.
