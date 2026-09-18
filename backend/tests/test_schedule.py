"""The plan as a calendar: what moves this month, what comes out of each paycheck,
and when each step finishes."""

from datetime import date

import pytest

import schedule as S
from models import Account, AccountType, Debt, Goal, PayFrequency, User

MARCH = date(2026, 3, 14)


def make_user(**kw) -> User:
    defaults = dict(
        age=35, income=60_000, annual_savings_capacity=12_000,
        pay_frequency=PayFrequency.BIWEEKLY, take_home_per_paycheck=1_800,
        has_401k_at_work=False,
        goal=Goal(monthly_expenses=2_000, emergency_fund_months=3),
        accounts=[Account(type=AccountType.CASH, balance=6_000)],   # cushion already full
    )
    defaults.update(kw)
    return User(**defaults)


def first_month(user: User, **kw) -> dict:
    return S.schedule(user, 2026, start=MARCH, **kw)["this_month"]


def labels(month: dict) -> list[str]:
    return [m["rule_id"] for m in month["moves"]]


# --- the monthly amount --------------------------------------------------------


def test_monthly_savings_is_the_yearly_figure_split_twelve_ways():
    assert S.monthly_savings(make_user()) == pytest.approx(1_000)


def test_per_paycheck_follows_how_often_you_are_paid():
    biweekly = first_month(make_user())["moves"][0]
    assert biweekly["per_paycheck"] == pytest.approx(1_000 * 12 / 26, abs=0.01)
    monthly = first_month(make_user(pay_frequency=PayFrequency.MONTHLY))["moves"][0]
    assert monthly["per_paycheck"] == pytest.approx(1_000)


def test_without_a_stated_capacity_it_schedules_current_contributions_only():
    user = make_user(annual_savings_capacity=None, accounts=[
        Account(type=AccountType.CASH, balance=6_000),
        Account(type=AccountType.IRA, balance=5_000, contributions_ytd=2_400),
    ])
    plan = S.schedule(user, 2026, start=MARCH)
    assert plan["capacity_set"] is False
    assert plan["monthly_savings"] == pytest.approx(200)


# --- order and finishing -------------------------------------------------------


def test_the_cushion_comes_before_investing():
    user = make_user(accounts=[Account(type=AccountType.CASH, balance=1_000)])
    assert labels(first_month(user))[0] == "R1_EMERGENCY_FUND"


def test_a_finished_step_hands_over_to_the_next_one():
    user = make_user(accounts=[Account(type=AccountType.CASH, balance=5_500)])
    month = first_month(user)
    assert labels(month)[:2] == ["R1_EMERGENCY_FUND", "R5_IRA"]
    assert month["moves"][0]["completes"] is True
    assert month["milestones"] == ["Emergency fund — done"]
    # Next month the cushion is gone from the list entirely.
    assert "R1_EMERGENCY_FUND" not in labels(S.schedule(user, 2026, start=MARCH)["months"][1])


def test_debt_accrues_interest_and_the_minimum_payment_is_treated_as_a_bill():
    user = make_user(annual_savings_capacity=0,
                     debts=[Debt("Card", 1_000, 0.24, minimum_payment=50)])
    months = S.schedule(user, 2026, months=2, start=MARCH)["months"]
    assert months[0]["moves"] == []          # nothing spare to throw at it
    # 1,000 -> +2% interest -> -50 minimum, twice over.
    user2 = make_user(annual_savings_capacity=12_000,
                      debts=[Debt("Card", 1_000, 0.24, minimum_payment=50)])
    month = first_month(user2)
    card = next(m for m in month["moves"] if m["rule_id"] == "R3_HIGH_INTEREST_DEBT")
    assert card["amount"] == pytest.approx(1_000 * 1.02 - 50)
    assert card["completes"] is True
    assert "Card (24% APR)" in card["label"]


def test_payroll_money_is_paced_across_the_year_not_front_loaded():
    plan = Account(type=AccountType.TRADITIONAL_401K, contributions_ytd=0)
    user = make_user(annual_savings_capacity=120_000, has_401k_at_work=True,
                     accounts=[Account(type=AccountType.CASH, balance=6_000), plan])
    month = first_month(user)
    k401 = next(m for m in month["moves"] if m["rule_id"] == "R6_REMAINING_401K")
    assert k401["amount"] == pytest.approx(24_500 / 10)      # March: ten months left
    assert k401["payroll"] is True
    assert k401["percent_of_pay"] == pytest.approx(24_500 / 10 * 12 / 60_000, abs=0.001)


def test_leftover_money_lands_in_a_taxable_account():
    user = make_user(annual_savings_capacity=120_000)
    month = first_month(user)
    assert labels(month)[-1] == "R7_TAXABLE"
    assert month["total"] == pytest.approx(10_000)


def test_annual_room_refills_in_january():
    user = make_user(annual_savings_capacity=120_000)
    months = S.schedule(user, 2026, months=12, start=MARCH)["months"]
    assert "R5_IRA" in labels(months[0])                      # March 2026
    assert all("R5_IRA" not in labels(m) for m in months[1:10])
    january = next(m for m in months if m["label"].startswith("January"))
    assert "R5_IRA" in labels(january)


# --- payday --------------------------------------------------------------------


def test_payday_view_subtracts_bills_and_transfers_but_not_deferrals():
    plan = Account(type=AccountType.TRADITIONAL_401K, employer_match_rate=0.5,
                   employer_match_limit_pct=0.06)
    user = make_user(has_401k_at_work=True,
                     accounts=[Account(type=AccountType.CASH, balance=6_000), plan])
    pay = S.schedule(user, 2026, start=MARCH)["paycheck"]
    assert pay["paychecks_per_year"] == 26
    assert pay["bills"] == pytest.approx(2_000 * 12 / 26, abs=0.01)
    assert pay["payroll_deferrals"] > 0
    assert pay["free_to_spend"] == pytest.approx(pay["take_home"] - pay["bills"] - pay["transfers"], abs=0.01)


def test_an_unaffordable_plan_shows_a_negative_leftover():
    user = make_user(annual_savings_capacity=60_000)      # $5k a month on $1,800 a payday
    assert S.schedule(user, 2026, start=MARCH)["paycheck"]["free_to_spend"] < 0


def test_unknown_take_home_says_so_rather_than_guessing():
    plan = S.schedule(make_user(take_home_per_paycheck=None), 2026, start=MARCH)
    assert plan["paycheck"]["take_home"] is None
    assert plan["paycheck"]["free_to_spend"] is None
    assert any("take-home" in note for note in plan["notes"])


# --- endpoint ------------------------------------------------------------------


def test_schedule_endpoint(client):
    body = client.get("/api/schedule").get_json()
    assert len(body["months"]) == 12
    assert body["this_month"]["moves"]
    assert body["paycheck"]["paychecks_per_year"] == 26
    assert body["notes"] and body["disclaimer"]

    assert len(client.get("/api/schedule?months=3").get_json()["months"]) == 3
    assert client.get("/api/schedule?months=30").status_code == 400


def test_pay_details_are_editable_on_the_profile(client):
    client.patch("/api/profile", json={
        "pay_frequency": "semimonthly", "take_home_per_paycheck": 2_500,
    })
    profile = client.get("/api/profile").get_json()
    assert profile["pay_frequency"] == "semimonthly"
    assert client.get("/api/schedule").get_json()["paycheck"]["paychecks_per_year"] == 24
