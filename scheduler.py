"""
Scheduler for monthly bond purchase reminders.

Designed to run as a cron job on any cloud platform.
Loads the plan, checks if a purchase is due, and sends the reminder email.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from planner import generate_investment_plan
from emailer import send_reminder_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

PLAN_FILE = Path(__file__).parent / "plan.json"


def load_or_create_plan() -> dict:
    """Load saved plan from disk, or generate a new one."""
    if PLAN_FILE.exists():
        log.info("Loading existing plan from %s", PLAN_FILE)
        with open(PLAN_FILE) as f:
            return json.load(f)

    log.info("No saved plan found. Generating new plan.")
    rate = float(os.environ.get("TBILL_RATE", "0.045"))
    total = float(os.environ.get("TOTAL_INVESTMENT", "100000"))
    batches = int(os.environ.get("NUM_BATCHES", "10"))
    start = os.environ.get("START_DATE")

    plan = generate_investment_plan(
        total_investment=total,
        num_batches=batches,
        start_date=start,
        annual_rate=rate,
    )

    with open(PLAN_FILE, "w") as f:
        json.dump(plan, f, indent=2)
    log.info("Plan saved to %s", PLAN_FILE)

    return plan


def run_monthly_check():
    """
    Main entry point for the cron job.
    Checks if a purchase is due this month and sends a reminder email.
    """
    log.info("Running monthly bond purchase check — %s", datetime.now().isoformat())

    plan = load_or_create_plan()

    today = datetime.now()
    due_this_month = None
    for p in plan["purchases"]:
        pd = datetime.strptime(p["purchase_date"], "%Y-%m-%d")
        if pd.year == today.year and pd.month == today.month:
            due_this_month = p
            break

    if not due_this_month:
        log.info("No purchase due this month. Skipping.")
        return

    log.info(
        "Purchase due: Batch #%d — $%s on %s",
        due_this_month["month_number"],
        f"{due_this_month['investment_amount']:,.2f}",
        due_this_month["purchase_date"],
    )

    try:
        result = send_reminder_email(plan)
        log.info("Email result: %s", json.dumps(result))
    except Exception as e:
        log.error("Failed to send reminder email: %s", e)
        raise


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_monthly_check()
