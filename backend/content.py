"""Layer 1/2/3 content for the Foundational Five.

The layered disclosure pattern from the scope doc:
  Layer 1 — Decision: one line, and it uses the user's own numbers where we have them.
  Layer 2 — Why: plain-English mechanics, one paragraph, written from the learning log.
  Layer 3 — Full detail: exact numbers, edge cases, comparisons.

Everything here is explanatory, not directive. We describe how the accounts work and
what the well-established prioritization is; we don't tell anyone what to buy.
"""

from __future__ import annotations

import limits as L
from models import AccountType, User

DISCLAIMER = (
    "Educational information, not investment, tax, or legal advice. Rules described are "
    "general federal rules for the tax year shown; your plan documents and your state may "
    "differ. Nothing here is a recommendation to buy or sell any specific security."
)

# --- Layer 2 / Layer 3 content -------------------------------------------------
# Layer 2 bodies are written from the learning log at the bottom of this file — same
# voice, tightened. Change the log first, then the copy.

CONTENT: dict[str, dict] = {
    "401k": {
        "name": "401(k)",
        "account_type": AccountType.TRADITIONAL_401K,
        "tagline": "Workplace retirement account, with the one guaranteed return you'll ever get.",
        "layer2": (
            "A 401(k) is a retirement account your employer sets up, funded straight out of "
            "your paycheck before it reaches you. You choose a percentage of pay; payroll "
            "moves it. Two things make it distinct from any account you could open yourself. "
            "First, the employer match — many employers add money when you contribute, which "
            "is an immediate return no investment can promise. Second, the size of the "
            "allowance: you can put far more into a 401(k) each year than an IRA. The tradeoff "
            "is that you're limited to the fund menu your plan offers, and the money is meant "
            "to stay put until 59½ — taking it out early generally costs income tax plus a 10% "
            "penalty. Traditional contributions skip tax now and get taxed on withdrawal; Roth "
            "contributions are taxed now and come out untaxed later."
        ),
        "layer3": [
            "Employee deferral limit is per person, not per plan — two jobs in one year still "
            "share one limit, and over-contributing means filing to pull the excess back out.",
            "The match is separate from your own limit; employer money doesn't consume your "
            "deferral allowance.",
            "Matches often vest on a schedule — leaving before you're vested can forfeit "
            "unvested employer money. Your own contributions are always yours.",
            "New for 2026: if your prior-year wages from that employer were above $150,000, "
            "catch-up contributions must be made as Roth.",
            "Ages 60–63 get a larger catch-up than 50–59; it drops back down at 64.",
            "Rolling an old 401(k) into a traditional IRA is easy, but a pre-tax IRA balance "
            "complicates a later backdoor Roth because of the pro-rata rule.",
        ],
    },
    "ira": {
        "name": "IRA / Roth IRA",
        "account_type": AccountType.IRA,
        "tagline": "The retirement account you open yourself — smaller allowance, better menu.",
        "layer2": (
            "An IRA is a retirement account you open at a brokerage on your own, with no "
            "employer involved. The yearly allowance is much smaller than a 401(k)'s, but you "
            "can hold nearly anything in it, including the cheapest index funds available, "
            "which is why it usually gets filled before the rest of your 401(k) space. The "
            "choice inside it is Roth or traditional. Roth means you contribute money you've "
            "already paid tax on and never pay tax on it again — not on the growth, not on the "
            "withdrawal. Traditional means you may deduct the contribution now and pay ordinary "
            "income tax when you withdraw. The whole decision reduces to one question: is your "
            "tax rate higher today or in retirement? High earners get pushed out of Roth by an "
            "income phase-out, which is why the 'backdoor' route exists."
        ),
        "layer3": [
            "The annual limit is combined across all your traditional and Roth IRAs, not per "
            "account.",
            "You can contribute for a tax year up until that year's filing deadline, roughly "
            "April 15 of the following year.",
            "Roth contributions (not earnings) can be withdrawn any time, tax and penalty free — "
            "the Roth IRA doubles as a deep backstop.",
            "Traditional IRA deductibility phases out separately if you're covered by a "
            "workplace plan; the contribution is still allowed, just possibly non-deductible.",
            "Backdoor Roth: contribute non-deductible money to a traditional IRA, then convert "
            "it. The pro-rata rule aggregates all your traditional IRA balances, so an existing "
            "pre-tax balance makes the conversion partly taxable.",
            "You need earned income to contribute; a non-working spouse can contribute through "
            "a spousal IRA on a working spouse's income.",
        ],
    },
    "hsa": {
        "name": "HSA",
        "account_type": AccountType.HSA,
        "tagline": "The only account that's untaxed on the way in, while growing, and on the way out.",
        "layer2": (
            "An HSA is attached to a high-deductible health plan, and it is the only account in "
            "the tax code that's untaxed three times over: the contribution is deductible, the "
            "growth is untaxed, and withdrawals for qualified medical expenses are untaxed too. "
            "Every other account gives you two of those at most. Most people treat it as a "
            "spending account for this year's copays, which wastes the best part of it. Used as "
            "a retirement account instead — invested, not left in cash, with current medical "
            "bills paid out of pocket — it's the most tax-efficient dollar you can save. There's "
            "no deadline on reimbursing yourself, so a receipt you keep from today can be "
            "reimbursed tax-free decades from now. After 65, non-medical withdrawals are simply "
            "taxed as income, which makes the worst case no worse than a traditional 401(k)."
        ),
        "layer3": [
            "Requires HDHP enrollment. Enrolling mid-year prorates your limit by month, though "
            "the last-month rule can let you contribute the full amount if you stay enrolled "
            "through the following year.",
            "Contributions made through payroll also skip FICA — an extra ~7.65% saving that a "
            "direct contribution doesn't get.",
            "Medicare enrollment ends HSA eligibility; contributing after that triggers "
            "penalties, and Part A can apply retroactively for up to six months.",
            "Non-medical withdrawals before 65 are taxed and hit with a 20% penalty.",
            "The account is yours, not your employer's — it follows you between jobs, unlike an FSA.",
            "Most custodians keep contributions in cash by default. It has to be invested "
            "manually, and often only above a cash threshold the custodian sets.",
            "California and New Jersey don't recognize HSAs for state income tax purposes.",
        ],
    },
    "taxable": {
        "name": "Taxable brokerage",
        "account_type": AccountType.TAXABLE,
        "tagline": "No limits, no rules, no tax shelter — where money goes once the sheltered accounts are full.",
        "layer2": (
            "A taxable brokerage account is a plain investment account. Nothing is deductible, "
            "dividends and realized gains are taxed each year, and there is no penalty structure "
            "because there's nothing to shelter. That's exactly what makes it useful in two "
            "places: after the tax-advantaged accounts are full, and for goals before 59½, "
            "since the money is available any time without a penalty. Two rules do most of the "
            "work in keeping the tax bill low. Hold more than a year and gains get the "
            "long-term capital gains rate instead of your income rate. And what you hold "
            "matters: broad index funds generate very little in annual distributions, so a "
            "buy-and-hold position can go years generating almost no taxable events."
        ),
        "layer3": [
            "Long-term (held >1 year) capital gains are taxed at 0/15/20% depending on income; "
            "short-term gains are taxed as ordinary income.",
            "Qualified dividends get the long-term rate; interest from bonds and cash is "
            "ordinary income.",
            "Tax-loss harvesting: realized losses offset gains, plus up to $3,000 of ordinary "
            "income a year, with the rest carrying forward. The wash-sale rule disallows the "
            "loss if you rebuy a substantially identical security within 30 days either side.",
            "Inherited taxable assets get a step-up in basis; inherited traditional retirement "
            "accounts do not.",
            "Municipal bond interest is federally tax-exempt, which mainly matters at high "
            "brackets.",
            "There's no contribution limit and no required minimum distribution, ever.",
        ],
    },
    "index_funds": {
        "name": "Index funds & target-date funds",
        "account_type": None,
        "tagline": "The account is the container. This is what actually goes inside it.",
        "layer2": (
            "Opening an account and investing are two different steps, and money that clears "
            "the first but not the second sits in cash for years. What goes inside is a fund: a "
            "single ticker holding hundreds or thousands of companies at once, so no individual "
            "company failing can take you with it. An index fund does this by tracking a set "
            "list — the S&P 500, or the entire US market — with no manager picking, which is why "
            "it costs almost nothing to own. That cost is the expense ratio, a percentage "
            "skimmed annually whatever the market does; broad index funds charge roughly 0.03%, "
            "actively managed funds ten to thirty times that, and the fee compounds against you "
            "exactly the way returns compound for you. A target-date fund goes one step further: "
            "pick the year you'll retire, and it holds a diversified mix and gradually shifts "
            "toward bonds as that date approaches, rebalancing on its own."
        ),
        "layer3": [
            "Expense ratio is charged on assets, not gains — a 1% fund charges 1% in a down "
            "year too. On a $100,000 balance, 0.03% is $30 a year and 0.75% is $750.",
            "Total-market and S&P 500 funds behave almost identically; the total-market version "
            "just adds mid- and small-caps.",
            "A three-fund portfolio — US total market, international, total bond — is the "
            "standard do-it-yourself version of what a target-date fund does automatically.",
            "Target-date funds are best used alone. Holding one alongside other funds undoes "
            "the allocation it's managing for you.",
            "In a taxable account, a target-date fund's automatic rebalancing generates taxable "
            "distributions; they're a cleaner fit inside retirement accounts.",
            "ETFs and mutual funds tracking the same index are largely interchangeable; ETFs "
            "trade intraday and are slightly more tax-efficient in taxable accounts.",
            "Your 401(k) menu may not carry a cheap index fund. Look for the lowest expense "
            "ratio broad-market option available in that plan, and use the IRA for the rest.",
        ],
    },
}


# --- Layer 1: the personalized one-liner ---------------------------------------


def layer1(key: str, user: User | None = None, year: int = L.DEFAULT_YEAR) -> str:
    """One line: what this account means for this user, using their numbers.

    Falls back to a generic statement when we don't have the user yet.
    """
    entry = CONTENT[key]
    if user is None:
        return entry["tagline"]

    if key == "401k":
        plans = user.accounts_of(AccountType.TRADITIONAL_401K)
        limit = L.elective_401k_limit(user.age, year)
        if not plans:
            return f"If you have a 401(k) at work, you can put up to ${limit:,} into it in {year}."
        used = sum(p.contributions_ytd for p in plans)
        matched = next((p for p in plans if p.employer_match_rate > 0), None)
        if matched:
            needed = user.income * matched.employer_match_limit_pct
            if used < needed:
                unclaimed = (needed - used) * matched.employer_match_rate
                return (
                    f"You're leaving about ${unclaimed:,.0f} of employer match unclaimed — "
                    f"contributing ${needed - used:,.0f} more this year captures all of it."
                )
        return (
            f"You've contributed ${used:,.0f} of your ${limit:,} {year} limit — "
            f"${max(0, limit - used):,.0f} of space left."
        )

    if key == "ira":
        limit = L.ira_limit(user.age, year, user.income)
        used = sum(a.contributions_ytd for a in user.accounts_of(AccountType.IRA))
        roth = L.roth_ira_eligibility(
            user.effective_magi, user.filing_status.value, user.age, year, user.income
        )
        if roth["status"] == "phased_out":
            return (
                f"Your income puts you past the Roth cutoff, so your ${limit:,} of {year} IRA "
                f"room has to come in through a backdoor conversion rather than directly."
            )
        if roth["status"] == "partial":
            return (
                f"You're mid-phase-out: ${roth['allowed']:,} of your ${limit:,} {year} IRA "
                f"limit can go straight into a Roth."
            )
        return (
            f"You can put ${max(0, limit - used):,.0f} more into an IRA for {year}, and at your "
            f"income all of it can be Roth."
        )

    if key == "hsa":
        hsas = [a for a in user.accounts_of(AccountType.HSA) if a.hdhp_enrolled]
        if not hsas:
            return (
                "You're not recorded as being on a high-deductible health plan, so the HSA "
                "isn't available to you this year."
            )
        hsa = hsas[0]
        limit = L.hsa_limit(hsa.hsa_coverage.value, user.age, year)
        room = max(0.0, limit - hsa.contributions_ytd)
        if room <= 0:
            return f"Your HSA is maxed for {year} at ${limit:,} — the best-treated dollars you have."
        return (
            f"You have ${room:,.0f} of HSA room left in {year}, and it's the only money you'll "
            f"save that's untaxed at all three stages."
        )

    if key == "taxable":
        sheltered = 0.0
        hsas = [a for a in user.accounts_of(AccountType.HSA) if a.hdhp_enrolled]
        for hsa in hsas:
            sheltered += max(0.0, L.hsa_limit(hsa.hsa_coverage.value, user.age, year)
                             - hsa.contributions_ytd)
        sheltered += max(0.0, L.ira_limit(user.age, year, user.income)
                         - sum(a.contributions_ytd for a in user.accounts_of(AccountType.IRA)))
        if user.accounts_of(AccountType.TRADITIONAL_401K):
            sheltered += max(0.0, L.elective_401k_limit(user.age, year)
                             - sum(p.contributions_ytd for p in
                                   user.accounts_of(AccountType.TRADITIONAL_401K)))
        if sheltered > 0:
            return (
                f"You still have about ${sheltered:,.0f} of tax-advantaged room this year, so "
                f"taxable investing isn't the next dollar for you yet."
            )
        return (
            "Your tax-advantaged space is full for the year — a taxable brokerage is where "
            "additional savings go from here."
        )

    if key == "index_funds":
        idle = sum(
            a.uninvested_cash for a in user.accounts_of(
                AccountType.TRADITIONAL_401K, AccountType.IRA,
                AccountType.HSA, AccountType.TAXABLE)
        )
        if idle > 1:
            return (
                f"About ${idle:,.0f} across your investment accounts is sitting in cash rather "
                f"than invested in anything."
            )
        return "Everything you've contributed is invested, which is the part most people miss."

    return entry["tagline"]


def account_page(key: str, user: User | None = None, year: int = L.DEFAULT_YEAR) -> dict:
    """The full layered-disclosure payload for one account page."""
    entry = CONTENT[key]
    at = entry["account_type"]
    return {
        "key": key,
        "name": entry["name"],
        "account_type": at.value if at else None,
        "layer1": {"decision": layer1(key, user, year)},
        "layer2": {"why": entry["layer2"]},
        "layer3": {
            "details": entry["layer3"],
            "numbers": key_numbers(key, user, year),
        },
        "learning_log": LEARNING_LOGS.get(key),
        "disclaimer": DISCLAIMER,
    }


def key_numbers(key: str, user: User | None = None, year: int = L.DEFAULT_YEAR) -> dict:
    """Layer 3's hard numbers — the seed table, plus the user's position against it."""
    data = L.load_limits(year)
    age = user.age if user else None

    if key == "401k":
        numbers = {
            "year": year,
            "base_employee_deferral": data["401k"]["employee_deferral"],
            "catch_up_tiers": data["401k"]["catch_up_tiers"],
            "mandatory_roth_catchup_wage_threshold":
                data["401k"]["mandatory_roth_catchup_prior_year_wage_threshold"],
        }
        if age is not None:
            numbers["your_limit"] = L.elective_401k_limit(age, year)
            numbers["your_catch_up"] = L.catch_up_401k(age, year)
        return numbers

    if key == "ira":
        numbers = {
            "year": year,
            "combined_limit": data["ira"]["combined_limit"],
            "catch_up_tiers": data["ira"]["catch_up_tiers"],
            "roth_magi_phaseout": data["ira"]["roth_magi_phaseout"],
        }
        if user is not None:
            numbers["your_limit"] = L.ira_limit(user.age, year, user.income)
            numbers["your_roth_eligibility"] = L.roth_ira_eligibility(
                user.effective_magi, user.filing_status.value, user.age, year, user.income
            )
        return numbers

    if key == "hsa":
        numbers = {
            "year": year,
            "self_only": data["hsa"]["self_only"],
            "family": data["hsa"]["family"],
            "catch_up_tiers": data["hsa"]["catch_up_tiers"],
        }
        if age is not None:
            numbers["your_self_only_limit"] = L.hsa_limit("self_only", age, year)
            numbers["your_family_limit"] = L.hsa_limit("family", age, year)
        return numbers

    if key == "taxable":
        return {
            "contribution_limit": None,
            "long_term_capital_gains_rates": [0.0, 0.15, 0.20],
            "long_term_holding_period_days": 366,
            "wash_sale_window_days": 30,
            "capital_loss_ordinary_income_offset": 3000,
        }

    if key == "index_funds":
        return {
            "typical_broad_index_expense_ratio": [0.0003, 0.001],
            "typical_target_date_expense_ratio": [0.0008, 0.0015],
            "expensive_threshold": 0.005,
            "cost_per_100k_at_0_03_pct": 30,
            "cost_per_100k_at_0_75_pct": 750,
        }

    return {}


def waterfall_explainer(year: int = L.DEFAULT_YEAR) -> dict:
    """Why the order is the order — shown next to the action list."""
    return {
        "year": year,
        "steps": [
            {"step": 1, "rule_id": "R1_EMERGENCY_FUND", "title": "Emergency fund first",
             "why": "Investing without a cash cushion means selling at a bad moment or taking on "
                    "credit card debt the first time something breaks."},
            {"step": 2, "rule_id": "R2_EMPLOYER_MATCH", "title": "Full employer match",
             "why": "A match is an immediate, guaranteed return on the money — nothing else in "
                    "this list can promise that."},
            {"step": 3, "rule_id": "R3_HIGH_INTEREST_DEBT", "title": "High-interest debt",
             "why": "Paying off a 20% debt is a guaranteed 20% return. No portfolio reliably "
                    "beats that."},
            {"step": 4, "rule_id": "R4_HSA", "title": "Max the HSA",
             "why": "Triple tax advantage — deductible in, untaxed growth, untaxed out for "
                    "medical. Strictly better tax treatment than any other account."},
            {"step": 5, "rule_id": "R5_IRA", "title": "Max the IRA",
             "why": "Same tax shelter as a 401(k), but you pick the funds, so the fees can be "
                    "far lower than a typical plan menu."},
            {"step": 6, "rule_id": "R6_REMAINING_401K", "title": "Remaining 401(k) space",
             "why": "Still tax-advantaged and a large allowance; it just comes after the "
                    "accounts with better treatment or cheaper funds."},
            {"step": 7, "rule_id": "R7_TAXABLE", "title": "Taxable brokerage",
             "why": "No shelter, but no limits and no penalties — the overflow, and the account "
                    "for goals before 59½."},
            {"step": 8, "rule_id": "R8_VEHICLE", "title": "Actually invest it",
             "why": "A funded account holding cash isn't investing. This runs alongside every "
                    "step above, not after them."},
            {"step": 9, "rule_id": "R9_RETIREMENT_AGE", "title": "Match your accounts to your retirement age",
             "why": "Retiring before 59½ needs money you can reach without a penalty; before 65, "
                    "health coverage; working past 73, a plan for required withdrawals. The "
                    "order above holds — this makes it work at your age."},
            {"step": 10, "rule_id": "R10_READINESS", "title": "Check it adds up",
             "why": "The steps are how to save. This checks whether it pays for the retirement "
                    "you picked, and if not, what saving more, retiring later or spending less "
                    "would each take."},
        ],
        "disclaimer": DISCLAIMER,
    }


# --- Learning logs -------------------------------------------------------------
# Ethan's own-words explanation per account type — written before the feature is built,
# and the source content the Layer 2 copy above is derived from. Rewriting a log is the
# right way to change the app's explanation of that account.

LEARNING_LOGS: dict[str, dict] = {
    "401k": {
        "account_type": "401k",
        "summary": "Payroll-funded retirement account whose real feature is the match.",
        "body": (
            "The thing that took me longest to see is that a 401(k) isn't an investment — it's "
            "a wrapper. You pick a percentage of pay, payroll diverts it, and then you still "
            "have to choose what it buys inside. Two people with identical 401(k)s can have "
            "wildly different outcomes because one picked a target-date fund and one left it in "
            "the default cash option.\n\n"
            "The match is the part that's genuinely unusual. If the employer matches 50% up to "
            "6% of pay, then on $100k you put in $6,000 and they add $3,000. That's a 50% "
            "return, instantly, with no market risk. Nothing else in personal finance works "
            "like that, which is why it sits at the top of the waterfall above even paying off "
            "credit card debt.\n\n"
            "Traditional vs Roth inside the 401(k) is the same question as in an IRA: pay tax "
            "now or later. The catch is that the limit is per person, not per account — if you "
            "switch jobs mid-year, both plans draw on the same allowance and it's on you to "
            "track it."
        ),
    },
    "ira": {
        "account_type": "ira",
        "summary": "The account you open yourself; smaller limit, far better fund selection.",
        "body": (
            "An IRA is what you'd have if you built a 401(k) yourself with no employer. Smaller "
            "annual limit, no match, but you're not stuck with a plan menu — you can buy the "
            "cheapest total-market fund that exists. That fund-choice freedom is the actual "
            "reason it outranks the leftover 401(k) space in the waterfall.\n\n"
            "Roth vs traditional confused me until I stopped thinking about it as two accounts "
            "and started thinking about it as one question: is your tax rate higher now or in "
            "retirement? Early career, probably now is lower, so Roth. Peak earning years, "
            "probably later is lower, so traditional. Everything else is detail.\n\n"
            "The phase-out is where it gets awkward: above a certain income you can't contribute "
            "to a Roth directly at all. The workaround — put money in a traditional IRA, "
            "immediately convert it to Roth — is completely standard and openly acknowledged by "
            "the IRS. The trap is the pro-rata rule: if you already have pre-tax money in any "
            "traditional IRA, the conversion isn't clean and part of it gets taxed. That single "
            "rule is why rolling an old 401(k) into an IRA can quietly cost you later."
        ),
    },
    "hsa": {
        "account_type": "hsa",
        "summary": "The best account in the tax code, and most people use it as a debit card.",
        "body": (
            "Every other account gives you a tax break on the way in or on the way out. The HSA "
            "gives you both, plus untaxed growth in between. There is no other account like it, "
            "and it's the one people skip.\n\n"
            "The reason they skip it is that it's presented as a health spending account, so it "
            "gets used as one — money goes in, copays come out, balance stays near zero. The "
            "version that actually matters is: contribute the max, invest it like a retirement "
            "account, pay current medical bills out of pocket, and keep the receipts. There's no "
            "time limit on reimbursement, so a receipt from today can pull money out tax-free in "
            "thirty years.\n\n"
            "The downside risk is small. After 65 you can withdraw for anything and just pay "
            "income tax — so the worst case is that it behaves like a traditional 401(k). The "
            "real gotchas are practical: you need an HDHP to contribute, Medicare enrollment "
            "ends eligibility, and most custodians park everything in cash until you manually "
            "invest it. The last one is how people end up with a decade-old HSA that earned "
            "nothing."
        ),
    },
    "taxable": {
        "account_type": "taxable",
        "summary": "No shelter, no rules — the overflow account and the pre-59½ account.",
        "body": (
            "This is the account with no special treatment: no deduction, taxes on dividends "
            "each year, taxes on gains when you sell. Which is exactly why it's last in the "
            "waterfall — it only makes sense once the sheltered accounts are full.\n\n"
            "But 'last' isn't 'never', and the flexibility is a real feature. Retirement "
            "accounts are locked until 59½; a taxable account isn't. For anything between now "
            "and then — a house, a sabbatical, early retirement — this is the account.\n\n"
            "Two rules do most of the work. Hold longer than a year and gains get the long-term "
            "rate instead of your income rate, which is often a 10-17 point difference. And "
            "what you hold matters more here than anywhere else: index funds barely distribute "
            "anything, so a buy-and-hold position can go years generating almost no taxable "
            "events at all. An actively managed fund throws off capital gains distributions you "
            "get taxed on whether or not you sold anything."
        ),
    },
    "index_funds": {
        "account_type": None,
        "summary": "Accounts are containers; this is the thing that actually grows.",
        "body": (
            "The single biggest gap in how this gets explained: opening the account and "
            "investing the money are two separate actions. People do the first, feel finished, "
            "and find cash sitting there years later.\n\n"
            "An index fund is one ticker that holds the whole market — thousands of companies — "
            "so no single company can sink you, and nobody is being paid to pick. That last part "
            "is why it's cheap, and cheap is the whole argument. The expense ratio comes out "
            "every year regardless of performance: 0.03% on $100k is $30, 0.75% is $750, and "
            "over decades that gap compounds into real money. The decades of evidence that most "
            "active managers don't beat the index after fees is what makes paying more a bad "
            "trade rather than just an expensive one.\n\n"
            "A target-date fund is the one-decision version: pick the year you'll retire, and it "
            "holds a global mix and slowly shifts toward bonds as the date nears. It's not the "
            "cheapest option, but it's rebalanced for you, and it's strictly better than the "
            "cash the account defaults to. Use it alone, though — holding one plus three other "
            "funds quietly undoes the allocation it's managing."
        ),
    },
}


# --- Glossary ------------------------------------------------------------------
# Inline definitions for every term the UI can't avoid using. The audience for this
# app is specifically people who freeze at this vocabulary, so any term appearing in
# Layer 1 or an action title needs an entry here.

GLOSSARY: dict[str, dict] = {
    "401k": {
        "term": "401(k)",
        "short": "A retirement account your employer sets up, funded from your paycheck.",
        "more": "Named after the section of tax law that created it. Money goes in before it "
                "reaches your bank account, and many employers add money on top.",
    },
    "ira": {
        "term": "IRA",
        "short": "A retirement account you open yourself, at any brokerage.",
        "more": "Stands for Individual Retirement Arrangement. No employer needed. Smaller "
                "yearly limit than a 401(k), but you can hold whatever funds you want.",
    },
    "roth": {
        "term": "Roth",
        "short": "You pay tax on the money now, and never again.",
        "more": "The opposite of 'traditional'. Roth money is taxed on the way in, then grows "
                "and comes out completely untaxed. Better when your tax rate today is lower "
                "than it will be in retirement.",
    },
    "traditional": {
        "term": "Traditional",
        "short": "You skip the tax now and pay it when you withdraw.",
        "more": "The opposite of Roth. You may deduct the contribution from this year's taxes, "
                "and pay ordinary income tax on withdrawals in retirement.",
    },
    "hsa": {
        "term": "HSA",
        "short": "A health savings account that's untaxed three separate ways.",
        "more": "Health Savings Account. Requires a high-deductible health plan. Money goes in "
                "untaxed, grows untaxed, and comes out untaxed for medical costs — no other "
                "account does all three.",
    },
    "hdhp": {
        "term": "HDHP",
        "short": "A health plan with a high deductible — the kind that unlocks an HSA.",
        "more": "High-Deductible Health Plan. Lower monthly premium, higher out-of-pocket cost "
                "before coverage kicks in. It's the only way to be eligible for an HSA.",
    },
    "employer_match": {
        "term": "Employer match",
        "short": "Free money your employer adds when you contribute to your 401(k).",
        "more": "A common setup is '50% up to 6% of pay': contribute 6% of your salary and "
                "your employer adds half that again. Not contributing enough to get all of it "
                "is leaving pay on the table.",
    },
    "taxable_brokerage": {
        "term": "Taxable brokerage",
        "short": "A normal investment account with no special tax treatment.",
        "more": "No contribution limit and no penalty for taking money out — but you owe tax "
                "on dividends each year and on gains when you sell. It's where money goes "
                "after the tax-advantaged accounts are full.",
    },
    "index_fund": {
        "term": "Index fund",
        "short": "One investment that holds hundreds or thousands of companies at once.",
        "more": "Instead of picking stocks, it buys the whole list — like every company in the "
                "S&P 500. Nobody is paid to choose, so it costs almost nothing to own, and no "
                "single company failing can sink you.",
    },
    "target_date_fund": {
        "term": "Target-date fund",
        "short": "A one-pick fund that manages itself based on when you'll retire.",
        "more": "Pick the fund with a year near your retirement (like 2055). It holds a mix of "
                "investments and automatically gets more conservative as that year approaches.",
    },
    "expense_ratio": {
        "term": "Expense ratio",
        "short": "The yearly fee a fund charges, as a percentage of what you hold.",
        "more": "Taken automatically whether the market is up or down. On $100,000, a 0.03% "
                "fund costs $30 a year and a 0.75% fund costs $750. Over decades that gap "
                "compounds into real money.",
    },
    "contribution_limit": {
        "term": "Contribution limit",
        "short": "The most the IRS lets you put into an account in one year.",
        "more": "Set annually and different for each account type. Going over means paperwork "
                "to pull the excess back out, plus a penalty if you don't.",
    },
    "catch_up": {
        "term": "Catch-up contribution",
        "short": "Extra room to contribute once you're 50 or older.",
        "more": "On top of the normal limit, so people closer to retirement can save faster. "
                "The 401(k) version is even larger between ages 60 and 63.",
    },
    "magi": {
        "term": "MAGI",
        "short": "The income figure the IRS uses to decide what you're eligible for.",
        "more": "Modified Adjusted Gross Income. Usually close to your total income with a few "
                "deductions added back. It's what determines whether you can contribute to a "
                "Roth IRA directly.",
    },
    "phase_out": {
        "term": "Phase-out",
        "short": "An income range where an option gradually shrinks instead of stopping at once.",
        "more": "Below the range you get the full amount; above it you get nothing; inside it "
                "you get a partial amount that shrinks as income rises.",
    },
    "backdoor_roth": {
        "term": "Backdoor Roth",
        "short": "A standard, legal route into a Roth IRA when your income is too high.",
        "more": "Contribute to a traditional IRA — which has no income limit — then convert it "
                "to Roth. Watch out if you already hold pre-tax money in a traditional IRA; "
                "the 'pro-rata rule' makes part of the conversion taxable.",
    },
    "emergency_fund": {
        "term": "Emergency fund",
        "short": "Plain cash set aside for things that go wrong.",
        "more": "Three to six months of expenses, in a savings account, not invested. It's what "
                "stops a car repair from becoming credit card debt.",
    },
    "apr": {
        "term": "APR",
        "short": "The yearly interest rate you're charged on money you owe.",
        "more": "Annual Percentage Rate. A 22% APR card costs you 22 cents a year for every "
                "dollar of balance — which is why paying it off beats almost any investment.",
    },
    "vesting": {
        "term": "Vesting",
        "short": "How long you have to stay before employer contributions are really yours.",
        "more": "Your own contributions are always yours. Employer match money may take a few "
                "years to fully belong to you; leaving early can forfeit the unvested part.",
    },
    "capital_gains": {
        "term": "Capital gains",
        "short": "The profit when you sell an investment for more than you paid.",
        "more": "Held more than a year, it's taxed at a lower 'long-term' rate. Held less than "
                "a year, it's taxed as regular income, which is usually higher.",
    },
    "take_home": {
        "term": "Take-home pay",
        "short": "What actually lands in your bank account on payday.",
        "more": "Your salary after income tax, payroll taxes, health insurance and any "
                "401(k) contributions have already come out. It's the number a monthly "
                "plan has to fit inside.",
    },
    "payroll_deferral": {
        "term": "Payroll deferral",
        "short": "Money moved from your pay into your 401(k) before it reaches you.",
        "more": "You set it as a percentage of pay, not a dollar amount, and it only "
                "moves on payday. Raising it lowers your take-home pay by less than the "
                "amount contributed, because traditional contributions cut your tax bill.",
    },
    "age_59_half": {
        "term": "59½",
        "short": "The age retirement accounts open up without a penalty.",
        "more": "Take money out of a 401(k) or IRA before 59½ and you generally owe a 10% "
                "penalty on top of income tax. A few exceptions — the Rule of 55, 72(t) "
                "payments, Roth contributions — let early retirees reach some of it sooner.",
    },
    "rule_of_55": {
        "term": "Rule of 55",
        "short": "Leave a job at 55 or later, and that job's 401(k) opens up early.",
        "more": "Leave your employer in or after the year you turn 55 and withdrawals from "
                "that employer's 401(k) skip the 10% penalty. It doesn't cover IRAs or plans "
                "from earlier jobs — a reason not to roll that 401(k) into an IRA before you "
                "need it. Some public-safety workers qualify from 50.",
    },
    "roth_conversion_ladder": {
        "term": "Roth conversion ladder",
        "short": "Moving traditional money into a Roth, five years before you'll spend it.",
        "more": "Each conversion is taxed as income that year, then can come out of the Roth "
                "penalty-free after five years. Early retirees convert a slice every year, "
                "ideally in low-income years when the tax is small.",
    },
    "sepp_72t": {
        "term": "72(t) payments",
        "short": "A way to take IRA money before 59½ without the penalty, on a fixed schedule.",
        "more": "Substantially equal periodic payments: you commit to withdrawing a set amount "
                "every year for five years or until 59½, whichever is longer. Break the "
                "schedule and the penalty applies to everything you took.",
    },
    "rmd": {
        "term": "Required minimum distribution",
        "short": "The minimum you must withdraw from traditional accounts each year, from a set age.",
        "more": "73 if you were born 1951–1959, and 75 if you were born in 1960 or later. It's "
                "taxed as income. Roth IRAs don't have them during your lifetime, and since "
                "2024 Roth 401(k)s don't either.",
    },
    "medicare": {
        "term": "Medicare",
        "short": "Federal health insurance that starts at 65.",
        "more": "Retire before 65 and you need other coverage for the gap — COBRA, a spouse's "
                "plan, or the ACA marketplace. Enrolling in Medicare also ends your ability to "
                "contribute to an HSA.",
    },
    "social_security": {
        "term": "Social Security",
        "short": "A monthly benefit from the government, based on your work history.",
        "more": "You can claim from 62, but each year before full retirement age (67 for anyone "
                "born in 1960 or later) shrinks the check for life — by up to 30%. Each year "
                "you wait past it, up to 70, adds 8%. Your own estimate is at ssa.gov/myaccount.",
    },
    "todays_money": {
        "term": "Today's money",
        "short": "A future amount, shrunk by inflation so you can compare it with prices now.",
        "more": "At 2.5% inflation, $1 million in 40 years buys about what $372,000 buys "
                "today. Planning in today's money keeps big future numbers from looking better "
                "than they are.",
    },
    "savings_rate": {
        "term": "Savings rate",
        "short": "The share of your pay you invest, rather than the dollar amount.",
        "more": "It's the figure that travels: 15% means the same thing on any salary, and it "
                "rises with a raise by itself. It's also the single number that moves a "
                "retirement date most — far more than which funds you pick.",
    },
    "coast_number": {
        "term": "Coast number",
        "short": "The balance where you could stop contributing and still arrive on time.",
        "more": "Past that point, compounding alone carries you to the target. It doesn't mean "
                "you should stop — it means the hard part is behind you, and it usually "
                "arrives years before the target itself.",
    },
    "compounding": {
        "term": "Compounding",
        "short": "Growth earning growth — the reason early money counts more than later money.",
        "more": "A dollar invested at 25 has forty years to double and re-double; the same "
                "dollar at 45 has twenty. This is why waiting is expensive in a way that "
                "saving less for longer usually isn't.",
    },
}
