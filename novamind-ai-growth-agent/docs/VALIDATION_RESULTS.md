# V4 Validation Results — Executed, Source-Backed

**Date:** 2026-10-14. **Executed command:** `python evals/run_offline_evals.py` (runs actual pytest subprocess and writes JUnit XML). **Report:** generated locally at `reports/offline_engineering_results.json` by the evaluation script (ignored in Git); GitHub Actions runs the same tests on each push.

## Result
**53 passed, 0 failed, 0 skipped** in the local deterministic suite (32 V3 regression cases + 21 new V4 tests), with isolated temporary SQLite DB for each test.

## Newly tested properties
- Proposed plan and draft creation are separate. Plan confirmation is required; stale revision confirmation blocked.
- Human message-angle edits persist and flow into generated campaign content.
- A changed plan cannot weaken audience, KPI, goal, or compiled business constraints.
- Duplicate MessageAngle entries are rejected by shared schema.
- `Avoid the word demo in any CTA` changes the CTA and post-generation QA enforces it.
- Unrecognized natural-language constraints cause validation failures rather than being silently dropped.
- Concurrent generate requests for one confirmed plan produce only one campaign.
- Long valid Topic strings do not violate newsletter Subject length contracts.
- SOC 2 / regulatory endorsement / customers-in-thousands claims are flagged.
- Reviewer attestation requires valid local token; exact claim match is required to lift deterministic hold.
- Reviewer feedback hides simple email strings and remains untrusted, not factual evidence.
- Plan confirmation never authorizes Dry-run; a separate content approval is required.
- Telemetry preserves missing real USD usage and active-human-minutes as null.
- Failed export can be retried from the canonical database.

## Pre-existing V3 regressions re-run
Version/audience hashes, stale approval refusal, atomic thread-concurrent execution, synthetic provenance, quantity outcome claims, reviewer token validation, input segmentation and no live sends.

## NOT tested and NOT claimed
**0 real OpenAI model-agent evaluation runs out of 30 planned scenarios; 0 real HubSpot integration calls; 0 real marketing messages; 0 real conversion measurements.** No measured improvement in productivity, conversion, reviewer workload or model cost. UI browser-level QA, SSO, data deletion, tenant isolation, independent claim verification and network failure-recovery remain open.

## Interpreting test quality
These are unit/integration tests of deterministic Python code and SQLite transaction boundaries, **not** evidence that an LLM reliably chooses tools or follows prompts under attack. The locally generated JUnit XML is the test runner evidence; this document records the executed suite, not manual PASS labels.
