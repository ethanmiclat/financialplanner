"""The plan run backwards: what reaching a number actually costs."""

import pytest

import retirement as R
import target as T
from models import Account, AccountType, Goal, PayFrequency, User


def make_user(**kw) -> User:
    defaults = dict(
        age=35, income=60_000, annual_savings_capacity=12_000,
        pay_frequency=PayFrequency.BIWEEKLY, take_home_per_paycheck=1_800,
        has_401k_at_work=False,
        goal=Goal(monthly_expenses=2_000, emergency_fund_months=3, retirement_age=65),
        accounts=[
            Account(type=AccountType.CASH, balance=6_000),        # cushion already full
            Account(type=AccountType.TAXABLE, balance=50_000),
        ],
    )
    defaults.update(kw)
    return User(**defaults)


def grown(user: User, annual: float, years: int, delay: float = 0.0) -> float:
    a = user.assumptions
    return R.future_value(R.invested_balance(user), annual, a.return_rate, years,
                          delay, a.contribution_growth)


# --- the arithmetic ------------------------------------------------------------


def test_the_required_amount_actually_reaches_the_target():
    user = make_user()
    est = T.estimate(user, 2026, goal="amount", amount=1_000_000)
    nominal_target = 1_000_000 * (1 + user.assumptions.inflation) ** est["years"]
    assert grown(user, est["required"]["annual"], est["years"]) == pytest.approx(
        nominal_target, rel=1e-6)


def test_every_unit_describes_the_same_money():
    req = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000)["required"]
    assert req["monthly"] * 12 == pytest.approx(req["annual"], abs=0.5)
    assert req["per_paycheck"] * 26 == pytest.approx(req["annual"], abs=0.5)
    assert req["percent_of_pay"] == pytest.approx(req["annual"] / 60_000, abs=0.001)


def test_per_paycheck_follows_how_often_you_are_paid():
    weekly = T.estimate(make_user(pay_frequency=PayFrequency.WEEKLY), 2026,
                        goal="amount", amount=1_000_000)["required"]
    assert weekly["paychecks_per_year"] == 52
    assert weekly["per_paycheck"] * 52 == pytest.approx(weekly["annual"], abs=0.5)


def test_a_bigger_target_costs_more_and_an_earlier_one_costs_more_still():
    small = T.estimate(make_user(), 2026, goal="amount", amount=500_000)
    big = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000)
    sooner = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000, by_age=55)
    assert big["required"]["annual"] > small["required"]["annual"]
    assert sooner["required"]["annual"] > big["required"]["annual"]


def test_what_you_already_have_counts_toward_it():
    poorer = make_user(accounts=[Account(type=AccountType.CASH, balance=6_000)])
    with_savings = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000)
    without = T.estimate(poorer, 2026, goal="amount", amount=1_000_000)
    assert without["required"]["annual"] > with_savings["required"]["annual"]
    assert with_savings["already_have"] == 50_000


def test_a_target_your_balance_already_covers_asks_for_nothing():
    rich = make_user(accounts=[Account(type=AccountType.TAXABLE, balance=900_000)])
    est = T.estimate(rich, 2026, goal="amount", amount=1_000_000)
    assert est["on_track"] is True
    assert est["required"]["annual"] == 0
    assert est["shortfall"] == 0
    assert any("without another dollar" in n for n in est["notes"])


# --- the three kinds of goal ---------------------------------------------------


def test_the_default_goal_prices_the_retirement_on_the_profile():
    user = make_user()
    est = T.estimate(user, 2026)
    assert est["target_age"] == 65
    assert est["needed_at_target"] == round(R.needed_at_retirement(user, 2026))


def test_a_monthly_income_goal_asks_for_more_when_the_income_is_higher():
    modest = T.estimate(make_user(), 2026, goal="income", monthly=3_000)
    lavish = T.estimate(make_user(), 2026, goal="income", monthly=8_000)
    assert lavish["needed_at_target"] > modest["needed_at_target"]
    assert lavish["required"]["annual"] > modest["required"]["annual"]
    assert "$8,000 a month" in lavish["description"]


def test_the_income_goal_is_not_saved_to_the_profile():
    user = make_user()
    T.estimate(user, 2026, goal="income", monthly=9_000, by_age=50)
    assert user.goal.retirement_monthly_spending is None
    assert user.goal.retirement_age == 65


# --- what it compares against --------------------------------------------------


def test_it_says_how_far_off_the_current_plan_is():
    est = T.estimate(make_user(), 2026, goal="amount", amount=2_000_000)
    assert est["current"]["annual"] == pytest.approx(12_000)
    assert est["extra"]["annual"] == pytest.approx(
        est["required"]["annual"] - 12_000, abs=0.5)


def test_waiting_to_start_raises_the_monthly_figure():
    est = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000)
    waits = est["cost_of_waiting"]
    assert [w["wait_years"] for w in waits] == [1, 3, 5]
    assert all(w["extra_per_month"] > 0 for w in waits)
    assert waits[2]["required"]["monthly"] > waits[0]["required"]["monthly"]
    # Starting late is the same as asking for the figure with a delay.
    delayed = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000, starting_in=3)
    assert delayed["required"]["annual"] == pytest.approx(waits[1]["required"]["annual"])


def test_the_coast_number_is_the_point_you_could_stop():
    est = T.estimate(make_user(), 2026, goal="amount", amount=1_000_000)
    coast = est["coast"]
    assert coast["number"] < est["needed_at_target"]
    assert coast["reached"] is False
    # Left completely alone from the coast number, the balance still lands on target.
    a = make_user().assumptions
    assert coast["number"] * (1 + a.return_rate) ** est["years"] == pytest.approx(
        1_000_000 * (1 + a.inflation) ** est["years"], rel=1e-3)


def test_reaching_the_coast_number_is_reported():
    rich = make_user(accounts=[Account(type=AccountType.TAXABLE, balance=300_000)])
    coast = T.estimate(rich, 2026, goal="amount", amount=1_000_000)["coast"]
    assert coast["reached"] is True
    assert coast["age"] == 35


def test_an_unreachable_target_says_so_rather_than_quoting_a_number():
    est = T.estimate(make_user(), 2026, goal="amount", amount=50_000_000, by_age=40)
    assert any("more than you earn" in n for n in est["notes"])


def test_no_saving_years_left_returns_no_figure():
    est = T.estimate(make_user(age=65), 2026, goal="amount", amount=1_000_000)
    assert est["years"] == 0
    assert est["required"]["annual"] is None
    assert any("no saving years left" in n for n in est["notes"])


def test_it_flags_money_that_would_not_fit_in_tax_advantaged_accounts():
    # Demanding, but inside what they earn — an unreachable target reports that
    # instead, and where the overflow would land is noise at that point.
    est = T.estimate(make_user(), 2026, goal="amount", amount=700_000, by_age=50)
    assert est["required"]["annual"] < 60_000
    assert any("taxable brokerage" in n for n in est["notes"])


def test_it_flags_a_figure_the_paycheck_cannot_cover():
    est = T.estimate(make_user(), 2026, goal="amount", amount=700_000, by_age=50)
    assert any("take-home pay" in n for n in est["notes"])


# --- rejected input ------------------------------------------------------------


@pytest.mark.parametrize("kwargs, message", [
    ({"goal": "lottery"}, "Unknown goal"),
    ({"goal": "amount"}, "amount you want to reach"),
    ({"goal": "income"}, "monthly income"),
    ({"goal": "amount", "amount": 1_000, "by_age": 99}, "between 18 and 90"),
    ({"goal": "amount", "amount": 1_000, "starting_in": -2}, "in the past"),
])
def test_targets_that_cannot_be_planned_are_rejected(kwargs, message):
    with pytest.raises(ValueError, match=message):
        T.estimate(make_user(), 2026, **kwargs)


def test_a_target_age_past_the_end_of_the_plan_is_rejected():
    user = make_user(goal=Goal(monthly_expenses=2_000, retirement_age=65, plan_to_age=70))
    with pytest.raises(ValueError, match="last past age 75"):
        T.estimate(user, 2026, goal="amount", amount=1_000, by_age=75)


# --- endpoint ------------------------------------------------------------------


def test_target_endpoint(client):
    body = client.get("/api/target").get_json()
    assert body["goal"] == "retirement"
    assert body["required"]["monthly"] is not None
    assert body["disclaimer"]

    amount = client.get("/api/target?goal=amount&amount=1000000&by_age=60").get_json()
    assert amount["target_age"] == 60
    assert amount["needed_at_target"] == 1_000_000

    income = client.get("/api/target?goal=income&monthly=4000").get_json()
    assert income["needed_at_target"] > 0


def test_target_endpoint_rejects_nonsense(client):
    assert client.get("/api/target?goal=amount").status_code == 400
    assert client.get("/api/target?goal=amount&amount=abc").status_code == 400
    assert client.get("/api/target?by_age=62.5").status_code == 400


def test_the_estimator_leaves_the_profile_alone(client):
    before = client.get("/api/profile").get_json()
    client.get("/api/target?goal=income&monthly=9000&by_age=45")
    assert client.get("/api/profile").get_json() == before
