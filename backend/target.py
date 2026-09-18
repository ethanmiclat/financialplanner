"""Working backwards from a number.

Every other module runs forwards: here's what you save, here's where it gets you. This
one runs the other way — here's where you want to be, what does it take? That's the
question people actually arrive with, and the answer is only useful in the unit they
save in, so it comes back yearly, monthly, per paycheck and as a share of pay at once.

Three kinds of target, because "a goal for retirement" means different things:
  - `retirement` — fund the retirement already configured on the profile
  - `amount`     — a nest egg, in today's money ("I want a million")
  - `income`     — a monthly income in retirement ("I want $5,000 a month")

The arithmetic is the same closed-form growing annuity the projection uses, solved for
the contribution instead of the balance: a contribution is linear in the final balance,
so the required amount is the shortfall divided by what one dollar a year grows into.

Pure functions. Nothing here writes anything — an estimate is a question, not a change
of plan.
"""

from __future__ import annotations

import copy

import limits as L
import pay
import retirement as R
import waterfall as W
from models import User

GOALS = ("retirement", "amount", "income")
# "What does waiting cost?" — asked at the horizons where the answer still stings.
WAIT_YEARS = (1, 3, 5)


def _target_user(user: User, by_age: int | None, monthly: float | None) -> User:
    """A copy of the profile with the target applied. Validated, so a target that
    can't be planned — retiring after the money is meant to run out — is rejected with
    a message rather than quietly producing a number."""
    trial = copy.deepcopy(user)
    if by_age is not None:
        trial.goal.retirement_age = int(by_age)
    if monthly is not None:
        trial.goal.retirement_monthly_spending = float(monthly)
    R.validate(trial)
    return trial


def _required_annual(rate: float, growth: float, years: float, delay: float,
                     gap_nominal: float) -> float | None:
    """The level yearly contribution that closes `gap_nominal` by the target date.
    None when there's no time left to contribute in."""
    if gap_nominal <= 0:
        return 0.0
    per_dollar = R.future_value(0, 1, rate, years, delay, growth)
    return None if per_dollar <= 0 else gap_nominal / per_dollar


def _coast_age(user: User, start: float, annual: float, rate: float, growth: float,
               delay: float, years: int, needed_nominal: float) -> int | None:
    """The age you could stop contributing entirely and still arrive on time.

    Worth naming, because it reframes the whole exercise: the finish line isn't the
    target, it's the much earlier point where compounding alone can carry you there.
    """
    for k in range(years + 1):
        balance = R.future_value(start, annual, rate, k, delay, growth)
        if balance * (1 + rate) ** (years - k) >= needed_nominal - 0.5:
            return user.age + k
    return None


def _tax_advantaged_room(user: User, year: int) -> float:
    return sum(
        item.amount or 0
        for fn in (W.rule_hsa, W.rule_ira, W.rule_remaining_401k)
        for item in fn(user, year)
    )


def estimate(user: User, year: int = L.DEFAULT_YEAR, *, goal: str = "retirement",
             amount: float | None = None, monthly: float | None = None,
             by_age: int | None = None, starting_in: float = 0.0) -> dict:
    """What it takes to hit a target, in every unit somebody might save in."""
    if goal not in GOALS:
        raise ValueError(f"Unknown goal '{goal}'. Choose one of: {', '.join(GOALS)}")
    if goal == "amount" and (amount is None or amount < 0):
        raise ValueError("Tell us the amount you want to reach.")
    if goal == "income" and (monthly is None or monthly < 0):
        raise ValueError("Tell us the monthly income you want in retirement.")
    if starting_in < 0:
        raise ValueError("You can't start saving in the past.")

    trial = _target_user(user, by_age, monthly if goal == "income" else None)
    a = trial.assumptions
    rate, growth, inflation = a.return_rate, a.contribution_growth, a.inflation
    target_age = R.retirement_age(trial)
    years = R.years_to_retirement(trial)
    delay = min(starting_in, float(years))

    needed_today = (float(amount) if goal == "amount"
                    else R.needed_at_retirement(trial, year))
    deflator = (1 + inflation) ** years
    needed_nominal = needed_today * deflator

    start = R.invested_balance(user)
    from_balance = start * (1 + rate) ** years
    gap_nominal = needed_nominal - from_balance
    required_annual = _required_annual(rate, growth, years, delay, gap_nominal)

    planned = W.annual_investing(user, year)
    current_annual = planned["total"]
    extra_annual = (None if required_annual is None
                    else max(0.0, required_annual - current_annual))

    # The balance that, left alone, arrives on its own. Discounted at the growth rate
    # rather than inflation, so it's a balance for today, not a spending figure.
    coast_number = needed_nominal / (1 + rate) ** years if years else needed_nominal

    waiting = []
    for wait in WAIT_YEARS:
        if wait >= years:
            continue
        later = _required_annual(rate, growth, years, wait, gap_nominal)
        if later is None or required_annual is None:
            continue
        waiting.append({
            "wait_years": wait,
            "required": pay.amounts(user, later),
            "extra_per_month": round((later - required_annual) / 12, 2),
        })

    return {
        "year": year,
        "goal": goal,
        "target_age": target_age,
        "current_age": user.age,
        "years": years,
        "starting_in": round(delay, 2),
        "description": _describe(goal, trial, needed_today, target_age),
        "needed_at_target": round(needed_today),
        "already_have": round(start),
        "balance_grows_to": round(from_balance / deflator) if years else round(start),
        "shortfall": round(max(0.0, gap_nominal / deflator)),
        "on_track": required_annual == 0.0,
        "required": pay.amounts(user, required_annual),
        "current": pay.amounts(user, current_annual),
        "extra": pay.amounts(user, extra_annual),
        "coast": {
            "number": round(coast_number),
            "reached": start >= coast_number - 0.5,
            "age": _coast_age(user, start, current_annual, rate, growth,
                              planned["years_until_investing"], years, needed_nominal),
        },
        "cost_of_waiting": waiting,
        "notes": _notes(user, trial, year, goal, required_annual, current_annual,
                        needed_today, years, planned),
        "disclaimer": (
            "An illustration on your own numbers at the return you've assumed — not a "
            "forecast or a promise. Real markets don't deliver the same return every "
            "year, so treat this as the size of the task, not a schedule to trust."
        ),
    }


def _describe(goal: str, trial: User, needed_today: float, target_age: int) -> str:
    if goal == "amount":
        return f"Reach ${needed_today:,.0f} in today's money by age {target_age}"
    if goal == "income":
        monthly = R.retirement_spending_annual(trial) / 12
        return (f"Retire at {target_age} on ${monthly:,.0f} a month, lasting until "
                f"{R.plan_to_age(trial)}")
    return (f"Fund the retirement you've planned — stopping at {target_age}, with the "
            f"money lasting to {R.plan_to_age(trial)}")


def _notes(user: User, trial: User, year: int, goal: str, required: float | None,
           current: float, needed_today: float, years: int, planned: dict) -> list[str]:
    notes: list[str] = []

    if years <= 0:
        notes.append(
            "You're already at the age you're planning to, so there are no saving years "
            "left to spread this across. The levers now are spending, when you claim "
            "Social Security, and how long the money has to last.")
        return notes

    if required is None:
        return notes

    if required == 0:
        notes.append(
            "What you already have invested gets there on its own at this return, "
            "without another dollar going in. That's worth knowing before you commit to "
            "a bigger number than you need.")
    elif user.income and required > user.income:
        notes.append(
            "This asks for more than you earn in a year, which means the target can't be "
            "reached by saving alone from here. A later date, a smaller number, or both, "
            "is the honest way through.")
    elif required > current:
        room = _tax_advantaged_room(user, year)
        if required > room:
            notes.append(
                f"Your tax-advantaged room this year is about ${room:,.0f}, so roughly "
                f"${required - room:,.0f} of this would go into a taxable brokerage "
                f"account. That still works — it just doesn't get the tax break.")

    if planned["one_off_first"] > 0:
        notes.append(
            f"This assumes the money starts being invested now. Your plan clears "
            f"${planned['one_off_first']:,.0f} of debt and emergency fund first, which "
            f"takes about {planned['years_until_investing']:.1f} years — real progress, "
            f"but not years of compounding.")

    if user.take_home_per_paycheck is not None and required:
        spare = (user.take_home_per_paycheck * pay.paychecks_per_year(user)
                 - user.goal.monthly_expenses * 12)
        if required > spare:
            notes.append(
                f"After your bills you have about ${max(0.0, spare):,.0f} a year left, so "
                f"this doesn't fit your current take-home pay. Money going into a "
                f"traditional 401(k) costs you less than it puts away, because it comes "
                f"out before tax — but the gap here is bigger than that covers.")

    if goal != "amount" and not trial.goal.social_security_monthly:
        notes.append(
            "No Social Security is counted, because we don't have your estimate. Adding "
            "it from ssa.gov will lower this figure, probably by a lot.")

    return notes
