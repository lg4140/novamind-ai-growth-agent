# V4 UX Interaction Specification

## Experience principles
One clear business goal per campaign; show model/tool provenance; surface meaningful decision moments; never confuse proposed plan, content approval or local simulation; explain why automation stopped and what a human can do next.

## Proposed implementation
1. Brief tab: Goal, Topic, Personas, KPI, Brand voice, explicitly supported constraints and planning mode.
2. Plan tab: Saved session and revision; editable Persona problem/value proposition/CTA; compare actual plan with source labels. Save as new revision, then explicit Confirm.
3. Draft tab: Blog and email forms; Save creates immutable content version. Risk claims show `NEEDS_EVIDENCE` and block reviewer approval; add an exact evidence reference by reviewer attestation and resubmit a new version.
4. Review tab (co-located): Local reviewer token, approve/reject the exact version, then local-only simulation with separate Approval ID.
5. Analytics tab: Synthetic source label, tool trace, timeline and audit. Lessons tab: explicitly untrusted reviewer feedback.

## Acceptance and pending UX
Code path implemented in `ui/v4_dashboard.py`; browser-level test not completed. Human-friendly plan diffs, collaborative comments, rich text, accessibility review, multiuser sessions and full active-time observation remain backlog items.
