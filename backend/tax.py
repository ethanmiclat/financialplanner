"""Federal income tax, just far enough to answer one question: Roth or traditional?

That choice is a bet on one comparison — your tax rate on this dollar now, against
your rate on it when you take it out. The engine used to ask the user to guess the
answer ("do you expect a lower bracket?"). This estimates both sides from numbers
the plan already has: income now, and retirement spending and Social Security later.

What it deliberately leaves out, and why that's acceptable here:
- State tax. It moves both sides by similar amounts unless you move states.
- Credits, other deductions, capital gains. They shift the effective rate, rarely
  which bracket the next dollar lands in.
- Brackets are indexed to inflation and retirement spending is in today's dollars,
  so today's brackets apply to it directly. The Social Security thresholds are *not*
  indexed, so the estimate slightly understates how much of it will be taxed.

The retirement side assumes all spending beyond Social Security comes out of
pre-tax accounts — the case where the traditional side is taxed hardest. That's the
comparison the decision is about: what the traditional dollar would face.
"""

from __future__ import annotations

import limits as L
from models import User

ASSUMED_RETIREMENT_AGE = 67


def _data(year: int) -> dict:
    return L.load_limits(year)["federal_tax"]


def _status(user_or_status) -> str:
    s = getattr(user_or_status, "filing_status", user_or_status)
    return getattr(s, "value", s)


def standard_deduction(status: str, year: int, age: int | None = None) -> float:
    d = _data(year)
    base = d["standard_deduction"][status]
    if age is not None and age >= 65:
        base += d["additional_deduction_65_plus"][status]
    return base


def tax_on(taxable: float, status: str, year: int) -> float:
    """Tax on taxable income (after deductions), walking the brackets."""
    owed, floor = 0.0, 0.0
    for top, rate in _data(year)["brackets"][status]:
        if taxable <= floor:
            break
        ceiling = taxable if top is None else min(taxable, top)
        owed += (ceiling - floor) * rate
        if top is None:
            break
        floor = top
    return owed


def marginal_rate(taxable: float, status: str, year: int) -> float:
    """The rate on the next dollar. Under the standard deduction that's 0% — the case
    a student on a part-time wage is in, and the strongest case for Roth there is."""
    if taxable <= 0:
        return 0.0
    for top, rate in _data(year)["brackets"][status]:
        if top is None or taxable < top:
            return rate
    return 0.37


def taxable_social_security(ss: float, other_income: float, status: str, year: int) -> float:
    """IRC §86: up to 85% of benefits become taxable as other income rises."""
    if ss <= 0:
        return 0.0
    lo, hi = _data(year)["social_security_taxation"][status]
    provisional = other_income + ss / 2
    if provisional <= lo:
        return 0.0
    if provisional <= hi:
        return min(0.5 * ss, 0.5 * (provisional - lo))
    return min(0.85 * ss, 0.85 * (provisional - hi) + min(0.5 * ss, 0.5 * (hi - lo)))


def _picture(gross: float, taxable: float, status: str, year: int, deduction: float) -> dict:
    tax = tax_on(max(0.0, taxable), status, year)
    return {
        "gross": round(gross, 2),
        "deduction": deduction,
        "taxable": round(max(0.0, taxable), 2),
        "tax": round(tax, 2),
        "marginal_rate": marginal_rate(taxable, status, year),
        "effective_rate": round(tax / gross, 4) if gross > 0 else 0.0,
    }


def now(user: User, year: int) -> dict:
    status = _status(user)
    ded = standard_deduction(status, year, user.age)
    return _picture(user.income, user.income - ded, status, year, ded)


def retirement(user: User, year: int) -> dict | None:
    """Spending in today's dollars, funded by Social Security first and pre-tax
    withdrawals for the rest. None when there's no spending figure to go on."""
    g = user.goal
    monthly = g.retirement_monthly_spending or g.monthly_expenses
    if not monthly:
        return None
    status = _status(user)
    spending = monthly * 12
    ss = (g.social_security_monthly or 0) * 12
    withdrawals = max(0.0, spending - ss)
    ss_taxable = taxable_social_security(ss, withdrawals, status, year)
    age = g.retirement_age or ASSUMED_RETIREMENT_AGE
    ded = standard_deduction(status, year, age)
    picture = _picture(withdrawals + ss, withdrawals + ss_taxable - ded, status, year, ded)
    picture.update(
        spending=round(spending, 2), social_security=round(ss, 2),
        withdrawals=round(withdrawals, 2), social_security_taxable=round(ss_taxable, 2),
        spending_source="retirement_monthly_spending" if g.retirement_monthly_spending else "monthly_expenses",
    )
    return picture


def compare(user: User, year: int) -> dict:
    """Both sides, the verdict, and what it's worth per $1,000.

    A tie goes to Roth: the same rate either way, and Roth adds no required
    withdrawals and tax-free money to draw on in a high-income year."""
    today, later = now(user, year), retirement(user, year)
    override = user.expects_lower_bracket_in_retirement
    if later is None:
        verdict = "unknown"
    elif today["marginal_rate"] > later["marginal_rate"]:
        verdict = "traditional"
    else:
        verdict = "roth"
    estimated = verdict
    if override is True:
        verdict = "traditional"
    elif override is False:
        verdict = "roth"
    gap = (today["marginal_rate"] - later["marginal_rate"]) if later else None
    return {
        "now": today,
        "retirement": later,
        "verdict": verdict,                 # what the plan acts on
        "estimated_verdict": estimated,     # what the numbers alone say
        "overridden": override is not None and estimated not in ("unknown", verdict),
        "override": override,
        # Traditional's edge on $1,000 of pre-tax money (negative = Roth's edge).
        "per_1000": round(1000 * gap, 2) if gap is not None else None,
        "year": year,
    }


def expects_lower(user: User, year: int) -> bool | None:
    """The engine's old question, now answered: the user's own answer if they gave
    one, otherwise the estimate. None only when there's nothing to estimate from."""
    if user.expects_lower_bracket_in_retirement is not None:
        return user.expects_lower_bracket_in_retirement
    c = compare(user, year)
    if c["estimated_verdict"] == "unknown":
        return None
    return c["estimated_verdict"] == "traditional"
