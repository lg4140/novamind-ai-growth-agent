# V4 Product Decision Log

| Decision | Rationale | Tradeoff / evidence |
|---|---|---|
| Keep one orchestrated planning Agent, not a swarm | Fewer handoff failure modes; easier evaluation | Real agent autonomy still limited; evaluate incrementally |
| Plan confirmation separate from content approval | Reduces unreviewed audience and strategy surprises | Adds a user step; usability needs measurement |
| Reject unknown free-text constraints | Safer than falsely claiming compliance | Narrow grammar; requires UI help/examples |
| Evidence attestation requires exact sentence + reviewer token | Supports citation provenance and blocks obvious unsupported claims | Attestation not independent verification, potential false positives |
| Reviewer feedback is untrusted memory | Allows reuse without treating comments as commands/facts | No semantic ranking/vector DB or privacy deletion yet |
| SQLite as source of truth | Reproducible local demonstration and simple atomicity | Not suitable as proof of distributed delivery semantics |
| Live marketing send disabled | Safe portfolio demonstration with no lawful-consent assumptions | No real conversions or CRM operational validation |
| Preserve V3 one-step workflow | Backward compatibility while V4 plans evolve | Two CLI entrypoints need documentation |
| Report unavailable costs as null | No invented unit economics | PM ROI cannot be claimed before instrumenting model usage |
