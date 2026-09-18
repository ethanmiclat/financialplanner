"""Single-user JSON persistence.

v1 is deliberately single-user (auth is deferred in the scope doc), so the whole store
is one JSON file. The interface — load/save/reset — is what a real DB layer would expose,
so swapping this out later doesn't touch the routes.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextvars import ContextVar
from pathlib import Path

import ledger
import limits as L
import pay
from models import (
    Account,
    AccountType,
    Debt,
    FilingStatus,
    Goal,
    HsaCoverage,
    Holding,
    PayFrequency,
    SavingsBasis,
    Snapshot,
    TaxTreatment,
    User,
    to_dict,
    user_from_dict,
)

STORE_PATH = Path(
    os.environ.get("FP_STORE", Path(__file__).parent / "data" / "profile.json")
)

# Demo mode points each visitor at their own file for the length of a request (see
# app.py). A context variable rather than a global, so concurrent requests can't
# read each other's profiles.
_request_path: ContextVar[Path | None] = ContextVar("store_path", default=None)


def use_path(path: Path | None):
    """Route load/save to `path` for the current request; returns the reset token."""
    return _request_path.set(path)


def _path() -> Path:
    return _request_path.get() or STORE_PATH


def seed_user() -> User:
    """A demo profile: 20-year-old college student, part-time job at minimum wage.

    Chosen deliberately over a high earner. It exercises the branches that matter for
    someone starting out — no 401(k) offered, no HSA, a small card balance above the
    high-interest cutoff and a student loan below it — and it makes the projection
    honest: small amounts, but forty-plus years of compounding.
    """
    return User(
        age=20,
        income=13_500,               # ~20 hrs/week at minimum wage
        filing_status=FilingStatus.SINGLE,
        state="",
        has_401k_at_work=False,      # part-time roles usually don't offer one
        expects_lower_bracket_in_retirement=False,   # earning less now than they will later
        annual_savings_capacity=1_200,               # $100/month
        savings_basis=SavingsBasis.MONTHLY,
        savings_amount=100,
        pay_frequency=PayFrequency.BIWEEKLY,
        take_home_per_paycheck=480,                  # ~$13.5k a year, after tax
        plan_year=L.current_year(),
        goal=Goal(monthly_expenses=950, emergency_fund_months=3, retirement_age=67),
        accounts=[
            Account(type=AccountType.CASH, nickname="Savings", balance=800),
            Account(
                type=AccountType.IRA,
                nickname="Roth IRA",
                balance=450,
                contributions_ytd=450,
                tax_treatment=TaxTreatment.ROTH,
                holdings=[
                    Holding("VTTSX", "Vanguard Target Retirement 2070", 300,
                            expense_ratio=0.0008, is_target_date=True)
                ],
            ),
        ],
        debts=[
            Debt("Credit card", balance=350, apr=0.2699, minimum_payment=25),
            Debt("Subsidized student loan", balance=5_500, apr=0.0653,
                 minimum_payment=0),
        ],
    )


def load() -> User:
    if not _path().exists():
        user = seed_user()
        save(user)
        return user
    # Synced on the way out as well as in, so a profile written before the saving unit
    # existed still reports a coherent pair rather than a blank field.
    user = pay.sync_capacity(user_from_dict(json.loads(_path().read_text())))
    # The first load of a new year starts it. Saved at once, so it happens exactly once.
    before = user.plan_year
    ledger.roll_over(user, L.current_year())
    if user.plan_year != before:
        save(user)
    return user


HISTORY_LIMIT = 3_660          # ten years of days


def snapshot(user: User) -> Snapshot:
    cash = sum(a.balance for a in user.accounts if a.type == AccountType.CASH)
    owned = sum(a.balance for a in user.accounts)
    return Snapshot(
        date=L.today().isoformat(),
        owned=round(owned, 2),
        owed=round(sum(d.balance for d in user.debts), 2),
        cash=round(cash, 2),
        invested=round(owned - cash, 2),
    )


def save(user: User) -> User:
    # Every save is a change worth charting; same-day saves replace each other.
    snap = snapshot(user)
    if user.history and user.history[-1].date == snap.date:
        user.history[-1] = snap
    else:
        user.history = [*user.history, snap][-HISTORY_LIMIT:]
    _path().parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(to_dict(user), indent=2)
    # Atomic write so a crash mid-save can't leave a truncated profile behind.
    with tempfile.NamedTemporaryFile(
        "w", dir=_path().parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    tmp_path.replace(_path())
    return user


def reset() -> User:
    return save(seed_user())
