import pytest

import projection as P
from models import Account, AccountType, Debt, FilingStatus, Goal, User


def base_user(**kw) -> User:
    defaults = dict(
        age=30, income=60_000, filing_status=FilingStatus.SINGLE,
        goal=Goal(monthly_expenses=2_000, emergency_fund_months=3, retirement_age=67),
        accounts=[
            Account(type=AccountType.CASH, balance=6_000),
            Account(type=AccountType.IRA, balance=10_000, contributions_ytd=1_000),
        ],
        annual_savings_capacity=6_000,
    )
    defaults.update(kw)
    return User(**defaults)


# --- the maths -----------------------------------------------------------------


def test_future_value_matches_the_closed_form():
    # $1,000 at 10% for 1 year, plus a $100 contribution at year end.
    assert P.future_value(1_000, 100, 0.10, 1) == pytest.approx(1_200)
    # No growth: it's just the sum.
    assert P.future_value(1_000, 100, 0.0, 10) == pytest.approx(2_000)
    # No time: nothing has happened yet.
    assert P.future_value(1_000, 500, 0.07, 0) == pytest.approx(1_000)


def test_delay_defers_contributions_but_not_the_starting_balance():
    no_delay = P.future_value(1_000, 1_000, 0.07, 10)
    delayed = P.future_value(1_000, 1_000, 0.07, 10, delay=3)
    assert delayed < no_delay
    # The principal still compounds for the full ten years.
    assert delayed > 1_000 * 1.07 ** 10
    # A delay past the horizon means no contributions land at all.
    assert P.future_value(1_000, 1_000, 0.07, 5, delay=9) == pytest.approx(1_000 * 1.07 ** 5)


def test_growth_is_monotonic_in_rate_and_time():
    prev = 0
    for rate in (0.0, 0.05, 0.07, 0.09):
        v = P.future_value(1_000, 500, rate, 20)
        assert v > prev
        prev = v
    values = [P.future_value(1_000, 500, 0.07, n) for n in range(0, 40, 5)]
    assert values == sorted(values)


# --- one-off vs recurring ------------------------------------------------------


def test_debt_and_emergency_fund_are_one_off_not_annual():
    """The bug this guards: treating a card payoff as a recurring cost projected
    "$0 invested a year, forever"."""
    user = base_user(
        accounts=[Account(type=AccountType.CASH, balance=0),
                  Account(type=AccountType.IRA, balance=0)],
        debts=[Debt("Card", 1_200, 0.25)],
        annual_savings_capacity=6_000,
    )
    planned = P.planned_annual_contributions(user, 2026)
    assert planned["total"] == 6_000, "recurring investing must survive one-off costs"
    assert planned["one_off_first"] > 0
    assert planned["years_until_investing"] > 0


def test_no_one_off_costs_means_no_delay():
    user = base_user(accounts=[
        Account(type=AccountType.CASH, balance=100_000),   # cushion already full
        Account(type=AccountType.IRA, balance=10_000),
    ])
    assert P.planned_annual_contributions(user, 2026)["years_until_investing"] == 0


def test_capacity_unset_falls_back_to_current_contributions():
    """Without a stated capacity we must not invent money the user doesn't have."""
    user = base_user(annual_savings_capacity=None)
    planned = P.planned_annual_contributions(user, 2026)
    assert planned["total"] == P.current_annual_contributions(user)
    assert planned["one_off_first"] == 0


def test_employer_match_is_counted_but_capped():
    plan = Account(type=AccountType.TRADITIONAL_401K, balance=0,
                   employer_match_rate=0.5, employer_match_limit_pct=0.06)
    user = base_user(income=100_000, annual_savings_capacity=20_000,
                     accounts=[Account(type=AccountType.CASH, balance=100_000), plan])
    planned = P.planned_annual_contributions(user, 2026)
    # Match is 50% of the first 6% of $100k = $6,000 deferral -> $3,000, not 50% of 20k.
    assert planned["employer_match"] == pytest.approx(3_000)
    assert planned["total"] == pytest.approx(23_000)


# --- the projection payload ----------------------------------------------------


def test_following_the_plan_beats_the_current_pace():
    result = P.project(base_user())
    assert all(p["following_plan"] >= p["current_pace"] for p in result["points"])
    assert result["points"][-1]["difference"] > 0


def test_horizons_include_retirement():
    result = P.project(base_user(age=20, goal=Goal(monthly_expenses=900, retirement_age=67)))
    assert result["points"][-1]["years"] == 47
    assert result["points"][-1]["age"] == 67
    assert result["points"][-1]["is_retirement"] is True


def test_growth_and_contributions_reconcile():
    for point in P.project(base_user())["points"]:
        assert point["contributed_by_then"] + point["growth_by_then"] == pytest.approx(
            point["following_plan"], abs=1
        )


def test_todays_money_is_lower_than_nominal():
    for point in P.project(base_user())["points"]:
        if point["years"] > 0:
            assert point["following_plan_todays_money"] < point["following_plan"]


def test_scenarios_are_ordered():
    values = [
        P.project(base_user(), scenario=s)["points"][-1]["following_plan"]
        for s in ("cautious", "middling", "strong")
    ]
    assert values == sorted(values)


def test_assumptions_and_disclaimer_always_present():
    result = P.project(base_user())
    assert len(result["assumptions"]) >= 4
    assert "not a forecast" in result["disclaimer"]


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError, match="reckless"):
        P.project(base_user(), scenario="reckless")


def test_empty_profile_does_not_crash():
    result = P.project(User(age=22, income=0))
    assert result["starting_balance"] == 0
    assert all(p["following_plan"] >= 0 for p in result["points"])


def test_series_runs_past_retirement_and_draws_down():
    """The chart needs the whole shape: growth while saving, then spending it."""
    result = P.project(base_user(age=30))
    series = result["series"]
    assert [p["years"] for p in series] == list(range(0, 66))      # age 30 to 95
    assert series[0]["following_plan"] == result["starting_balance"]
    saving = [p["following_plan"] for p in series if p["phase"] == "saving"]
    assert len(saving) == 38 and saving == sorted(saving)
    retired = [p for p in series if p["phase"] == "retired"]
    assert retired[0]["age"] == 68 and retired[0]["withdrawn"] > 0


def test_series_agrees_with_milestone_points():
    result = P.project(base_user())
    by_year = {p["years"]: p for p in result["series"]}
    for point in result["points"]:
        assert by_year[point["years"]]["following_plan"] == point["following_plan"]
