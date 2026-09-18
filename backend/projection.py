"""Projections — what the plan is worth over time, and whether it lasts.

The point of this module is motivational honesty. A 20-year-old putting $100 a month
into a Roth IRA sees a number that feels pointless; the same number over 45 years is
the entire argument for starting now. So we show it — with the assumptions stated on
the face of the result, three return scenarios rather than one confident line, and
both nominal and inflation-adjusted figures.

The line doesn't stop at retirement. It grows until the age the user picked, then pays
for their spending until the age the money has to last to — which is where "is this
enough?" actually gets answered. Every assumption is the user's to change, and
`with_overrides` lets the projection page try a different age, return or spending
level without saving anything.

This is an illustration of compound growth, not a forecast. Returns are an assumption
the user can change, not a prediction we're making, and the payload says so.
"""

from __future__ import annotations

import copy
import math

import limits as L
import retirement as R
import waterfall as W
from models import User

# The arithmetic lives with the rest of the retirement maths now; these names stay
# importable from here.
future_value = R.future_value
invested_balance = R.invested_balance
current_annual_contributions = R.current_annual_contributions

# Long-run assumptions. Deliberately three, so no single number reads as a promise.
SCENARIOS = {
    "cautious": {"label": "If markets are kind to you", "rate": 0.05},
    "middling": {"label": "Roughly the long-run average", "rate": 0.07},
    "strong": {"label": "If markets do well", "rate": 0.09},
}
DEFAULT_SCENARIO = "middling"
YOURS = "yours"   # the user's own return assumption, when it isn't one of the three

# What the projection page can try out without saving: field -> (where it lives,
# how to parse it, whether blank means "use the default").
WHAT_IF_FIELDS = {
    "retirement_age": ("goal", int, False),
    "plan_to_age": ("goal", int, False),
    "retirement_monthly_spending": ("goal", float, True),
    "social_security_monthly": ("goal", float, True),
    "social_security_claim_age": ("goal", int, False),
    "return_rate": ("assumptions", float, False),
    "retirement_return_rate": ("assumptions", float, False),
    "inflation": ("assumptions", float, False),
    "contribution_growth": ("assumptions", float, False),
    "annual_savings_capacity": ("user", float, True),
    # Added for the free-text bot's "what if I made $75k" scenario. Anything that
    # overrides income must re-run `pay.sync_capacity` afterwards, or a percent-of-pay
    # savings plan silently keeps the old salary's dollar figure.
    "income": ("user", float, False),
}


def with_overrides(user: User, overrides: dict) -> User:
    """A what-if copy of the profile. Nothing is saved — this is what lets someone
    drag the retirement age from 67 to 50 and watch the plan respond before committing."""
    trial = copy.deepcopy(user)
    for key, raw in overrides.items():
        if key not in WHAT_IF_FIELDS:
            raise ValueError(f"'{key}' isn't something the projection can try out.")
        where, cast, blank_allowed = WHAT_IF_FIELDS[key]
        if raw in (None, "", "null"):
            if not blank_allowed:
                raise ValueError(f"'{key}' needs a value.")
            value = None
        else:
            try:
                number = float(raw)
            except (TypeError, ValueError):
                raise ValueError(f"'{key}' must be a number.") from None
            if not math.isfinite(number):
                raise ValueError(f"'{key}' must be a number.")
            if cast is int and number != int(number):
                raise ValueError(f"'{key}' must be a whole number.")
            value = int(number) if cast is int else number
        target = {"goal": trial.goal, "assumptions": trial.assumptions, "user": trial}[where]
        setattr(target, key, value)

    if trial.annual_savings_capacity is not None and trial.annual_savings_capacity < 0:
        raise ValueError("What you can save can't be negative.")
    R.validate(trial)
    return trial


def scenarios(user: User) -> dict:
    """The three standard scenarios, plus the user's own return when it's different."""
    options = {key: dict(s) for key, s in SCENARIOS.items()}
    rate = user.assumptions.return_rate
    if not any(math.isclose(s["rate"], rate) for s in SCENARIOS.values()):
        options[YOURS] = {"label": "The return you set", "rate": rate}
    return options


def default_scenario(user: User) -> str:
    rate = user.assumptions.return_rate
    return next((key for key, s in SCENARIOS.items() if math.isclose(s["rate"], rate)), YOURS)


def planned_annual_contributions(user: User, year: int) -> dict:
    return W.annual_investing(user, year)


def horizons(user: User) -> list[int]:
    """Milestones while saving: 5, 10 and 20 years where they fall before retirement,
    plus retirement itself — for a young user, the number that makes the case."""
    to_retirement = R.years_to_retirement(user)
    return sorted({m for m in (5, 10, 20) if m < to_retirement} | {to_retirement})


def _line(user: User, year: int, start: float, annual: float, rate: float,
          delay: float) -> tuple[list[float], list[float], int | None]:
    """One balance per year from today to the plan-to age: growing until retirement,
    then paying for it. Returns the balances, what was withdrawn in the year leading to
    each one, and the age the money ran out (None if it lasted)."""
    a = user.assumptions
    saving_years = R.years_to_retirement(user)
    balances: list[float] = []
    withdrawn: list[float] = []
    ran_out = None
    balance = start
    for n in range(R.plan_to_age(user) - user.age + 1):
        if n <= saving_years:
            balance = R.future_value(start, annual, rate, n, delay, a.contribution_growth)
            withdrawn.append(0.0)
        else:
            age = user.age + n - 1
            need = R.net_need_today(user, age, year) * (1 + a.inflation) ** (n - 1)
            taken = min(balance, need)
            if taken < need - 0.5 and ran_out is None:
                ran_out = age
            balance = (balance - taken) * (1 + a.retirement_return_rate)
            withdrawn.append(taken)
        balances.append(balance)
    return balances, withdrawn, ran_out


def project(user: User, year: int = L.DEFAULT_YEAR, scenario: str | None = None) -> dict:
    options = scenarios(user)
    default = default_scenario(user)
    scenario = scenario or default
    if scenario not in options:
        raise ValueError(
            f"Unknown scenario '{scenario}'. Choose one of: {', '.join(options)}"
        )
    rate = options[scenario]["rate"]

    # The readiness check and the chart must agree, so both run on the scenario's rate.
    user = copy.deepcopy(user)
    user.assumptions.return_rate = rate
    a = user.assumptions

    start = R.invested_balance(user)
    baseline = R.current_annual_contributions(user)
    planned = W.annual_investing(user, year)
    delay = planned["years_until_investing"]
    saving_years = R.years_to_retirement(user)

    plan_values, withdrawn, plan_ran_out = _line(user, year, start, planned["total"], rate, delay)
    pace_values, _, pace_ran_out = _line(user, year, start, baseline, rate, 0.0)

    # A yearly series for the chart. Milestone `points` below are the readable summary;
    # this is the shape of the curve, which is the actual argument.
    series = [
        {
            "years": n,
            "age": user.age + n,
            "phase": "retired" if n > saving_years else "saving",
            "current_pace": round(pace_values[n]),
            "following_plan": round(plan_values[n]),
            "withdrawn": round(withdrawn[n]),
        }
        for n in range(len(plan_values))
    ]

    points = []
    for n in horizons(user):
        deflator = (1 + a.inflation) ** n
        paid_in = start + R.contributions_paid(planned["total"], n, delay, a.contribution_growth)
        plan_value = plan_values[n]
        points.append({
            "years": n,
            "age": user.age + n,
            "is_retirement": n == saving_years,
            "current_pace": round(pace_values[n]),
            "following_plan": round(plan_value),
            "difference": round(plan_value - pace_values[n]),
            "following_plan_todays_money": round(plan_value / deflator),
            "contributed_by_then": round(paid_in),
            "growth_by_then": round(plan_value - paid_in),
        })

    readiness = R.readiness(user, year, start, planned["total"], delay)
    readiness["plan_runs_out_age"] = plan_ran_out
    readiness["current_pace_runs_out_age"] = pace_ran_out

    return {
        "year": year,
        "scenario": scenario,
        "default_scenario": default,
        "scenarios": options,
        "series": series,
        "starting_balance": round(start),
        "current_annual_contributions": round(baseline),
        "planned_annual_contributions": {
            k: round(v, 1) if k == "years_until_investing" else round(v)
            for k, v in planned.items()
        },
        "retirement_age": R.retirement_age(user),
        "plan_to_age": R.plan_to_age(user),
        "years_to_retirement": saving_years,
        "retirement": readiness,
        "milestones": R.milestones(user, year),
        "settings": _settings(user),
        "points": points,
        "assumptions": _assumption_notes(user, year, planned, rate),
        "disclaimer": (
            "An illustration of how compounding works on your numbers — not a forecast, "
            "a promise, or a recommendation to buy anything. Investments can lose money."
        ),
    }


def _settings(user: User) -> dict:
    """The values this projection actually used — what the what-if controls start from."""
    goal, a = user.goal, user.assumptions
    return {
        "age": user.age,
        "retirement_age": R.retirement_age(user),
        "plan_to_age": R.plan_to_age(user),
        "retirement_monthly_spending": goal.retirement_monthly_spending,
        "retirement_monthly_spending_effective": round(R.retirement_spending_annual(user) / 12),
        "social_security_monthly": goal.social_security_monthly,
        "social_security_claim_age": goal.social_security_claim_age,
        "return_rate": a.return_rate,
        "retirement_return_rate": a.retirement_return_rate,
        "inflation": a.inflation,
        "contribution_growth": a.contribution_growth,
        "annual_savings_capacity": user.annual_savings_capacity,
    }


def _assumption_notes(user: User, year: int, planned: dict, rate: float) -> list[str]:
    a = user.assumptions
    ra, plan_to = R.retirement_age(user), R.plan_to_age(user)
    ss = R.social_security_annual(user, year)

    if a.contribution_growth:
        saving = (f"You contribute {_fmt(planned['total'])} a year, rising "
                  f"{_pct(a.contribution_growth)} each year, until {ra}.")
    else:
        saving = (f"You keep contributing {_fmt(planned['total'])} a year, without increasing "
                  f"it, until {ra}. Most people's contributions rise with their income, so "
                  f"this is on the conservative side.")
    if planned["one_off_first"]:
        saving += (f" The first {_fmt(planned['one_off_first'])} of your saving clears debt "
                   f"and builds your cash cushion, so investing starts after about "
                   f"{planned['years_until_investing']:.1f} years.")

    spending = (f"From {ra} to {plan_to} you spend "
                f"{_fmt(R.retirement_spending_annual(user))} a year in today's money, rising "
                f"with inflation")
    spending += (f", with {_fmt(ss)} a year of Social Security from "
                 f"{user.goal.social_security_claim_age}." if ss else
                 ", with no Social Security counted because we don't have your estimate.")

    return [
        f"A steady {_pct(rate)} return every year until you retire, then "
        f"{_pct(a.retirement_return_rate)} after — retirees usually hold a steadier mix. Real "
        f"markets don't move in straight lines, and a bad few years just after retiring "
        f"hurts more than the same years later on.",
        saving,
        spending,
        f"Today's-money figures assume {_pct(a.inflation)} inflation, so you can compare "
        f"them with what things cost now.",
        "Tax isn't modelled. A Roth balance is yours to keep; a traditional balance has "
        "income tax still to pay on withdrawal, so it stretches less far.",
        "Future contribution limits aren't applied — if the plan saves more than your "
        "accounts can take, the rest is assumed to grow in a taxable account instead.",
    ]


def _fmt(x: float) -> str:
    return f"${x:,.0f}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}".rstrip("0").rstrip(".") + "%"
