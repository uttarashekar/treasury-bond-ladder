"""
Treasury Bond Ladder Planner

Generates a staggered investment plan: $100K spread across 10 monthly purchases
of 52-week T-Bills, so that starting ~12 months from the first purchase,
one bond matures each month returning ~$10K + interest.
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional


TREASURY_DIRECT_BUY_URL = "https://www.treasurydirect.gov/RS/UN-Display.do"


@dataclass
class BondPurchase:
    month_number: int
    security_type: str
    term: str
    purchase_date: str
    maturity_date: str
    investment_amount: float
    estimated_rate: float
    discount_amount: float
    purchase_price: float
    maturity_value: float
    interest_earned: float
    purchase_url: str


def generate_investment_plan(
    total_investment: float = 100_000.0,
    num_batches: int = 10,
    start_date: Optional[str] = None,
    annual_rate: float = 0.0450,
) -> dict:
    """
    Generate a bond ladder plan.

    Args:
        total_investment: Total amount to invest (default $100,000)
        num_batches: Number of monthly batches (default 10, yielding $10K each)
        start_date: First purchase date (ISO format). Defaults to next month's 1st.
        annual_rate: Estimated annual T-Bill discount rate (default 4.50%)

    Returns:
        dict with plan details, purchases list, and summary statistics.
    """
    if start_date:
        first_purchase = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        today = datetime.now()
        if today.month == 12:
            first_purchase = datetime(today.year + 1, 1, 1)
        else:
            first_purchase = datetime(today.year, today.month + 1, 1)

    batch_amount = total_investment / num_batches

    purchases = []
    total_interest = 0.0
    total_purchase_price = 0.0

    for i in range(num_batches):
        if first_purchase.month + i > 12:
            purchase_year = first_purchase.year + (first_purchase.month + i - 1) // 12
            purchase_month = (first_purchase.month + i - 1) % 12 + 1
        else:
            purchase_year = first_purchase.year
            purchase_month = first_purchase.month + i

        purchase_date = datetime(purchase_year, purchase_month, 1)
        maturity_date = purchase_date + timedelta(weeks=52)

        # T-Bills are sold at a discount. The face value is what you get at maturity.
        # Price = Face Value × (1 - (discount_rate × days_to_maturity / 360))
        face_value = batch_amount
        days_to_maturity = (maturity_date - purchase_date).days
        discount_amount = face_value * annual_rate * days_to_maturity / 360
        purchase_price = face_value - discount_amount
        interest_earned = face_value - purchase_price

        total_interest += interest_earned
        total_purchase_price += purchase_price

        purchases.append(BondPurchase(
            month_number=i + 1,
            security_type="Treasury Bill (T-Bill)",
            term="52-Week",
            purchase_date=purchase_date.strftime("%Y-%m-%d"),
            maturity_date=maturity_date.strftime("%Y-%m-%d"),
            investment_amount=round(face_value, 2),
            estimated_rate=annual_rate,
            discount_amount=round(discount_amount, 2),
            purchase_price=round(purchase_price, 2),
            maturity_value=round(face_value, 2),
            interest_earned=round(interest_earned, 2),
            purchase_url=TREASURY_DIRECT_BUY_URL,
        ))

    plan = {
        "plan_name": "Treasury Bond Ladder — Monthly Maturity Plan",
        "total_investment_face_value": total_investment,
        "total_purchase_price": round(total_purchase_price, 2),
        "total_savings_from_discount": round(total_investment - total_purchase_price, 2),
        "num_batches": num_batches,
        "batch_face_value": batch_amount,
        "estimated_annual_rate": annual_rate,
        "first_purchase": purchases[0].purchase_date,
        "last_purchase": purchases[-1].purchase_date,
        "first_maturity": purchases[0].maturity_date,
        "last_maturity": purchases[-1].maturity_date,
        "total_interest_earned": round(total_interest, 2),
        "effective_return_pct": round((total_interest / total_purchase_price) * 100, 2),
        "purchases": [asdict(p) for p in purchases],
    }

    return plan


def verify_math(plan: dict) -> dict:
    """
    Independently verify all math in a plan using pure arithmetic.
    Returns a verification report with pass/fail for each check.
    """
    checks = []
    all_passed = True

    purchases = plan["purchases"]
    num = len(purchases)
    face_value = plan["batch_face_value"]
    rate = plan["estimated_annual_rate"]

    # Check 1: Total face value = total_investment
    total_face = sum(p["investment_amount"] for p in purchases)
    check1 = abs(total_face - plan["total_investment_face_value"]) < 0.01
    checks.append({
        "check": "Total face value matches total investment",
        "expected": plan["total_investment_face_value"],
        "actual": total_face,
        "passed": check1,
    })
    if not check1:
        all_passed = False

    # Check 2: Each batch face value is correct
    for p in purchases:
        batch_ok = abs(p["investment_amount"] - face_value) < 0.01
        if not batch_ok:
            checks.append({
                "check": f"Batch {p['month_number']} face value",
                "expected": face_value,
                "actual": p["investment_amount"],
                "passed": False,
            })
            all_passed = False

    checks.append({
        "check": "All batch face values correct",
        "passed": all(abs(p["investment_amount"] - face_value) < 0.01 for p in purchases),
    })

    # Check 3: Discount calculation for each bond
    for p in purchases:
        purchase_dt = datetime.strptime(p["purchase_date"], "%Y-%m-%d")
        maturity_dt = datetime.strptime(p["maturity_date"], "%Y-%m-%d")
        days = (maturity_dt - purchase_dt).days
        expected_discount = round(p["investment_amount"] * rate * days / 360, 2)
        expected_price = round(p["investment_amount"] - expected_discount, 2)

        discount_ok = abs(p["discount_amount"] - expected_discount) < 0.02
        price_ok = abs(p["purchase_price"] - expected_price) < 0.02
        interest_ok = abs(p["interest_earned"] - (p["maturity_value"] - p["purchase_price"])) < 0.02

        if not (discount_ok and price_ok and interest_ok):
            checks.append({
                "check": f"Batch {p['month_number']} discount/price math",
                "days_to_maturity": days,
                "expected_discount": expected_discount,
                "actual_discount": p["discount_amount"],
                "expected_price": expected_price,
                "actual_price": p["purchase_price"],
                "passed": False,
            })
            all_passed = False

    checks.append({
        "check": "All discount/price calculations verified",
        "passed": all_passed,
    })

    # Check 4: Total interest
    recalc_interest = sum(p["interest_earned"] for p in purchases)
    interest_ok = abs(recalc_interest - plan["total_interest_earned"]) < 0.10
    checks.append({
        "check": "Total interest matches sum of individual interests",
        "expected": plan["total_interest_earned"],
        "actual": round(recalc_interest, 2),
        "passed": interest_ok,
    })
    if not interest_ok:
        all_passed = False

    # Check 5: Total purchase price
    recalc_price = sum(p["purchase_price"] for p in purchases)
    price_ok = abs(recalc_price - plan["total_purchase_price"]) < 0.10
    checks.append({
        "check": "Total purchase price matches sum of individual prices",
        "expected": plan["total_purchase_price"],
        "actual": round(recalc_price, 2),
        "passed": price_ok,
    })
    if not price_ok:
        all_passed = False

    # Check 6: Maturity dates are ~52 weeks after purchase
    for p in purchases:
        purchase_dt = datetime.strptime(p["purchase_date"], "%Y-%m-%d")
        maturity_dt = datetime.strptime(p["maturity_date"], "%Y-%m-%d")
        days = (maturity_dt - purchase_dt).days
        if not (360 <= days <= 370):
            checks.append({
                "check": f"Batch {p['month_number']} maturity ~52 weeks",
                "days": days,
                "passed": False,
            })
            all_passed = False

    checks.append({
        "check": "All maturity dates are ~52 weeks after purchase",
        "passed": all(
            360 <= (datetime.strptime(p["maturity_date"], "%Y-%m-%d") -
                    datetime.strptime(p["purchase_date"], "%Y-%m-%d")).days <= 370
            for p in purchases
        ),
    })

    return {
        "verification_status": "ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED",
        "all_passed": all_passed,
        "checks": checks,
    }


def format_plan_table(plan: dict) -> str:
    """Format the plan as a readable ASCII table."""
    lines = []
    lines.append(f"\n{'='*100}")
    lines.append(f"  {plan['plan_name']}")
    lines.append(f"{'='*100}")
    lines.append(f"  Total Face Value:    ${plan['total_investment_face_value']:>12,.2f}")
    lines.append(f"  Total Purchase Cost: ${plan['total_purchase_price']:>12,.2f}")
    lines.append(f"  Total Savings:       ${plan['total_savings_from_discount']:>12,.2f}")
    lines.append(f"  Total Interest:      ${plan['total_interest_earned']:>12,.2f}")
    lines.append(f"  Effective Return:    {plan['effective_return_pct']:>12.2f}%")
    lines.append(f"  Annual Rate (est):   {plan['estimated_annual_rate']*100:>12.2f}%")
    lines.append(f"  Security:            {'52-Week Treasury Bill (T-Bill)':>30}")
    lines.append(f"  Purchase At:         {'https://www.treasurydirect.gov/RS/UN-Display.do'}")
    lines.append(f"{'='*120}\n")

    header = (
        f"  {'#':>2}  {'Security':>18}  {'Purchase Date':>14}  {'Maturity Date':>14}  "
        f"{'Face Value':>12}  {'Buy Price':>12}  {'Interest':>10}  {'Rate':>6}"
    )
    lines.append(header)
    lines.append(f"  {'-'*2}  {'-'*18}  {'-'*14}  {'-'*14}  {'-'*12}  {'-'*12}  {'-'*10}  {'-'*6}")

    for p in plan["purchases"]:
        lines.append(
            f"  {p['month_number']:>2}  {'52-Wk T-Bill':>18}  {p['purchase_date']:>14}  {p['maturity_date']:>14}  "
            f"${p['investment_amount']:>11,.2f}  ${p['purchase_price']:>11,.2f}  "
            f"${p['interest_earned']:>9,.2f}  {p['estimated_rate']*100:>5.2f}%"
        )

    lines.append(f"\n  {'':>2}  {'':>18}  {'':>14}  {'TOTALS':>14}  "
                 f"${plan['total_investment_face_value']:>11,.2f}  "
                 f"${plan['total_purchase_price']:>11,.2f}  "
                 f"${plan['total_interest_earned']:>9,.2f}")
    lines.append(f"{'='*120}\n")

    return "\n".join(lines)


if __name__ == "__main__":
    plan = generate_investment_plan()
    print(format_plan_table(plan))

    verification = verify_math(plan)
    print(f"\n{'='*60}")
    print(f"  MATH VERIFICATION REPORT")
    print(f"{'='*60}")
    print(f"  Status: {verification['verification_status']}")
    print(f"{'='*60}")
    for check in verification["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"  [{status}] {check['check']}")
        for k, v in check.items():
            if k not in ("check", "passed"):
                print(f"         {k}: {v}")
    print(f"{'='*60}\n")
