"""The second surface: a structured Q&A layer over the same state.

The scope doc calls for a "chat" that reasons about the user's actual numbers. v1
does that without an LLM: a fixed set of questions people actually ask, each answered
by a pure function reading the same models, limits and rules the dashboard uses. No
external API, no cost, and — the point — no generated financial explanation that would
need vetting. Every answer is traceable to a rule or a content entry.

Answers use the same three layers as everything else: `summary` (one line, their
numbers), `detail` (plain English), `facts` (the arithmetic).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import content
import limits as L
import retirement as R
import schedule as S
import target as T
import tax
import waterfall as W
from models import AccountType, User


@dataclass
class Answer:
    summary: str
    detail: str
    facts: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    content_key: str | None = None


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _fact(label: str, value: str) -> dict:
    return {"label": label, "value": value}


# --- answers -------------------------------------------------------------------


def a_next_dollar(user: User, year: int) -> Answer:
    todo = W.prioritized(user, year)
    if not todo:
        return Answer(
            summary="You're through every step of the waterfall for this year.",
            detail=(
                "Emergency fund funded, match captured, no expensive debt, and every "
                "tax-advantaged account is full. Additional savings go into a taxable "
                "brokerage account, where there's no limit."
            ),
            sources=["R7_TAXABLE"],
            follow_ups=["what_to_invest_in", "taxable_tax"],
            content_key="taxable",
        )

    top = todo[0]
    facts = [_fact("This came from", f"{top.rule_id} — {top.rule_name}")]
    if top.amount:
        facts.insert(0, _fact("Amount", _money(top.amount)))
    if len(todo) > 1:
        facts.append(_fact("After that", todo[1].title))

    return Answer(
        summary=top.title,
        detail=top.detail,
        facts=facts,
        sources=[top.rule_id],
        follow_ups=["why_this_order", "how_much_can_i_put_in", "what_to_invest_in"],
    )


def a_why_this_order(user: User, year: int) -> Answer:
    explainer = content.waterfall_explainer(year)
    return Answer(
        summary="The order is about guaranteed returns first, then tax treatment.",
        detail=(
            "Nothing here is a ranking of which account is 'best' in the abstract. Each "
            "step sits above the next because the money does more there: an employer "
            "match is an instant guaranteed return, paying off a 22% card is a "
            "guaranteed 22%, and an HSA is the only account untaxed at all three stages. "
            "A taxable brokerage is last because it's the only one with no tax "
            "advantage at all — which also makes it the one with no limits."
        ),
        facts=[_fact(f"{s['step']}. {s['title']}", s["why"]) for s in explainer["steps"]],
        sources=[s["rule_id"] for s in explainer["steps"]],
        follow_ups=["next_dollar", "debt_or_invest"],
    )


def a_how_much_can_i_put_in(user: User, year: int) -> Answer:
    facts = []
    k401 = L.elective_401k_limit(user.age, year)
    catch_up = L.catch_up_401k(user.age, year)
    ira = L.ira_limit(user.age, year, user.income)
    facts.append(_fact("401(k), from your paycheck", _money(k401)))
    facts.append(_fact("IRA (traditional and Roth combined)", _money(ira)))

    hsas = [a for a in user.accounts_of(AccountType.HSA) if a.hdhp_enrolled]
    if hsas:
        cov = hsas[0].hsa_coverage.value
        facts.append(_fact(
            f"HSA ({cov.replace('_', '-')} coverage)", _money(L.hsa_limit(cov, user.age, year))
        ))
    else:
        facts.append(_fact("HSA", "Not available — needs a high-deductible health plan"))
    facts.append(_fact("Taxable brokerage", "No limit"))

    if catch_up:
        facts.append(_fact(
            f"Catch-up included at age {user.age}", f"{_money(catch_up)} extra in the 401(k)"
        ))

    total = k401 + ira + (L.hsa_limit(hsas[0].hsa_coverage.value, user.age, year) if hsas else 0)

    return Answer(
        summary=f"Across all your tax-advantaged accounts, {_money(total)} in {year}.",
        detail=(
            "These are separate allowances, not one shared pot — filling the IRA doesn't "
            "use up 401(k) room. Two things to watch: the 401(k) limit is per person, not "
            "per plan, so two jobs in one year still share one allowance; and the IRA "
            "limit is combined across traditional and Roth. Almost nobody fills all of "
            "this, which is why the order matters more than the totals."
        ),
        facts=facts,
        sources=[f"limits_{year}"],
        follow_ups=["next_dollar", "can_i_do_roth", "what_is_hsa"],
    )


def a_can_i_do_roth(user: User, year: int) -> Answer:
    elig = L.roth_ira_eligibility(
        user.effective_magi, user.filing_status.value, user.age, year, user.income
    )
    limit = L.ira_limit(user.age, year, user.income)
    facts = [
        _fact("Your income figure (MAGI)", _money(elig["magi"])),
        _fact("Phase-out starts", _money(elig["phaseout_start"])),
        _fact("Phase-out ends", _money(elig["phaseout_end"])),
        _fact("You can put into a Roth directly", _money(elig["allowed"])),
        _fact("Your total IRA limit", _money(limit)),
    ]

    if elig["status"] == "full":
        summary = f"Yes — all {_money(limit)} of your IRA room can go into a Roth."
        detail = (
            "Your income is below the point where the Roth option starts shrinking, so "
            "nothing is restricted. The remaining question is whether Roth or traditional "
            "suits you, which is a separate one about tax rates."
        )
    elif elig["status"] == "partial":
        summary = f"Partly — {_money(elig['allowed'])} of your {_money(limit)} can go in directly."
        detail = (
            "You're inside the phase-out band, where the direct Roth allowance shrinks as "
            "income rises rather than cutting off at once. The rest of your limit can go "
            "to a traditional IRA, or in through a backdoor conversion."
        )
    else:
        summary = "Not directly — but the backdoor route is open to you."
        detail = (
            "Your income is above the cut-off for contributing to a Roth IRA directly. "
            "The standard workaround is a backdoor Roth: contribute to a traditional IRA, "
            "which has no income limit on contributions, then convert it to Roth. Watch "
            "the pro-rata rule — if you already hold pre-tax money in any traditional IRA, "
            "part of that conversion is taxable."
        )

    return Answer(
        summary=summary,
        detail=detail,
        facts=facts,
        sources=["R5_IRA"],
        follow_ups=["roth_or_traditional", "what_is_ira", "how_much_can_i_put_in"],
        content_key="ira",
    )


def a_roth_or_traditional(user: User, year: int) -> Answer:
    c = tax.compare(user, year)
    now_r, later = c["now"]["marginal_rate"], c["retirement"]
    override = user.expects_lower_bracket_in_retirement
    facts = [
        _fact("Roth", "Taxed now, never again — not on growth, not on withdrawal"),
        _fact("Traditional", "Deduction now, ordinary income tax when you withdraw"),
        _fact("Your federal rate now", f"{now_r:.0%} on your next dollar"),
    ]
    if later:
        facts.append(_fact("In retirement (estimate)", f"{later['marginal_rate']:.0%} on your next dollar"))

    if override is not None:
        pick = "traditional" if override else "Roth"
        summary = f"On what you've told us, {pick} is the better fit."
        detail = (
            ("You said you expect a lower bracket in retirement — the case traditional is "
             "built for: take the deduction now at your higher rate, pay tax later at the "
             "lower one." if override else
             "You said you don't expect a lower bracket later — the case Roth is built for: "
             "pay the tax at today's rate and never again, on the contribution or its growth.")
        )
        if later and c["estimated_verdict"] != c["verdict"]:
            detail += (
                f" For what it's worth, the estimate from your numbers points the other way "
                f"({now_r:.0%} now against {later['marginal_rate']:.0%} later). Clear your "
                f"answer on 'About you' to let the estimate decide."
            )
    elif later is None:
        summary = "It comes down to your tax rate now against in retirement."
        detail = (
            f"Your next dollar is taxed at about {now_r:.0%} today. To estimate the "
            f"retirement side we need what you spend a month — add it on 'About you'. Early "
            f"in a career, now is usually the lower rate, which favours Roth."
        )
    else:
        later_r = later["marginal_rate"]
        pick = "traditional" if c["estimated_verdict"] == "traditional" else "Roth"
        summary = f"On your numbers, {pick} comes out ahead."
        spend = f"{later['spending'] / 12:,.0f}"
        detail = (
            f"Today your next dollar is taxed at about {now_r:.0%}. In retirement, spending "
            f"${spend} a month"
            + (f" with ${later['social_security'] / 12:,.0f} of it from Social Security"
               if later["social_security"] else "")
            + f", the money you'd withdraw from a traditional account would be taxed at about "
            f"{later_r:.0%}. "
            + ("Paying the lower rate now is the better deal — that's Roth."
               if pick == "Roth" and now_r < later_r else
               "The rates are level, and a tie leans Roth: no required withdrawals, and "
               "tax-free money to draw on later." if pick == "Roth" else
               "Taking the deduction at today's higher rate is the better deal — that's "
               "traditional.")
            + " It's an estimate — federal only, today's brackets — and splitting between "
            "both is a perfectly reasonable hedge."
        )
        if c["per_1000"]:
            facts.append(_fact(
                "Worth, per $1,000",
                f"about ${abs(c['per_1000']):,.0f} more with {pick}"))

    return Answer(
        summary=summary,
        detail=detail,
        facts=facts,
        sources=["R5_IRA"],
        follow_ups=["can_i_do_roth", "what_is_ira"],
        content_key="ira",
    )


def a_emergency_fund(user: User, year: int) -> Answer:
    items = W.rule_emergency_fund(user, year)
    item = items[0]
    return Answer(
        summary=item.title,
        detail=item.detail,
        facts=[
            _fact("Cash you have", _money(item.inputs.get("cash_on_hand", 0))),
            _fact("Your monthly expenses", _money(item.inputs.get("monthly_expenses", 0))),
            _fact("Months that covers", str(item.inputs.get("months_covered", "—"))),
            _fact("Minimum recommended", _money(item.inputs.get("floor_amount", 0))),
            _fact("Your target", _money(item.inputs.get("target_amount", 0))),
        ] if item.inputs.get("monthly_expenses") else [],
        sources=["R1_EMERGENCY_FUND"],
        follow_ups=["next_dollar", "why_this_order"],
    )


def a_debt_or_invest(user: User, year: int) -> Answer:
    cutoff = L.load_limits(year)["thresholds"]["high_interest_debt_apr"]
    owing = [d for d in user.debts if d.balance > 0]   # paid-off debts stay on file
    expensive = sorted((d for d in owing if d.apr > cutoff),
                       key=lambda d: d.apr, reverse=True)
    cheap = [d for d in owing if d.apr <= cutoff]

    facts = [_fact(d.name, f"{d.apr:.1%} — pay this off first") for d in expensive]
    facts += [_fact(d.name, f"{d.apr:.1%} — pay on schedule, invest alongside") for d in cheap]
    facts.append(_fact("The cutoff we use", f"{cutoff:.1%} APR"))

    if expensive:
        worst = expensive[0]
        summary = f"Pay off {worst.name} first — {worst.apr:.1%} is a guaranteed return you can't beat."
        detail = (
            f"Clearing a {worst.apr:.1%} debt is mathematically identical to earning "
            f"{worst.apr:.1%} risk-free, which is well above the roughly 7% a diversified "
            f"stock portfolio has averaged over the long run — and that average comes with "
            f"years where it's negative. The one exception is an employer match, which "
            f"beats almost any interest rate, so capture that first and then attack the debt."
        )
    else:
        summary = "Invest — nothing you owe is expensive enough to come first."
        detail = (
            f"Debt below about {cutoff:.1%} is generally worth paying on schedule while you "
            f"invest, because long-run market returns have historically exceeded low "
            f"single-digit interest. That's a judgement about averages, not a guarantee — "
            f"if the debt is causing you stress, paying it off early is a legitimate choice "
            f"the math doesn't capture."
        )

    return Answer(
        summary=summary, detail=detail, facts=facts,
        sources=["R3_HIGH_INTEREST_DEBT", "R2_EMPLOYER_MATCH"],
        follow_ups=["next_dollar", "why_this_order"],
    )


def a_what_to_invest_in(user: User, year: int) -> Answer:
    idle = sum(a.uninvested_cash for a in user.accounts_of(
        AccountType.TRADITIONAL_401K, AccountType.IRA,
        AccountType.HSA, AccountType.TAXABLE))
    pricey = [
        (acct, h) for acct in user.accounts
        for h in acct.holdings
        if h.expense_ratio is not None and h.expense_ratio > 0.005
    ]

    facts = [
        _fact("A broad index fund costs about", "0.03% a year — $30 per $100,000"),
        _fact("An expensive fund costs about", "0.75% a year — $750 per $100,000"),
        _fact("The one-decision option", "A target-date fund near your retirement year"),
    ]
    if idle > 1:
        facts.insert(0, _fact("Sitting in cash right now", _money(idle)))
    for acct, h in pricey:
        facts.append(_fact(
            f"{h.symbol} in your {acct.nickname or acct.type.value}",
            f"{h.expense_ratio:.2%} a year — about {_money(h.value * h.expense_ratio)}",
        ))

    if idle > 1:
        summary = f"First, get the {_money(idle)} sitting in cash actually invested."
    elif pricey:
        summary = "You're invested — but you're paying more in fees than you need to."
    else:
        summary = "A broad index fund or a target-date fund covers the whole decision."

    return Answer(
        summary=summary,
        detail=(
            "Opening the account and investing the money are two separate actions, and "
            "money that clears the first but not the second sits in cash for years. What "
            "goes inside is a fund: one ticker holding hundreds or thousands of companies, "
            "so no single company failing can take you with it. An index fund does that by "
            "tracking a list rather than paying anyone to pick, which is why it costs almost "
            "nothing — and that cost, the expense ratio, comes out every year whether the "
            "market is up or down. A target-date fund goes further: pick the year you'll "
            "retire and it handles the mix and the rebalancing for you."
        ),
        facts=facts,
        sources=["R8_VEHICLE"],
        follow_ups=["what_is_taxable", "next_dollar"],
        content_key="index_funds",
    )


def a_am_i_missing_match(user: User, year: int) -> Answer:
    items = W.rule_employer_match(user, year)
    if not items:
        return Answer(
            summary="You haven't told us about a 401(k), so we can't check.",
            detail=(
                "An employer match is the only guaranteed return in the whole plan, and it's "
                "the easiest thing to leave unclaimed without noticing. Add your 401(k) on "
                "the Accounts page with the match terms from your benefits paperwork."
            ),
            sources=["R2_EMPLOYER_MATCH"],
            follow_ups=["what_is_401k", "next_dollar"],
            content_key="401k",
        )
    item = items[0]
    return Answer(
        summary=item.title,
        detail=item.detail,
        facts=[_fact(k.replace("_", " ").capitalize(),
                     _money(v) if isinstance(v, (int, float)) and v > 1 else str(v))
               for k, v in item.inputs.items()],
        sources=["R2_EMPLOYER_MATCH"],
        follow_ups=["what_is_401k", "why_this_order"],
        content_key="401k",
    )


def _explainer(key: str):
    """"What is X?" answers come straight from the content module, so the Q&A layer
    and the Learn pages can never drift apart."""
    def answer(user: User, year: int) -> Answer:
        entry = content.CONTENT[key]
        return Answer(
            summary=content.layer1(key, user, year),
            detail=entry["layer2"],
            facts=[_fact("Worth knowing", d) for d in entry["layer3"][:4]],
            sources=[f"content:{key}"],
            follow_ups={
                "401k": ["am_i_missing_match", "roth_or_traditional", "how_much_can_i_put_in"],
                "ira": ["can_i_do_roth", "roth_or_traditional"],
                "hsa": ["how_much_can_i_put_in", "next_dollar"],
                "taxable": ["what_to_invest_in", "taxable_tax"],
            }[key],
            content_key=key,
        )
    return answer


def a_taxable_tax(user: User, year: int) -> Answer:
    return Answer(
        summary="Hold for more than a year, and hold index funds — that's most of it.",
        detail=(
            "A taxable account owes tax on dividends each year and on gains when you sell. "
            "Two rules do most of the work in keeping that small. Sell something you've "
            "held over a year and the gain is taxed at the long-term capital gains rate "
            "instead of your income rate — often a 10 to 17 point difference. And broad "
            "index funds distribute very little year to year, so a buy-and-hold position "
            "can go years generating almost no taxable events at all."
        ),
        facts=[
            _fact("Held over a year", "Long-term rate — 0%, 15% or 20% by income"),
            _fact("Held under a year", "Taxed as ordinary income"),
            _fact("Losses", "Offset gains, plus up to $3,000 of income a year"),
            _fact("Wash-sale rule", "No loss deduction if you rebuy within 30 days either side"),
        ],
        sources=["content:taxable"],
        follow_ups=["what_to_invest_in", "what_is_taxable"],
        content_key="taxable",
    )


def a_monthly_plan(user: User, year: int) -> Answer:
    """The same waterfall, written as a month and a payday."""
    plan = S.schedule(user, year, months=1)
    moves = plan["this_month"]["moves"] if plan["this_month"] else []
    pay = plan["paycheck"]

    if not moves:
        return Answer(
            summary="We can't schedule anything yet — tell us what you could save.",
            detail=(
                "A monthly schedule needs one number to work from: what you can put aside "
                "each month. Add it on About you and this turns into a list of exactly what "
                "to move, in what order, and how much of it comes out of each paycheck "
                "rather than in one lump."
            ),
            sources=["R7_TAXABLE"],
            follow_ups=["next_dollar", "emergency_fund"],
        )

    facts = [
        _fact(m["label"], f"{_money(m['amount'])} a month — {_money(m['per_paycheck'])} "
                          f"per paycheck" + (f" ({m['percent_of_pay']:.0%} of pay)"
                                             if m["percent_of_pay"] else ""))
        for m in moves
    ]
    facts.append(_fact("You're paid", f"{pay['label']} — {pay['paychecks_per_year']} times a year"))
    if pay["free_to_spend"] is not None:
        facts.append(_fact("Left to spend each payday", _money(pay["free_to_spend"])))

    return Answer(
        summary=f"{_money(plan['monthly_savings'])} a month, split across {len(moves)} "
                f"{'move' if len(moves) == 1 else 'moves'}.",
        detail=(
            "This is the same order as your plan, just written as a month. Two things are "
            "worth knowing about the split. Money going into a 401(k) only moves on payday, "
            "so it's set as a percentage of pay and paced across the year rather than "
            "front-loaded. Everything else is a transfer you make yourself, which can happen "
            "any day of the month — the day after payday is the one people actually stick to. "
            "Minimum payments on debts are treated as bills, so they're not in this list."
        ),
        facts=facts,
        sources=[m["rule_id"] for m in moves],
        follow_ups=["next_dollar", "can_i_retire_when_i_want", "what_to_invest_in"],
    )


def _age(age: float) -> str:
    return "59½" if age == 59.5 else f"{age:g}"


def a_can_i_retire(user: User, year: int) -> Answer:
    """Read straight from rule 10, so the answer and the dashboard can't disagree."""
    item = W.rule_readiness(user, year)[0]
    i = item.inputs
    facts = []
    if i.get("funded_ratio") is not None:
        earliest = i["earliest_retirement_age"]
        facts = [
            _fact("Retirement age you picked", str(i["retirement_age"])),
            _fact("Your plan reaches (today's money)", _money(i["projected_at_retirement"])),
            _fact(f"Needed to last to {i['plan_to_age']}", _money(i["needed_at_retirement"])),
            _fact("How far that gets you", f"{i['funded_ratio']:.0%}"),
            _fact("Earliest age this plan supports",
                  str(earliest) if earliest is not None else "Not before 80 on current savings"),
            _fact("Spending that lasts the whole plan",
                  f"{_money(i['sustainable_monthly_spending'])} a month"),
        ]
        if i["extra_savings_per_year"]:
            facts.append(_fact("Extra saving to retire at your age",
                               f"{_money(i['extra_savings_per_year'])} a year"))
        if i["money_lasts_to_age"]:
            facts.append(_fact("Money runs out around age", str(i["money_lasts_to_age"])))
    return Answer(
        summary=item.title,
        detail=item.detail,
        facts=facts,
        sources=["R10_READINESS"],
        follow_ups=["retirement_age_changes", "next_dollar", "how_much_can_i_put_in"],
    )


def a_retirement_age_changes(user: User, year: int) -> Answer:
    items = W.rule_retirement_age(user, year)
    return Answer(
        summary=items[0].title,
        detail=" ".join(i.detail for i in items),
        facts=[_fact(f"Age {_age(m['age'])}", f"{m['label']}. {m['detail']}")
               for m in R.milestones(user, year)],
        sources=["R9_RETIREMENT_AGE"],
        follow_ups=["can_i_retire_when_i_want", "what_is_taxable", "roth_or_traditional"],
    )


def a_what_it_takes(user: User, year: int) -> Answer:
    """The plan run backwards — the one question the waterfall never answers on its
    own, because it's about the size of the task rather than the order of it."""
    est = T.estimate(user, year)
    req, cur, extra = est["required"], est["current"], est["extra"]
    coast = est["coast"]

    if req["annual"] is None:
        return Answer(
            summary="There are no saving years left to spread this across.",
            detail=(
                "You're at or past the age you're planning to, so the question changes "
                "from what to put in to what to take out. Spending, when you claim "
                "Social Security, and how long the money has to last are the levers now."
            ),
            sources=["R10_READINESS"],
            follow_ups=["can_i_retire_when_i_want", "retirement_age_changes"],
        )

    facts = [
        _fact("A year", _money(req["annual"])),
        _fact("A month", _money(req["monthly"])),
        _fact(f"Per paycheck ({req['paychecks_per_year']} a year)", _money(req["per_paycheck"])),
    ]
    if req["percent_of_pay"] is not None:
        facts.append(_fact("Share of your pay", f"{req['percent_of_pay']:.0%}"))
    facts += [
        _fact("You're on track for", f"{_money(cur['monthly'])} a month"),
        _fact(f"Needed by {est['target_age']} (today's money)", _money(est["needed_at_target"])),
        _fact("You have invested now", _money(est["already_have"])),
        _fact("Stop-saving point", _money(coast["number"])),
    ]

    if est["on_track"]:
        summary = "Nothing more — what you have invested already gets there on its own."
    elif extra["annual"] and extra["annual"] > 0:
        summary = (f"{_money(req['monthly'])} a month — {_money(extra['monthly'])} more "
                   f"than you're putting in now.")
    else:
        summary = f"{_money(req['monthly'])} a month, which your plan already covers."

    detail = (
        f"{est['description']}. Working backwards from that number and assuming your "
        f"existing balance keeps growing, the contribution that closes the gap is "
        f"{_money(req['annual'])} a year. The same money three ways: "
        f"{_money(req['monthly'])} a month, or {_money(req['per_paycheck'])} out of every "
        f"paycheck — the last one is the version that becomes a standing transfer. "
    )
    if coast["age"] is not None and not coast["reached"]:
        detail += (
            f"Worth knowing: once you've got {_money(coast['number'])} invested — around "
            f"age {coast['age']} at this pace — compounding alone carries you to the "
            f"target even if you never contribute again. "
        )
    if est["cost_of_waiting"]:
        wait = est["cost_of_waiting"][0]
        detail += (
            f"Waiting {wait['wait_years']} year"
            f"{'' if wait['wait_years'] == 1 else 's'} to start pushes it to "
            f"{_money(wait['required']['monthly'])} a month — the cost of a late start is "
            f"paid every month afterwards."
        )

    return Answer(
        summary=summary,
        detail=detail,
        facts=facts,
        sources=["R10_READINESS"],
        follow_ups=["can_i_retire_when_i_want", "how_much_per_month", "how_much_can_i_put_in"],
    )


# --- the question set ----------------------------------------------------------

QUESTIONS: dict[str, dict] = {
    "next_dollar": {
        "question": "Where should my next dollar go?",
        "topic": "Getting started",
        "answer": a_next_dollar,
    },
    "why_this_order": {
        "question": "Why is the order what it is?",
        "topic": "Getting started",
        "answer": a_why_this_order,
    },
    "emergency_fund": {
        "question": "Do I have enough saved for emergencies?",
        "topic": "Getting started",
        "answer": a_emergency_fund,
    },
    "debt_or_invest": {
        "question": "Should I pay off debt or invest?",
        "topic": "Getting started",
        "answer": a_debt_or_invest,
    },
    "how_much_per_month": {
        "question": "What do I actually do each month?",
        "topic": "Getting started",
        "answer": a_monthly_plan,
    },
    "can_i_retire_when_i_want": {
        "question": "Can I retire at the age I want?",
        "topic": "Retirement timing",
        "answer": a_can_i_retire,
    },
    "retirement_age_changes": {
        "question": "What changes if I retire earlier or later?",
        "topic": "Retirement timing",
        "answer": a_retirement_age_changes,
    },
    "what_it_takes": {
        "question": "How much do I need to invest to get there?",
        "topic": "Retirement timing",
        "answer": a_what_it_takes,
    },
    "how_much_can_i_put_in": {
        "question": "How much can I put in this year?",
        "topic": "Limits and eligibility",
        "answer": a_how_much_can_i_put_in,
    },
    "can_i_do_roth": {
        "question": "Can I contribute to a Roth IRA?",
        "topic": "Limits and eligibility",
        "answer": a_can_i_do_roth,
    },
    "am_i_missing_match": {
        "question": "Am I leaving employer match on the table?",
        "topic": "Limits and eligibility",
        "answer": a_am_i_missing_match,
    },
    "roth_or_traditional": {
        "question": "Roth or traditional — which should I pick?",
        "topic": "Choosing between options",
        "answer": a_roth_or_traditional,
    },
    "what_to_invest_in": {
        "question": "What do I actually invest in?",
        "topic": "Choosing between options",
        "answer": a_what_to_invest_in,
    },
    "taxable_tax": {
        "question": "How is a taxable account taxed?",
        "topic": "Choosing between options",
        "answer": a_taxable_tax,
    },
    "what_is_401k": {
        "question": "What is a 401(k)?",
        "topic": "What these accounts are",
        "answer": _explainer("401k"),
    },
    "what_is_ira": {
        "question": "What is an IRA?",
        "topic": "What these accounts are",
        "answer": _explainer("ira"),
    },
    "what_is_hsa": {
        "question": "What is an HSA?",
        "topic": "What these accounts are",
        "answer": _explainer("hsa"),
    },
    "what_is_taxable": {
        "question": "What is a taxable brokerage account?",
        "topic": "What these accounts are",
        "answer": _explainer("taxable"),
    },
}

TOPIC_ORDER = [
    "Getting started",
    "Retirement timing",
    "Limits and eligibility",
    "Choosing between options",
    "What these accounts are",
]


def index() -> list[dict]:
    """Questions grouped by topic, in a deliberate order — the browse surface."""
    return [
        {
            "topic": topic,
            "questions": [
                {"id": qid, "question": q["question"]}
                for qid, q in QUESTIONS.items()
                if q["topic"] == topic
            ],
        }
        for topic in TOPIC_ORDER
    ]


def ask(question_id: str, user: User, year: int = L.DEFAULT_YEAR) -> dict:
    entry = QUESTIONS.get(question_id)
    if entry is None:
        raise KeyError(question_id)
    answer = entry["answer"](user, year)
    return {
        "id": question_id,
        "question": entry["question"],
        "topic": entry["topic"],
        "year": year,
        "answer": asdict(answer),
        "follow_ups": [
            {"id": fid, "question": QUESTIONS[fid]["question"]}
            for fid in answer.follow_ups
            if fid in QUESTIONS
        ],
        "disclaimer": content.DISCLAIMER,
    }
