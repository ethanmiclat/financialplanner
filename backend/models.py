"""v1 data model. Plain dataclasses + JSON serialization — no ORM yet, since the
single-user store is a JSON file. Shapes are chosen so swapping in SQLAlchemy later
is a persistence change, not a redesign.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class FilingStatus(str, Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


class AccountType(str, Enum):
    TRADITIONAL_401K = "401k"
    IRA = "ira"
    HSA = "hsa"
    TAXABLE = "taxable"
    CASH = "cash"  # checking/savings — where the emergency fund lives


class TaxTreatment(str, Enum):
    TRADITIONAL = "traditional"
    ROTH = "roth"
    NA = "n/a"  # HSA, taxable, cash


class PayFrequency(str, Enum):
    """How often money actually arrives — the unit a schedule has to be written in."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"            # every two weeks: 26 a year
    SEMIMONTHLY = "semimonthly"      # twice a month: 24 a year
    MONTHLY = "monthly"


class SavingsBasis(str, Enum):
    """The unit somebody actually thinks about their saving in.

    All four mean the same thing to the engine — dollars a year — but "10% of my pay"
    and "$92 a paycheck" are the versions people can act on, and a percent-of-pay plan
    should follow a raise without being retyped.
    """

    YEARLY = "yearly"
    MONTHLY = "monthly"
    PER_PAYCHECK = "per_paycheck"
    PERCENT_OF_PAY = "percent_of_pay"


class HsaCoverage(str, Enum):
    SELF_ONLY = "self_only"
    FAMILY = "family"


class ActionStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    DISMISSED = "dismissed"


class Priority(str, Enum):
    """Where an action sits in the waterfall — drives ordering in the dashboard."""

    BLOCKING = "blocking"      # do before investing at all
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"              # nothing to do; shown for transparency


@dataclass
class Holding:
    """A fund inside an account. v1 only needs enough to flag un-invested cash and
    obviously expensive funds."""

    symbol: str
    name: str = ""
    value: float = 0.0
    expense_ratio: float | None = None
    is_target_date: bool = False
    id: str = field(default_factory=_new_id)


@dataclass
class Account:
    type: AccountType
    nickname: str = ""
    balance: float = 0.0
    contributions_ytd: float = 0.0
    tax_treatment: TaxTreatment = TaxTreatment.NA
    # 401k only
    employer_match_rate: float = 0.0          # e.g. 0.50 = 50 cents on the dollar
    employer_match_limit_pct: float = 0.0     # matched up to this % of salary
    employer_match_received_ytd: float = 0.0
    prior_year_wages_from_employer: float | None = None
    # hsa only
    hsa_coverage: HsaCoverage = HsaCoverage.SELF_ONLY
    hdhp_enrolled: bool = False
    holdings: list[Holding] = field(default_factory=list)
    id: str = field(default_factory=_new_id)

    @property
    def uninvested_cash(self) -> float:
        if self.type in (AccountType.CASH,):
            return 0.0
        return round(max(0.0, self.balance - sum(h.value for h in self.holdings)), 2)


@dataclass
class Debt:
    name: str
    balance: float
    apr: float                 # 0.22 == 22%
    minimum_payment: float = 0.0
    id: str = field(default_factory=_new_id)


@dataclass
class Activity:
    """One thing the user told us happened — "I put $200 in savings". Kept so the
    change can be seen and undone. `changes` records every field it touched as
    [before, after], which is what makes undo exact rather than a guess at the
    inverse (a debt payment capped at the balance isn't undone by adding the typed
    amount back)."""

    kind: str                  # add | withdraw | pay | set_balance
    target: str                # account | debt
    target_id: str
    target_name: str
    amount: float
    changes: dict[str, list[float]] = field(default_factory=dict)
    created_holdings: list[str] = field(default_factory=list)   # removed again on undo
    note: str = ""
    date: str = ""
    id: str = field(default_factory=_new_id)


@dataclass
class Snapshot:
    """Where things stood at the end of a day. One per day, the last save wins — the
    chart wants a trend, not every keystroke."""

    date: str                  # YYYY-MM-DD
    owned: float
    owed: float
    cash: float
    invested: float


@dataclass
class Goal:
    monthly_expenses: float = 0.0
    emergency_fund_months: int = 6
    retirement_target: float | None = None
    retirement_age: int | None = None          # None means the default, 67
    # How long the money has to last. Planning to 95 rather than to average life
    # expectancy is deliberate: running out at 88 is the failure that matters.
    plan_to_age: int = 95
    # Today's dollars. None means "the same as I spend now".
    retirement_monthly_spending: float | None = None
    # The estimate from ssa.gov at full retirement age, in today's dollars. None means
    # we don't know it, and the plan assumes nothing rather than guessing.
    social_security_monthly: float | None = None
    social_security_claim_age: int = 67

    @property
    def emergency_fund_target(self) -> float:
        return self.monthly_expenses * self.emergency_fund_months


@dataclass
class Assumptions:
    """The numbers a projection has to guess. Every one is the user's to change —
    defaults are reasonable, not correct."""

    return_rate: float = 0.07              # while saving, before inflation
    retirement_return_rate: float = 0.05   # after retiring, usually a steadier mix
    inflation: float = 0.025
    contribution_growth: float = 0.0       # yearly increase in what you save


@dataclass
class User:
    age: int
    income: float
    filing_status: FilingStatus = FilingStatus.SINGLE
    state: str = ""
    magi: float | None = None                # defaults to income when unset
    has_401k_at_work: bool = True
    expects_lower_bracket_in_retirement: bool | None = None
    # Dollars/year the user can actually put to work. When set, the engine allocates
    # it down the waterfall; when None it just reports remaining room per step.
    annual_savings_capacity: float | None = None
    # What they typed, and the unit they typed it in. `annual_savings_capacity` above
    # is derived from these on save (see `pay.sync_capacity`) and is what rules read;
    # these two are kept so a percent-of-pay plan stays a percent as income changes.
    savings_basis: SavingsBasis = SavingsBasis.MONTHLY
    savings_amount: float | None = None
    pay_frequency: PayFrequency = PayFrequency.BIWEEKLY
    # What actually lands in the bank each payday, after tax and payroll deductions.
    # None means we don't know it, and the schedule says so rather than guessing.
    take_home_per_paycheck: float | None = None
    goal: Goal = field(default_factory=Goal)
    assumptions: Assumptions = field(default_factory=Assumptions)
    accounts: list[Account] = field(default_factory=list)
    debts: list[Debt] = field(default_factory=list)
    activity: list[Activity] = field(default_factory=list)   # newest first
    # The tax year the "this year" figures (contributions_ytd, match received) belong
    # to. When the calendar passes it, they're reset — see `ledger.roll_over`. None on
    # profiles saved before this existed; they're adopted into the current year as-is.
    plan_year: int | None = None
    history: list[Snapshot] = field(default_factory=list)       # oldest first
    id: str = field(default_factory=_new_id)

    @property
    def effective_magi(self) -> float:
        return self.income if self.magi is None else self.magi

    def accounts_of(self, *types: AccountType) -> list[Account]:
        return [a for a in self.accounts if a.type in types]


@dataclass
class ActionItem:
    """Produced by the waterfall engine. `rule_id` is the traceability contract:
    every item on the dashboard points back at the rule that made it."""

    rule_id: str
    rule_name: str
    step: int
    title: str                 # Layer 1 — the decision
    detail: str                # Layer 2 — why, in plain English
    amount: float | None = None
    priority: Priority = Priority.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    account_type: AccountType | None = None
    inputs: dict[str, Any] = field(default_factory=dict)   # Layer 3 — show the math
    id: str = field(default_factory=_new_id)


@dataclass
class LearningLog:
    """Ethan's own-words explanation per account type — the source content that
    Layer 2/3 copy is written from."""

    account_type: AccountType
    summary: str
    body: str
    updated: str = ""
    id: str = field(default_factory=_new_id)


# --- serialization -------------------------------------------------------------

def to_dict(obj: Any) -> Any:
    """asdict() + enum unwrapping + computed properties the frontend will want."""
    if isinstance(obj, list):
        return [to_dict(o) for o in obj]
    if isinstance(obj, Enum):
        return obj.value
    if not hasattr(obj, "__dataclass_fields__"):
        return obj

    data = asdict(obj, dict_factory=lambda kv: {k: _plain(v) for k, v in kv})
    if isinstance(obj, Account):
        data["uninvested_cash"] = obj.uninvested_cash
    if isinstance(obj, Goal):
        data["emergency_fund_target"] = obj.emergency_fund_target
    if isinstance(obj, User):
        data["effective_magi"] = obj.effective_magi
        data["goal"]["emergency_fund_target"] = obj.goal.emergency_fund_target
        for raw, acct in zip(data["accounts"], obj.accounts):
            raw["uninvested_cash"] = acct.uninvested_cash
    return data


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


_ENUM_FIELDS = {
    "filing_status": FilingStatus,
    "pay_frequency": PayFrequency,
    "savings_basis": SavingsBasis,
    "type": AccountType,
    "account_type": AccountType,
    "tax_treatment": TaxTreatment,
    "hsa_coverage": HsaCoverage,
    "status": ActionStatus,
    "priority": Priority,
}


def _coerce(cls, data: dict) -> Any:
    fields = cls.__dataclass_fields__
    kwargs = {}
    for key, value in data.items():
        if key not in fields:
            continue  # ignore computed/unknown keys so round-tripping is safe
        if key in _ENUM_FIELDS and value is not None:
            value = _ENUM_FIELDS[key](value)
        kwargs[key] = value
    return cls(**kwargs)


def account_from_dict(data: dict) -> Account:
    data = dict(data)
    holdings = [_coerce(Holding, h) for h in data.pop("holdings", [])]
    account = _coerce(Account, data)
    account.holdings = holdings
    return account


def goal_from_dict(data: dict) -> Goal:
    return _coerce(Goal, data)


def assumptions_from_dict(data: dict) -> Assumptions:
    return _coerce(Assumptions, data)


def user_from_dict(data: dict) -> User:
    data = dict(data)
    accounts = [account_from_dict(a) for a in data.pop("accounts", [])]
    debts = [_coerce(Debt, d) for d in data.pop("debts", [])]
    # Profiles saved before the activity log existed start with an empty one.
    activity = [_coerce(Activity, a) for a in data.pop("activity", []) or []]
    history_raw = data.pop("history", []) or []
    goal = goal_from_dict(data.pop("goal", {}) or {})
    # Profiles saved before assumptions existed simply get the defaults.
    assumptions = assumptions_from_dict(data.pop("assumptions", {}) or {})
    user = _coerce(User, data)
    user.accounts, user.debts, user.goal = accounts, debts, goal
    user.activity = activity
    user.history = [_coerce(Snapshot, h) for h in history_raw]
    user.assumptions = assumptions
    return user
