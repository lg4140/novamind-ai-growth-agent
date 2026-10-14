"""Reproducible demonstration in an ephemeral directory; zero external sends.

No real API credentials are required. Only aggregate synthetic counts are printed.
"""
import json
import tempfile
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app import agent, contacts, content, db, dispatch, evidence, memory_service
from app.stateful import propose, confirm_plan, generate_from_confirmed
from app.workflow import decide, dispatch as run_dispatch


def main():
    with tempfile.TemporaryDirectory(prefix="novamind_public_demo_") as temp:
        cfg = replace(
            settings,
            db_path=Path(temp) / "demo.sqlite3",
            output_dir=Path(temp) / "content",
            local_demo_review_token="ephemeral-offline-review-token",
            contact_hmac_key="ephemeral-offline-hmac-key",
            dry_run=True,
            max_recipients=100,
        )
        # Existing V4 modules capture settings at import time; isolate these references
        # without altering the original engine or writing to the repo.
        for module in (agent, contacts, content, db, dispatch, evidence, memory_service):
            module.settings = cfg
        proposed = propose({
            "goal": "Prepare a cautious workflow-automation campaign",
            "topic": "AI workflow automation for small studios",
            "primary_kpi": "email_engagement",
            "audience": ["freelancer"],
            "constraints": ["No live marketing sends", "Avoid the word demo in any CTA"],
        }, planner="demo")
        confirmed = confirm_plan(proposed["session_id"], proposed["revision"])
        drafted = generate_from_confirmed(proposed["session_id"], mode="demo")
        approval = decide(drafted["campaign_id"], cfg.local_demo_review_token, "APPROVED")
        summary = run_dispatch(drafted["campaign_id"], approval["approval_id"])
        assert summary["live_emails_sent"] == 0
        assert summary["synthetic_recipients_prepared"] == 2
        assert confirmed["status"] == "CONFIRMED"
        print(json.dumps({
            "mode": "DETERMINISTIC_OFFLINE_PREVIEW",
            "plan_created": bool(proposed["plan"]),
            "plan_confirmed": True,
            "draft_generated": drafted["status"] == "REVIEW",
            "content_approved": True,
            "synthetic_recipients_prepared": summary["synthetic_recipients_prepared"],
            "live_emails_sent": summary["live_emails_sent"],
            "real_agent_model_tests": 0,
        }, indent=2))


if __name__ == "__main__":
    main()
