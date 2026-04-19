"""
Run this at the start of any month to see exactly what to buy and how.

Usage:
    python3 buy_now.py              # shows this month's purchase
    python3 buy_now.py 2026-07      # shows a specific month's purchase
    python3 buy_now.py --plan       # shows the full plan with all dates and URLs
"""

import sys
from datetime import datetime
from planner import generate_investment_plan, format_plan_table
from bonds import get_purchase_details_for_month


def show_purchase_instructions(target_year: int, target_month: int, plan: dict):
    for p in plan["purchases"]:
        pd = datetime.strptime(p["purchase_date"], "%Y-%m-%d")
        if pd.year == target_year and pd.month == target_month:
            details = get_purchase_details_for_month(p["month_number"], p)
            print(f"\n{'='*70}")
            print(f"  TREASURY BOND PURCHASE — {pd.strftime('%B %Y').upper()}")
            print(f"{'='*70}")
            print(f"  Batch:              #{details['month']} of {len(plan['purchases'])}")
            print(f"  Security:           {details['form_fields']['security_type']}")
            print(f"  Term:               {details['form_fields']['term']}")
            print(f"  Face Value:         {details['face_value']}")
            print(f"  Est. Purchase Price:{details['estimated_purchase_price']}")
            print(f"  Est. Interest:      {details['estimated_interest']}")
            print(f"  Maturity Date:      {details['maturity_date']}")
            print(f"  Reinvest:           {details['form_fields']['reinvestment']}")
            print(f"{'='*70}")
            print()
            print("  HOW TO PURCHASE:")
            print(f"{'─'*70}")
            for step in details["form_fields"]["steps"]:
                print(f"    {step}")
            print()
            print(f"{'─'*70}")
            print(f"  LOGIN:    {details['login_url']}")
            print(f"  BUY:      {details['treasury_direct_url']}")
            print(f"  AUCTIONS: {details['upcoming_auctions_url']}")
            print(f"{'─'*70}")
            print()
            print("  NOTES:")
            for note in details["form_fields"]["notes"]:
                print(f"    • {note}")
            print(f"\n{'='*70}\n")
            return

    print(f"\n  No purchase scheduled for {target_year}-{target_month:02d}.")
    print(f"  Your plan runs from {plan['first_purchase']} to {plan['last_purchase']}.\n")


def show_full_plan(plan: dict):
    print(format_plan_table(plan))
    print(f"  PURCHASE URLS BY MONTH:")
    print(f"{'─'*70}")
    for p in plan["purchases"]:
        pd = datetime.strptime(p["purchase_date"], "%Y-%m-%d")
        print(f"    Batch #{p['month_number']:>2} ({pd.strftime('%b %Y'):>8})  →  {p['purchase_url']}")
    print(f"{'─'*70}")
    print(f"\n  LOGIN:    https://www.treasurydirect.gov/RS/UN-AccountLogin.do")
    print(f"  AUCTIONS: https://www.treasurydirect.gov/auctions/upcoming/")
    print(f"  T-BILL INFO: https://www.treasurydirect.gov/marketable-securities/treasury-bills/")
    print()


def main():
    plan = generate_investment_plan()

    if len(sys.argv) > 1 and sys.argv[1] == "--plan":
        show_full_plan(plan)
        return

    if len(sys.argv) > 1:
        parts = sys.argv[1].split("-")
        target_year, target_month = int(parts[0]), int(parts[1])
    else:
        today = datetime.now()
        target_year, target_month = today.year, today.month

    show_purchase_instructions(target_year, target_month, plan)


if __name__ == "__main__":
    main()
