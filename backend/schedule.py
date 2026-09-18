"""Turning the year's plan into a calendar.

The waterfall answers "where does the next dollar go". This answers "what do I do on
payday, this month, and over the next twelve" — the version of a plan somebody can
actually follow. The targets come from the same rules in the same order, so the
schedule can't drift from the dashboard.

Two modelling decisions worth knowing, both surfaced in `notes`:

- **Minimum debt payments are bills, not savings decisions.** They're treated as part of
  monthly expenses, so savings capacity is what's left after them, and a debt's balance
  moves by interest minus the minimum before any extra payment lands.
- **Payroll money only moves on payday.** 401(k) lines are paced evenly across the
  remaining months of the year rather than front-loaded — in a plan without a true-up,
  filling the limit early can cost you match in the months that follow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import content
import limits as L
import pay
import waterfall as W
from models import AccountType, User

# Pay-frequency maths lives in `pay` now, shared with the goal estimator so a figure
# per paycheck means the same thing on both screens. Re-exported for callers here.
PAYCHECKS_PER_YEAR = pay.PAYCHECKS_PER_YEAR
PAY_LABELS = pay.PAY_LABELS
paychecks_per_year = pay.paychecks_per_year
per_paycheck = pay.per_paycheck

# How each rule's money actually moves.
#   asap      — a finite gap; fill it as fast as the money allows
#   spread    — payroll; it only moves on payday, so it's paced across the year
#   recurring — a standing monthly amount that never "finishes"
#   sink      — absorbs whatever is left over
MODES = {
    "R1_EMERGENCY_FUND": "asap",
    "R2_EMPLOYER_MATCH": "spread",
    "R3_HIGH_INTEREST_DEBT": "asap",
    "R4_HSA": "asap",
    "R5_IRA": "asap",
    "R6_REMAINING_401K": "spread",
    "R7_TAXABLE": "sink",
    "R9_RETIREMENT_AGE": "recurring",
}
PAYROLL_RULES = {"R2_EMPLOYER_MATCH", "R6_REMAINING_401K"}
# Room that refills on 1 January rather than running out for good.
ANNUAL_ROOM_RULES = {"R2_EMPLOYER_MATCH", "R4_HSA", "R5_IRA", "R6_REMAINING_401K"}

LABELS = {
    "R1_EMERGENCY_FUND": "Emergency fund",
    "R2_EMPLOYER_MATCH": "401(k) — up to the full match",
    "R4_HSA": "HSA",
    "R5_IRA": "IRA",
    "R6_REMAINING_401K": "401(k) — beyond the match",
    "R7_TAXABLE": "Taxable brokerage",
    "R9_RETIREMENT_AGE": "Taxable brokerage — money you can reach before 59½",
}

ACCOUNTS = {
    "R1_EMERGENCY_FUND": AccountType.CASH,
    "R2_EMPLOYER_MATCH": AccountType.TRADITIONAL_401K,
    "R4_HSA": AccountType.HSA,
    "R5_IRA": AccountType.IRA,
    "R6_REMAINING_401K": AccountType.TRADITIONAL_401K,
    "R7_TAXABLE": AccountType.TAXABLE,
    "R9_RETIREMENT_AGE": AccountType.TAXABLE,
}


@dataclass
class _Target:
    rule_id: str
    label: str
    mode: str
    remaining: float = 0.0
    monthly: float = 0.0          # recurring targets only
    annual_room: float = 0.0      # what it refills to in January
    apr: float = 0.0
    minimum_payment: float = 0.0
    account_type: AccountType | None = None


def monthly_savings(user: User, year: int = L.DEFAULT_YEAR) -> float:
    """What the user themselves moves each month. The employer's match rides along on
    top of it and isn't theirs to schedule."""
    return W.annual_investing(user, year)["own"] / 12


def _targets(user: User, year: int) -> list[_Target]:
    targets: list[_Target] = []
    for item in W.prioritized(user, year):
        mode = MODES.get(item.rule_id)
        if mode is None or mode == "sink":
            continue
        if mode == "recurring":
            targets.append(_Target(
                rule_id=item.rule_id, label=LABELS[item.rule_id], mode=mode,
                monthly=(item.amount or 0) / 12, account_type=ACCOUNTS[item.rule_id],
            ))
            continue
        if not item.amount:
            continue
        if item.rule_id == "R3_HIGH_INTEREST_DEBT":
            label = f"{item.inputs['name']} ({item.inputs['apr']:.0%} APR)"
        else:
            label = LABELS[item.rule_id]
        targets.append(_Target(
            rule_id=item.rule_id,
            label=label,
            mode=mode,
            remaining=item.amount,
            annual_room=item.amount if item.rule_id in ANNUAL_ROOM_RULES else 0.0,
            apr=item.inputs.get("apr", 0.0) if item.rule_id == "R3_HIGH_INTEREST_DEBT" else 0.0,
            minimum_payment=item.inputs.get("minimum_payment", 0.0),
            account_type=ACCOUNTS.get(item.rule_id),
        ))
    targets.append(_Target(
        rule_id="R7_TAXABLE", label=LABELS["R7_TAXABLE"], mode="sink",
        account_type=AccountType.TAXABLE,
    ))
    return targets


def _move(user: User, target: _Target, amount: float, completes: bool) -> dict:
    payroll = target.rule_id in PAYROLL_RULES
    return {
        "rule_id": target.rule_id,
        "label": target.label,
        "account_type": target.account_type.value if target.account_type else None,
        "amount": round(amount, 2),
        "per_paycheck": round(per_paycheck(user, amount * 12), 2),
        "payroll": payroll,
        "percent_of_pay": (round(amount * 12 / user.income, 4)
                           if payroll and user.income else None),
        "completes": completes,
    }


def _add_months(first_of_month: date, offset: int) -> date:
    index = first_of_month.month - 1 + offset
    return date(first_of_month.year + index // 12, index % 12 + 1, 1)


def _month_rows(user: User, year: int, months: int, start: date,
                capacity: float) -> list[dict]:
    targets = _targets(user, year)
    rows = []
    invested_so_far = 0.0

    for offset in range(months):
        month = _add_months(start.replace(day=1), offset)
        if offset and month.month == 1:
            for target in targets:
                if target.rule_id in ANNUAL_ROOM_RULES:
                    target.remaining = target.annual_room

        # Interest first: a balance grows by interest and shrinks by the minimum
        # payment before any extra money from savings arrives.
        for target in targets:
            if target.apr and target.remaining > 0:
                target.remaining = max(
                    0.0, target.remaining * (1 + target.apr / 12) - target.minimum_payment)

        moves = []
        left = capacity
        months_left_in_year = 13 - month.month
        for target in targets:
            if left <= 0.01 or target.mode == "sink":
                continue
            if target.mode == "recurring":
                amount = min(left, target.monthly)
            elif target.mode == "spread":
                amount = min(left, target.remaining / months_left_in_year)
            else:
                amount = min(left, target.remaining)
            if amount <= 0.01:
                continue
            if target.mode != "recurring":
                target.remaining -= amount
            left -= amount
            moves.append(_move(user, target, amount,
                               completes=target.mode != "recurring" and target.remaining <= 0.01))

        if left > 0.01:
            sink = next(t for t in targets if t.mode == "sink")
            moves.append(_move(user, sink, left, completes=False))
            left = 0.0

        # "Invested" excludes cash and debt: both are worth doing first, neither is
        # money in the market.
        invested = sum(m["amount"] for m in moves
                       if m["rule_id"] not in ("R1_EMERGENCY_FUND", "R3_HIGH_INTEREST_DEBT"))
        invested_so_far += invested
        rows.append({
            "month": offset + 1,
            "date": month.isoformat(),
            "label": month.strftime("%B %Y"),
            "total": round(sum(m["amount"] for m in moves), 2),
            "invested": round(invested, 2),
            "invested_so_far": round(invested_so_far, 2),
            "moves": moves,
            "milestones": [f"{m['label']} — done" for m in moves if m["completes"]],
        })
    return rows


def paycheck_view(user: User, moves: list[dict]) -> dict:
    """What one payday looks like. Payroll deferrals are already out before take-home
    pay lands, so only the transfers come off the figure in your bank account."""
    ppy = paychecks_per_year(user)
    take_home = user.take_home_per_paycheck
    bills = user.goal.monthly_expenses * 12 / ppy
    payroll = sum(m["per_paycheck"] for m in moves if m["payroll"])
    transfers = sum(m["per_paycheck"] for m in moves if not m["payroll"])
    return {
        "frequency": user.pay_frequency.value,
        "label": PAY_LABELS[user.pay_frequency],
        "paychecks_per_year": ppy,
        "take_home": None if take_home is None else round(take_home, 2),
        "bills": round(bills, 2),
        "payroll_deferrals": round(payroll, 2),
        "transfers": round(transfers, 2),
        "free_to_spend": (None if take_home is None
                          else round(take_home - bills - transfers, 2)),
        "gross_per_paycheck": round(user.income / ppy, 2) if user.income else None,
    }


def schedule(user: User, year: int = L.DEFAULT_YEAR, months: int = 12,
             start: date | None = None) -> dict:
    if not 1 <= months <= 24:
        raise ValueError("Ask for between 1 and 24 months.")
    start = start or date.today()
    capacity = monthly_savings(user, year)
    rows = _month_rows(user, year, months, start, capacity)
    this_month = rows[0] if rows else None
    paycheck = paycheck_view(user, this_month["moves"] if this_month else [])

    notes = [
        "Minimum payments on your debts are treated as bills inside your monthly "
        "expenses, so everything scheduled here is what's left after them.",
        "401(k) money only moves on payday, so those lines are paced across the rest of "
        "the year rather than front-loaded — in a plan without a true-up, filling the "
        "limit early can cost you match in the months that follow.",
    ]
    if user.take_home_per_paycheck is None:
        notes.append("Add your take-home pay on About you and this becomes a full payday "
                     "breakdown, including what's left to spend.")
    if rows and rows[-1]["date"][:4] != str(start.year):
        notes.append(f"Next year's IRS limits aren't published yet, so months after "
                     f"December reuse the {year} numbers.")
    if user.annual_savings_capacity is None:
        notes.append("This schedules what you already contribute. Tell us what you could "
                     "save each month and it will schedule that instead.")

    return {
        "year": year,
        "start": start.isoformat(),
        "monthly_savings": round(capacity, 2),
        "capacity_set": user.annual_savings_capacity is not None,
        # The same figure in every unit, so the page can show what this is as a share
        # of a paycheck without doing the arithmetic itself.
        "savings": pay.amounts(user, capacity * 12) | {
            "basis": user.savings_basis.value,
            "basis_label": pay.BASIS_LABELS[user.savings_basis],
        },
        "paycheck": paycheck,
        "this_month": this_month,
        "months": rows,
        "notes": notes,
        "disclaimer": content.DISCLAIMER,
    }
