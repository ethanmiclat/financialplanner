"""Pay, and the units a savings figure can be written in.

One number — what you put away in a year — is the only thing the engine stores. But
nobody thinks in that number. People think "10% of my paycheck", or "$200 a month",
or "$92 every two weeks", and a plan phrased in the wrong unit is a plan that doesn't
get followed. So this module converts in both directions and hands every surface all
the units at once.

Pure functions over `User`; imports nothing but the models, so both the schedule and
the goal estimator can depend on it without a cycle.
"""

from __future__ import annotations

from models import PayFrequency, SavingsBasis, User

PAYCHECKS_PER_YEAR = {
    PayFrequency.WEEKLY: 52,
    PayFrequency.BIWEEKLY: 26,
    PayFrequency.SEMIMONTHLY: 24,
    PayFrequency.MONTHLY: 12,
}

PAY_LABELS = {
    PayFrequency.WEEKLY: "every week",
    PayFrequency.BIWEEKLY: "every two weeks",
    PayFrequency.SEMIMONTHLY: "twice a month",
    PayFrequency.MONTHLY: "once a month",
}

BASIS_LABELS = {
    SavingsBasis.YEARLY: "a year",
    SavingsBasis.MONTHLY: "a month",
    SavingsBasis.PER_PAYCHECK: "per paycheck",
    SavingsBasis.PERCENT_OF_PAY: "of every paycheck",
}


def paychecks_per_year(user: User) -> int:
    return PAYCHECKS_PER_YEAR[user.pay_frequency]


def per_paycheck(user: User, annual_amount: float) -> float:
    return annual_amount / paychecks_per_year(user)


def annual_from(user: User, basis: SavingsBasis, amount: float) -> float:
    """What the user typed, in the unit they typed it, as dollars a year."""
    if amount is None:
        return None
    if basis is SavingsBasis.YEARLY:
        return float(amount)
    if basis is SavingsBasis.MONTHLY:
        return amount * 12
    if basis is SavingsBasis.PER_PAYCHECK:
        return amount * paychecks_per_year(user)
    return amount * user.income          # percent_of_pay, held as a fraction


def amount_in(user: User, basis: SavingsBasis, annual: float) -> float:
    """The inverse — for showing a stored annual figure back in the chosen unit."""
    if annual is None:
        return None
    if basis is SavingsBasis.YEARLY:
        return annual
    if basis is SavingsBasis.MONTHLY:
        return annual / 12
    if basis is SavingsBasis.PER_PAYCHECK:
        return per_paycheck(user, annual)
    return annual / user.income if user.income else 0.0


def sync_capacity(user: User) -> User:
    """Keep the stored yearly figure in step with the unit the user chose.

    `savings_amount` + `savings_basis` are what they entered; `annual_savings_capacity`
    is what every rule reads. Deriving one from the other on save means a raise or a
    change of pay frequency carries through to a percent-of-pay plan by itself, and the
    two can never drift apart.

    It fills backwards too: a profile saved before the unit was recorded has a yearly
    figure and nothing else, and would otherwise show an empty box on About you next to
    a plan that is visibly spending the money.
    """
    if user.savings_amount is not None:
        user.annual_savings_capacity = annual_from(
            user, user.savings_basis, user.savings_amount)
    elif user.annual_savings_capacity is not None:
        user.savings_amount = amount_in(
            user, user.savings_basis, user.annual_savings_capacity)
    return user


def amounts(user: User, annual: float | None) -> dict:
    """The same money in every unit somebody might want it in. `None` stays `None` —
    "we don't know" is a different statement from "zero"."""
    ppy = paychecks_per_year(user)
    take_home_year = (user.take_home_per_paycheck * ppy
                      if user.take_home_per_paycheck is not None else None)
    return {
        "annual": None if annual is None else round(annual, 2),
        "monthly": None if annual is None else round(annual / 12, 2),
        "per_paycheck": None if annual is None else round(annual / ppy, 2),
        "paychecks_per_year": ppy,
        "pay_label": PAY_LABELS[user.pay_frequency],
        "percent_of_pay": (round(annual / user.income, 4)
                           if annual is not None and user.income else None),
        "percent_of_take_home": (round(annual / take_home_year, 4)
                                 if annual is not None and take_home_year else None),
    }
