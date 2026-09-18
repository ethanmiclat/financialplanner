"""Reading numbers out of sentences — and, just as important, not reading them
where they aren't."""

import pytest

import slots


@pytest.mark.parametrize("text,value", [
    ("35k", 35_000), ("35K", 35_000), ("$35,000", 35_000), ("35,000", 35_000), ("35000", 35_000),
    ("$1.2m", 1_200_000), ("1.5 million", 1_500_000), ("thirty five thousand", 35_000),
    ("twelve hundred", 1_200), ("two grand", 2_000), ("$500", 500),
])
def test_amount_forms(text, value):
    assert slots.extract(f"i have {text} in debt").amount == value


def test_cadence_separates_a_balance_from_a_flow():
    s = slots.extract("my 35k of student debt")
    assert s.balances and not s.flows
    s = slots.extract("what if i saved $300 a month")
    assert s.flows and s.flows[0].cadence == "monthly" and not s.balances
    s = slots.extract("i can put away 500 per paycheck")
    assert s.flows[0].cadence == "per_paycheck"
    s = slots.extract("10k a year")
    assert s.flows[0].cadence == "yearly"


def test_percent_is_a_rate_not_money_or_age():
    s = slots.extract("is 62% too much in stocks")
    assert not s.amounts and not s.ages
    assert s.rates == [0.62]
    s = slots.extract("at 6.5%")
    assert s.rates == [0.065]
    s = slots.extract("at 22 percent")
    assert s.rates == [0.22]


def test_ages():
    assert slots.extract("can i retire at 55").ages == [55]
    assert slots.extract("what if i retire at 62").ages == [62]
    assert slots.extract("at 62%").ages == []
    assert slots.extract("retire by 2040").ages == []
    assert slots.extract("retire by 2040").amounts == []


def test_bare_small_integers_are_not_money():
    assert slots.extract("retire at 55").amounts == []
    assert slots.extract("what about 300").amounts == []
    assert slots.extract("300 a month").amounts[0].value == 300


def test_debt_and_account_kinds():
    assert slots.extract("my student loans").debt_kind == "student_loan"
    assert slots.extract("credit card debt").debt_kind == "credit_card"
    assert slots.extract("my car loan").debt_kind == "auto"
    assert slots.extract("my mortgage").debt_kind == "mortgage"
    assert slots.extract("i owe money").mentions_debt and slots.extract("i owe money").debt_kind is None
    assert slots.extract("my 401k").account_kind == "401k"
    assert slots.extract("my roth").account_kind == "ira"
    assert slots.extract("my hsa").account_kind == "hsa"


def test_signals():
    assert slots.extract("what if i made 75k").mentions_income
    assert slots.extract("i got a bonus").mentions_windfall
    assert slots.extract("what if i saved more").mentions_saving
    assert slots.extract("an extra 200 a month").mentions_increment
    assert slots.extract("a 10% raise").mentions_increment
    assert not slots.extract("a raise to 90k").mentions_increment
