"""Recording what actually happened: "I put $200 in savings", "I paid $100 on the card".

The plan is derived from balances, so keeping it current means changing balances. The
account forms can already do that, but only by retyping a total — which asks the user
to do arithmetic the app should do, and leaves no trace of what changed. This module
applies a change as a *movement* (add, withdraw, pay, set) and logs it, so:

- the arithmetic is ours: add $200 and the balance and this year's contributions
  both move, because both are what the limit and emergency-fund rules read;
- every entry records the exact fields it touched as [before, after], so undo restores
  them precisely — and refuses if something else has changed those fields since,
  rather than silently clobbering a later edit.
"""

from __future__ import annotations

import math
from datetime import datetime

import limits as L
from models import Account, AccountType, Activity, Debt, Holding, User

KINDS = {"add", "withdraw", "pay", "set_balance", "invest"}
LOG_LIMIT = 200          # newest kept; old entries only ever mattered for undo
_EPS = 0.005             # half a cent — money compared as money, not as floats


_TYPE_NAMES = {"401k": "401(k)", "ira": "IRA", "hsa": "HSA", "taxable": "Brokerage", "cash": "Savings"}


class Conflict(Exception):
    """Undo would overwrite a change made after the entry. Maps to HTTP 409."""


def _amount(value, *, allow_zero: bool = False) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError("Amount must be a number") from None
    if not math.isfinite(n) or n < 0 or (n == 0 and not allow_zero):
        raise ValueError("Amount must be more than zero" if not allow_zero else "Amount can't be negative")
    if n > 1e12:
        raise ValueError("That amount is too large")
    return round(n, 2)


def _find(items, item_id: str, what: str):
    for item in items:
        if item.id == item_id:
            return item
    raise LookupError(f"No {what} {item_id}")


class _Recorder:
    """Sets fields and remembers each one's first-seen value."""

    def __init__(self):
        self.changes: dict[str, list[float]] = {}
        self.created: list[str] = []

    def set(self, obj, attr: str, value: float, path: str | None = None):
        path = path or attr
        before = getattr(obj, attr)
        value = round(value, 2)
        if path in self.changes:
            self.changes[path][1] = value
        else:
            self.changes[path] = [round(before, 2), value]
        setattr(obj, attr, value)


def _scale_holdings(acct: Account, rec: _Recorder, factor: float):
    for h in acct.holdings:
        rec.set(h, "value", h.value * factor, f"holdings.{h.id}.value")


def _apply_account(acct: Account, kind: str, amount: float, body: dict, rec: _Recorder):
    if kind == "add":
        rec.set(acct, "balance", acct.balance + amount)
        # Money you put into a 401(k), IRA or HSA counts against this year's limit.
        # Cash has no limit; a transfer between your own accounts can opt out.
        counts = body.get("counts_as_contribution", acct.type != AccountType.CASH)
        if counts and acct.type != AccountType.CASH:
            rec.set(acct, "contributions_ytd", acct.contributions_ytd + amount)
        # If the account records its funds, say whether the new money was invested.
        # Default yes — leaving it out would flag it as idle cash straight away.
        if acct.holdings and body.get("invested", True):
            biggest = max(acct.holdings, key=lambda h: h.value)
            rec.set(biggest, "value", biggest.value + amount, f"holdings.{biggest.id}.value")
    elif kind == "withdraw":
        if amount > acct.balance + _EPS:
            raise ValueError(f"That's more than the {acct.balance:,.2f} in {acct.nickname or 'this account'}")
        idle = acct.uninvested_cash
        rec.set(acct, "balance", max(0.0, acct.balance - amount))
        # Idle cash goes first; only the rest comes out of the funds, proportionally.
        from_funds = max(0.0, amount - idle)
        invested = sum(h.value for h in acct.holdings)
        if from_funds > 0 and invested > 0:
            _scale_holdings(acct, rec, max(0.0, 1 - from_funds / invested))
    elif kind == "set_balance":
        # A statement check — the market moved. Funds move by the same proportion, so
        # the share sitting uninvested stays what it was.
        if acct.balance > 0 and acct.holdings:
            _scale_holdings(acct, rec, amount / acct.balance)
        rec.set(acct, "balance", amount)
    elif kind == "invest":
        # Cash already in the account buys a fund. The balance doesn't move — only the
        # split between cash and funds does, which is what step 8 reads.
        if acct.type == AccountType.CASH:
            raise ValueError("A savings account doesn't hold funds — this is for investment accounts")
        idle = acct.uninvested_cash
        if idle <= 0.005:
            raise ValueError(f"Everything in {acct.nickname or 'this account'} is already invested")
        if amount > idle + _EPS:
            raise ValueError(f"Only {idle:,.2f} in {acct.nickname or 'this account'} is uninvested")
        if acct.holdings:
            fund = str(body.get("fund") or "").strip()
            match = next((h for h in acct.holdings if fund and fund.lower() in (h.symbol.lower(), h.name.lower())), None)
            holding = match or max(acct.holdings, key=lambda h: h.value)
            rec.set(holding, "value", holding.value + amount, f"holdings.{holding.id}.value")
        else:
            # Nothing recorded yet: the fund they bought becomes the account's first.
            fund = str(body.get("fund") or "").strip()[:60]
            if not fund:
                raise ValueError("Say which fund you bought, like VTI or a target-date fund")
            holding = Holding(symbol=fund.upper() if len(fund) <= 6 and " " not in fund else fund,
                              name=fund, value=0.0)
            acct.holdings.append(holding)
            rec.created.append(holding.id)
            rec.set(holding, "value", amount, f"holdings.{holding.id}.value")
    else:
        raise ValueError("Accounts take add, withdraw, invest or set_balance")


def _apply_debt(debt: Debt, kind: str, amount: float, rec: _Recorder) -> float:
    if kind == "pay":
        paid = min(amount, debt.balance)
        if paid <= 0:
            raise ValueError(f"{debt.name} is already paid off")
        rec.set(debt, "balance", debt.balance - paid)
        return paid
    if kind == "set_balance":
        rec.set(debt, "balance", amount)
        return amount
    raise ValueError("Debts take pay or set_balance")


def record(user: User, body: dict, *, now: datetime | None = None) -> Activity:
    """Apply one movement to `user` in place and log it. The caller saves."""
    kind = body.get("kind")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(sorted(KINDS))}")
    amount = _amount(body.get("amount"), allow_zero=kind == "set_balance")
    rec = _Recorder()

    if body.get("account_id"):
        target = _find(user.accounts, body["account_id"], "account")
        _apply_account(target, kind, amount, body, rec)
        name, where = target.nickname or _TYPE_NAMES[target.type.value], "account"
    elif body.get("debt_id"):
        target = _find(user.debts, body["debt_id"], "debt")
        amount = _apply_debt(target, kind, amount, rec)
        name, where = target.name, "debt"
    else:
        raise ValueError("Say which account_id or debt_id this is for")

    entry = Activity(
        kind=kind, target=where, target_id=target.id, target_name=name, amount=amount,
        changes=rec.changes, created_holdings=rec.created, note=str(body.get("note") or "")[:140],
        date=(now or L.now()).isoformat(timespec="seconds"),
    )
    user.activity = [entry, *user.activity][:LOG_LIMIT]
    return entry


def roll_over(user: User, year: int, *, now: datetime | None = None) -> Activity | None:
    """Start a new tax year: this year's contributions and match go back to zero, and
    the user is a year older. Logged like any other change, so it shows in the history
    and can be undone (a wrong system clock shouldn't cost anyone their numbers).

    Returns the entry, or None when there's nothing to do."""
    if user.plan_year is None:
        user.plan_year = year          # an old profile: adopt it, don't wipe it
        return None
    if year <= user.plan_year:
        return None
    rec = _Recorder()
    for acct in user.accounts:
        for attr in ("contributions_ytd", "employer_match_received_ytd"):
            if getattr(acct, attr):
                rec.set(acct, attr, 0.0, f"account.{acct.id}.{attr}")
    elapsed = year - user.plan_year
    rec.set(user, "age", user.age + elapsed, "user.age")
    rec.set(user, "plan_year", year, "user.plan_year")
    entry = Activity(
        kind="new_year", target="profile", target_id=user.id, target_name=str(year),
        amount=0.0, changes=rec.changes,
        note=f"{year} started: this year's contributions reset to $0, age {user.age}",
        date=(now or L.now()).isoformat(timespec="seconds"),
    )
    user.activity = [entry, *user.activity][:LOG_LIMIT]
    return entry


def _resolve(user: User, entry: Activity, path: str):
    """The object and attribute a change path points at, or None if it's gone."""
    if entry.target == "profile":
        head, _, rest = path.partition(".")
        if head == "user":
            return user, rest
        acct_id, attr = rest.split(".")
        acct = next((a for a in user.accounts if a.id == acct_id), None)
        return (acct, attr) if acct else None
    pool = user.accounts if entry.target == "account" else user.debts
    target = next((t for t in pool if t.id == entry.target_id), None)
    if target is None:
        return None
    if path.startswith("holdings."):
        _, hid, attr = path.split(".")
        holding = next((h for h in target.holdings if h.id == hid), None)
        return (holding, attr) if holding else None
    return target, path


def undo(user: User, activity_id: str, *, year: int | None = None) -> Activity:
    """Put back every field the entry changed, and drop it from the log."""
    entry = _find(user.activity, activity_id, "activity entry")
    if entry.kind == "new_year" and year is not None and year >= int(entry.target_name):
        raise Conflict(
            f"It's {year} on this computer, so the new-year reset would just happen again. "
            f"If the date is wrong, fix the clock and it will undo cleanly."
        )
    resolved = []
    for path, (before, after) in entry.changes.items():
        spot = _resolve(user, entry, path)
        if spot is None:
            raise Conflict(f"{entry.target_name} has been removed since, so this can't be undone")
        obj, attr = spot
        if abs(getattr(obj, attr) - after) > _EPS:
            raise Conflict(
                f"{entry.target_name} has changed since this was logged. Undo the newer "
                f"entries first, or set the balance directly."
            )
        resolved.append((obj, attr, before))
    for obj, attr, before in resolved:
        setattr(obj, attr, before)
    if entry.created_holdings:
        acct = next(a for a in user.accounts if a.id == entry.target_id)
        acct.holdings = [h for h in acct.holdings if h.id not in entry.created_holdings]
    user.activity = [a for a in user.activity if a.id != activity_id]
    return entry
