# V4 Agent Evaluation Results — Evidence Boundary

## Deterministic executed engineering suite
**53 passing tests, 0 failures** in the original V4 release. In this public repo, rerun `python evals/run_offline_evals.py` to regenerate ignored JUnit XML at `reports/offline_pytest_junit.xml`; details in `docs/VALIDATION_RESULTS.md`.

## Real-model LLM Agent scenarios
**0 of 30 scenarios actually run**. The `evals/test_cases.jsonl` corpus is a spec, not evidence of model behavior. `planner=agent` is optional unverified SDK integration code; no network test, model version freeze, run-to-run variance, prompt-injection measurements or live cost data exists for this release.

## Next execution method
Supply an instrumented OpenAI sandbox, isolated fake tools and fixture data; run each in-scope case, inspect tool trace and forbidden actions, capture prompt/SDK model versions, track cost/time, grade outcomes and critical safety invariants. Cases that need an unavailable external send/consent system must be marked NOT_RUN_UNSUPPORTED, never PASS.
