"""
Side-by-side comparison of two treasury bond ladder strategies.

Plan A: Monthly Ladder — Buy one 52-week T-Bill per month for 10 months.
Plan B: All-at-Once — Invest all $100K immediately across mixed T-Bill maturities,
        then reinvest short-term proceeds into 52-week T-Bills to build the ladder.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass


TBILL_TERMS = {
    "4-Week T-Bill":  28,
    "8-Week T-Bill":  56,
    "13-Week T-Bill": 91,
    "17-Week T-Bill": 119,
    "26-Week T-Bill": 182,
    "52-Week T-Bill": 364,
}

RATES_BY_TERM = {
    "4-Week T-Bill":  0.0430,
    "8-Week T-Bill":  0.0435,
    "13-Week T-Bill": 0.0440,
    "17-Week T-Bill": 0.0440,
    "26-Week T-Bill": 0.0445,
    "52-Week T-Bill": 0.0450,
}

BUY_URL = "https://www.treasurydirect.gov/RS/UN-Display.do"


@dataclass
class Purchase:
    step: str
    security: str
    purchase_date: str
    maturity_date: str
    face_value: float
    rate: float
    purchase_price: float
    interest: float
    action: str


def calc_tbill(face_value: float, days: int, rate: float) -> tuple[float, float]:
    discount = face_value * rate * days / 360
    price = face_value - discount
    return round(price, 2), round(discount, 2)


def generate_plan_a(start: datetime, total: float = 100_000, batches: int = 10, rate: float = 0.0450):
    batch_amt = total / batches
    purchases = []
    total_interest = 0.0
    total_cost = 0.0

    for i in range(batches):
        if start.month + i > 12:
            yr = start.year + (start.month + i - 1) // 12
            mo = (start.month + i - 1) % 12 + 1
        else:
            yr = start.year
            mo = start.month + i

        buy_date = datetime(yr, mo, 1)
        mat_date = buy_date + timedelta(days=364)
        price, interest = calc_tbill(batch_amt, 364, rate)
        total_interest += interest
        total_cost += price

        purchases.append(Purchase(
            step=f"Buy #{i+1}",
            security="52-Week T-Bill",
            purchase_date=buy_date.strftime("%Y-%m-%d"),
            maturity_date=mat_date.strftime("%Y-%m-%d"),
            face_value=batch_amt,
            rate=rate,
            purchase_price=price,
            interest=interest,
            action="BUY",
        ))

    return purchases, total_cost, total_interest


def generate_plan_b(start: datetime, total: float = 100_000):
    """
    Invest all $100K on day 1 across different T-Bill maturities.
    As each short-term bill matures, reinvest into a 52-week T-Bill.
    The 52-week bill bought on day 1 matures directly.
    """
    purchases = []
    total_interest = 0.0
    total_cost = 0.0

    terms_for_ladder = [
        ("52-Week T-Bill", 364),
        ("4-Week T-Bill",  28),
        ("8-Week T-Bill",  56),
        ("13-Week T-Bill", 91),
        ("17-Week T-Bill", 119),
        ("26-Week T-Bill", 182),
    ]

    batch_amt = 10_000.0
    remaining = total

    phase1_maturities = []

    for i, (term_name, days) in enumerate(terms_for_ladder):
        if remaining <= 0:
            break
        invest_amt = min(batch_amt, remaining)
        remaining -= invest_amt

        rate = RATES_BY_TERM[term_name]
        price, interest = calc_tbill(invest_amt, days, rate)
        total_interest += interest
        total_cost += price

        mat_date = start + timedelta(days=days)

        purchases.append(Purchase(
            step=f"Phase 1 #{i+1}",
            security=term_name,
            purchase_date=start.strftime("%Y-%m-%d"),
            maturity_date=mat_date.strftime("%Y-%m-%d"),
            face_value=invest_amt,
            rate=rate,
            purchase_price=price,
            interest=interest,
            action="BUY",
        ))

        if term_name != "52-Week T-Bill":
            phase1_maturities.append((mat_date, invest_amt, term_name))

    # Remaining $40K: park in 4-week T-Bills, rolling until we can buy 52-week
    # We need 4 more slots. Use staggered 4-week bills that reinvest into 52-week.
    parking_offsets_weeks = [5, 6, 7, 9]
    for j, offset_wk in enumerate(parking_offsets_weeks):
        if remaining <= 0:
            break
        invest_amt = min(batch_amt, remaining)
        remaining -= invest_amt

        park_days = offset_wk * 7
        park_rate = RATES_BY_TERM["4-Week T-Bill"]
        park_price, park_interest = calc_tbill(invest_amt, 28, park_rate)
        total_interest += park_interest
        total_cost += park_price

        park_mat = start + timedelta(days=28)
        # After first 4-week bill, roll into another short bill to hit the target offset
        if offset_wk > 4:
            extra_days = (offset_wk - 4) * 7
            extra_price, extra_interest = calc_tbill(invest_amt, extra_days, park_rate)
            total_interest += extra_interest
            park_mat = start + timedelta(days=park_days)

        purchases.append(Purchase(
            step=f"Phase 1 #{len(purchases)+1}",
            security=f"4-Week T-Bill (park {offset_wk}wk)",
            purchase_date=start.strftime("%Y-%m-%d"),
            maturity_date=park_mat.strftime("%Y-%m-%d"),
            face_value=invest_amt,
            rate=park_rate,
            purchase_price=park_price,
            interest=park_interest,
            action="BUY + PARK",
        ))

        phase1_maturities.append((park_mat, invest_amt, f"parked-{offset_wk}wk"))

    # Phase 2: Reinvest each matured short-term bill into a 52-week T-Bill
    reinvest_rate = RATES_BY_TERM["52-Week T-Bill"]
    for mat_date, face_val, source in sorted(phase1_maturities):
        reinvest_price, reinvest_interest = calc_tbill(face_val, 364, reinvest_rate)
        total_interest += reinvest_interest
        final_mat = mat_date + timedelta(days=364)

        purchases.append(Purchase(
            step=f"Phase 2",
            security="52-Week T-Bill",
            purchase_date=mat_date.strftime("%Y-%m-%d"),
            maturity_date=final_mat.strftime("%Y-%m-%d"),
            face_value=face_val,
            rate=reinvest_rate,
            purchase_price=reinvest_price,
            interest=reinvest_interest,
            action=f"REINVEST (from {source})",
        ))

    return purchases, total_cost, total_interest


def format_comparison(start: datetime):
    plan_a, cost_a, interest_a = generate_plan_a(start)
    plan_b, cost_b, interest_b = generate_plan_b(start)

    lines = []
    w = 130

    # ── Plan A ──
    lines.append(f"\n{'='*w}")
    lines.append(f"  PLAN A: MONTHLY LADDER — Buy one 52-Week T-Bill per month")
    lines.append(f"  Strategy: Invest $10K/month over 10 months. Simple and predictable.")
    lines.append(f"  Downside: Uninvested cash sits idle for months 2–10.")
    lines.append(f"{'='*w}")
    lines.append(f"  Total Face Value:    ${100_000:>12,.2f}")
    lines.append(f"  Total Purchase Cost: ${cost_a:>12,.2f}")
    lines.append(f"  Total Interest:      ${interest_a:>12,.2f}")
    lines.append(f"  Effective Return:    {(interest_a/cost_a)*100:>12.2f}%")
    lines.append(f"{'='*w}\n")

    hdr = (f"  {'Step':<10}  {'Security':<18}  {'Purchase Date':>14}  "
           f"{'Maturity Date':>14}  {'Face Value':>12}  {'Buy Price':>12}  "
           f"{'Interest':>10}  {'Rate':>6}  {'URL'}")
    lines.append(hdr)
    lines.append(f"  {'-'*10}  {'-'*18}  {'-'*14}  {'-'*14}  {'-'*12}  {'-'*12}  {'-'*10}  {'-'*6}  {'-'*20}")

    for p in plan_a:
        lines.append(
            f"  {p.step:<10}  {p.security:<18}  {p.purchase_date:>14}  "
            f"{p.maturity_date:>14}  ${p.face_value:>11,.2f}  ${p.purchase_price:>11,.2f}  "
            f"${p.interest:>9,.2f}  {p.rate*100:>5.2f}%  {BUY_URL}"
        )

    lines.append(f"\n  MATURITY SCHEDULE (when you get money back):")
    lines.append(f"  {'-'*60}")
    for p in plan_a:
        mat = datetime.strptime(p.maturity_date, "%Y-%m-%d")
        lines.append(f"    {mat.strftime('%B %Y'):<20} ← ${p.face_value:>10,.2f} returned")

    # ── Plan B ──
    lines.append(f"\n\n{'='*w}")
    lines.append(f"  PLAN B: ALL-AT-ONCE — Invest $100K immediately across mixed T-Bill maturities")
    lines.append(f"  Strategy: Buy 6 different T-Bill terms on day 1. As short-term bills mature,")
    lines.append(f"            reinvest into 52-week T-Bills. All money works from day 1.")
    lines.append(f"  Downside: More complex — requires reinvestment actions. More transactions.")
    lines.append(f"{'='*w}")
    lines.append(f"  Total Upfront Cost:  ${cost_b:>12,.2f}")
    lines.append(f"  Total Interest:      ${interest_b:>12,.2f}  (includes parking + reinvestment interest)")
    lines.append(f"  Extra Interest vs A: ${interest_b - interest_a:>12,.2f}")
    lines.append(f"{'='*w}\n")

    lines.append(f"  PHASE 1 — Initial Purchases (all on {start.strftime('%Y-%m-%d')}):")
    lines.append(f"  {'-'*w}")

    hdr2 = (f"  {'Step':<14}  {'Security':<28}  {'Purchase Date':>14}  "
            f"{'Maturity Date':>14}  {'Face Value':>12}  {'Buy Price':>12}  "
            f"{'Interest':>10}  {'Rate':>6}  {'Action':<20}")
    lines.append(hdr2)
    lines.append(f"  {'-'*14}  {'-'*28}  {'-'*14}  {'-'*14}  {'-'*12}  {'-'*12}  {'-'*10}  {'-'*6}  {'-'*20}")

    phase1 = [p for p in plan_b if p.step.startswith("Phase 1")]
    phase2 = [p for p in plan_b if p.step.startswith("Phase 2")]

    for p in phase1:
        lines.append(
            f"  {p.step:<14}  {p.security:<28}  {p.purchase_date:>14}  "
            f"{p.maturity_date:>14}  ${p.face_value:>11,.2f}  ${p.purchase_price:>11,.2f}  "
            f"${p.interest:>9,.2f}  {p.rate*100:>5.2f}%  {p.action:<20}"
        )

    lines.append(f"\n  PHASE 2 — Reinvestments (as short-term bills mature, buy 52-week T-Bills):")
    lines.append(f"  {'-'*w}")

    for p in phase2:
        lines.append(
            f"  {p.step:<14}  {p.security:<28}  {p.purchase_date:>14}  "
            f"{p.maturity_date:>14}  ${p.face_value:>11,.2f}  ${p.purchase_price:>11,.2f}  "
            f"${p.interest:>9,.2f}  {p.rate*100:>5.2f}%  {p.action:<20}"
        )

    lines.append(f"\n  FINAL MATURITY SCHEDULE (when you get money back):")
    lines.append(f"  {'-'*60}")

    # The 52-week bill from phase 1 matures directly; phase 2 bills mature later
    all_final_maturities = []
    for p in phase1:
        if p.security == "52-Week T-Bill":
            all_final_maturities.append((p.maturity_date, p.face_value, "direct"))
    for p in phase2:
        all_final_maturities.append((p.maturity_date, p.face_value, "reinvested"))

    for mat_str, fv, source in sorted(all_final_maturities):
        mat = datetime.strptime(mat_str, "%Y-%m-%d")
        lines.append(f"    {mat.strftime('%B %Y'):<20} ← ${fv:>10,.2f} returned ({source})")

    # ── Comparison Summary ──
    lines.append(f"\n\n{'='*w}")
    lines.append(f"  SIDE-BY-SIDE COMPARISON")
    lines.append(f"{'='*w}")
    lines.append(f"  {'Metric':<40} {'Plan A (Monthly)':>20} {'Plan B (All-at-Once)':>22}")
    lines.append(f"  {'-'*40} {'-'*20} {'-'*22}")
    lines.append(f"  {'Total invested':<40} {'$100,000.00':>20} {'$100,000.00':>22}")
    lines.append(f"  {'Upfront cash needed':<40} {'$10,000':>20} {'$100,000':>22}")
    lines.append(f"  {'Total purchase cost':<40} ${cost_a:>19,.2f} ${cost_b:>21,.2f}")
    lines.append(f"  {'Total interest earned':<40} ${interest_a:>19,.2f} ${interest_b:>21,.2f}")
    lines.append(f"  {'Number of transactions':<40} {'10':>20} {str(len(plan_b)):>22}")
    lines.append(f"  {'Complexity':<40} {'Low':>20} {'High':>22}")
    lines.append(f"  {'Idle cash months':<40} {'9 months':>20} {'0 months':>22}")
    lines.append(f"  {'Distinct security types':<40} {'1':>20} {'6':>22}")

    num_final_b = len(all_final_maturities)
    lines.append(f"  {'Final maturity events':<40} {'10':>20} {str(num_final_b):>22}")
    lines.append(f"{'='*w}\n")

    lines.append(f"  VERDICT:")
    lines.append(f"  • Plan A is simpler: same bond every month, easy to automate with email reminders.")
    lines.append(f"  • Plan B earns ~${interest_b - interest_a:,.2f} more interest by keeping all cash working,")
    lines.append(f"    but requires {len(plan_b)} transactions across {len(set(p.security for p in plan_b))} different security types.")
    lines.append(f"  • Both achieve the same goal: ~$10K/month returning to your bank account.\n")

    return "\n".join(lines)


def verify_plan_a_math(start: datetime):
    purchases, cost, interest = generate_plan_a(start)
    checks = []

    total_face = sum(p.face_value for p in purchases)
    checks.append(("Total face value = $100,000", abs(total_face - 100_000) < 0.01))

    recalc_interest = sum(p.interest for p in purchases)
    checks.append(("Sum of interest matches total", abs(recalc_interest - interest) < 0.10))

    recalc_cost = sum(p.purchase_price for p in purchases)
    checks.append(("Sum of prices matches total cost", abs(recalc_cost - cost) < 0.10))

    for p in purchases:
        expected_price, expected_int = calc_tbill(p.face_value, 364, p.rate)
        ok = abs(p.purchase_price - expected_price) < 0.02 and abs(p.interest - expected_int) < 0.02
        if not ok:
            checks.append((f"{p.step} discount math", False))

    checks.append(("All discount calculations verified", all(c[1] for c in checks)))
    return checks


def verify_plan_b_math(start: datetime):
    purchases, cost, interest = generate_plan_b(start)
    checks = []

    phase1 = [p for p in purchases if p.step.startswith("Phase 1")]
    total_face_p1 = sum(p.face_value for p in phase1)
    checks.append(("Phase 1 total face value = $100,000", abs(total_face_p1 - 100_000) < 0.01))

    for p in phase1:
        term_days = None
        for term, days in TBILL_TERMS.items():
            if p.security.startswith(term.split(" ")[0]):
                term_days = days
                break
        if term_days is None:
            term_days = 28
        expected_price, expected_int = calc_tbill(p.face_value, term_days, p.rate)
        ok = abs(p.purchase_price - expected_price) < 0.02
        if not ok:
            checks.append((f"{p.step} ({p.security}) price calc", False))

    phase2 = [p for p in purchases if p.step.startswith("Phase 2")]
    for p in phase2:
        expected_price, expected_int = calc_tbill(p.face_value, 364, p.rate)
        ok = abs(p.purchase_price - expected_price) < 0.02
        if not ok:
            checks.append((f"Phase 2 reinvest ({p.purchase_date}) price calc", False))

    checks.append(("All discount calculations verified", all(c[1] for c in checks)))
    return checks


if __name__ == "__main__":
    start = datetime(2026, 5, 1)

    print(format_comparison(start))

    print(f"{'='*60}")
    print(f"  MATH VERIFICATION — PLAN A")
    print(f"{'='*60}")
    for desc, passed in verify_plan_a_math(start):
        print(f"  [{'PASS' if passed else 'FAIL'}] {desc}")

    print(f"\n{'='*60}")
    print(f"  MATH VERIFICATION — PLAN B")
    print(f"{'='*60}")
    for desc, passed in verify_plan_b_math(start):
        print(f"  [{'PASS' if passed else 'FAIL'}] {desc}")
    print(f"{'='*60}\n")
