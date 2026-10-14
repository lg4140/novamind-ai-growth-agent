# V4 Security, Privacy and Product Risk Register

| Severity | Risk | V4 mitigation | Residual limitation |
|---|---|---|---|
| Critical before production | Unauthorized real sends | No live-send implementation, local transaction guard | No real CRM consent/permissions system exists |
| High | Approval bypass | Local secret token, immutable version+audience fingerprints | Token is not hosted identity, SSO, roles or separation of duties |
| High | Unsupported marketing claims | Enhanced patterns, exact reviewer-attested evidence | Not independent verification; nuanced hallucinations possible |
| High | Prompt injection in reviewer memory | Memory tool labels untrusted; no write/approval tools to LLM | No real prompt-injection evaluation has been executed |
| High | Reviewer note PII leakage | Basic email/token redaction and truncated length | Incomplete PII detection, retention/deletion not implemented |
| High | Free-text constraint ambiguity | Fail closed for unsupported input | Narrow supported grammar; user experience cost |
| Medium | Duplicate local execution | BEGIN IMMEDIATE + UNIQUE execution/metrics | Network retries/distributed outbox not implemented |
| Medium | Export failure after DB write | DB is authoritative, retry-export | No automated async recovery job |
| Medium | Agent token/cost runaway | `max_turns=7` in optional Agent path | No live token-budget or cost-stop watchdog |
| Medium | Malicious upload / tenant leakage | No upload ingestion or multi-tenant deployment | No access controls for hosting |

## Deployment blockers
Authenticated accounts and reviewer permissions, explicit marketing opt-in and unsubscribe suppression, verified platform API scopes, audit access control, encryption/key management, rate limit/reconciliation, monitoring/on-call, retention and deletion requests, legal claim sign-off, independent adversarial evaluation. Local unit tests do NOT clear these gates.
