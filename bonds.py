"""
Treasury bond reference data: URLs, form fields, and rate fetching.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

TREASURY_DIRECT_BASE = "https://www.treasurydirect.gov"

URLS = {
    "home": f"{TREASURY_DIRECT_BASE}/",
    "login": f"{TREASURY_DIRECT_BASE}/RS/UN-AccountLogin.do",
    "buy_direct": f"{TREASURY_DIRECT_BASE}/RS/UN-Display.do",
    "t_bill_info": f"{TREASURY_DIRECT_BASE}/marketable-securities/treasury-bills/",
    "upcoming_auctions": f"{TREASURY_DIRECT_BASE}/auctions/upcoming/",
    "auction_results": f"{TREASURY_DIRECT_BASE}/auctions/auction-query/results/",
    "account_setup_guide": f"{TREASURY_DIRECT_BASE}/indiv/myaccount/",
}

PURCHASE_FORM_FIELDS = {
    "security_type": "Treasury Bill (T-Bill)",
    "term": "52-Week",
    "purchase_amount": "$10,000 (face value per batch)",
    "reinvestment": "No (we want the cash back at maturity)",
    "source_of_funds": "Your linked bank account",
    "steps": [
        "1. Log in to TreasuryDirect.gov",
        "2. Click 'BuyDirect' in the top navigation",
        "3. Select 'Bills' under Security Type",
        "4. Select '52-Week' as the Term",
        "5. Enter purchase amount (face value, e.g., $10,000)",
        "6. Select 'No' for Reinvest at Maturity",
        "7. Select your bank account as the funding source",
        "8. Review and submit the purchase",
        "9. Save your confirmation number",
    ],
    "notes": [
        "T-Bills are auctioned on a schedule — 52-week bills typically auction every 4 weeks.",
        "You are buying at auction, so you'll get the market-determined discount rate.",
        "The purchase price will be debited from your bank account on the issue date.",
        "At maturity, the full face value ($10,000) is deposited back to your bank account.",
        "You can schedule purchases in advance — set up a non-competitive bid.",
    ],
}

FISCAL_DATA_API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
RATES_ENDPOINT = f"{FISCAL_DATA_API}/v2/accounting/od/avg_interest_rates"


def fetch_current_rates() -> Optional[dict]:
    """
    Fetch the latest average interest rates from the Treasury Fiscal Data API.
    Returns parsed JSON or None on failure.
    """
    params = (
        "?filter=security_desc:eq:Treasury Bills"
        "&sort=-record_date"
        "&page[size]=12"
        "&fields=record_date,security_desc,avg_interest_rate_amt"
    )
    url = RATES_ENDPOINT + params
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def get_latest_tbill_rate() -> Optional[float]:
    """Return the most recent T-Bill average rate as a decimal, or None."""
    data = fetch_current_rates()
    if data and data.get("data"):
        latest = data["data"][0]
        return float(latest["avg_interest_rate_amt"]) / 100
    return None


def get_purchase_details_for_month(month_number: int, purchase: dict) -> dict:
    """
    Return full purchase instructions for a specific month's bond buy.
    """
    return {
        "month": month_number,
        "action": f"Purchase 52-Week T-Bill — Batch #{month_number}",
        "purchase_date": purchase["purchase_date"],
        "maturity_date": purchase["maturity_date"],
        "face_value": f"${purchase['investment_amount']:,.2f}",
        "estimated_purchase_price": f"${purchase['purchase_price']:,.2f}",
        "estimated_interest": f"${purchase['interest_earned']:,.2f}",
        "treasury_direct_url": URLS["buy_direct"],
        "login_url": URLS["login"],
        "form_fields": PURCHASE_FORM_FIELDS,
        "upcoming_auctions_url": URLS["upcoming_auctions"],
    }


def get_next_purchase(plan: dict) -> Optional[dict]:
    """
    Determine which bond to purchase this month based on the plan.
    Returns purchase details or None if all purchases are complete.
    """
    today = datetime.now()
    for p in plan["purchases"]:
        purchase_date = datetime.strptime(p["purchase_date"], "%Y-%m-%d")
        if purchase_date.year == today.year and purchase_date.month == today.month:
            return get_purchase_details_for_month(p["month_number"], p)
        if purchase_date > today:
            return get_purchase_details_for_month(p["month_number"], p)
    return None
