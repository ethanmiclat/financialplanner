"""The composer: a typed question, run as a what-if, answered from the engine.

"How should I plan around my 35K of student debt?" can't be looked up, because the
answer depends on a number the user just typed. But it doesn't need a language model
either — the engine already knows where debt sits in the waterfall, what a year of
saving is worth at retirement, and what happens when either changes. What's missing is
the bridge: read the slots out of the sentence, build a copy of the profile with them
applied, run the same rules the dashboard runs, and write the result up.

Two disciplines carried over from `/api/target` and the projection's what-ifs:

- **Nothing is saved.** Every scenario runs on a deep copy. If the user wants to keep
  it, the answer carries a `save_hint` naming the *existing* write endpoint that would
  do it — there is no new write path here.
- **Every number comes from the engine.** `waterfall`, `retirement` and `projection`
  produce the figures; this module only chooses which to run and how to phrase what
  comes back. The one thing it adds is loan amortization, which the engine never
  needed until now — and every assumption that goes into it is listed on the face of
  the answer, because an assumed interest rate is the hinge of the whole thing.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import limits as L
import pay
import projection
import retirement as R
import waterfall as W
from models import Debt, SavingsBasis, User
from qa import Answer
from slots import Slots

# --- the composed answer -------------------------------------------------------


@dataclass
class Composed(Answer):
    """`Answer` plus the parts a synthesised reply needs: headed sections rather than
    one block of prose, the assumptions we had to make, and how to keep the result."""

    sections: list[dict] = field(default_factory=list)
    assumptions: list[dict] = field(default_factory=list)
    save_hint: dict | None = None


@dataclass
class NeedsInput:
    """The intent was clear but a number wasn't. Ask, don't guess."""

    question: str
    missing: str
    hint: str = ""


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}".rstrip("0").rstrip(".") + "%"


def _fact(label: str, value: str) -> dict:
    return {"label": label, "value": value}


def _assume(label: str, value: str, note: str) -> dict:
    return {"label": label, "value": value, "note": note}


def _section(heading: str, body: str, facts: list[dict] | None = None) -> dict:
    return {"heading": heading, "body": body, "facts": facts or []}


def _years(n: float) -> str:
    if n < 1:
        months = round(n * 12)
        return f"{months} month{'s' if months != 1 else ''}"
    return f"{n:.1f} years".replace(".0 years", " years")


# --- the trial copy ------------------------------------------------------------


def trial(user: User, *, add_debts: list[Debt] | None = None, **overrides) -> User:
    """A what-if copy. Scalars go through `projection.with_overrides` so they get the
    same validation the projection page's controls do; debts are appended here because
    that helper only knows about fields, not lists. Income changes re-sync capacity so a
    percent-of-pay plan follows the new salary instead of quietly keeping the old one."""
    if overrides:
        t = projection.with_overrides(user, overrides)
    else:
        t = copy.deepcopy(user)
        R.validate(t)
    if add_debts:
        t.debts = list(t.debts) + [copy.deepcopy(d) for d in add_debts]
    if "income" in overrides:
        pay.sync_capacity(t)
    return t


# --- loan arithmetic -----------------------------------------------------------
# The engine never amortized a loan before this. It's plain arithmetic, but it's
# arithmetic the answer depends on, so the assumptions feeding it are all disclosed.

TYPICAL_APR = {
    "student_loan": 0.065,
    "credit_card": 0.23,
    "auto": 0.075,
    "mortgage": 0.065,
    "medical": 0.0,
    "personal": 0.12,
    "other": 0.10,
}
TYPICAL_TERM_YEARS = {
    "student_loan": 10, "auto": 5, "mortgage": 30, "medical": 3, "personal": 5, "other": 5,
}
KIND_LABELS = {
    "student_loan": "student loan", "credit_card": "credit card", "auto": "car loan",
    "mortgage": "mortgage", "medical": "medical debt", "personal": "personal loan",
    "other": "loan",
}


def level_payment(balance: float, apr: float, years: float) -> float:
    """The fixed monthly payment that clears `balance` in `years`."""
    n = max(1, round(years * 12))
    i = apr / 12
    if i <= 0:
        return balance / n
    return balance * i / (1 - (1 + i) ** -n)


def estimate_minimum(balance: float, apr: float, kind: str) -> float:
    if kind == "credit_card":
        return max(25.0, round(balance * 0.02, 2))     # the usual 2% floor
    return round(level_payment(balance, apr, TYPICAL_TERM_YEARS.get(kind, 5)), 2)


def amortize(balance: float, apr: float, payment: float, cap_months: int = 600) -> dict:
    """Month by month, the way `schedule.py` moves a balance: interest first, then the
    payment. Returns months to clear and total interest paid — or `never` when the
    payment doesn't cover the interest."""
    i = apr / 12
    b = balance
    interest = 0.0
    for month in range(1, cap_months + 1):
        accrued = b * i
        if payment <= accrued + 1e-9 and i > 0:
            return {"months": None, "interest": None, "never": True}
        interest += accrued
        b = b + accrued - payment
        if b <= 0.005:
            return {"months": month, "interest": round(interest), "never": False}
    return {"months": None, "interest": None, "never": True}


def simulate_branches(balance: float, apr: float, minimum: float, capacity: float,
                      start_invested: float, return_rate: float, years: int,
                      growth: float = 0.0) -> dict:
    """The fair comparison: both routes deploy the same cash every month — the
    savings figure plus the loan's minimum — and differ only in where it goes first.

    Route A puts all of it at the loan until the loan is gone, then invests all of it.
    Route B pays the minimum, invests the savings figure, and once the loan is gone
    invests the minimum too. Anything less symmetric flatters one side: crediting the
    investing route with the minimum payment for free is exactly the mistake that makes
    a 22% card look worth keeping."""
    i_debt = apr / 12
    i_inv = (1 + return_rate) ** (1 / 12) - 1
    months = years * 12
    out = {}
    for route in ("payoff_first", "invest_now"):
        debt, invested, interest, cleared_at = balance, start_invested, 0.0, None
        contrib = capacity / 12
        for m in range(1, months + 1):
            if m > 1 and (m - 1) % 12 == 0:
                contrib *= (1 + growth)
            invested *= (1 + i_inv)
            available = contrib + minimum
            if debt > 0.005:
                accrued = debt * i_debt
                interest += accrued
                debt += accrued
                to_debt = min(debt, available if route == "payoff_first" else minimum)
                debt -= to_debt
                invested += available - to_debt
                if debt <= 0.005 and cleared_at is None:
                    cleared_at = m
            else:
                invested += available
        out[route] = {"invested": invested, "interest": interest,
                      "cleared_months": cleared_at, "still_owed": max(0.0, debt)}
    return out


# --- scenario 1: debt strategy (the benchmark) ---------------------------------


def _match_stored_debt(user: User, kind: str | None) -> list[Debt]:
    owing = [d for d in user.debts if d.balance > 0]   # a paid-off debt isn't a strategy question
    if not kind:
        return owing
    words = {
        "student_loan": ("student", "college", "tuition"),
        "credit_card": ("card", "visa", "amex", "mastercard", "discover"),
        "auto": ("car", "auto", "vehicle", "truck"),
        "mortgage": ("mortgage", "home", "house"),
        "medical": ("medical", "hospital"),
        "personal": ("personal", "loan"),
    }[kind]
    import re as _re
    return [d for d in owing
            if any(_re.search(rf"\b{w}\b", d.name.lower()) for w in words)]


def run_debt_strategy(user: User, year: int, slots: Slots) -> Composed | NeedsInput:
    cutoff = L.load_limits(year)["thresholds"]["high_interest_debt_apr"]
    assumptions: list[dict] = []
    kind = slots.debt_kind or "other"
    label = KIND_LABELS[kind]

    # Which debt are we talking about — one they just typed, or one on file?
    if slots.balances:
        balance = slots.balances[0].value
        if slots.rate is not None:
            apr = slots.rate
        else:
            apr = TYPICAL_APR[kind]
            assumptions.append(_assume(
                "Interest rate", _pct(apr),
                f"You didn't say, so this uses a typical {label} rate. It's the hinge of "
                f"the whole answer — tell me the real rate and it re-runs.",
            ))
        minimum = estimate_minimum(balance, apr, kind)
        assumptions.append(_assume(
            "Minimum payment", f"{_money(minimum)} a month",
            f"Estimated from a typical {label} term; your statement has the real one.",
        ))
        debt = Debt(name=label.capitalize(), balance=balance, apr=apr, minimum_payment=minimum)
        others = list(user.debts)
        from_question = True
    else:
        matched = _match_stored_debt(user, slots.debt_kind)
        if not matched:
            if slots.debt_kind:
                return NeedsInput(
                    question=f"How much is the {label}, and do you know the interest rate?",
                    missing="amount",
                    hint=f"I don't see a {label} in your plan yet. Something like "
                         f"\"{label} of $12,000 at 6%\" is enough.",
                )
            return NeedsInput(
                question="How much do you owe, and at what rate?",
                missing="amount",
                hint="There's no debt in your plan yet. \"I owe $8,000 on a card at 24%\" "
                     "is enough to go on.",
            )
        debt = max(matched, key=lambda d: d.apr)
        others = [d for d in user.debts if d.id != debt.id]
        balance, apr, minimum = debt.balance, debt.apr, debt.minimum_payment
        if minimum <= 0:
            minimum = estimate_minimum(balance, apr, kind if slots.debt_kind else "other")
            assumptions.append(_assume(
                "Minimum payment", f"{_money(minimum)} a month",
                "No minimum is on file for this debt, so this is an estimate.",
            ))
        from_question = False

    # Where does it land? Ask the engine, on a copy with the debt present.
    t = trial(user, add_debts=[debt]) if from_question else copy.deepcopy(user)
    r3 = [i for i in W.rule_high_interest_debt(t, year) if i.inputs.get("name") == debt.name]
    expensive = apr > cutoff
    sources = ["R3_HIGH_INTEREST_DEBT"]

    if expensive:
        placement = (
            f"At {_pct(apr)} this is above the {_pct(cutoff)} line, so it's step 3 of your "
            f"plan: it comes before the HSA, the IRA and any 401(k) money beyond the match. "
            f"Paying it down is a guaranteed {_pct(apr)} return, and nothing in the market "
            f"promises that."
        )
        if r3:
            placement += f" The dashboard shows it as \"{r3[0].title}\"."
    else:
        placement = (
            f"At {_pct(apr)} this is under the {_pct(cutoff)} line, so it doesn't block "
            f"investing. Keep paying it on schedule and keep going down the waterfall — "
            f"the match, the HSA and the IRA all come first. It isn't free, though, and "
            f"the numbers below show what carrying it costs."
        )
    sections = [_section("Where it lands in your plan", placement, [
        _fact("Balance", _money(balance)),
        _fact("Rate", _pct(apr)),
        _fact("The line we use", f"{_pct(cutoff)} APR — from the {year} data file"),
    ])]

    # The illustration: pay it off first, or pay the minimum and invest.
    a = user.assumptions
    capacity = user.annual_savings_capacity
    n = R.years_to_retirement(user)
    ret_age = R.retirement_age(user)
    start = R.invested_balance(user)
    deflator = (1 + a.inflation) ** n if n else 1.0
    facts_cmp: list[dict] = []
    compare_body: str
    result_gap = None

    at_minimum = amortize(balance, apr, minimum)
    sim = None
    if capacity and capacity > 0 and n > 0:
        sim = simulate_branches(balance, apr, minimum, capacity, start, a.return_rate, n,
                                a.contribution_growth)
        A, B = sim["payoff_first"], sim["invest_now"]
        if A["cleared_months"] is None:
            compare_body = (
                f"Even putting all {_money(capacity + minimum * 12)} a year at it, the loan "
                f"isn't cleared before {ret_age} — this needs a bigger payment or a lower "
                f"rate before anything else."
            )
        else:
            a_today, b_today = A["invested"] / deflator, B["invested"] / deflator
            result_gap = b_today - a_today
            facts_cmp = [
                _fact("Pay it off first — cleared in", _years(A["cleared_months"] / 12)),
                _fact("Interest paid that way", _money(A["interest"])),
                _fact(f"Invested by {ret_age}, today's money", _money(a_today)),
                _fact("Pay the minimum and invest — cleared in",
                      _years(B["cleared_months"] / 12) if B["cleared_months"] else f"not by {ret_age}"),
                _fact("Interest paid that way", _money(B["interest"])
                      + (f" and still owing {_money(B['still_owed'])}" if B["still_owed"] > 1 else "")),
                _fact(f"Invested by {ret_age}, today's money", _money(b_today)),
            ]
            winner = "investing first" if result_gap > 0 else "paying it off first"
            facts_cmp.append(_fact("Difference", f"{_money(abs(result_gap))} in favour of {winner}"))
            compare_body = (
                f"Both routes put the same money to work each month — your "
                f"{_money(capacity)} a year plus the {_money(minimum)} minimum — and differ "
                f"only in what gets it first. Aim all of it at the loan and it's gone in "
                f"{_years(A['cleared_months'] / 12)}, then everything goes to investing: about "
                f"{_money(a_today)} by {ret_age} in today's money, having paid "
                f"{_money(A['interest'])} in interest. Pay the minimum and invest the rest "
                f"from day one and you reach about {_money(b_today)}, having paid "
                f"{_money(B['interest'])} in interest along the way. That's "
                f"{_money(abs(result_gap))} in favour of {winner} — because the "
                f"{_pct(a.return_rate)} return you're assuming is "
                f"{'above' if a.return_rate > apr else 'below'} the loan's {_pct(apr)}."
            )
        assumptions.append(_assume(
            "Investment return", _pct(a.return_rate),
            "Your projection assumption. Not a guarantee — the loan's rate is.",
        ))
        assumptions.append(_assume(
            "Same cash both ways", f"{_money(capacity)} a year plus the minimum",
            "Both routes deploy identical money each month; only the order differs.",
        ))
        sources.append("R10_READINESS")
    else:
        compare_body = (
            "To put dollars on the two routes I need one more number: what you can save "
            "in a year. Add it on About you and this section fills in — how long each "
            "route takes, and what each leaves you with at retirement."
        )
    sections.append(_section("Pay it off first, or pay the minimum and invest", compare_body, facts_cmp))

    # The rate that flips it.
    flip = a.return_rate
    sections.append(_section(
        "The rate that flips the answer",
        f"Paying a loan down earns exactly its rate, guaranteed. Investing is expected to "
        f"earn about {_pct(flip)} — expected, not promised, with years where it's negative. "
        f"So the honest rule is: below roughly {_pct(flip)}, invest while paying the minimum; "
        f"above it, clear the debt. Your plan draws the hard line at {_pct(cutoff)} to leave "
        f"room for the risk. At {_pct(apr)}, this loan is "
        f"{'above' if expensive else 'below'} that line"
        f"{'' if expensive else ' — but close enough that paying extra when you can is a reasonable call, and the peace of mind is real'}.",
        [_fact("Guaranteed by paying it down", _pct(apr)),
         _fact("Expected from investing", _pct(flip)),
         _fact("Where the plan draws the line", _pct(cutoff))],
    ))

    if others:
        rows = [_fact(d.name, f"{_pct(d.apr)} on {_money(d.balance)}"
                      + (" — above the line" if d.apr > cutoff else "")) for d in others]
        sections.append(_section(
            "Your other debts",
            "The same test applies to each of these. Anything above the line comes first, "
            "highest rate first; the rest get paid on schedule.",
            rows,
        ))

    save_hint = None
    if from_question:
        save_hint = {
            "label": f"Add this {_money(balance)} {label} to my plan",
            "method": "POST",
            "path": "/api/debts",
            "body": {"name": debt.name, "balance": balance, "apr": apr,
                     "minimum_payment": minimum},
        }

    if expensive:
        summary = (f"Your {_money(balance)} {label} at {_pct(apr)} is step 3 — clear it "
                   f"before investing beyond the match.")
    else:
        summary = (f"Your {_money(balance)} {label} at {_pct(apr)} sits below the line where "
                   f"paying it off first beats investing.")

    detail = (
        f"The whole decision comes down to one comparison: the loan's rate against what "
        f"investing is expected to return. A {_pct(apr)} loan is a guaranteed {_pct(apr)} "
        f"return for every extra dollar you put at it, and the plan draws its line at "
        f"{_pct(cutoff)}. "
        + ("Above that, the guaranteed return wins and the loan goes ahead of everything "
           "except an employer match." if expensive else
           "Below that, the money is expected to do more invested, so the loan is paid on "
           "schedule while you keep going down the list — though the gap is small enough "
           "that paying extra is never a mistake.")
    )

    return Composed(
        summary=summary, detail=detail,
        facts=[_fact("Balance", _money(balance)), _fact("Rate", _pct(apr)),
               _fact("Minimum payment", f"{_money(minimum)} a month"),
               _fact("Step in your plan", "3 — before the HSA and IRA" if expensive
                     else "paid on schedule, alongside investing")],
        sources=sources,
        follow_ups=["debt_or_invest", "next_dollar", "how_much_per_month"],
        sections=sections, assumptions=assumptions, save_hint=save_hint,
    )


# --- scenario 2: windfall ------------------------------------------------------


_STEP_LABELS = {
    "R1_EMERGENCY_FUND": "your emergency fund",
    "R2_EMPLOYER_MATCH": "your 401(k), up to the full match",
    "R4_HSA": "your HSA",
    "R5_IRA": "your IRA",
    "R6_REMAINING_401K": "your 401(k), beyond the match",
    "R7_TAXABLE": "a taxable brokerage account",
    "R9_RETIREMENT_AGE": "money you can reach before 59½",
}


def _step_label(step: dict) -> str:
    if step["rule_id"] == "R3_HIGH_INTEREST_DEBT":
        return "paying off " + step["title"].split("(")[0].replace("Pay off ", "").strip().lower()
    return _STEP_LABELS.get(step["rule_id"], step["title"].lower())


def run_windfall(user: User, year: int, slots: Slots) -> Composed | NeedsInput:
    if not slots.balances:
        return NeedsInput(question="How much did you get?", missing="amount",
                          hint="\"I got a $5,000 bonus\" is enough.")
    amount = slots.balances[0].value
    base_cap = user.annual_savings_capacity or 0.0
    t = trial(user, annual_savings_capacity=base_cap + amount)
    before = {s["rule_id"]: s for s in W.allocate(user, year)["steps"]}
    after = W.allocate(t, year)

    rows, body_bits = [], []
    for step in after["steps"]:
        was = before.get(step["rule_id"], {}).get("funded") or 0.0
        now = step["funded"] or 0.0
        delta = now - was
        if delta > 0.5:
            lbl = _step_label(step)
            done = (" — clears it" if step["rule_id"] in ("R1_EMERGENCY_FUND", "R3_HIGH_INTEREST_DEBT")
                    else " — fills it for the year") if step["fully_funded"] else ""
            rows.append(_fact(lbl[0].upper() + lbl[1:], _money(delta) + done))
            body_bits.append(f"{_money(delta)} to {_step_label(step)}")
    left = after["unallocated"] or 0.0
    if left > 0.5:
        rows.append(_fact("Left over — taxable brokerage", _money(left)))

    if body_bits:
        body = ("Run down the waterfall in order, the money goes: "
                + "; ".join(body_bits) + ".")
        if left > 0.5:
            body += f" The remaining {_money(left)} has no tax-advantaged home left this year and goes to a taxable account."
    else:
        body = (f"Every step is already full this year, so all {_money(amount)} goes to a "
                f"taxable brokerage account — no limit there, and no penalty to take it out.")

    first = rows[0]["label"].lower() if rows else "a taxable brokerage account"
    if len(rows) == 1:
        summary = f"All {_money(amount)} goes to {first}."
    else:
        summary = f"Your {_money(amount)} goes first to {first}, then on down the list."
    return Composed(
        summary=summary,
        detail=(
            "A lump sum runs down exactly the same list as your monthly money — it's just "
            "all at once. Whatever the top unfilled step is gets it first, then the next, "
            "until the money runs out. The one thing to watch is annual room: an IRA or HSA "
            "only takes so much per year, so a big enough windfall spills into a taxable "
            "account by December regardless."
        ),
        facts=rows,
        sources=[s["rule_id"] for s in after["steps"] if (s["funded"] or 0) > 0] or ["R7_TAXABLE"],
        follow_ups=["next_dollar", "why_this_order", "what_to_invest_in"],
        sections=[_section("Where it goes, step by step", body, rows)],
        assumptions=[_assume("Treated as", "this year's money",
                             "Added to what you can save this year, so annual limits apply.")],
        save_hint=None,
    )


# --- scenario 3: income change -------------------------------------------------


def _readiness(u: User, year: int) -> dict:
    """Straight from the retirement maths, so `status` is present (the rule strips it)."""
    inv = W.annual_investing(u, year)
    return R.readiness(u, year, R.invested_balance(u), inv["total"], inv["years_until_investing"])


def run_income_change(user: User, year: int, slots: Slots) -> Composed | NeedsInput:
    amt = next((a for a in slots.amounts if a.cadence in (None, "yearly")), None)
    monthly = next((a for a in slots.amounts if a.cadence == "monthly"), None)
    if amt is None and monthly is None and slots.mentions_increment and slots.rates:
        amt = None                                    # "a 10% raise" — handled below
    elif amt is None and monthly is None:
        return NeedsInput(question="What would the new income be, per year?", missing="amount",
                          hint="\"what if I made $80k\" is enough.")
    income = amt.value if amt else (monthly.value * 12 if monthly else user.income)
    if income < 1000:
        income *= 1000          # "what if i made 80" almost certainly means 80k
    if slots.mentions_increment and slots.rates and not slots.amounts:
        income = user.income * (1 + slots.rate)      # "a 10% raise"
    elif slots.mentions_increment:
        income = user.income + income                # "a $5k raise"
    t = trial(user, income=income)

    ira_before, ira_after = L.ira_limit(user.age, year, user.income), L.ira_limit(t.age, year, t.income)
    roth_b = L.roth_ira_eligibility(user.effective_magi, user.filing_status.value, user.age, year, user.income)
    roth_a = L.roth_ira_eligibility(t.effective_magi, t.filing_status.value, t.age, year, t.income)
    rb, ra = _readiness(user, year), _readiness(t, year)

    rows = [
        _fact("Income", f"{_money(user.income)} → {_money(income)}"),
        _fact("IRA room (capped at earned income)", f"{_money(ira_before)} → {_money(ira_after)}"),
        _fact("Direct Roth IRA", f"{_money(roth_b['allowed'])} → {_money(roth_a['allowed'])}"),
    ]
    if user.annual_savings_capacity != t.annual_savings_capacity:
        rows.append(_fact("What you save a year",
                          f"{_money(user.annual_savings_capacity or 0)} → {_money(t.annual_savings_capacity or 0)}"))
    sections = [_section(
        "What changes on paper",
        (f"Income moves three things the engine reads: the IRA limit (you can't put in more "
         f"than you earn), the Roth phase-out (direct Roth contributions shrink once income "
         f"crosses {_money(roth_a['phaseout_start'])}), and — if your saving is a share of pay "
         f"— the dollars that share turns into."),
        rows,
    )]
    if rb.get("funded_ratio") is not None and ra.get("funded_ratio") is not None:
        sections.append(_section(
            "What it does to retirement",
            (f"At the same savings rate, the plan reaches {_money(ra['projected_at_retirement'])} "
             f"at {ra['retirement_age']} in today's money, against {_money(rb['projected_at_retirement'])} "
             f"today. "
             + ("The bigger lever is what you do with the raise: putting even half of it into "
                "the plan moves the date more than the raise itself." if income > user.income else
                "Lower income shows up through the employer match and, on a percent-of-pay "
                "plan, the savings figure itself.")),
            [_fact("Funded at retirement", f"{rb['funded_ratio']:.0%} → {ra['funded_ratio']:.0%}"),
             _fact("Earliest age the plan supports",
                   f"{rb['earliest_retirement_age'] or '80+'} → {ra['earliest_retirement_age'] or '80+'}")],
        ))
    if roth_b["status"] != roth_a["status"]:
        note = {"full": "you can contribute the full amount directly",
                "partial": "you're in the phase-out, so only part goes in directly",
                "phased_out": "direct contributions close and the backdoor route opens"}[roth_a["status"]]
        sections.append(_section("Roth eligibility changes", f"At {_money(income)}, {note}.", []))

    return Composed(
        summary=f"At {_money(income)}, your IRA room is {_money(ira_after)} and direct Roth is "
                f"{_money(roth_a['allowed'])}" + (
                    " — and your savings figure follows the raise." if
                    user.annual_savings_capacity != t.annual_savings_capacity else "."),
        detail=(
            "A raise changes what's allowed before it changes what's saved. Contribution "
            "limits are per person and don't move with income — except the IRA, which is "
            "capped at what you earn, and the Roth phase-out, which closes the direct route "
            "for high earners. The thing that moves the retirement date is what fraction of "
            "the new pay actually gets saved."
        ),
        facts=rows, sources=["R5_IRA", "R10_READINESS", f"limits_{year}"],
        follow_ups=["can_i_do_roth", "how_much_can_i_put_in", "what_it_takes"],
        sections=sections,
        assumptions=[_assume("Savings figure", "same rule as now",
                             "Percent-of-pay plans follow the raise; dollar plans stay put.")],
        save_hint={"label": f"Set my income to {_money(income)}", "method": "PATCH",
                   "path": "/api/profile", "body": {"income": income}},
    )


# --- scenario 4: contribution change -------------------------------------------


def _annual_from_flow(user: User, amount) -> tuple[float, str, float, str]:
    """(annual, basis, amount_in_basis, label)."""
    c = amount.cadence
    if c == "monthly":
        return amount.value * 12, SavingsBasis.MONTHLY.value, amount.value, "a month"
    if c == "per_paycheck":
        return amount.value * pay.paychecks_per_year(user), SavingsBasis.PER_PAYCHECK.value, amount.value, "per paycheck"
    if c == "biweekly":
        return amount.value * 26, SavingsBasis.PER_PAYCHECK.value, amount.value, "every two weeks"
    if c == "weekly":
        return amount.value * 52, SavingsBasis.MONTHLY.value, amount.value * 52 / 12, "a week"
    return amount.value, SavingsBasis.YEARLY.value, amount.value, "a year"


def run_contribution_change(user: User, year: int, slots: Slots) -> Composed | NeedsInput:
    flow = slots.flows[0] if slots.flows else None
    if flow is None:
        # "what if i saved 10k" — a bare amount with a saving verb reads as a year.
        if slots.balances and slots.mentions_saving:
            flow = slots.balances[0]
            flow.cadence = "yearly"
        else:
            return NeedsInput(question="How much, and how often — a month, a paycheck, a year?",
                              missing="amount", hint="\"$400 a month\" is enough.")
    annual, basis, in_basis, label = _annual_from_flow(user, flow)
    incremental = slots.mentions_increment and user.annual_savings_capacity
    if incremental:
        annual = user.annual_savings_capacity + annual
        in_basis = pay.amount_in(user, SavingsBasis(basis), annual)
    t = trial(user, annual_savings_capacity=annual)
    t.savings_basis = SavingsBasis(basis)
    t.savings_amount = in_basis

    rb, ra = _readiness(user, year), _readiness(t, year)
    before_alloc = {s["rule_id"]: s for s in W.allocate(user, year)["steps"]}
    after_alloc = W.allocate(t, year)
    cur = user.annual_savings_capacity or 0.0

    rows = [_fact("What you save a year", f"{_money(cur)} → {_money(annual)}")]
    if rb.get("funded_ratio") is not None and ra.get("funded_ratio") is not None:
        rows += [
            _fact(f"Reaches by {ra['retirement_age']}, today's money",
                  f"{_money(rb['projected_at_retirement'])} → {_money(ra['projected_at_retirement'])}"),
            _fact("Funded", f"{rb['funded_ratio']:.0%} → {ra['funded_ratio']:.0%}"),
            _fact("Earliest age the plan supports",
                  f"{rb['earliest_retirement_age'] or '80+'} → {ra['earliest_retirement_age'] or '80+'}"),
        ]
        if ra.get("money_lasts_to_age") or rb.get("money_lasts_to_age"):
            rows.append(_fact("Money lasts to",
                              f"{rb['money_lasts_to_age'] or ra['plan_to_age']} → {ra['money_lasts_to_age'] or ra['plan_to_age']}"))

    steps = []
    for s in after_alloc["steps"]:
        was = before_alloc.get(s["rule_id"], {}).get("funded") or 0.0
        now = s["funded"] or 0.0
        if abs(now - was) > 0.5:
            steps.append(_fact(s["title"], f"{_money(was)} → {_money(now)}"))

    sections = [_section("What the new figure does",
                         (f"An extra {_money(flow.value)} {label} on top of what you save now makes "
                          if incremental else f"Saving {_money(in_basis)} {label} is ")
                         + f"{_money(annual)} a year. "
                         + (f"That's {_money(annual - cur)} more than now." if annual > cur
                            else f"That's {_money(cur - annual)} less than now."),
                         rows)]
    if steps:
        sections.append(_section("Where the difference lands", "Step by step, down the same list:", steps))

    earlier = (rb.get("earliest_retirement_age") and ra.get("earliest_retirement_age")
               and ra["earliest_retirement_age"] < rb["earliest_retirement_age"])
    if rb.get("funded_ratio") is not None and ra.get("funded_ratio") is not None:
        summary = (f"{_money(in_basis)} {label} takes the plan from {rb['funded_ratio']:.0%} to "
                   f"{ra['funded_ratio']:.0%} funded at {ra['retirement_age']}"
                   + (f", and the earliest age moves to {ra['earliest_retirement_age']}." if earlier else "."))
    else:
        summary = f"{_money(in_basis)} {label} is {_money(annual)} a year down the waterfall."

    return Composed(
        summary=summary,
        detail=("The savings figure is the single number that moves a retirement date most — "
                "more than returns, more than which funds. It's also the one entirely in your "
                "hands. The comparison above holds everything else fixed and changes only that."),
        facts=rows, sources=["R10_READINESS"],
        follow_ups=["can_i_retire_when_i_want", "how_much_per_month", "what_it_takes"],
        sections=sections,
        assumptions=[_assume("Everything else", "unchanged", "Same return, same retirement age, same spending.")],
        save_hint={"label": f"Save {_money(in_basis)} {label} as my plan", "method": "PATCH",
                   "path": "/api/profile",
                   "body": {"savings_basis": basis, "savings_amount": in_basis}},
    )


# --- scenario 5: retirement age ------------------------------------------------


def run_retirement_age(user: User, year: int, slots: Slots) -> Composed | NeedsInput:
    if slots.age is None:
        return NeedsInput(question="Retire at what age?", missing="age",
                          hint="\"what if I retire at 60\" is enough.")
    age = slots.age
    try:
        t = trial(user, retirement_age=age)
    except ValueError as e:
        return NeedsInput(question=str(e), missing="age")
    rb, ra = _readiness(user, year), _readiness(t, year)
    items = W.rule_retirement_age(t, year)

    rows = [_fact("Retirement age", f"{rb['retirement_age']} → {age}"),
            _fact("Years of saving left", f"{rb['years_to_retirement']} → {ra['years_to_retirement']}")]
    if rb.get("funded_ratio") is not None and ra.get("funded_ratio") is not None:
        rows += [_fact("Reaches, today's money",
                       f"{_money(rb['projected_at_retirement'])} → {_money(ra['projected_at_retirement'])}"),
                 _fact("Needed to last to " + str(ra["plan_to_age"]),
                       f"{_money(rb['needed_at_retirement'])} → {_money(ra['needed_at_retirement'])}"),
                 _fact("Funded", f"{rb['funded_ratio']:.0%} → {ra['funded_ratio']:.0%}")]
        if ra.get("extra_savings_per_year"):
            rows.append(_fact("Extra saving to make it work", f"{_money(ra['extra_savings_per_year'])} a year"))
        if ra.get("sustainable_monthly_spending"):
            rows.append(_fact("Spending that would last", f"{_money(ra['sustainable_monthly_spending'])} a month"))

    sections = [_section("The plan at " + str(age),
                         ("Retiring earlier does two things at once: fewer years of growth going "
                          "in, and more years of spending coming out." if age < rb["retirement_age"]
                          else "Every extra working year adds growth and removes a year of drawdown, "
                               "so the plan strengthens at both ends."),
                         rows)]
    for item in items:
        if item.priority.value != "info":
            sections.append(_section(item.title, item.detail, []))

    if ra.get("funded_ratio") is not None:
        status = {"on_track": "works", "close": "is close", "short": "falls short"}.get(ra["status"], "changes")
        summary = f"Retiring at {age}, the current plan {status} — {ra['funded_ratio']:.0%} funded."
    else:
        summary = f"Retiring at {age} changes the shape of the plan — add a spending figure to see if it holds."

    return Composed(
        summary=summary,
        detail=("Retirement age changes the advice, not just the chart. Before 59½ the plan needs "
                "money you can reach without a penalty; before 65 there's a health-coverage gap "
                "to bridge; past the RMD age withdrawals become mandatory. Each of those shows "
                "up above when it applies."),
        facts=rows, sources=["R9_RETIREMENT_AGE", "R10_READINESS"],
        follow_ups=["retirement_age_changes", "can_i_retire_when_i_want", "what_it_takes"],
        sections=sections,
        assumptions=[_assume("Everything else", "unchanged", "Same saving, same return, same spending.")],
        save_hint={"label": f"Plan to retire at {age}", "method": "PUT", "path": "/api/goal",
                   "body": {"retirement_age": age}},
    )


# --- registry ------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    "debt_strategy": {
        "question": "How should I plan around my debt?",
        "topic": "Debt",
        "keywords": [
            "plan around my debt", "manage my debt", "handle my debt", "deal with my debt",
            "what do i do about my loan", "pay off my loan", "pay off my student loans",
            "student debt", "student loans", "credit card debt", "car loan", "owe money",
            "get rid of my debt", "attack my debt", "tackle my debt", "loan strategy",
            "should i pay extra on my loan", "prioritize my debt", "debt plan",
            "pay off faster", "throw money at my loan", "in debt", "my debt",
        ],
        "needs": lambda s: s.mentions_debt,
        "slot_ready": lambda s, u: bool(s.balances) or any(d.balance > 0 for d in u.debts),
        "run": run_debt_strategy,
    },
    "windfall": {
        "question": "What should I do with a lump sum?",
        "topic": "Getting started",
        "keywords": [
            "what do i do with", "where should i put", "got a bonus", "inheritance",
            "inherited", "windfall", "lump sum", "tax refund", "came into money",
            "extra cash", "extra money", "gift", "settlement", "severance", "sold my",
            "what to do with 10k", "what should i do with this money", "large sum",
        ],
        "needs": lambda s: s.mentions_windfall or (bool(s.balances) and not s.mentions_debt
                                                   and not s.mentions_income and not s.ages),
        "slot_ready": lambda s, u: bool(s.balances),
        "run": run_windfall,
    },
    "income_change": {
        "question": "What changes if my income changes?",
        "topic": "Limits and eligibility",
        "keywords": [
            "what if i made", "what if i make", "what if i earned", "if my salary was",
            "got a raise", "new job paying", "if i earn", "income goes up", "promotion",
            "if i made more", "make more money", "higher salary", "pay cut", "make less",
            "salary of", "my income is", "i make", "i earn", "job offer",
        ],
        "needs": lambda s: s.mentions_income,
        "slot_ready": lambda s, u: bool(s.amounts) or (s.mentions_increment and bool(s.rates)),
        "run": run_income_change,
    },
    "contribution_change": {
        "question": "What if I saved a different amount?",
        "topic": "Retirement timing",
        "keywords": [
            "what if i saved", "if i save", "if i put away", "if i invested", "if i contribute",
            "save more", "save less", "a month instead", "per paycheck instead", "bump my",
            "increase my contribution", "what if i invest", "put in more", "saving more",
            "double my savings", "save an extra", "invest an extra", "more each month",
            "contribute more", "max out", "what if i saved more",
        ],
        "needs": lambda s: s.mentions_saving or bool(s.flows),
        "slot_ready": lambda s, u: bool(s.flows) or (bool(s.balances) and s.mentions_saving),
        "run": run_contribution_change,
    },
    "retirement_age": {
        "question": "What if I retire at a different age?",
        "topic": "Retirement timing",
        "keywords": [
            "retire at", "retire by", "retire early", "retire when i'm", "what if i retire",
            "stop working at", "quit at", "can i retire at", "retirement at", "retire in",
            "if i retired at", "retiring at", "leave work at", "done working at",
            "retire at 50", "retire at 55", "retire at 60", "retire at 62", "retire at 70",
        ],
        "needs": lambda s: bool(s.ages),
        "slot_ready": lambda s, u: bool(s.ages),
        "run": run_retirement_age,
    },
}


def run(scenario_id: str, user: User, year: int, slots: Slots) -> Composed | NeedsInput:
    return SCENARIOS[scenario_id]["run"](user, year, slots)
