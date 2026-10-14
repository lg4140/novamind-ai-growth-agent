# Security and responsible use

This repository is an **offline-first educational prototype**, not a production
marketing system. It must never be connected to real customer data or used to
send live marketing messages in its current form.

- The `LOCAL_DEMO_REVIEW_TOKEN` is **not** a real identity or permissions system.
- Reviewer-submitted claim sources are **not** independently fact-checked.
- Claim scanning is heuristic; it is not legal, compliance, or brand approval.
- No real HubSpot sending, unsubscribe-list management or customer consent enforcement exists.
- Historical or runtime databases, logs, keys, `.env`, customer exports and generated
  artifacts must not be committed. `.gitignore` is a convenience, not a substitute
  for checking `git status` and `git diff --cached`.

## Before making the repository public

1. Run `python scripts/public_release_check.py` and review `git status`.
2. Verify that the six demo addresses end in `@example.com`.
3. Never commit real OpenAI, HubSpot or reviewer credentials. Keep `.env` locally.
4. If secrets were accidentally committed, **revoke/rotate them immediately**;
   deleting a file in a later commit is not enough to remove historical exposure.

For potential vulnerabilities, avoid posting credentials or personal data in public issues.
