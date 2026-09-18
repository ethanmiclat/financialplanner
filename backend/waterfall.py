"""The prioritization waterfall — the recommendation engine.

Deterministic and inspectable by design: every ActionItem carries the `rule_id` that
produced it plus the exact inputs used, so the UI can show its work. No LLM, no
"black box", nothing that reads as personalized buy/sell advice.

Each rule is a pure function `(user, limits_year) -> list[ActionItem]`.
"""

from __future__ import annotations

from dataclasses import dataclass

import limits as L
import retirement as R
import tax
from models import (
    AccountType,
    ActionItem,
    Priority,
    User,
)

# --- shared helpers ------------------------------------------------------------


def _money(x: float) -> str:
    return f"${x:,.0f}"


def cash_balance(user: User) -> float:
    return sum(a.balance for a in user.accounts_of(AccountType.CASH))


@dataclass
class Rule:
    id: str
    step: int
    name: str


RULES = [
    Rule("R1_EMERGENCY_FUND", 1, "Emergency fund before investing"),
    Rule("R2_EMPLOYER_MATCH", 2, "Capture the full employer 401(k) match"),
    Rule("R3_HIGH_INTEREST_DEBT", 3, "Pay down high-interest debt"),
    Rule("R4_HSA", 4, "Max the HSA (if HDHP-eligible)"),
    Rule("R5_IRA", 5, "Max a Roth or Traditional IRA"),
    Rule("R6_REMAINING_401K", 6, "Max remaining 401(k) space"),
    Rule("R7_TAXABLE", 7, "Invest in a taxable brokerage account"),
    Rule("R8_VEHICLE", 8, "Get contributed dollars actually invested"),
    Rule("R9_RETIREMENT_AGE", 9, "Line your accounts up with when you'll retire"),
    Rule("R10_READINESS", 10, "Check the plan pays for the retirement you picked"),
]
RULES_BY_ID = {r.id: r for r in RULES}


def _item(rule_id: str, *, title: str, detail: str, **kw) -> ActionItem:
    rule = RULES_BY_ID[rule_id]
    return ActionItem(
        rule_id=rule.id, rule_name=rule.name, step=rule.step,
        title=title, detail=detail, **kw
    )


# --- Rule 1: emergency fund ----------------------------------------------------


def rule_emergency_fund(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    thresholds = L.load_limits(year)["thresholds"]
    monthly = user.goal.monthly_expenses
    if monthly <= 0:
        return [_item(
            "R1_EMERGENCY_FUND",
            title="Tell us your monthly expenses so we can size your emergency fund",
            detail=(
                "Every step below this one assumes you have cash set aside first. "
                "Without a monthly expense figure we can't size that cushion."
            ),
            priority=Priority.BLOCKING,
            inputs={"monthly_expenses": monthly},
        )]

    cash = cash_balance(user)
    floor = monthly * thresholds["emergency_fund_months_floor"]
    target = user.goal.emergency_fund_target
    months_covered = cash / monthly

    inputs = {
        "cash_on_hand": cash,
        "monthly_expenses": monthly,
        "months_covered": round(months_covered, 1),
        "floor_months": thresholds["emergency_fund_months_floor"],
        "target_months": user.goal.emergency_fund_months,
        "floor_amount": floor,
        "target_amount": target,
    }

    if cash < floor:
        return [_item(
            "R1_EMERGENCY_FUND",
            title=f"Build your emergency fund to {_money(floor)} before investing",
            detail=(
                f"You have {_money(cash)} in cash — about {months_covered:.1f} months of "
                f"expenses. Below three months, an unexpected bill turns into credit card "
                f"debt or an early withdrawal from a retirement account, and both cost more "
                f"than the investment returns you'd be giving up by waiting."
            ),
            amount=floor - cash,
            priority=Priority.BLOCKING,
            account_type=AccountType.CASH,
            inputs=inputs,
        )]

    if cash < target:
        return [_item(
            "R1_EMERGENCY_FUND",
            title=f"Top up your emergency fund toward {_money(target)}",
            detail=(
                f"You're past the three-month floor at {months_covered:.1f} months, so you can "
                f"start investing. Keep filling toward your {user.goal.emergency_fund_months}-month "
                f"target alongside the steps below rather than instead of them."
            ),
            amount=target - cash,
            priority=Priority.MEDIUM,
            account_type=AccountType.CASH,
            inputs=inputs,
        )]

    return [_item(
        "R1_EMERGENCY_FUND",
        title=f"Emergency fund is funded — {months_covered:.1f} months covered",
        detail=(
            "Cash cushion is where it should be. Extra cash beyond this earns a savings "
            "rate, so the steps below are where additional dollars do more work."
        ),
        priority=Priority.INFO,
        account_type=AccountType.CASH,
        inputs=inputs,
    )]


# --- Rule 2: employer match ----------------------------------------------------


def rule_employer_match(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    items: list[ActionItem] = []
    plans = user.accounts_of(AccountType.TRADITIONAL_401K)

    if not plans:
        if user.has_401k_at_work:
            items.append(_item(
                "R2_EMPLOYER_MATCH",
                title="Add your 401(k) so we can check whether you're leaving match on the table",
                detail=(
                    "An employer match is the only guaranteed return in this whole list. "
                    "A 50% match is a 50% return the moment the money lands."
                ),
                priority=Priority.HIGH,
                account_type=AccountType.TRADITIONAL_401K,
            ))
        else:
            # Still report. A silently skipped step reads as a bug, and plenty of
            # part-time and hourly roles genuinely don't offer a plan.
            items.append(_item(
                "R2_EMPLOYER_MATCH",
                title="No workplace retirement plan — this step doesn't apply to you",
                detail=(
                    "You've told us your job doesn't offer a 401(k), so there's no employer "
                    "match to capture. That's common in part-time and hourly work, and it "
                    "isn't a problem: an IRA is the account you open yourself, and it does "
                    "the same job. If a future employer does offer a match, this jumps "
                    "straight to the top of your list."
                ),
                priority=Priority.INFO,
                account_type=AccountType.TRADITIONAL_401K,
                inputs={"has_401k_at_work": False},
            ))
        return items

    for plan in plans:
        if plan.employer_match_rate <= 0 or plan.employer_match_limit_pct <= 0:
            items.append(_item(
                "R2_EMPLOYER_MATCH",
                title=f"No employer match recorded on {plan.nickname or '401(k)'}",
                detail=(
                    "Nothing to capture here, so this step is a no-op for you. If your plan "
                    "does match and it just isn't entered, add it — it would jump to the top."
                ),
                priority=Priority.INFO,
                account_type=AccountType.TRADITIONAL_401K,
                inputs={"employer_match_rate": plan.employer_match_rate},
            ))
            continue

        deferral_needed = user.income * plan.employer_match_limit_pct
        max_match = deferral_needed * plan.employer_match_rate
        shortfall = max(0.0, deferral_needed - plan.contributions_ytd)
        match_left = shortfall * plan.employer_match_rate

        inputs = {
            "income": user.income,
            "match_rate": plan.employer_match_rate,
            "match_limit_pct": plan.employer_match_limit_pct,
            "deferral_needed_for_full_match": deferral_needed,
            "max_match_dollars": max_match,
            "contributions_ytd": plan.contributions_ytd,
            "employer_match_received_ytd": plan.employer_match_received_ytd,
            "unclaimed_match": match_left,
        }

        if shortfall > 0:
            items.append(_item(
                "R2_EMPLOYER_MATCH",
                title=f"Contribute {_money(shortfall)} more to capture {_money(match_left)} of match",
                detail=(
                    f"Your plan matches {plan.employer_match_rate:.0%} on the first "
                    f"{plan.employer_match_limit_pct:.0%} of pay — {_money(deferral_needed)} of "
                    f"contributions unlocks {_money(max_match)}. You've put in "
                    f"{_money(plan.contributions_ytd)} so far. Unclaimed match is money your "
                    f"employer has already budgeted for you; it doesn't roll over to next year."
                ),
                amount=shortfall,
                priority=Priority.HIGH,
                account_type=AccountType.TRADITIONAL_401K,
                inputs=inputs,
            ))
        else:
            items.append(_item(
                "R2_EMPLOYER_MATCH",
                title=f"Full employer match captured ({_money(max_match)})",
                detail=(
                    "You're contributing enough to get every matched dollar. Additional 401(k) "
                    "contributions still help, but they come back at step 6, after the HSA and IRA."
                ),
                priority=Priority.INFO,
                account_type=AccountType.TRADITIONAL_401K,
                inputs=inputs,
            ))
    return items


# --- Rule 3: high-interest debt ------------------------------------------------


def rule_high_interest_debt(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    cutoff = L.load_limits(year)["thresholds"]["high_interest_debt_apr"]
    expensive = sorted(
        # A logged-down-to-zero debt stays on file (so the payment can be undone) but
        # is no longer in the way.
        (d for d in user.debts if d.apr > cutoff and d.balance > 0),
        key=lambda d: d.apr, reverse=True
    )
    if not expensive:
        return [_item(
            "R3_HIGH_INTEREST_DEBT",
            title="No high-interest debt in the way",
            detail=(
                f"Nothing on file above {cutoff:.1%} APR. Debt cheaper than that is generally "
                f"worth paying on schedule while you invest, since long-run market returns have "
                f"historically exceeded low single-digit interest."
            ),
            priority=Priority.INFO,
            inputs={"cutoff_apr": cutoff},
        )]

    items = []
    for debt in expensive:
        annual_interest = debt.balance * debt.apr
        items.append(_item(
            "R3_HIGH_INTEREST_DEBT",
            title=f"Pay off {debt.name} ({debt.apr:.1%} APR, {_money(debt.balance)})",
            detail=(
                f"This debt costs you about {_money(annual_interest)} a year. Paying it down is a "
                f"guaranteed {debt.apr:.1%} return — better than the ~7% a diversified stock "
                f"portfolio has averaged, and without the risk. Clear it before steps 4-7."
            ),
            amount=debt.balance,
            priority=Priority.BLOCKING if debt.apr >= 0.15 else Priority.HIGH,
            inputs={
                "name": debt.name,
                "balance": debt.balance,
                "apr": debt.apr,
                "cutoff_apr": cutoff,
                "annual_interest_cost": annual_interest,
                "minimum_payment": debt.minimum_payment,
            },
        ))
    return items


# --- Rule 4: HSA ---------------------------------------------------------------


def rule_hsa(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    hsas = user.accounts_of(AccountType.HSA)
    eligible = [a for a in hsas if a.hdhp_enrolled]

    if not eligible:
        return [_item(
            "R4_HSA",
            title="No HDHP on file — the HSA step doesn't apply to you this year",
            detail=(
                "HSAs require enrollment in a high-deductible health plan. If you are on one "
                "and just haven't added the account, add it: the HSA is the only account that's "
                "untaxed going in, growing, and coming out for medical costs."
            ),
            priority=Priority.INFO,
            account_type=AccountType.HSA,
            inputs={"hdhp_enrolled": False},
        )]

    items = []
    base = L.load_limits(year)["hsa"]
    for hsa in eligible:
        limit = L.hsa_limit(hsa.hsa_coverage.value, user.age, year)
        room = max(0.0, limit - hsa.contributions_ytd)
        inputs = {
            "coverage": hsa.hsa_coverage.value,
            "annual_limit": limit,
            "catch_up_included": limit - base[hsa.hsa_coverage.value],
            "contributions_ytd": hsa.contributions_ytd,
            "remaining_room": room,
            "year": year,
        }
        if room <= 0:
            items.append(_item(
                "R4_HSA",
                title=f"HSA maxed for {year} ({_money(limit)})",
                detail="Nothing left to contribute here this year. Move to the IRA step.",
                priority=Priority.INFO,
                account_type=AccountType.HSA,
                inputs=inputs,
            ))
            continue
        items.append(_item(
            "R4_HSA",
            title=f"Contribute {_money(room)} more to your HSA (limit {_money(limit)})",
            detail=(
                f"The HSA is the only triple-tax-advantaged account: contributions are "
                f"deductible, growth is untaxed, and withdrawals for qualified medical expenses "
                f"are untaxed too. Your {hsa.hsa_coverage.value.replace('_', '-')} limit for "
                f"{year} is {_money(limit)} and you've contributed {_money(hsa.contributions_ytd)}."
            ),
            amount=room,
            priority=Priority.HIGH,
            account_type=AccountType.HSA,
            inputs=inputs,
        ))
    return items


# --- Rule 5: IRA ---------------------------------------------------------------


def rule_ira(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    iras = user.accounts_of(AccountType.IRA)
    used = sum(a.contributions_ytd for a in iras)
    limit = L.ira_limit(user.age, year, user.income)
    room = max(0.0, limit - used)
    roth = L.roth_ira_eligibility(
        user.effective_magi, user.filing_status.value, user.age, year, user.income
    )

    inputs = {
        "combined_limit": limit,
        "statutory_limit": L.ira_limit(user.age, year),
        "capped_by_earned_income": limit < L.ira_limit(user.age, year),
        "contributions_ytd": used,
        "remaining_room": room,
        "roth_eligibility": roth,
        "filing_status": user.filing_status.value,
        "year": year,
    }

    if room <= 0:
        return [_item(
            "R5_IRA",
            title=f"IRA maxed for {year} ({_money(limit)})",
            detail=(
                "The limit is combined across traditional and Roth IRAs, and you've used it. "
                "Remaining dollars go to step 6."
            ),
            priority=Priority.INFO,
            account_type=AccountType.IRA,
            inputs=inputs,
        )]

    if roth["status"] == "phased_out":
        detail = (
            f"Your MAGI of {_money(roth['magi'])} is above the "
            f"{_money(roth['phaseout_end'])} Roth cutoff for your filing status, so you can't "
            f"contribute to a Roth IRA directly. The standard route is a 'backdoor Roth': "
            f"contribute to a traditional IRA (there's no income limit on contributing) and "
            f"convert it to Roth. Watch the pro-rata rule — existing pre-tax traditional IRA "
            f"balances make the conversion partly taxable."
        )
        title = f"Contribute {_money(room)} to an IRA — direct Roth is phased out for you"
    elif roth["status"] == "partial":
        detail = (
            f"You're inside the Roth phase-out band ({_money(roth['phaseout_start'])}–"
            f"{_money(roth['phaseout_end'])} MAGI), so {_money(roth['allowed'])} of your "
            f"{_money(limit)} limit can go directly into a Roth this year. The rest can go to a "
            f"traditional IRA, or in via a backdoor conversion."
        )
        title = f"Contribute {_money(room)} to an IRA ({_money(roth['allowed'])} of it Roth-eligible)"
    else:
        detail = (
            f"You're under the {_money(roth['phaseout_start'])} phase-out, so the full "
            f"{_money(limit)} can go into a Roth IRA. Roth means you pay tax now and nothing "
            f"later; traditional means a deduction now and tax on withdrawal. The deciding "
            f"question is whether your tax rate is lower now than it will be in retirement — "
            + tax_sentence(user, year)
        )
        title = f"Contribute {_money(room)} to an IRA (Roth available in full)"

    if inputs["capped_by_earned_income"]:
        detail += (
            f" Note: your limit here is {_money(limit)} rather than the standard "
            f"{_money(L.ira_limit(user.age, year))} because you can't contribute more to "
            f"an IRA than you earned this year."
        )

    return [_item(
        "R5_IRA",
        title=title,
        detail=detail,
        amount=room,
        priority=Priority.HIGH,
        account_type=AccountType.IRA,
        inputs=inputs,
    )]


def tax_sentence(user: User, year: int) -> str:
    """How the Roth-or-traditional question comes out for this user, in one sentence
    that shows the two rates it rests on."""
    c = tax.compare(user, year)
    now_r, later = c["now"]["marginal_rate"], c["retirement"]
    if user.expects_lower_bracket_in_retirement is True:
        return ("and you've said you expect a lower bracket then, which is the case "
                "traditional is built for: take the deduction at today's higher rate.")
    if user.expects_lower_bracket_in_retirement is False:
        return ("and you've said you don't expect a lower bracket then, which is the case "
                "Roth is built for: pay the tax at today's rate and never again.")
    if later is None:
        return ("add what you spend a month and we can estimate both rates; until then, "
                "both are open options.")
    later_r = later["marginal_rate"]
    if c["estimated_verdict"] == "traditional":
        return (f"and on your numbers it is: about {now_r:.0%} on your next dollar today "
                f"against {later_r:.0%} in retirement, so traditional's deduction is worth more.")
    if now_r == later_r:
        return (f"and on your numbers it's a tie at {now_r:.0%}, which leans Roth: no required "
                f"withdrawals, and tax-free money to draw on in a high-income year.")
    return (f"and on your numbers it isn't: about {now_r:.0%} on your next dollar today "
            f"against {later_r:.0%} in retirement, so paying the tax now with Roth is cheaper.")


# --- Rule 6: remaining 401(k) --------------------------------------------------


def rule_remaining_401k(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    plans = user.accounts_of(AccountType.TRADITIONAL_401K)
    if not plans:
        return [_item(
            "R6_REMAINING_401K",
            title="No 401(k) on file",
            detail="Nothing to fill here. Remaining dollars go to a taxable brokerage at step 7.",
            priority=Priority.INFO,
            account_type=AccountType.TRADITIONAL_401K,
        )]

    # The elective deferral limit is per person across all plans, not per account.
    limit = L.elective_401k_limit(user.age, year)
    used = sum(p.contributions_ytd for p in plans)
    room = max(0.0, limit - used)
    catch_up = L.catch_up_401k(user.age, year)
    threshold = L.load_limits(year)["401k"][
        "mandatory_roth_catchup_prior_year_wage_threshold"
    ]
    wages = next(
        (p.prior_year_wages_from_employer for p in plans
         if p.prior_year_wages_from_employer is not None), None
    )
    roth_required = L.catch_up_must_be_roth(user.age, wages, year)

    inputs = {
        "elective_deferral_limit": limit,
        "base_limit": L.load_limits(year)["401k"]["employee_deferral"],
        "catch_up_amount": catch_up,
        "contributions_ytd": used,
        "remaining_room": room,
        "catch_up_must_be_roth": roth_required,
        "prior_year_wages_from_employer": wages,
        "year": year,
    }

    if room <= 0:
        return [_item(
            "R6_REMAINING_401K",
            title=f"401(k) elective deferrals maxed for {year} ({_money(limit)})",
            detail=(
                "You've hit the employee contribution limit across your plans. Anything further "
                "goes to a taxable brokerage."
            ),
            priority=Priority.INFO,
            account_type=AccountType.TRADITIONAL_401K,
            inputs=inputs,
        )]

    detail = (
        f"Your {year} employee deferral limit is {_money(limit)}"
        + (f", including a {_money(catch_up)} age-{user.age} catch-up" if catch_up else "")
        + f", and you've contributed {_money(used)}. This space comes after the HSA and IRA "
        f"because those have either better tax treatment or a wider choice of low-cost funds, "
        f"but 401(k) space is still tax-advantaged and worth filling."
    )
    if roth_required:
        detail += (
            f" Note: because your prior-year wages from this employer were above "
            f"{_money(threshold)}, your catch-up portion must be made as Roth in {year}."
        )

    return [_item(
        "R6_REMAINING_401K",
        title=f"Contribute {_money(room)} more to your 401(k) (limit {_money(limit)})",
        detail=detail,
        amount=room,
        priority=Priority.MEDIUM,
        account_type=AccountType.TRADITIONAL_401K,
        inputs=inputs,
    )]


# --- Rule 7: taxable -----------------------------------------------------------


def rule_taxable(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    tax_advantaged_room = 0.0
    for fn in (rule_hsa, rule_ira, rule_remaining_401k):
        tax_advantaged_room += sum(i.amount or 0 for i in fn(user, year))

    inputs = {"remaining_tax_advantaged_room": tax_advantaged_room}
    ra = R.retirement_age(user)
    early_note = (
        f" Retiring at {ra} gives this account a second job: it's money you can reach "
        f"before 59½, which step 9 sizes for you."
        if ra < R.ages(year)["penalty_free_withdrawal"] else ""
    )

    if tax_advantaged_room > 0:
        return [_item(
            "R7_TAXABLE",
            title="Fill tax-advantaged space first",
            detail=(
                f"You still have about {_money(tax_advantaged_room)} of tax-advantaged room this "
                f"year. A taxable brokerage has no contribution limit and no early-withdrawal "
                f"rules, which is why it comes last — it's where money goes once the sheltered "
                f"accounts are full."
            ) + early_note,
            priority=Priority.LOW,
            account_type=AccountType.TAXABLE,
            inputs=inputs,
        )]

    return [_item(
        "R7_TAXABLE",
        title="Tax-advantaged space is full — invest additional savings in a taxable brokerage",
        detail=(
            "No contribution limit here. Broad index funds are tax-efficient in a taxable "
            "account because they distribute little in capital gains, and holding more than a "
            "year before selling gets long-term capital gains treatment."
        ) + early_note,
        priority=Priority.MEDIUM,
        account_type=AccountType.TAXABLE,
        inputs=inputs,
    )]


# --- Rule 8: the vehicle (Foundational Five #5) --------------------------------


def rule_vehicle(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    """Contributing and investing are two different actions. Cash sitting inside a
    retirement account is the most common unforced error in this whole list."""
    items = []
    investable = user.accounts_of(
        AccountType.TRADITIONAL_401K, AccountType.IRA,
        AccountType.HSA, AccountType.TAXABLE,
    )
    for account in investable:
        idle = account.uninvested_cash
        label = account.nickname or account.type.value
        if idle > 1 and account.holdings:
            items.append(_item(
                "R8_VEHICLE",
                title=f"{_money(idle)} is sitting uninvested in your {label}",
                detail=(
                    "Money that's been contributed but not invested is still just cash. Funding "
                    "the account and choosing what it holds are two separate actions — a broad "
                    "index fund or a target-date fund covers the second one in a single pick."
                ),
                amount=idle,
                priority=Priority.HIGH,
                account_type=account.type,
                inputs={
                    "balance": account.balance,
                    "invested": account.balance - idle,
                    "uninvested": idle,
                },
            ))
        elif idle > 1:
            items.append(_item(
                "R8_VEHICLE",
                title=f"No holdings recorded in your {label} ({_money(account.balance)})",
                detail=(
                    "We don't know what this account is invested in, so we can't tell whether "
                    "the balance is working or sitting in cash. Add the funds it holds."
                ),
                priority=Priority.MEDIUM,
                account_type=account.type,
                inputs={"balance": account.balance, "holdings": 0},
            ))

        for holding in account.holdings:
            if holding.expense_ratio is not None and holding.expense_ratio > 0.005:
                cost = holding.value * holding.expense_ratio
                items.append(_item(
                    "R8_VEHICLE",
                    title=f"{holding.symbol} charges {holding.expense_ratio:.2%} — about {_money(cost)} a year",
                    detail=(
                        "The expense ratio is the annual fee a fund takes off the top whatever "
                        "the market does. Broad index funds commonly run 0.03%–0.10%; anything "
                        "above 0.50% has to justify itself, and most funds at that price don't."
                    ),
                    amount=cost,
                    priority=Priority.MEDIUM,
                    account_type=account.type,
                    inputs={
                        "symbol": holding.symbol,
                        "expense_ratio": holding.expense_ratio,
                        "value": holding.value,
                        "annual_cost": cost,
                        "index_fund_reference_range": [0.0003, 0.001],
                    },
                ))

    if not items:
        items.append(_item(
            "R8_VEHICLE",
            title="Everything contributed is invested",
            detail=(
                "No idle cash and no expensive funds found in your investment accounts. The "
                "account is the container; the fund inside it is what actually grows."
            ),
            priority=Priority.INFO,
        ))
    return items


# --- Rule 9: retirement age ----------------------------------------------------


def _years(n: float) -> str:
    return "year" if n == 1 else "years"


def rule_retirement_age(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    """Steps 1-8 decide which account each dollar goes to. This checks those accounts
    are reachable, and the gaps around them covered, at the age the user picked —
    retiring at 50 and working to 76 raise completely different problems."""
    data = R.ages(year)
    ra = R.retirement_age(user)
    rmd = R.rmd_age(user, year)
    items: list[ActionItem] = []

    bridge = R.bridge(user, year)
    if bridge["applies"]:
        items.append(_bridge_item(bridge))

    uncovered = R.medicare_gap_years(user, year)
    if uncovered > 0:
        hsa_note = (
            " An invested HSA helps here: it pays medical costs tax-free at any age, and "
            "COBRA premiums count as a qualified expense."
            if user.accounts_of(AccountType.HSA) else ""
        )
        items.append(_item(
            "R9_RETIREMENT_AGE",
            title=f"Plan for {uncovered} {_years(uncovered)} of health coverage before Medicare",
            detail=(
                f"Workplace health insurance usually ends with the job, and Medicare doesn't "
                f"start until {data['medicare']}. Retiring at {ra} leaves {uncovered} "
                f"{_years(uncovered)} to cover — through COBRA (usually up to 18 months), a "
                f"spouse's plan, or the ACA marketplace, where premium subsidies depend on that "
                f"year's income. Early retirees can partly steer that income by choosing which "
                f"accounts to draw from." + hsa_note
            ),
            priority=Priority.MEDIUM,
            inputs={"retirement_age": ra, "medicare_age": data["medicare"],
                    "years_without_medicare": uncovered},
        ))

    if ra >= rmd:
        items.append(_item(
            "R9_RETIREMENT_AGE",
            title=f"Required withdrawals start at {rmd}, before you plan to stop working",
            detail=(
                f"From {rmd}, traditional 401(k)s and IRAs must pay out a minimum each year, "
                f"taxed as income — on top of your salary if you're still working. The 401(k) "
                f"at the job you're still at is exempt, as long as you don't own 5% or more of "
                f"the company. Roth IRAs have no required withdrawals during your lifetime, and "
                f"since 2024 neither do Roth 401(k)s, so leaning Roth keeps those years' tax "
                f"bill down."
            ),
            priority=Priority.LOW,
            inputs={"retirement_age": ra, "rmd_age": rmd, "birth_year": year - user.age},
        ))

    if ra > data["medicare"] and any(a.hdhp_enrolled for a in user.accounts_of(AccountType.HSA)):
        items.append(_item(
            "R9_RETIREMENT_AGE",
            title="Enrolling in Medicare ends HSA contributions",
            detail=(
                f"You plan to work past {data['medicare']} with an HSA. Once you enroll in any "
                f"part of Medicare you can't contribute any more, and Part A coverage can be "
                f"backdated up to six months — so stop contributing six months before you "
                f"enroll. If you keep employer health coverage you can usually delay Medicare "
                f"and keep contributing, but claiming Social Security enrolls you in Part A "
                f"automatically."
            ),
            priority=Priority.LOW,
            account_type=AccountType.HSA,
            inputs={"retirement_age": ra, "medicare_age": data["medicare"]},
        ))

    if not items:
        items.append(_item(
            "R9_RETIREMENT_AGE",
            title=f"Retiring at {ra} lines up with when your accounts open up",
            detail=(
                f"By {ra} you're past 59½, so 401(k) and IRA withdrawals carry no "
                f"early-withdrawal penalty, and Medicare has started. Required withdrawals "
                f"don't begin until {rmd}. Nothing about this age changes the order of the "
                f"steps above."
            ),
            priority=Priority.INFO,
            inputs={"retirement_age": ra, "penalty_free_age": data["penalty_free_withdrawal"],
                    "medicare_age": data["medicare"], "rmd_age": rmd},
        ))
    return items


def _bridge_item(b: dict) -> ActionItem:
    ra = b["retirement_age"]
    routes = []
    if b["rule_of_55_applies"]:
        routes.append(
            f"the Rule of 55 lets you draw penalty-free from the 401(k) at the job you leave "
            f"at {ra}, so that balance is counted here"
        )
    routes += [
        "Roth IRA contributions (not the growth) can come out any time",
        "a Roth conversion ladder moves traditional money into a Roth five years before "
        "you spend it",
        "72(t) payments open an IRA early if you commit to a fixed yearly withdrawal",
    ]
    context = (
        f"Retiring at {ra} leaves {b['bridge_years']:g} {_years(b['bridge_years'])} before "
        f"401(k) and IRA money comes out without the 10% early-withdrawal penalty. Those "
        f"years need money you can reach — mainly a taxable brokerage account, plus cash "
        f"beyond your emergency fund. On your numbers that's about "
        f"{_money(b['reachable_total'])} reachable against roughly "
        f"{_money(b['spending_to_cover'])} of spending, in today's money."
    )
    routes_text = " Other ways in before 59½: " + "; ".join(routes) + "."

    if b["gap"] <= 0:
        return _item(
            "R9_RETIREMENT_AGE",
            title="Your years before 59½ are covered",
            detail=context + routes_text,
            priority=Priority.INFO,
            account_type=AccountType.TAXABLE,
            inputs=b,
        )

    if b["annual_to_close_gap"] is None:
        return _item(
            "R9_RETIREMENT_AGE",
            title=f"You're about {_money(b['gap'])} short of money you can reach before 59½",
            detail=(
                context + " With no working years left to save it, the penalty-free routes "
                "are the plan." + routes_text
            ),
            priority=Priority.HIGH,
            account_type=AccountType.TAXABLE,
            inputs=b,
        )

    return _item(
        "R9_RETIREMENT_AGE",
        title=f"Save about {_money(b['annual_to_close_gap'])} a year you can reach before 59½",
        detail=(
            context + f" That's {_money(b['gap'])} short. This comes after the match, the "
            f"HSA and the IRA — they're still worth more — and ahead of extra 401(k) space, "
            f"which you couldn't touch in time." + routes_text + " The low-income years "
            f"between retiring and 59½ are also a cheap time to convert traditional money "
            f"to Roth."
        ),
        amount=b["annual_to_close_gap"],
        priority=Priority.HIGH,
        account_type=AccountType.TAXABLE,
        inputs=b,
    )


# --- what the plan invests each year -------------------------------------------


def annual_investing(user: User, year: int = L.DEFAULT_YEAR) -> dict:
    """What the plan has them investing each year once they're up and running, plus
    how long it takes to get there.

    Clearing a card and filling an emergency fund are one-off costs, not annual ones.
    Modelling them as permanent would say "you invest $0 a year forever", which is both
    wrong and the opposite of the point. So they become a delay of
    `years_until_investing`, then the full recurring amount after that. Lives here
    rather than in the projection because the readiness rule needs it too.
    """
    capacity = user.annual_savings_capacity
    if capacity is None:
        # No stated capacity: carry on at the current pace, which already includes any
        # match that's arriving — adding the match again would count it twice.
        current = R.current_annual_contributions(user)
        return {"own": current, "employer_match": 0.0, "total": current,
                "one_off_first": 0.0, "years_until_investing": 0.0}

    one_off = sum(
        item.amount or 0
        for rule in (rule_emergency_fund, rule_high_interest_debt)
        for item in rule(user, year)
        if item.priority is not Priority.INFO
    )

    # Employer match is real money landing alongside their own contributions.
    match = 0.0
    for account in user.accounts_of(AccountType.TRADITIONAL_401K):
        if account.employer_match_rate <= 0:
            continue
        deferral_for_full_match = user.income * account.employer_match_limit_pct
        match += min(capacity, deferral_for_full_match) * account.employer_match_rate

    return {
        "own": capacity,
        "employer_match": match,
        "total": capacity + match,
        "one_off_first": one_off,
        "years_until_investing": one_off / capacity if capacity else 0.0,
    }


# --- Rule 10: does it add up ---------------------------------------------------


def rule_readiness(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    """Steps 1-9 are how to save. This checks whether that saving pays for the
    retirement the user picked — and when it doesn't, puts a number on all three levers
    (save more, retire later, spend less) instead of choosing one for them."""
    investing = annual_investing(user, year)
    r = R.readiness(user, year, R.invested_balance(user), investing["total"],
                    investing["years_until_investing"])
    inputs = {k: v for k, v in r.items() if k != "status"}
    ra, plan_to = r["retirement_age"], r["plan_to_age"]

    if r["status"] == "no_spending_info":
        return [_item(
            "R10_READINESS",
            title="Tell us what you'll spend in retirement so we can check your plan",
            detail=(
                "A retirement age only means something next to a spending figure. Add your "
                "monthly expenses, or what you expect to spend once you stop working, and this "
                "step will show whether your plan pays for it — and what to change if it doesn't."
            ),
            priority=Priority.LOW,
            inputs=inputs,
        )]

    retired = r["years_to_retirement"] == 0
    have = (
        f"You have about {_money(r['projected_at_retirement'])} invested."
        if retired else
        f"Your plan reaches about {_money(r['projected_at_retirement'])} by {ra}, in "
        f"today's money."
    )
    ss = r["social_security_annual"]
    spending = f"{_money(r['retirement_spending_annual'])} a year" + (
        f", less {_money(ss)} of Social Security from {r['social_security_claim_age']},"
        if ss else ""
    )
    need = f" Spending {spending} until {plan_to} takes about {_money(r['needed_at_retirement'])}."
    ss_note = (
        "" if r["social_security_provided"] else
        " No Social Security is counted, because we don't have your estimate — adding it "
        "from ssa.gov will almost certainly improve this."
    )
    earliest = r["earliest_retirement_age"]
    sustainable = _money(r["sustainable_monthly_spending"])

    if r["status"] == "on_track":
        sooner = (
            f" On the same assumptions, the earliest age this plan supports is {earliest}."
            if earliest is not None and earliest < ra and not retired else ""
        )
        return [_item(
            "R10_READINESS",
            title=(f"Your money is on track to last to {plan_to}" if retired
                   else f"On track to retire at {ra}"),
            detail=(
                have + need + sooner + ss_note + " Returns are a guess, so try a lower one on "
                "the projection page to see how much room you have."
            ),
            priority=Priority.INFO,
            inputs=inputs,
        )]

    ratio = r["funded_ratio"]
    lasts = r["money_lasts_to_age"]
    runs_out = f" At that pace the money runs out around {lasts}." if lasts else ""

    if retired:
        return [_item(
            "R10_READINESS",
            title=(f"At this spending, your money lasts to about {lasts}" if lasts
                   else f"Your money covers {ratio:.0%} of your spending to {plan_to}"),
            detail=(
                have + need + runs_out + f" With no working years left, the levers are "
                f"spending — up to {sustainable} a month lasts to {plan_to} — delaying Social "
                f"Security, which raises the benefit about 8% for each year past full "
                f"retirement age, or part-time income in the early years." + ss_note
            ),
            priority=Priority.HIGH,
            inputs=inputs,
        )]

    extra = r["extra_savings_per_year"]
    levers = [
        f"save about {_money(extra)} more a year",
        f"retire at {earliest} on the savings you have planned" if earliest is not None
        else "retire later — though no age before 80 closes it on current savings alone",
        f"spend up to {sustainable} a month in retirement",
    ]
    title = f"Save about {_money(extra)} more a year to retire at {ra}"
    if earliest is not None:
        title += f", or plan for {earliest}"
    return [_item(
        "R10_READINESS",
        title=title,
        detail=(
            have + need + f" That's {ratio:.0%} of the way there.{runs_out} Any one of these "
            f"closes the gap: " + "; ".join(levers) + ". None is the right answer on its own "
            "— they're trade-offs, and you can try each on the projection page." + ss_note
        ),
        amount=extra,
        priority=Priority.HIGH if ratio < 0.75 else Priority.MEDIUM,
        inputs=inputs,
    )]


# --- engine --------------------------------------------------------------------

RULE_FUNCTIONS = [
    rule_emergency_fund,
    rule_employer_match,
    rule_high_interest_debt,
    rule_hsa,
    rule_ira,
    rule_remaining_401k,
    rule_taxable,
    rule_vehicle,
    rule_retirement_age,
    rule_readiness,
]

_PRIORITY_ORDER = {
    Priority.BLOCKING: 0, Priority.HIGH: 1, Priority.MEDIUM: 2,
    Priority.LOW: 3, Priority.INFO: 4,
}


def evaluate(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    """Run every rule in waterfall order. Actionable items come first (ordered by
    waterfall step), informational ones after."""
    items: list[ActionItem] = []
    for fn in RULE_FUNCTIONS:
        items.extend(fn(user, year))
    items.sort(key=lambda i: (i.priority is Priority.INFO, i.step, _PRIORITY_ORDER[i.priority]))
    return items


def prioritized(user: User, year: int = L.DEFAULT_YEAR) -> list[ActionItem]:
    """Actionable items only, ordered by urgency then waterfall step.

    `evaluate` returns waterfall order, which is what the explainer wants. A to-do
    list wants this: a BLOCKING item shouldn't sit behind two lower-urgency ones just
    because its rule is numbered later. Both the allocator and the Q&A layer read
    "what should I do next" from here, so there is one answer to that question.
    """
    return sorted(
        (i for i in evaluate(user, year) if i.priority is not Priority.INFO),
        key=lambda i: (_PRIORITY_ORDER[i.priority], i.step),
    )


def allocate(user: User, year: int = L.DEFAULT_YEAR) -> dict:
    """If the user told us what they can save this year, walk that money down the
    waterfall and show where each dollar lands."""
    # Funding order is by urgency first, then waterfall step. That matters in one
    # place: an emergency fund that's already past the three-month floor is a
    # top-up, and the rule text says to fill it alongside the steps below rather
    # than ahead of a guaranteed employer match.
    items = prioritized(user, year)
    capacity = user.annual_savings_capacity
    plan = []
    remaining = capacity if capacity is not None else 0.0

    for item in items:
        if not item.amount:
            continue
        if item.rule_id == "R8_VEHICLE":
            continue  # reallocating existing dollars, not new savings
        if item.rule_id == "R10_READINESS":
            continue  # saving *more* than this year's capacity, not a slot to fill from it
        funded = min(remaining, item.amount) if capacity is not None else None
        if capacity is not None:
            remaining -= funded
        plan.append({
            "rule_id": item.rule_id,
            "step": item.step,
            "title": item.title,
            "needed": item.amount,
            "funded": funded,
            "fully_funded": None if funded is None else funded >= item.amount - 0.01,
        })

    return {
        "annual_savings_capacity": capacity,
        "allocated": None if capacity is None else capacity - remaining,
        "unallocated": None if capacity is None else remaining,
        "steps": plan,
    }
