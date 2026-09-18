"""Saving expressed in the unit somebody actually thinks in."""

import pytest

import pay
from models import Account, AccountType, Goal, PayFrequency, SavingsBasis, User


def make_user(**kw) -> User:
    defaults = dict(
        age=35, income=60_000, pay_frequency=PayFrequency.BIWEEKLY,
        take_home_per_paycheck=1_800, has_401k_at_work=False,
        goal=Goal(monthly_expenses=2_000, emergency_fund_months=3),
        accounts=[Account(type=AccountType.CASH, balance=6_000)],
    )
    defaults.update(kw)
    return User(**defaults)


@pytest.mark.parametrize("basis, amount, expected", [
    (SavingsBasis.YEARLY, 6_000, 6_000),
    (SavingsBasis.MONTHLY, 500, 6_000),
    (SavingsBasis.PER_PAYCHECK, 200, 5_200),      # 26 paychecks
    (SavingsBasis.PERCENT_OF_PAY, 0.10, 6_000),   # 10% of $60k
])
def test_every_basis_converts_to_the_same_yearly_figure(basis, amount, expected):
    assert pay.annual_from(make_user(), basis, amount) == pytest.approx(expected)


@pytest.mark.parametrize("basis", list(SavingsBasis))
def test_converting_back_returns_what_was_typed(basis):
    user = make_user()
    amount = 0.1 if basis is SavingsBasis.PERCENT_OF_PAY else 250
    annual = pay.annual_from(user, basis, amount)
    assert pay.amount_in(user, basis, annual) == pytest.approx(amount)


def test_amounts_gives_every_unit_at_once():
    a = pay.amounts(make_user(), 12_000)
    assert (a["annual"], a["monthly"], a["paychecks_per_year"]) == (12_000, 1_000, 26)
    assert a["per_paycheck"] == pytest.approx(461.54, abs=0.01)
    assert a["percent_of_pay"] == pytest.approx(0.2)
    assert a["percent_of_take_home"] == pytest.approx(12_000 / (1_800 * 26), abs=0.001)


def test_unknown_take_home_leaves_that_share_unknown():
    assert pay.amounts(make_user(take_home_per_paycheck=None), 12_000)[
        "percent_of_take_home"] is None


def test_an_unknown_amount_stays_unknown_rather_than_becoming_zero():
    assert pay.amounts(make_user(), None)["monthly"] is None


# --- keeping the stored figure in step -----------------------------------------


def test_a_percent_of_pay_plan_follows_a_raise():
    user = make_user(savings_basis=SavingsBasis.PERCENT_OF_PAY, savings_amount=0.10)
    assert pay.sync_capacity(user).annual_savings_capacity == pytest.approx(6_000)
    user.income = 90_000
    assert pay.sync_capacity(user).annual_savings_capacity == pytest.approx(9_000)


def test_a_per_paycheck_plan_follows_a_change_of_pay_frequency():
    user = make_user(savings_basis=SavingsBasis.PER_PAYCHECK, savings_amount=100)
    assert pay.sync_capacity(user).annual_savings_capacity == pytest.approx(2_600)
    user.pay_frequency = PayFrequency.MONTHLY
    assert pay.sync_capacity(user).annual_savings_capacity == pytest.approx(1_200)


def test_a_profile_saved_before_units_existed_is_filled_in_backwards():
    """An older profile has a yearly figure and no unit. Left alone, About you would
    show an empty box next to a plan that is visibly spending the money."""
    user = make_user(annual_savings_capacity=4_800)   # savings_amount defaults to None
    synced = pay.sync_capacity(user)
    assert synced.annual_savings_capacity == 4_800    # unchanged
    assert synced.savings_amount == pytest.approx(400)   # shown back as $400 a month
    assert synced.savings_basis is SavingsBasis.MONTHLY


def test_a_profile_with_no_savings_figure_at_all_stays_empty():
    assert pay.sync_capacity(make_user()).savings_amount is None


# --- through the API -----------------------------------------------------------


def test_saving_as_a_share_of_pay(client):
    client.patch("/api/profile", json={
        "income": 60_000, "savings_basis": "percent_of_pay", "savings_amount": 0.15,
    })
    assert client.get("/api/profile").get_json()["annual_savings_capacity"] == pytest.approx(9_000)

    # A raise carries through without the figure being retyped.
    client.patch("/api/profile", json={"income": 80_000})
    profile = client.get("/api/profile").get_json()
    assert profile["annual_savings_capacity"] == pytest.approx(12_000)
    assert profile["savings_amount"] == 0.15


def test_a_yearly_figure_sent_on_its_own_wins(client):
    """What the projection page's "save as my plan" sends — it must not be overwritten
    by the unit the profile happened to remember."""
    client.patch("/api/profile", json={
        "savings_basis": "percent_of_pay", "savings_amount": 0.15,
    })
    client.patch("/api/profile", json={"annual_savings_capacity": 5_000})
    profile = client.get("/api/profile").get_json()
    assert profile["annual_savings_capacity"] == 5_000
    assert profile["savings_basis"] == "yearly"


def test_the_schedule_reports_the_plan_in_every_unit(client):
    client.patch("/api/profile", json={
        "income": 60_000, "savings_basis": "percent_of_pay", "savings_amount": 0.10,
    })
    savings = client.get("/api/schedule").get_json()["savings"]
    assert savings["annual"] == pytest.approx(6_000)
    assert savings["monthly"] == pytest.approx(500)
    assert savings["basis"] == "percent_of_pay"
    assert savings["percent_of_pay"] == pytest.approx(0.10)
