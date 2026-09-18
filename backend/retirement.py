"""Retirement timing — everything that changes when *when* you retire changes.

Contribution limits are about this year. Retirement age is about the shape of the
whole plan: how long the money has to grow, how long it has to last, and which
accounts you can actually reach at the age you stop working. A plan that's right for
retiring at 67 can be wrong at 50 — not because the waterfall order changes, but
because money locked in a 401(k) until 59½ can't pay rent at 52.

Pure functions, no I/O. The age thresholds live in the limits data file next to the
dollar limits, so a rule change is a data change. The waterfall and the projection
both read from here, so the advice and the chart can't disagree about the same age.

Money is compared in today's dollars throughout: a nominal figure forty years out is
a number nobody can picture.
"""

from __future__ import annotations

import math

import limits as L
from models import AccountType, User

DEFAULT_RETIREMENT_AGE = 67
# Searching past this for "the earliest age your plan supports" stops being advice.
_EARLIEST_AGE_SEARCH_CAP = 80

INVESTED_TYPES = (
    AccountType.TRADITIONAL_401K,
    AccountType.IRA,
    AccountType.HSA,
    AccountType.TAXABLE,
)


# --- the user's settings, resolved ---------------------------------------------


def retirement_age(user: User) -> int:
    age = user.goal.retirement_age
    return DEFAULT_RETIREMENT_AGE if age is None else age


def years_to_retirement(user: User) -> int:
    return max(0, retirement_age(user) - user.age)


def plan_to_age(user: User) -> int:
    """How long the money has to last. Never before the year after retiring, or
    next year — a profile edited out of order still gets a usable horizon."""
    return max(user.goal.plan_to_age, retirement_age(user) + 1, user.age + 1)


def retirement_spending_annual(user: User) -> float:
    """Today's dollars. Unset means "the same as I spend now", which is the honest
    default: spending usually falls less in retirement than people expect."""
    goal = user.goal
    monthly = (goal.monthly_expenses if goal.retirement_monthly_spending is None
               else goal.retirement_monthly_spending)
    return max(0.0, monthly) * 12


def validate(user: User) -> None:
    """Reject settings that can't be planned, with a message a person can act on.
    Runs on every save and every what-if, so nonsense never reaches the maths."""
    goal, a = user.goal, user.assumptions
    ra = retirement_age(user)
    if not isinstance(ra, int) or not 18 <= ra <= 90:
        raise ValueError("Pick a retirement age between 18 and 90.")
    floor = max(ra, user.age)
    if not isinstance(goal.plan_to_age, int) or goal.plan_to_age <= floor:
        raise ValueError(f"Plan for your money to last past age {floor}.")
    if goal.plan_to_age > 120:
        raise ValueError("Plan to an age of 120 or less.")
    if goal.social_security_claim_age not in range(62, 71):
        raise ValueError("Social Security can be claimed between ages 62 and 70.")
    for label, value in (
        ("retirement spending", goal.retirement_monthly_spending),
        ("Social Security estimate", goal.social_security_monthly),
    ):
        if value is not None and (not _is_number(value) or value < 0):
            raise ValueError(f"Your {label} can't be negative.")
    _check_rate("return while saving", a.return_rate, -0.05, 0.15)
    _check_rate("return in retirement", a.retirement_return_rate, -0.05, 0.15)
    _check_rate("inflation rate", a.inflation, 0.0, 0.10)
    _check_rate("yearly increase in savings", a.contribution_growth, 0.0, 0.15)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_rate(label: str, value, low: float, high: float) -> None:
    if not _is_number(value) or not low <= value <= high:
        raise ValueError(f"Keep the {label} between {low:.0%} and {high:.0%}.")


# --- rules that hang off an age ------------------------------------------------


def ages(year: int = L.DEFAULT_YEAR) -> dict:
    return L.load_limits(year)["ages"]


def rmd_age(user: User, year: int = L.DEFAULT_YEAR) -> int:
    """Required minimum distributions start at an age set by birth year."""
    born = year - user.age
    tiers = ages(year)["rmd"]
    for tier in tiers:
        if born >= tier["born_from"] and (tier["born_to"] is None or born <= tier["born_to"]):
            return tier["age"]
    return tiers[0]["age"]


def social_security_factor(claim_age: int, year: int = L.DEFAULT_YEAR) -> float:
    """Benefit as a share of the full-retirement-age amount, using SSA's formula:
    5/9 of 1% a month for the first 36 months early, 5/12 of 1% beyond that, and
    delayed credits for every month waited past full retirement age, up to 70."""
    ss = ages(year)["social_security"]
    full = ss["full"]
    if claim_age < full:
        months = (full - claim_age) * 12
        return 1 - min(months, 36) * 5 / 900 - max(0, months - 36) * 5 / 1200
    months = (min(claim_age, ss["latest"]) - full) * 12
    return 1 + months * ss["delay_credit_per_year"] / 12


def social_security_annual(user: User, year: int = L.DEFAULT_YEAR) -> float:
    """Today's dollars, adjusted for the age they claim at. Zero when unknown."""
    monthly = user.goal.social_security_monthly or 0.0
    return monthly * 12 * social_security_factor(user.goal.social_security_claim_age, year)


def net_need_today(user: User, age: int, year: int = L.DEFAULT_YEAR) -> float:
    """What the portfolio has to pay for in a year of retirement, in today's money.
    Before the claim age it carries all of the spending; after, Social Security
    takes its share."""
    ss = (social_security_annual(user, year)
          if age >= user.goal.social_security_claim_age else 0.0)
    return max(0.0, retirement_spending_annual(user) - ss)


def medicare_gap_years(user: User, year: int = L.DEFAULT_YEAR) -> int:
    start = max(retirement_age(user), user.age)
    return max(0, ages(year)["medicare"] - start)


# --- the maths -----------------------------------------------------------------


def future_value(principal: float, annual_contribution: float, rate: float,
                 years: float, delay: float = 0.0, growth: float = 0.0) -> float:
    """Compound growth with contributions at the end of each year.

    `delay` pushes the start of contributions back — the time spent paying off a card
    and building a cash cushion first. The starting balance compounds for the whole
    period regardless. `growth` raises the contribution each year; it's a closed-form
    growing annuity, so a fractional delay still works.
    """
    if years <= 0:
        return principal
    grown_principal = principal * (1 + rate) ** years
    contributing_years = max(0.0, years - delay)
    if contributing_years == 0:
        return grown_principal
    return grown_principal + annual_contribution * _annuity(rate, growth, contributing_years)


def _annuity(rate: float, growth: float, years: float) -> float:
    """What a contribution of 1, growing by `growth` a year, is worth after `years`."""
    if abs(rate - growth) < 1e-12:
        return years * (1 + rate) ** (years - 1)
    return ((1 + rate) ** years - (1 + growth) ** years) / (rate - growth)


def contributions_paid(annual: float, years: float, delay: float = 0.0,
                       growth: float = 0.0) -> float:
    """The sum of contributions made — the "your own money" half of a projection."""
    n = max(0.0, years - delay)
    if n == 0:
        return 0.0
    if growth == 0:
        return annual * n
    return annual * ((1 + growth) ** n - 1) / growth


def real_rate(nominal: float, inflation: float) -> float:
    return (1 + nominal) / (1 + inflation) - 1


def invested_balance(user: User) -> float:
    return sum(a.balance for a in user.accounts_of(*INVESTED_TYPES))


def current_annual_contributions(user: User) -> float:
    """What they already put in, plus any employer match already arriving. The
    'carry on as you are' baseline."""
    own = sum(a.contributions_ytd for a in user.accounts_of(*INVESTED_TYPES))
    match = sum(a.employer_match_received_ytd
                for a in user.accounts_of(AccountType.TRADITIONAL_401K))
    return own + match


def needed_at_retirement(user: User, year: int = L.DEFAULT_YEAR,
                         retire_at: int | None = None) -> float:
    """What you'd need on the day you retire, in today's money, for withdrawals to
    last to the plan-to age: the present value of each year's need, discounted at the
    real return in retirement, withdrawn at the start of each year."""
    start = max(retirement_age(user) if retire_at is None else retire_at, user.age)
    return _pv_of_spending(user, year, retirement_spending_annual(user), start)


def _pv_of_spending(user: User, year: int, spending_annual: float, start: int) -> float:
    r = real_rate(user.assumptions.retirement_return_rate, user.assumptions.inflation)
    ss = social_security_annual(user, year)
    claim = user.goal.social_security_claim_age
    return sum(
        max(0.0, spending_annual - (ss if age >= claim else 0.0)) / (1 + r) ** (age - start)
        for age in range(start, plan_to_age(user))
    )


def sustainable_spending_annual(user: User, year: int, available_today: float) -> float:
    """The most they could spend each year, in today's money, and still have it last
    to the plan-to age. Solved by bisection: the need rises steadily with spending, but
    Social Security starting partway through makes it piecewise, not a straight line."""
    start = max(retirement_age(user), user.age)
    low, high = 0.0, max(0.0, available_today) + social_security_annual(user, year) + 1.0
    for _ in range(60):
        mid = (low + high) / 2
        if _pv_of_spending(user, year, mid, start) <= available_today:
            low = mid
        else:
            high = mid
    return low


def depletion_age(user: User, year: int, balance_today: float,
                  start_age: int | None = None) -> int | None:
    """The age the money runs out, or None if it lasts to the plan-to age."""
    start = max(retirement_age(user) if start_age is None else start_age, user.age)
    r = real_rate(user.assumptions.retirement_return_rate, user.assumptions.inflation)
    balance = balance_today
    for age in range(start, plan_to_age(user)):
        need = net_need_today(user, age, year)
        if balance < need - 0.5:
            return age
        balance = (balance - need) * (1 + r)
    return None


def _projected_today(user: User, years: int, start_balance: float,
                     annual_contribution: float, delay: float) -> float:
    a = user.assumptions
    nominal = future_value(start_balance, annual_contribution, a.return_rate, years,
                           delay, a.contribution_growth)
    return nominal / (1 + a.inflation) ** years


def earliest_retirement_age(user: User, year: int, start_balance: float,
                            annual_contribution: float, delay: float) -> int | None:
    """The first age at which the plan, unchanged, pays for the spending to the
    plan-to age. The same savings buy more years of work-free life than most people
    guess, and fewer than some hope — this makes that concrete."""
    if retirement_spending_annual(user) <= 0:
        return None
    for candidate in range(user.age, min(plan_to_age(user), _EARLIEST_AGE_SEARCH_CAP + 1)):
        years = candidate - user.age
        have = _projected_today(user, years, start_balance, annual_contribution, delay)
        if have >= needed_at_retirement(user, year, candidate):
            return candidate
    return None


def readiness(user: User, year: int, start_balance: float,
              annual_contribution: float, delay: float = 0.0) -> dict:
    """Does the plan pay for retiring at the age they picked? And if not, the three
    levers — save more, retire later, spend less — each quantified."""
    a = user.assumptions
    ra = retirement_age(user)
    n = years_to_retirement(user)
    spending = retirement_spending_annual(user)
    projected = _projected_today(user, n, start_balance, annual_contribution, delay)
    needed = needed_at_retirement(user, year)

    result = {
        "retirement_age": ra,
        "years_to_retirement": n,
        "plan_to_age": plan_to_age(user),
        "retirement_spending_annual": round(spending),
        "social_security_annual": round(social_security_annual(user, year)),
        "social_security_provided": user.goal.social_security_monthly is not None,
        "social_security_claim_age": user.goal.social_security_claim_age,
        "projected_at_retirement": round(projected),
        "needed_at_retirement": round(needed),
        "funded_ratio": None,
        "gap": None,
        "extra_savings_per_year": None,
        "money_lasts_to_age": None,
        "earliest_retirement_age": None,
        "sustainable_monthly_spending": None,
        "status": "no_spending_info",
    }
    if spending <= 0:
        return result

    ratio = 1.0 if needed <= 0 else projected / needed
    gap = needed - projected
    extra = None
    if gap > 0 and n > 0:
        # Contributions are linear in the final balance, so the extra needed is the
        # gap divided by what one extra dollar a year grows into.
        per_dollar = future_value(0, 1, a.return_rate, n, 0, a.contribution_growth)
        extra = gap * (1 + a.inflation) ** n / per_dollar

    result.update(
        funded_ratio=round(ratio, 3),
        gap=round(max(0.0, gap)),
        extra_savings_per_year=None if extra is None else round(extra),
        money_lasts_to_age=depletion_age(user, year, projected),
        earliest_retirement_age=earliest_retirement_age(
            user, year, start_balance, annual_contribution, delay),
        sustainable_monthly_spending=math.floor(
            sustainable_spending_annual(user, year, projected) / 12),
        status="on_track" if ratio >= 1 else "close" if ratio >= 0.9 else "short",
    )
    return result


def bridge(user: User, year: int = L.DEFAULT_YEAR) -> dict:
    """Retiring before 59½: can you pay for the years before retirement accounts open
    up without the 10% penalty?

    Counted as reachable: a taxable brokerage (projected forward on its current
    contributions), cash beyond the emergency fund, and — when the Rule of 55 applies
    — the 401(k) from the job you leave. Roth IRA contributions are reachable too, but
    we don't track contribution basis, so they're described rather than counted.
    """
    data = ages(year)
    a = user.assumptions
    ra = retirement_age(user)
    penalty_free = data["penalty_free_withdrawal"]
    start = max(ra, user.age)
    if start >= penalty_free:
        return {"applies": False, "retirement_age": ra, "penalty_free_age": penalty_free}

    n = years_to_retirement(user)
    deflator = (1 + a.inflation) ** n
    r = real_rate(a.retirement_return_rate, a.inflation)
    # Through the whole year you turn 59 — slightly past 59½, on the cautious side.
    need = sum(
        net_need_today(user, age, year) / (1 + r) ** (age - start)
        for age in range(start, math.ceil(penalty_free))
    )

    def grow(accounts, with_match: bool = False) -> float:
        balance = sum(x.balance for x in accounts)
        yearly = sum(x.contributions_ytd + (x.employer_match_received_ytd if with_match else 0)
                     for x in accounts)
        return future_value(balance, yearly, a.return_rate, n, 0, a.contribution_growth) / deflator

    plans = user.accounts_of(AccountType.TRADITIONAL_401K)
    rule_of_55 = (bool(plans) or user.has_401k_at_work) and ra >= data["rule_of_55"]
    taxable = grow(user.accounts_of(AccountType.TAXABLE))
    cash = sum(x.balance for x in user.accounts_of(AccountType.CASH))
    spare_cash = max(0.0, cash - user.goal.emergency_fund_target)
    via_401k = grow(plans, with_match=True) if rule_of_55 else 0.0
    reachable = taxable + spare_cash + via_401k
    gap = max(0.0, need - reachable)

    annual = None
    if gap > 0 and n > 0:
        annual = gap * deflator / future_value(0, 1, a.return_rate, n, 0, a.contribution_growth)

    return {
        "applies": True,
        "retirement_age": ra,
        "penalty_free_age": penalty_free,
        "bridge_years": round(penalty_free - start, 1),
        "years_to_retirement": n,
        "spending_to_cover": round(need),
        "taxable_by_retirement": round(taxable),
        "cash_beyond_emergency_fund": round(spare_cash),
        "rule_of_55_applies": rule_of_55,
        "rule_of_55_age": data["rule_of_55"],
        "reachable_401k_by_retirement": round(via_401k),
        "reachable_total": round(reachable),
        "gap": round(gap),
        "annual_to_close_gap": None if annual is None else round(annual),
    }


def milestones(user: User, year: int = L.DEFAULT_YEAR) -> list[dict]:
    """The ages that matter between now and the end of the plan, in order."""
    data = ages(year)
    ss = data["social_security"]
    ra = retirement_age(user)
    claim = user.goal.social_security_claim_age
    factor = social_security_factor(claim, year)
    early_cut = 1 - social_security_factor(ss["earliest"], year)
    events = [
        (ra, "retire", "You stop working",
         "Contributions stop and withdrawals begin."),
        (data["penalty_free_withdrawal"], "access", "Retirement accounts open up",
         "401(k) and IRA withdrawals no longer carry the 10% early-withdrawal penalty."),
        (data["medicare"], "medicare", "Medicare begins",
         "Health coverage no longer depends on a job or the marketplace."),
        (claim, "claim", "You claim Social Security",
         f"At {claim} you get {factor:.0%} of your full-retirement-age benefit, for life."),
        (rmd_age(user, year), "rmd", "Required withdrawals begin",
         "Traditional accounts must start paying out a minimum each year."),
        (plan_to_age(user), "horizon", "Your plan runs to here",
         "The money is planned to last at least this long."),
    ]
    if claim != ss["earliest"]:
        events.append((ss["earliest"], "social_security", "Earliest Social Security",
                       f"Claiming this early pays about {early_cut:.0%} less for life "
                       f"than waiting until {ss['full']}."))
    return sorted(
        ({"age": age, "kind": kind, "label": label, "detail": detail}
         for age, kind, label, detail in events if age >= user.age),
        key=lambda e: (e["age"], e["kind"] != "retire"),
    )
