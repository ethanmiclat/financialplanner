"""General financial knowledge — the answers that are the same for everyone.

`qa.py` answers questions about *your* plan, from your numbers. This module answers the
other kind: "what is an expense ratio", "how do tax brackets actually work", "should I
wait for the market to drop". No `User` argument, because none of it depends on who's
asking — which is exactly why it lives apart from the personal layer.

Two things about how it's written:

- **It deepens the glossary rather than repeating it.** `content.GLOSSARY` is Layer 1:
  one line per term. Each entry here is Layer 2 — the mechanics, in a couple of
  paragraphs — and links back to the glossary term it extends, so the two can't drift.
- **It is reference material, not the learning log.** `content.LEARNING_LOGS` is
  Ethan's own-words study of the Foundational Five and stays untouched. This is the
  wider shelf next to it.

Every entry's `keywords` feed the matcher's alias map. That list is the difference
between a bot that understands "why are fund fees bad" and one that doesn't, so it's
the part worth being generous with.
"""

from __future__ import annotations

ENTRIES: dict[str, dict] = {

    # =========================================================================
    # Investing basics
    # =========================================================================

    "compound_interest": {
        "question": "How does compound interest actually work?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["compound interest", "compounding", "how does compounding work",
                     "interest on interest", "growth on growth", "why start early",
                     "snowball effect", "exponential growth", "why does time matter",
                     "rule of 72 compounding", "grows on itself"],
        "summary": "Growth earns growth — so the years matter more than the amount.",
        "detail": (
            "Put $1,000 somewhere that earns 7% and you have $1,070 after a year. The next "
            "year you earn 7% on $1,070, not $1,000 — $75 instead of $70. That five-dollar "
            "difference is compounding, and it's tiny at first and enormous later: the same "
            "$1,000 is about $2,000 after ten years, $4,000 after twenty, and $15,000 after "
            "forty. Nothing changed but time.\n\n"
            "The consequence people underrate is that early money is worth more than later "
            "money. A dollar invested at 25 has forty years to double and re-double; the same "
            "dollar at 45 has twenty. That's why a 20-year-old putting away $100 a month can "
            "end up ahead of a 40-year-old putting away $300 — and why the most expensive "
            "financial decision most people make is simply waiting."
        ),
        "facts": [{"label": "$1,000 at 7% after 10 years", "value": "about $2,000"},
                  {"label": "after 20 years", "value": "about $3,900"},
                  {"label": "after 40 years", "value": "about $15,000"}],
        "related": ["rule_of_72", "dollar_cost_averaging", "market_timing"],
        "glossary_terms": ["compounding"],
    },
    "rule_of_72": {
        "question": "What is the rule of 72?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["rule of 72", "how long to double", "doubling time", "double my money",
                     "years to double", "72 rule", "when will my money double"],
        "summary": "Divide 72 by the yearly return to get roughly how many years money takes to double.",
        "detail": (
            "At 7%, 72 ÷ 7 is about 10 — so money doubles roughly every ten years. At 10% it's "
            "about seven years; at 3% it's twenty-four. It's an approximation, but a good one, "
            "and it makes the case for starting early without a calculator: over a forty-year "
            "working life at 7%, money doubles four times, so $1 becomes about $16.\n\n"
            "It works in reverse for costs too. A 22% credit card doubles what you owe in "
            "about three and a half years if nothing is paid. And it's a quick way to feel the "
            "weight of fees: a fund charging 1% a year instead of 0.05% doesn't sound like much, "
            "but it turns a 7% return into 6%, and stretches every doubling from ten years to twelve."
        ),
        "related": ["compound_interest", "expense_ratios", "apr_vs_apy"],
        "glossary_terms": ["compounding"],
    },
    "index_funds_explained": {
        "question": "What is an index fund, and why does everyone recommend them?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["index fund", "what is an index fund", "why index funds", "passive fund",
                     "passive investing", "track the market", "s&p 500 fund", "total market fund",
                     "vti", "voo", "fxaix", "vtsax", "buy the whole market", "boglehead",
                     "three fund portfolio", "index investing"],
        "summary": "One fund that owns the whole market, for almost nothing — most people never need more.",
        "detail": (
            "An index is just a list of companies — the S&P 500 is the 500 largest in the US. An "
            "index fund buys every company on the list in proportion, so one purchase gives you a "
            "slice of all of them. Nobody is paid to pick, so the fund costs almost nothing to run, "
            "and no single company failing can take you with it.\n\n"
            "The reason it's the default recommendation is the evidence: over long periods, the "
            "great majority of professional fund managers fail to beat the index they're measured "
            "against, and the ones who do rarely keep doing it. Owning the average, cheaply, beats "
            "paying someone to try to beat it. A total-market fund goes one step wider than the "
            "S&P 500 and includes smaller companies too; the difference between the two is small."
        ),
        "facts": [{"label": "Typical index fund cost", "value": "0.03%–0.10% a year"},
                  {"label": "Typical actively managed fund", "value": "0.50%–1.00% a year"},
                  {"label": "Active managers beating the index over 15 years", "value": "roughly one in ten"}],
        "related": ["expense_ratios", "mutual_fund_vs_etf", "diversification", "target_date_funds"],
        "glossary_terms": ["index_fund"],
    },
    "mutual_fund_vs_etf": {
        "question": "What's the difference between a mutual fund and an ETF?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["mutual fund vs etf", "etf vs mutual fund", "what is an etf", "what is a mutual fund",
                     "exchange traded fund", "difference between etf and mutual fund", "should i buy etf or mutual fund",
                     "etf or index fund", "etfs"],
        "summary": "Two wrappers for the same thing — an ETF trades like a stock, a mutual fund settles once a day.",
        "detail": (
            "Both are baskets of investments you buy in one go, and both can be index funds. The "
            "difference is plumbing. A mutual fund is bought from the fund company at the end-of-day "
            "price, in dollar amounts — $100, exactly. An ETF trades on an exchange like a stock: you "
            "buy shares at whatever the price is that second, through any brokerage.\n\n"
            "In practice, for a long-term investor buying an index fund, it barely matters. ETFs are "
            "slightly more tax-efficient in a taxable account and can be bought at any brokerage; "
            "mutual funds are easier to automate in round dollar amounts and are what most 401(k) "
            "plans offer. Pick whichever your account makes easy and look at the expense ratio, not "
            "the wrapper."
        ),
        "related": ["index_funds_explained", "expense_ratios", "what_is_a_brokerage"],
        "glossary_terms": ["index_fund"],
    },
    "expense_ratios": {
        "question": "What is an expense ratio, and why does a fraction of a percent matter?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["expense ratio", "fund fee", "fund fees", "management fee", "how much do funds cost",
                     "why are fees bad", "what does a fund charge", "fund expenses", "cost of a fund",
                     "0.03%", "high fees", "low cost fund", "cheap fund", "fee drag", "fees matter",
                     "is 1% a lot", "load fee", "12b-1"],
        "summary": "The yearly slice a fund keeps — and over decades, a 1% fee can eat a quarter of your money.",
        "detail": (
            "An expense ratio is what the fund charges each year, as a share of what you hold, "
            "taken automatically whether the market goes up or down. 0.03% on $100,000 is $30 a "
            "year; 1% is $1,000. The number looks small, which is the problem.\n\n"
            "Fees compound in reverse. Money that went to the fee never earns the next year's "
            "growth, so the gap widens every year. Over thirty years, a 1% fee versus a 0.05% fee "
            "on the same investments leaves you with roughly a quarter less. It's the single "
            "biggest thing you control about your returns, and the only one you know in advance."
        ),
        "facts": [{"label": "0.03% on $100,000", "value": "$30 a year"},
                  {"label": "1.00% on $100,000", "value": "$1,000 a year"},
                  {"label": "Cost of 1% vs 0.05% over 30 years", "value": "roughly 25% of the final balance"}],
        "related": ["index_funds_explained", "rule_of_72", "target_date_funds"],
        "glossary_terms": ["expense_ratio"],
    },
    "target_date_funds": {
        "question": "What is a target-date fund, and is one enough?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["target date fund", "target-date fund", "target retirement fund", "2055 fund", "2060 fund",
                     "2065 fund", "lifecycle fund", "one fund", "is a target date fund good", "vanguard target retirement",
                     "set and forget", "glide path", "what year fund should i pick"],
        "summary": "A single fund that holds the whole mix and gets steadier as your retirement year nears.",
        "detail": (
            "Pick the fund with a year near when you'll retire — a 2060 fund for someone in their "
            "twenties — and it holds a global mix of stocks and bonds and slowly shifts toward bonds "
            "as that year approaches. That shift is called the glide path, and it's the part people "
            "otherwise forget to do themselves.\n\n"
            "For most people it's genuinely enough, and it's strictly better than the cash a new "
            "account defaults to. Two things to know: hold it alone, because adding other funds "
            "quietly undoes the mix it's managing; and check its expense ratio, since the cheapest "
            "ones cost about a tenth of a percent and some workplace plans offer much dearer versions."
        ),
        "related": ["asset_allocation", "index_funds_explained", "rebalancing"],
        "glossary_terms": ["target_date_fund"],
    },
    "diversification": {
        "question": "What does diversification mean, and how much is enough?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["diversification", "diversify", "diversified", "don't put all eggs in one basket",
                     "my company's stock", "my employer's stock", "own a lot of my company stock", "too much company stock",
                     "espp shares", "rsu concentration",
                     "spread out my investments", "too concentrated", "concentration risk", "single stock risk",
                     "how many stocks should i own", "company stock", "own too much of one company"],
        "summary": "Owning enough different things that no single one failing can hurt you.",
        "detail": (
            "Any one company can go to zero. A basket of thousands can't, because they don't all "
            "fail at once. That's the whole idea: you give up the chance of picking the one winner in "
            "exchange for never being wiped out by the one loser — and since nobody reliably picks "
            "the winner anyway, it's a trade you should take.\n\n"
            "A total-market index fund is diversified across companies by construction. The next "
            "layer is across countries, then across asset types like bonds. The most common way "
            "people are accidentally undiversified is holding a lot of their own employer's stock: "
            "your salary already depends on that company, so your savings shouldn't too."
        ),
        "related": ["index_funds_explained", "asset_allocation", "stocks_vs_bonds", "international_exposure"],
        "glossary_terms": ["index_fund"],
    },
    "asset_allocation": {
        "question": "What is asset allocation, and what mix should I hold?",
        "topic": "Investing basics", "level": "intermediate",
        "keywords": ["asset allocation", "stock bond mix", "what percentage in stocks", "how much in bonds",
                     "portfolio mix", "60/40", "80/20", "100 minus age", "110 minus age", "how aggressive should i be",
                     "allocation by age", "what should my portfolio look like"],
        "summary": "The split between stocks and bonds — it sets your risk more than any fund choice.",
        "detail": (
            "Stocks grow more over time but swing hard; bonds grow less but steady the ride. The "
            "share you hold in each is your asset allocation, and it explains most of how your "
            "portfolio behaves — far more than which specific funds you pick. A young investor with "
            "decades ahead can hold nearly all stocks and ride out the drops; someone five years "
            "from retirement can't afford a 40% fall the year before they need the money.\n\n"
            "The old rule of thumb — hold your age in bonds — is on the cautious side now that "
            "people live longer; \"110 minus your age in stocks\" is a common update. A target-date "
            "fund makes this decision for you and adjusts it as you go, which is the main reason "
            "to consider one."
        ),
        "facts": [{"label": "Age 25, \"110 minus age\"", "value": "85% stocks"},
                  {"label": "Age 55", "value": "55% stocks"},
                  {"label": "Worst calendar year for US stocks since 1950", "value": "about −37%"}],
        "related": ["stocks_vs_bonds", "target_date_funds", "risk_tolerance", "rebalancing"],
        "glossary_terms": ["target_date_fund"],
    },
    "stocks_vs_bonds": {
        "question": "What's the difference between stocks and bonds?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["stocks vs bonds", "what is a bond", "what is a stock", "what are bonds", "what are stocks",
                     "bonds explained", "equities", "fixed income", "shares", "difference between stocks and bonds",
                     "should i own bonds", "are bonds safe", "bond fund", "treasury bonds"],
        "summary": "A stock is a slice of ownership; a bond is a loan you've made — different risks, different jobs.",
        "detail": (
            "Buy a stock and you own a piece of a company: if it grows, your piece is worth more, "
            "and some companies pay you a share of profits as dividends. Buy a bond and you've lent "
            "money — to a government or a company — in exchange for regular interest and your money "
            "back at the end. The stock can go to zero or triple; the bond mostly just pays what it "
            "promised.\n\n"
            "Over long stretches stocks have returned roughly 7% a year after inflation and bonds "
            "roughly 2%, but stocks have also lost a third or more in a bad year while bonds barely "
            "moved. That's why they're held together: stocks for growth, bonds for the years you "
            "can't afford a bad one. You don't buy individual bonds any more than individual stocks "
            "— a bond index fund holds thousands."
        ),
        "related": ["asset_allocation", "diversification", "volatility_vs_risk", "dividends"],
        "glossary_terms": [],
    },
    "dollar_cost_averaging": {
        "question": "What is dollar-cost averaging, and should I invest all at once or gradually?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["dollar cost averaging", "dca", "invest a little at a time", "lump sum vs dca",
                     "all at once or over time", "invest gradually", "spread out my investment",
                     "should i invest it all at once", "average in", "buy every month"],
        "summary": "Investing a fixed amount on a schedule — which is what a paycheck plan does automatically.",
        "detail": (
            "Put $500 in every month regardless of price and you buy more shares when they're cheap "
            "and fewer when they're dear, without ever deciding when to buy. That's dollar-cost "
            "averaging, and if you invest from each paycheck you're already doing it. Its real value "
            "isn't a better price — it's that it removes the decision, which is where most people "
            "go wrong.\n\n"
            "If you have a lump sum, the arithmetic slightly favours investing it all at once, "
            "because the market rises more often than it falls, so waiting usually costs a little. "
            "But the difference is small, and spreading a windfall over six to twelve months is a "
            "reasonable price for not having to watch a big deposit drop the week after."
        ),
        "related": ["market_timing", "compound_interest", "volatility_vs_risk"],
        "glossary_terms": ["compounding"],
    },
    "market_timing": {
        "question": "Should I wait for the market to drop before investing?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["wait for the market to drop", "wait for a dip", "buy the dip", "is now a good time to invest",
                     "market is too high", "all time high", "should i wait to invest", "market timing",
                     "time the market", "is the market going to crash", "wait for a crash", "market seems expensive",
                     "should i get in now", "bad time to invest", "recession coming", "wait until things calm down"],
        "summary": "Time in the market beats timing the market — waiting for a dip usually costs more than the dip.",
        "detail": (
            "It feels prudent to wait for a fall before buying. The trouble is that the market "
            "spends most of its time at or near an all-time high, because it grows; waiting for a "
            "drop from here usually means buying later at a price that's still higher, after "
            "missing the gains in between. The best days tend to cluster right next to the worst "
            "ones, so anyone sitting out the scary weeks misses the recovery too.\n\n"
            "Nobody — not fund managers, not economists — has reliably called tops and bottoms. The "
            "approach that actually works is boring: invest on a schedule, keep investing through "
            "the drops, and don't look too often. A fall is just the same shares at a discount to "
            "someone who isn't selling."
        ),
        "facts": [{"label": "Share of days the S&P 500 has closed within 5% of a record", "value": "roughly one in three"},
                  {"label": "Missing the 10 best days in 20 years", "value": "cuts the return roughly in half"}],
        "related": ["dollar_cost_averaging", "bear_and_bull_markets", "volatility_vs_risk"],
        "glossary_terms": [],
    },
    "rebalancing": {
        "question": "What is rebalancing, and how often should I do it?",
        "topic": "Investing basics", "level": "intermediate",
        "keywords": ["rebalancing", "rebalance", "how often to rebalance", "portfolio drift", "my allocation drifted",
                     "sell high buy low automatically", "reset my mix", "back to target allocation"],
        "summary": "Nudging your mix back to target once growth has pushed it off — once a year is plenty.",
        "detail": (
            "Say you chose 80% stocks and 20% bonds. After a good year for stocks it might be "
            "85/15 without you doing anything. Rebalancing means selling a little of what grew and "
            "buying what didn't, to get back to 80/20 — which, conveniently, is selling high and "
            "buying low on autopilot.\n\n"
            "Once a year is enough; more often mostly generates taxes and effort. In a 401(k) or IRA "
            "there's no tax cost to selling, so just do it. In a taxable account, rebalance with new "
            "money instead — direct your contributions to whatever's under target — so you never "
            "have to sell. A target-date fund does all of this for you."
        ),
        "related": ["asset_allocation", "target_date_funds", "capital_gains_short_vs_long"],
        "glossary_terms": ["target_date_fund", "capital_gains"],
    },
    "dividends": {
        "question": "What are dividends, and are they a bonus?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["dividends", "what is a dividend", "dividend stocks", "dividend yield", "dividend investing",
                     "drip", "reinvest dividends", "are dividends good", "live off dividends", "passive income from stocks",
                     "high dividend", "are dividends a bonus", "dividend payout"],
        "summary": "A share of profits paid out to you — real, but not extra; the share price drops by the same amount.",
        "detail": (
            "Some companies pay part of their profit to shareholders every quarter. That's a dividend, "
            "and it's real cash. What it isn't is a bonus: on the day it's paid, the company is worth "
            "that much less, and the share price falls to match. You've moved money from one pocket to "
            "another, and in a taxable account you owe tax on it that year.\n\n"
            "That's why chasing high-dividend stocks isn't a strategy — a company paying out 8% is "
            "usually one that can't find anything better to do with the money. Broad index funds pay "
            "a modest dividend, around 1–2%, and the sensible setting is to reinvest it automatically "
            "so it compounds."
        ),
        "related": ["qualified_dividends", "index_funds_explained", "tax_drag"],
        "glossary_terms": ["capital_gains"],
    },
    "what_is_a_brokerage": {
        "question": "What is a brokerage, and which one should I use?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["what is a brokerage", "brokerage account", "which brokerage", "fidelity vs vanguard vs schwab",
                     "where do i open an account", "how do i start investing", "open an ira where", "robinhood",
                     "best brokerage", "how to buy an index fund", "where to invest"],
        "summary": "The company that holds your investment accounts — the big three are all fine, so just pick one.",
        "detail": (
            "A brokerage is where investment accounts live: it holds the money, executes your buys, "
            "and sends you the tax forms. You open an IRA or a taxable account at one the way you'd "
            "open a checking account at a bank. Your 401(k)'s brokerage is chosen by your employer; "
            "everything else is your choice.\n\n"
            "Fidelity, Vanguard and Schwab are the usual answers, and the differences between them "
            "are small: all three offer index funds costing a few hundredths of a percent, no account "
            "fees, and no commissions. What to avoid is anything that charges a percentage of your "
            "balance to \"manage\" it, and anything that makes trading feel like a game."
        ),
        "related": ["what_is_taxable_account", "index_funds_explained", "mutual_fund_vs_etf"],
        "glossary_terms": ["taxable_brokerage", "ira"],
    },
    "total_market_vs_sp500": {
        "question": "Total market or S&P 500 — does it matter?",
        "topic": "Investing basics", "level": "intermediate",
        "keywords": ["total market vs s&p 500", "vti vs voo", "vtsax vs vfiax", "s&p 500 or total market",
                     "small cap", "mid cap", "large cap", "does it matter which index", "which index fund",
                     "fxaix or fskax", "whole market"],
        "summary": "Barely — the S&P 500 is about 80% of the total market by weight, and they move together.",
        "detail": (
            "The S&P 500 holds the 500 largest US companies. A total-market fund holds those plus "
            "roughly 3,000 smaller ones. But size-weighting means the big 500 make up around four-fifths "
            "of the total-market fund anyway, so the two track each other closely — the long-run "
            "returns differ by fractions of a percent, and not consistently in one direction.\n\n"
            "If you have the choice, total market is marginally more diversified and there's no "
            "reason not to. If your 401(k) only offers an S&P 500 fund, it's not worth a second "
            "thought. What does matter is the expense ratio and that you actually own one of them "
            "rather than cash."
        ),
        "related": ["index_funds_explained", "international_exposure", "diversification"],
        "glossary_terms": ["index_fund"],
    },
    "international_exposure": {
        "question": "Should I own international stocks?",
        "topic": "Investing basics", "level": "intermediate",
        "keywords": ["international stocks", "international fund", "foreign stocks", "vxus", "vtiax", "ex-us",
                     "global diversification", "should i invest outside the us", "emerging markets",
                     "only us stocks", "home bias", "world fund", "vt"],
        "summary": "Reasonable to hold some — the US is about 60% of the world's market, not all of it.",
        "detail": (
            "American companies make up around three-fifths of the world's stock market by value. "
            "Holding only US stocks is a bet that the other two-fifths won't matter, and while that "
            "bet has paid off over the last fifteen years, it lost for the ten before that. Nobody "
            "knows which decade comes next.\n\n"
            "A common split is 60–80% US and 20–40% international, which is roughly what a target-date "
            "fund or a single world fund holds. It's a diversification decision, not a return "
            "prediction — you're not expecting international to win, you're declining to bet "
            "everything on one country. Reasonable people hold none; the mistake is holding none "
            "by accident."
        ),
        "related": ["diversification", "asset_allocation", "target_date_funds"],
        "glossary_terms": ["index_fund"],
    },
    "risk_tolerance": {
        "question": "How do I know my risk tolerance?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["risk tolerance", "how much risk", "am i too aggressive", "am i too conservative",
                     "how much risk should i take", "risk capacity", "can i handle a crash", "nervous about losing money",
                     "scared of the stock market", "what if i lose it all", "risk appetite"],
        "summary": "Less about your personality than your timeline — money you won't touch for 20 years can ride out anything.",
        "detail": (
            "Two things get bundled under this word. Risk *capacity* is how much loss your plan can "
            "absorb: money you need in three years can't afford a 30% drop, money you need in thirty "
            "can. Risk *tolerance* is how much of a drop you can watch without selling. The first is "
            "arithmetic; the second is the one that actually determines outcomes, because the people "
            "who lose in a crash are the ones who sell at the bottom.\n\n"
            "The honest test isn't a questionnaire. It's imagining your balance a third lower next "
            "March and asking whether you'd keep contributing. If yes, an all-stock portfolio suits a "
            "long horizon. If you'd panic, holding more bonds and earning a little less is a good "
            "trade — the best allocation is the one you'll stick with."
        ),
        "related": ["asset_allocation", "volatility_vs_risk", "bear_and_bull_markets"],
        "glossary_terms": [],
    },
    "volatility_vs_risk": {
        "question": "Is volatility the same thing as risk?",
        "topic": "Investing basics", "level": "intermediate",
        "keywords": ["volatility", "volatility vs risk", "market swings", "is the stock market risky", "ups and downs",
                     "market fluctuation", "how risky are stocks", "permanent loss", "temporary loss", "paper loss"],
        "summary": "No — volatility is the ride, risk is not having the money when you need it.",
        "detail": (
            "Stocks bounce around: a 10% fall happens most years and a 30% fall about once a decade. "
            "That's volatility, and for money you won't touch for twenty years it's noise — every one "
            "of those falls has been recovered. It only becomes a loss if you sell during it.\n\n"
            "Risk, properly, is the chance you don't have what you need when you need it. That "
            "includes market drops the year before retirement — but it also includes the quieter "
            "risk of holding cash for forty years and watching inflation eat it. A savings account "
            "has no volatility and a lot of that second kind of risk. Matching the investment to the "
            "timeline is how you manage both."
        ),
        "related": ["risk_tolerance", "asset_allocation", "inflation_explained"],
        "glossary_terms": [],
    },
    "bear_and_bull_markets": {
        "question": "What is a bear market, and what should I do in a crash?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["bear market", "bull market", "market crash", "what to do in a crash", "stock market crash",
                     "recession", "correction", "market is down", "market is falling", "should i sell",
                     "should i pull out", "the market dropped", "my portfolio is down", "stocks are tanking"],
        "summary": "A bear market is a 20% fall; they've all recovered, and the right move has always been to keep buying.",
        "detail": (
            "A correction is a 10% drop from a high; a bear market is 20% or more; a bull market is the "
            "long climb in between. Bears arrive every five or six years on average, last around a "
            "year, and have every time been followed by new highs — the 2008 crash, the 2020 crash, "
            "all of them. Bulls run longer and climb further than bears fall, which is why the long-run "
            "line goes up.\n\n"
            "The thing to do in a crash is almost nothing: keep contributing, don't check daily, and "
            "don't sell. A drop is the same funds at a discount. The people hurt by crashes are the "
            "ones who sold near the bottom and bought back near the top — which is exactly what fear "
            "tells you to do, and exactly why a plan you set in calm weather matters."
        ),
        "facts": [{"label": "Average bear market since 1950", "value": "about −33%, lasting roughly a year"},
                  {"label": "Average bull market", "value": "about +150%, lasting roughly five years"}],
        "related": ["market_timing", "volatility_vs_risk", "risk_tolerance"],
        "glossary_terms": [],
    },
    "fractional_shares": {
        "question": "What are fractional shares?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["fractional shares", "buy part of a share", "can't afford a whole share", "partial shares",
                     "invest $50", "small amounts", "share price too high", "invest with little money"],
        "summary": "A slice of a share, so you can invest $50 even when a share costs $500.",
        "detail": (
            "Most brokerages now let you buy investments in dollar amounts rather than whole shares — "
            "$50 of a fund whose shares cost $400 gets you an eighth of a share. Mutual funds have "
            "always worked this way; fractional shares extend it to ETFs and stocks.\n\n"
            "The practical upshot is that share price is irrelevant to whether you can start. A "
            "$500-a-share fund and a $50-a-share fund holding the same things are the same investment; "
            "one just comes in bigger pieces. Start with whatever you have."
        ),
        "related": ["what_is_a_brokerage", "mutual_fund_vs_etf", "dollar_cost_averaging"],
        "glossary_terms": [],
    },
    "ticker_symbols": {
        "question": "What is a ticker symbol?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["ticker", "ticker symbol", "what does vti mean", "fund codes", "what is voo", "what is vtsax",
                     "what is vti", "what does fxaix mean", "what is fxaix", "what is fskax",
                     "stock symbol", "how do i find a fund", "abbreviations for funds"],
        "summary": "The short code a fund or stock trades under — VTI, VOO, FXAIX — how you find it at a brokerage.",
        "detail": (
            "Every listed investment has a short code: AAPL is Apple, VTI is Vanguard's total-market "
            "ETF, FXAIX is Fidelity's S&P 500 index mutual fund. You type the ticker into your "
            "brokerage to buy it. The same index is sold under different tickers by different "
            "companies, and they're interchangeable — pick the cheapest your account offers.\n\n"
            "A few that come up constantly: VTI/VTSAX (Vanguard total US market, ETF/mutual fund), "
            "VOO/VFIAX (Vanguard S&P 500), FSKAX and FXAIX (Fidelity's equivalents), VXUS (Vanguard "
            "international), and the target-date families like VTTSX (Vanguard 2060) or FDKLX "
            "(Fidelity 2060)."
        ),
        "related": ["index_funds_explained", "total_market_vs_sp500", "what_is_a_brokerage"],
        "glossary_terms": ["index_fund"],
    },

    # =========================================================================
    # Retirement mechanics
    # =========================================================================

    "age_59_half_explained": {
        "question": "What happens at 59½, and what is the early withdrawal penalty?",
        "topic": "Retirement mechanics", "level": "basic",
        "keywords": ["59 1/2", "59.5", "59 and a half", "when can i withdraw", "early withdrawal", "early withdrawal penalty",
                     "10% penalty", "take money out of 401k early", "withdraw from ira early", "penalty free withdrawal",
                     "access retirement money early", "cash out my 401k", "hardship withdrawal"],
        "summary": "Retirement accounts open without penalty at 59½; before that it's income tax plus 10%, with a few exits.",
        "detail": (
            "The tax breaks on a 401(k) or IRA come with a string: the money is meant to stay until "
            "59½. Take it out earlier and you generally owe income tax on it plus a 10% penalty, "
            "which on a $10,000 withdrawal in a middle bracket means keeping only around $6,500.\n\n"
            "There are real exceptions. Roth IRA *contributions* — not the growth — can come out any "
            "time, tax- and penalty-free. The rule of 55 opens the 401(k) from the job you leave at "
            "55 or later. 72(t) payments let you take a fixed annual amount early. And a few hardship "
            "cases — a first home, certain medical costs, disability — skip the penalty. For an early "
            "retiree the cleaner answer is a taxable account for the years before 59½, which the plan "
            "sizes for you when you pick an early age."
        ),
        "related": ["rule_of_55_explained", "roth_withdrawal_ordering", "rollovers", "early_retirement_bridge"],
        "glossary_terms": ["age_59_half", "rule_of_55", "sepp_72t"],
    },
    "rule_of_55_explained": {
        "question": "How does the rule of 55 work?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["rule of 55", "retire at 55", "leave my job at 55", "separation from service", "401k at 55",
                     "penalty free at 55", "public safety 50"],
        "summary": "Leave a job in or after the year you turn 55, and that employer's 401(k) opens penalty-free.",
        "detail": (
            "Separate from an employer — quit, retire, get laid off — in the calendar year you turn 55 "
            "or later, and withdrawals from *that* employer's 401(k) skip the 10% early penalty. You "
            "still pay income tax. Public-safety workers get the same from 50.\n\n"
            "Two traps. It only covers the plan from the job you just left, not IRAs and not 401(k)s "
            "from earlier employers — so rolling that 401(k) into an IRA before you need it closes the "
            "door. And the plan itself has to allow partial withdrawals; some only permit a full "
            "distribution, which is a tax disaster. Check the plan document before you rely on it."
        ),
        "related": ["age_59_half_explained", "rollovers", "early_retirement_bridge"],
        "glossary_terms": ["rule_of_55", "age_59_half"],
    },
    "rmds_explained": {
        "question": "What are required minimum distributions?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["rmd", "required minimum distribution", "forced withdrawals", "have to take money out at 73",
                     "rmd age", "do roth iras have rmds", "minimum distribution", "what age do i have to withdraw"],
        "summary": "From 73 (or 75 if born 1960+), traditional accounts make you withdraw — and pay tax — each year.",
        "detail": (
            "The tax deferral on traditional money isn't forever. From age 73 — 75 for anyone born in "
            "1960 or later — the IRS requires a minimum withdrawal each year, worked out from your "
            "balance and life expectancy, and taxes it as income. Skip one and the penalty is steep. "
            "The first year's is about 4% of the balance and the share rises with age.\n\n"
            "Roth IRAs have no lifetime RMDs, and since 2024 neither do Roth 401(k)s — one of the "
            "stronger arguments for holding some Roth money. For someone with a large traditional "
            "balance, the years between retiring and 73 are the window to convert some of it to Roth "
            "at a low rate before the forced withdrawals push income up."
        ),
        "related": ["roth_conversions", "roth_vs_traditional_mechanics", "social_security_basics"],
        "glossary_terms": ["rmd", "roth"],
    },
    "rollovers": {
        "question": "What do I do with an old 401(k) when I leave a job?",
        "topic": "Retirement mechanics", "level": "basic",
        "keywords": ["rollover", "old 401k", "left my job", "what to do with 401k from old job", "roll over to ira",
                     "i left my job what happens to my 401k", "what happens to my 401k when i leave", "401k after leaving a job",
                     "should i roll over my 401k into an ira", "roll my 401k into an ira", "move my old 401k",
                     "roll into new 401k", "direct rollover", "60 day rollover", "cash out old 401k",
                     "changing jobs 401k", "forgot about a 401k", "orphan 401k"],
        "summary": "Roll it over — into the new 401(k) or an IRA — and never cash it out.",
        "detail": (
            "Your 401(k) is yours when you leave, but it's sitting in a plan you no longer have a "
            "relationship with. The options: leave it (fine if the funds are cheap), roll it into "
            "your new employer's plan, roll it into an IRA, or cash it out. The last one costs income "
            "tax plus a 10% penalty and is almost never right.\n\n"
            "Ask for a *direct* rollover, where the money goes plan-to-plan and never touches you; "
            "an indirect one withholds 20% for tax and gives you sixty days to make it whole. An IRA "
            "usually has better funds than a 401(k), but a traditional-IRA balance complicates a "
            "future backdoor Roth through the pro-rata rule, and loses the rule of 55 — reasons a "
            "high earner might prefer rolling into the new 401(k) instead."
        ),
        "related": ["rule_of_55_explained", "pro_rata_rule", "backdoor_roth_explained"],
        "glossary_terms": ["401k", "ira", "backdoor_roth"],
    },
    "vesting_explained": {
        "question": "How does vesting work?",
        "topic": "Retirement mechanics", "level": "basic",
        "keywords": ["vesting", "vested", "vesting schedule", "cliff vesting", "graded vesting", "unvested match",
                     "lose my match if i leave", "when is the match mine", "how long until vested", "forfeit"],
        "summary": "Your own contributions are always yours; employer money may take a few years to fully belong to you.",
        "detail": (
            "Everything you put into a 401(k) is yours from day one. Employer contributions — the "
            "match — may vest on a schedule: either a cliff, where nothing is yours until a date and "
            "then all of it is, or graded, where a fifth or a quarter becomes yours each year. Leave "
            "before you're fully vested and the unvested part is forfeited.\n\n"
            "It's designed to keep you in the job, and it's worth knowing the date before you resign: "
            "leaving a month before a cliff can cost thousands. The number is in your plan's summary "
            "document or the benefits portal. It never changes the advice to capture the match — "
            "even a partially vested match is free money — but it can change *when* you hand in notice."
        ),
        "related": ["employer_match_deep", "rollovers"],
        "glossary_terms": ["vesting", "employer_match"],
    },
    "social_security_basics": {
        "question": "How does Social Security work, and when should I claim it?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["social security", "when to claim social security", "claim at 62", "claim at 70", "full retirement age",
                     "will social security exist", "how much social security will i get", "ssa.gov", "social security estimate",
                     "delay social security", "social security running out", "fra"],
        "summary": "A monthly benefit from 62 to 70 — every year you wait adds roughly 8% for life.",
        "detail": (
            "Social Security pays a monthly benefit based on your 35 highest-earning years. You can "
            "claim any time from 62 to 70. Full retirement age is 67 for anyone born in 1960 or later; "
            "claiming at 62 cuts the check by about 30% permanently, and each year of waiting past 67 "
            "adds 8% until 70. That 8% is a guaranteed, inflation-adjusted increase no investment "
            "matches, which is why delaying is usually right if you can afford to.\n\n"
            "Your own estimate is at ssa.gov/myaccount, in today's dollars. The trust fund is "
            "projected to be able to pay around 80% of scheduled benefits from the mid-2030s if "
            "Congress does nothing — a cut, not a disappearance. The plan here counts Social "
            "Security as zero until you enter your estimate, which is deliberately cautious."
        ),
        "facts": [{"label": "Claim at 62", "value": "about 70% of the full benefit"},
                  {"label": "Claim at 67", "value": "100%"},
                  {"label": "Claim at 70", "value": "about 124%"}],
        "related": ["safe_withdrawal_rate", "rmds_explained", "medicare_gap"],
        "glossary_terms": ["social_security"],
    },
    "safe_withdrawal_rate": {
        "question": "What is the 4% rule, and how much do I need to retire?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["4% rule", "4 percent rule", "safe withdrawal rate", "how much do i need to retire", "25x expenses",
                     "retirement number", "how big a nest egg", "how much money to retire", "what's my number",
                     "million dollars enough", "trinity study", "swr", "fire number", "how much is enough"],
        "summary": "Withdraw 4% of the starting balance a year, adjusted for inflation, and it has lasted 30 years — so you need about 25× your spending.",
        "detail": (
            "The 4% rule comes from studies of every 30-year retirement since the 1920s: a portfolio "
            "of mostly stocks, drawn at 4% of its starting value in year one and that same dollar "
            "amount rising with inflation after, survived every one of them. Flip it around and the "
            "nest egg you need is roughly 25 times what you spend in a year — $40,000 of spending "
            "means about $1 million.\n\n"
            "It's a rule of thumb, not a law. It assumes 30 years, so a 40-year-old retiring early "
            "wants nearer 3.5%; Social Security and any pension reduce what the portfolio has to "
            "cover; and the worst case in the data was a specific bad sequence of years, so most "
            "retirements could have spent more. The plan here does the fuller version — it projects "
            "your actual spending against your actual balance to the age you chose — but 25× is the "
            "back-of-envelope answer."
        ),
        "facts": [{"label": "Spending $40,000 a year", "value": "about $1,000,000"},
                  {"label": "Spending $60,000 a year", "value": "about $1,500,000"},
                  {"label": "Retiring before 50", "value": "closer to 30× spending"}],
        "related": ["social_security_basics", "compound_interest", "sequence_risk"],
        "glossary_terms": ["todays_money", "coast_number"],
    },
    "sequence_risk": {
        "question": "What is sequence-of-returns risk?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["sequence risk", "sequence of returns", "bad years early in retirement", "crash right after retiring",
                     "order of returns", "retiring into a bear market", "why bonds near retirement"],
        "summary": "A bad market in the first years of retirement hurts far more than the same years later on.",
        "detail": (
            "While you're saving, the order of good and bad years doesn't matter — you end up in the "
            "same place. Once you're withdrawing, it does. A 30% fall in year one of retirement means "
            "you're selling shares cheap to pay the bills, and there are fewer left to recover when "
            "the market does. The same fall in year fifteen barely dents the plan.\n\n"
            "This is the reason to hold more bonds or cash in the years around retirement than at any "
            "other time: not because stocks are bad, but so the first few years' spending doesn't have "
            "to come from a portfolio that's just fallen. Two or three years of expenses somewhere "
            "steady is the usual defence. It's also why retiring the year after a crash is, oddly, "
            "safer than retiring the year before one."
        ),
        "related": ["safe_withdrawal_rate", "asset_allocation", "bear_and_bull_markets"],
        "glossary_terms": [],
    },
    "roth_conversions": {
        "question": "What is a Roth conversion, and when does it make sense?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["roth conversion", "convert to roth", "convert traditional to roth", "roth conversion ladder",
                     "conversion ladder", "when to convert", "low income year conversion", "5 year rule conversion",
                     "should i convert my ira"],
        "summary": "Moving traditional money to Roth, paying the tax now — best done in a low-income year.",
        "detail": (
            "A conversion takes money from a traditional IRA or 401(k), pays income tax on it this "
            "year, and lands it in a Roth where it's never taxed again. It makes sense when your tax "
            "rate this year is lower than it'll be when you'd otherwise withdraw — a gap year, early "
            "retirement before Social Security and RMDs start, a year with unusually low income.\n\n"
            "Each converted amount has its own five-year clock before it can come out penalty-free, "
            "which is what the \"conversion ladder\" uses: convert one year's spending every year, and "
            "five years on it starts arriving on schedule. That's the standard way early retirees "
            "reach 401(k) money before 59½ without penalty. Convert only what fits in a low bracket; "
            "pushing yourself into a higher one defeats the point."
        ),
        "related": ["rmds_explained", "roth_vs_traditional_mechanics", "age_59_half_explained", "marginal_vs_effective"],
        "glossary_terms": ["roth_conversion_ladder", "roth", "traditional"],
    },
    "backdoor_roth_explained": {
        "question": "How does a backdoor Roth work?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["backdoor roth", "back door roth", "income too high for roth", "make too much for roth",
                     "mega backdoor", "how to do a backdoor roth", "non deductible ira", "form 8606",
                     "roth for high earners"],
        "summary": "Contribute to a traditional IRA, then convert it to Roth — a legal route in when your income is too high.",
        "detail": (
            "Direct Roth IRA contributions phase out at high incomes. Traditional IRA *contributions* "
            "have no income limit — only the deduction does. So: contribute to a traditional IRA "
            "without deducting it, then convert that money to Roth. Since it was already taxed, the "
            "conversion is tax-free, and you've arrived in the Roth by a side door Congress has "
            "explicitly left open.\n\n"
            "The one thing that breaks it is the pro-rata rule: if you already hold pre-tax money in "
            "*any* traditional IRA, the conversion is taxed in proportion. The fix is to roll that "
            "pre-tax balance into a 401(k) first. File Form 8606 each year so the IRS knows the "
            "contribution was already taxed. The \"mega\" version does the same trick through a 401(k) "
            "that allows after-tax contributions — a much bigger amount, if your plan permits it."
        ),
        "related": ["pro_rata_rule", "rollovers", "roth_vs_traditional_mechanics"],
        "glossary_terms": ["backdoor_roth", "magi", "phase_out"],
    },
    "pro_rata_rule": {
        "question": "What is the pro-rata rule?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["pro rata rule", "pro-rata", "backdoor roth taxed", "why is my backdoor roth taxable",
                     "backdoor roth taxable", "existing traditional ira balance",
                     "aggregation rule", "why is my conversion taxable", "pre-tax ira and backdoor"],
        "summary": "A conversion is taxed in proportion to all your pre-tax IRA money — you can't pick which dollars convert.",
        "detail": (
            "The IRS treats all your traditional IRAs as one pot. If that pot is $90,000 of pre-tax "
            "money plus a fresh $7,000 non-deductible contribution, and you convert $7,000, the IRS "
            "says 90% of what you converted was pre-tax — so most of it is taxable, not none. That's "
            "the pro-rata rule, and it's the reason a backdoor Roth is clean for someone with no "
            "traditional IRA and messy for someone who rolled an old 401(k) into one.\n\n"
            "The standard fix is to move the pre-tax balance *out* — into a current 401(k), if the "
            "plan accepts roll-ins — before doing the backdoor. The rule counts balances on December "
            "31st, so there's time within the year. It doesn't count 401(k) balances, only IRAs."
        ),
        "related": ["backdoor_roth_explained", "rollovers"],
        "glossary_terms": ["backdoor_roth", "traditional"],
    },
    "catch_up_contributions": {
        "question": "What are catch-up contributions?",
        "topic": "Retirement mechanics", "level": "basic",
        "keywords": ["catch up contribution", "catch-up", "over 50 contribution", "extra contribution at 50",
                     "60 to 63 catch up", "super catch up", "limits after 50", "older worker contribution",
                     "hsa catch up 55"],
        "summary": "Extra room on top of the normal limit once you're 50 — and even more between 60 and 63.",
        "detail": (
            "From the year you turn 50, the 401(k) and IRA limits each get an extra allowance so "
            "people closer to retirement can save faster. The 401(k) catch-up is larger again between "
            "60 and 63, then drops back at 64. The HSA's catch-up starts at 55 rather than 50.\n\n"
            "New for 2026: if you earned more than $150,000 from that employer last year, your 401(k) "
            "catch-up has to go in as Roth rather than traditional. The exact amounts change yearly "
            "and live in the limits data file; the \"how much can I put in\" question applies them to "
            "your age automatically."
        ),
        "related": ["contribution_limits_deep", "roth_vs_traditional_mechanics"],
        "glossary_terms": ["catch_up", "contribution_limit"],
    },
    "roth_withdrawal_ordering": {
        "question": "Can I take money out of a Roth IRA early?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["roth withdrawal", "take contributions out of roth", "roth ira early withdrawal", "roth ordering rules",
                     "withdraw roth contributions", "roth as emergency fund", "roth 5 year rule", "roth earnings penalty",
                     "can i withdraw from my roth"],
        "summary": "Contributions, yes — any time, tax- and penalty-free. Earnings, not until 59½ and five years in.",
        "detail": (
            "Money comes out of a Roth IRA in a fixed order: your contributions first, then any "
            "converted amounts, then earnings. Contributions were already taxed, so they come back "
            "out free at any age, for any reason. That makes a Roth IRA a workable emergency reserve "
            "of last resort — though money you withdraw can't be put back, so it's a one-way door.\n\n"
            "Earnings are different: take those before 59½, or before the account is five years old, "
            "and you owe tax and the 10% penalty on the earnings portion. Conversions each have their "
            "own five-year clock. Track your contribution total somewhere, because the brokerage "
            "won't always separate it for you."
        ),
        "related": ["age_59_half_explained", "roth_conversions", "emergency_fund_sizing"],
        "glossary_terms": ["roth", "age_59_half"],
    },
    "early_retirement_bridge": {
        "question": "How do people retire before 59½ without paying penalties?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["retire early", "fire", "how does fire work", "what is fire", "fire movement", "financial independence",
                     "retire at 45", "retire at 50", "early retirement",
                     "bridge account", "money before 59 1/2", "how do early retirees access money", "lean fire", "fat fire",
                     "coast fire", "barista fire", "retire in my 40s"],
        "summary": "A taxable bridge account for the early years, plus Roth contributions and a conversion ladder for the rest.",
        "detail": (
            "The tax-advantaged accounts lock money until 59½, so an early retiree needs somewhere to "
            "draw from in the meantime. The standard structure has three parts. A taxable brokerage "
            "account covers the first years — no age rules, and long-term gains are taxed gently. "
            "Roth IRA contributions can be withdrawn any time. And a Roth conversion ladder, started "
            "five years before you need it, moves 401(k) money across in low-tax slices.\n\n"
            "When you pick an early retirement age here, the plan sizes the bridge for you: it works "
            "out how many years fall before 59½ and adds a taxable-account step ahead of extra 401(k) "
            "space. It also flags the gap before Medicare at 65, which is usually the biggest single "
            "cost early retirees underestimate."
        ),
        "related": ["age_59_half_explained", "roth_conversions", "safe_withdrawal_rate", "medicare_gap"],
        "glossary_terms": ["age_59_half", "roth_conversion_ladder", "coast_number"],
    },
    "medicare_gap": {
        "question": "What happens to health insurance if I retire before 65?",
        "topic": "Retirement mechanics", "level": "intermediate",
        "keywords": ["health insurance before 65", "medicare gap", "retire before medicare", "cobra", "aca marketplace",
                     "health coverage early retirement", "how much does health insurance cost retired", "obamacare retirement"],
        "summary": "Medicare starts at 65; before that you're buying coverage yourself — plan on it as a real cost.",
        "detail": (
            "Medicare doesn't begin until 65, so retiring earlier means arranging coverage for the gap: "
            "COBRA continues your employer plan for up to 18 months at full price, a spouse's plan if "
            "there is one, or the ACA marketplace. Marketplace subsidies are based on income, and an "
            "early retiree living off savings often has a low taxable income — which can make the "
            "premiums surprisingly manageable.\n\n"
            "The trap is Roth conversions: they count as income and can wipe out the subsidy. The "
            "plan flags the number of gap years when your retirement age is under 65, and it's worth "
            "budgeting a real figure for them rather than hoping. Enrolling in Medicare also ends your "
            "ability to contribute to an HSA."
        ),
        "related": ["early_retirement_bridge", "hsa_as_retirement_account", "roth_conversions"],
        "glossary_terms": ["medicare", "hsa"],
    },

    # =========================================================================
    # Taxes
    # =========================================================================

    "marginal_vs_effective": {
        "question": "What's the difference between my marginal and effective tax rate?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["marginal tax rate", "effective tax rate", "what's my tax rate", "what tax bracket am i in",
                     "marginal vs effective", "will a raise push me into a higher bracket", "lose money from a raise",
                     "how are taxes calculated", "tax rate on my income"],
        "summary": "Marginal is the rate on your *next* dollar; effective is what you actually pay overall — always lower.",
        "detail": (
            "Income tax is in layers. The first slice of income is taxed at the lowest rate, the next "
            "slice at the next rate, and so on. Your marginal rate is the rate on the top slice — the "
            "rate the next dollar you earn would face. Your effective rate is total tax divided by "
            "total income, which averages all the slices and is always lower.\n\n"
            "Someone \"in the 22% bracket\" doesn't pay 22% on everything; they might pay 12% overall. "
            "This is why a raise can never cost you money — only the dollars above the line are taxed "
            "at the higher rate. It's also why the marginal rate is the one that matters for "
            "decisions: a traditional 401(k) contribution saves you your *marginal* rate, and the Roth "
            "question is whether that's higher now or in retirement."
        ),
        "related": ["tax_brackets_explained", "roth_vs_traditional_mechanics", "standard_deduction"],
        "glossary_terms": ["traditional", "roth"],
    },
    "tax_brackets_explained": {
        "question": "How do tax brackets actually work?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["tax brackets", "how do brackets work", "progressive tax", "bracket creep", "federal tax brackets",
                     "income tax explained", "do i pay the bracket rate on everything", "what are the brackets"],
        "summary": "Each slice of income is taxed at its own rate — moving up a bracket only affects the dollars above the line.",
        "detail": (
            "Picture your income poured into a stack of buckets. The first bucket is taxed at 10%, and "
            "once it's full the overflow goes into the 12% bucket, then 22%, 24%, and so on. Only what "
            "lands in the higher bucket is taxed at the higher rate; everything below is untouched.\n\n"
            "So crossing into the 24% bracket by $1,000 costs you $240 on that $1,000 and changes "
            "nothing else. The bracket thresholds rise with inflation each year, and they sit *after* "
            "the standard deduction, so a single filer's first roughly $15,000 is taxed at zero before "
            "the 10% bucket even starts. State income tax is a separate stack on top, in most states."
        ),
        "related": ["marginal_vs_effective", "standard_deduction", "fica_explained"],
        "glossary_terms": [],
    },
    "standard_deduction": {
        "question": "What is the standard deduction?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["standard deduction", "itemize or standard", "should i itemize", "deductions", "what can i deduct",
                     "itemized deductions", "tax free amount", "first dollars untaxed"],
        "summary": "A flat amount of income taxed at zero — most people take it rather than itemizing.",
        "detail": (
            "Before any bracket applies, a fixed chunk of income is simply not taxed: the standard "
            "deduction, around $15,000 for a single filer and double for a married couple filing "
            "jointly, rising with inflation. You can instead itemize — add up mortgage interest, state "
            "taxes, charitable gifts — but you only come out ahead if the total beats the standard "
            "amount, and since it was doubled in 2018, roughly nine in ten filers don't.\n\n"
            "The practical consequence: the ordinary deductions people ask about (charity, medical "
            "bills) usually don't change your tax at all unless you itemize. The ones that always work "
            "are the above-the-line ones — traditional 401(k) and IRA contributions, HSA contributions "
            "— because they reduce income before the deduction question arises."
        ),
        "related": ["tax_brackets_explained", "pretax_vs_posttax", "marginal_vs_effective"],
        "glossary_terms": ["traditional", "hsa"],
    },
    "pretax_vs_posttax": {
        "question": "What does pre-tax versus post-tax mean?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["pre-tax", "pretax", "post-tax", "after-tax", "before tax", "pre tax vs after tax", "what does pretax mean",
                     "tax deferred", "tax deductible contribution", "taxed now or later"],
        "summary": "Pre-tax money skips tax now and pays it on the way out; post-tax paid it already and comes out free.",
        "detail": (
            "Pre-tax (traditional) contributions come off your income before tax is calculated, so a "
            "$1,000 contribution in the 22% bracket only costs you $780 of take-home pay. The trade is "
            "that every dollar withdrawn in retirement is taxed as income then. Post-tax (Roth) "
            "contributions are made from money already taxed, and come out — growth included — with "
            "nothing further owed.\n\n"
            "Same money, taxed at one end or the other. Which end is better is entirely about whether "
            "your rate is higher now or later, which is the Roth-versus-traditional question. Taxable "
            "brokerage money is post-tax too, but without the Roth's shelter: its growth is taxed as "
            "you go."
        ),
        "related": ["roth_vs_traditional_mechanics", "marginal_vs_effective", "tax_advantaged_vs_taxable"],
        "glossary_terms": ["traditional", "roth", "payroll_deferral"],
    },
    "roth_vs_traditional_mechanics": {
        "question": "Roth or traditional — how do I actually decide?",
        "topic": "Taxes", "level": "intermediate",
        "keywords": ["roth vs traditional", "roth or traditional", "which is better roth or traditional", "roth 401k vs traditional 401k",
                     "should i do roth", "traditional or roth ira", "tax now or tax later", "roth for young people",
                     "split roth and traditional", "why roth", "why traditional"],
        "summary": "Tax rate now versus tax rate in retirement — lower now means Roth, higher now means traditional, unsure means split.",
        "detail": (
            "The whole decision is one comparison. Traditional lets you skip tax at today's marginal "
            "rate and pay it at retirement's rate; Roth does the reverse. If today's rate is lower — "
            "early career, part-time, a gap year — Roth wins, because you're paying tax while it's "
            "cheap. If today's rate is higher — peak earning years — traditional wins. Nobody knows "
            "their future bracket, so a split between both is a reasonable hedge, and you can change "
            "the mix every year.\n\n"
            "Three tie-breakers favour Roth: no required minimum distributions, contributions you can "
            "withdraw early, and the fact that the Roth limit is effectively bigger because it's in "
            "after-tax dollars. One favours traditional: the tax saving arrives now, when you might "
            "need the cash flow more. For a 20-year-old on a low income, Roth is close to a free "
            "decision; the personal version of this question checks your own bracket setting."
        ),
        "related": ["marginal_vs_effective", "pretax_vs_posttax", "rmds_explained", "roth_withdrawal_ordering"],
        "glossary_terms": ["roth", "traditional"],
    },
    "tax_loss_harvesting": {
        "question": "What is tax-loss harvesting?",
        "topic": "Taxes", "level": "intermediate",
        "keywords": ["tax loss harvesting", "harvest losses", "sell at a loss for taxes", "offset gains with losses",
                     "3000 loss deduction", "capital loss", "use losses to reduce taxes", "tlh"],
        "summary": "Selling something at a loss to cancel out gains on your taxes — then buying something similar to stay invested.",
        "detail": (
            "In a taxable account, a realised loss can offset realised gains, and up to $3,000 a year "
            "of ordinary income beyond that, with the rest carried forward. So when a fund is down, "
            "you can sell it, book the loss, and immediately buy a *similar but not identical* fund — "
            "a total-market fund in place of an S&P 500 fund, say — so you're still invested. You've "
            "kept the same exposure and gained a tax deduction.\n\n"
            "The catch is the wash-sale rule: buy the same or a \"substantially identical\" thing "
            "within 30 days either side of the sale and the loss is disallowed. It only applies to "
            "taxable accounts — there's nothing to harvest in a 401(k) or IRA — and it's a nicety, not "
            "a strategy. Worth doing in a bad year if you hold a taxable account; not worth "
            "restructuring your life around."
        ),
        "related": ["wash_sale_rule", "capital_gains_short_vs_long", "what_is_taxable_account"],
        "glossary_terms": ["capital_gains", "taxable_brokerage"],
    },
    "wash_sale_rule": {
        "question": "What is the wash-sale rule?",
        "topic": "Taxes", "level": "intermediate",
        "keywords": ["wash sale", "wash sale rule", "30 day rule", "rebuy after selling at a loss", "substantially identical",
                     "sold at a loss and bought back", "wash sale ira"],
        "summary": "Sell at a loss and rebuy the same thing within 30 days, and the loss doesn't count.",
        "detail": (
            "The rule stops people from booking a tax loss while never really leaving the investment. "
            "Sell something at a loss, then buy it — or anything substantially identical — within 30 "
            "days before or after, and the loss is disallowed for that year. It's added to the cost of "
            "the new shares instead, so it isn't lost forever, just deferred.\n\n"
            "It catches automatic dividend reinvestment, and it counts purchases in your IRA and your "
            "spouse's accounts too. Two funds tracking different indexes — total market and S&P 500 — "
            "are generally treated as not identical, which is the usual way around it. If you never "
            "sell at a loss in a taxable account, it never applies to you."
        ),
        "related": ["tax_loss_harvesting", "capital_gains_short_vs_long"],
        "glossary_terms": ["capital_gains"],
    },
    "capital_gains_short_vs_long": {
        "question": "How are capital gains taxed?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["capital gains tax", "long term capital gains", "short term capital gains", "how are gains taxed",
                     "long term vs short term", "long term or short term", "longterm vs shortterm gains",
                     "tax when i sell", "hold for a year", "0% capital gains", "15% capital gains", "capital gains rate",
                     "tax on profit from stocks", "do i pay tax on investments"],
        "summary": "Hold over a year and the profit is taxed at 0%, 15% or 20%; under a year, it's taxed like wages.",
        "detail": (
            "A capital gain is the profit when you sell something for more than you paid. If you held "
            "it more than a year it's long-term, taxed at 0%, 15% or 20% depending on income — and the "
            "0% band is generous, reaching into the middle of the income range for a couple. Under a "
            "year it's short-term, taxed as ordinary income, usually much higher. That one-year line is "
            "the biggest tax lever a taxable investor has.\n\n"
            "None of this applies inside a 401(k), IRA or HSA — you can sell and rebuy there with no "
            "tax at all, which is why rebalancing belongs in those accounts. In a taxable account, "
            "buy-and-hold index funds generate very few sales, so most people go years without a "
            "significant gains bill."
        ),
        "facts": [{"label": "Held over a year", "value": "0%, 15% or 20% by income"},
                  {"label": "Held under a year", "value": "your ordinary income rate"},
                  {"label": "Losses", "value": "offset gains, plus $3,000 of income a year"}],
        "related": ["qualified_dividends", "tax_loss_harvesting", "what_is_taxable_account"],
        "glossary_terms": ["capital_gains", "taxable_brokerage"],
    },
    "qualified_dividends": {
        "question": "What are qualified dividends?",
        "topic": "Taxes", "level": "intermediate",
        "keywords": ["qualified dividends", "ordinary dividends", "how are dividends taxed", "dividend tax rate",
                     "1099-div", "tax on dividends", "non qualified dividends"],
        "summary": "Dividends from stocks held a couple of months get the low capital-gains rate; others are taxed as income.",
        "detail": (
            "Most dividends from US and many foreign stocks are \"qualified\" if you've held the shares "
            "for at least 61 days around the payment date, and they're taxed at the long-term "
            "capital-gains rates — 0%, 15% or 20%. Non-qualified ones — from REITs, bond funds, money "
            "market funds — are taxed as ordinary income.\n\n"
            "This is why a bond fund or a high-yield savings account belongs in a tax-advantaged "
            "account when you have the choice, and a stock index fund is the most tax-friendly thing "
            "to hold in a taxable one: most of its small dividend is qualified, and the rest of its "
            "return is unrealised growth that isn't taxed until you sell."
        ),
        "related": ["dividends", "capital_gains_short_vs_long", "tax_drag"],
        "glossary_terms": ["capital_gains"],
    },
    "tax_drag": {
        "question": "What is tax drag, and what should go in which account?",
        "topic": "Taxes", "level": "intermediate",
        "keywords": ["tax drag", "asset location", "what to hold in taxable", "bonds in ira", "tax efficient placement",
                     "which account for which fund", "tax efficient investing", "where to hold bonds"],
        "summary": "The yearly tax bite on a taxable account — put the tax-noisy things in sheltered accounts first.",
        "detail": (
            "Tax drag is the return you lose each year to tax in a taxable account: on dividends, "
            "interest and any gains you realise. A stock index fund has very little — a small mostly "
            "qualified dividend and no forced sales. A bond fund has a lot, because its whole return is "
            "interest taxed as income. Actively managed funds and REITs are noisy too.\n\n"
            "So asset *location* — which account holds which fund — matters once you have a taxable "
            "account alongside sheltered ones. Bonds, REITs and anything that throws off income belong "
            "in the 401(k) or IRA; broad stock index funds are the natural thing to hold in taxable. "
            "Fill the tax-advantaged accounts first, which the waterfall does anyway, and this mostly "
            "takes care of itself."
        ),
        "related": ["qualified_dividends", "tax_advantaged_vs_taxable", "what_is_taxable_account"],
        "glossary_terms": ["taxable_brokerage"],
    },
    "w2_vs_1099": {
        "question": "What's the difference between W-2 and 1099 income for saving?",
        "topic": "Taxes", "level": "intermediate",
        "keywords": ["1099", "w2 vs 1099", "self employed retirement", "freelance retirement account", "solo 401k",
                     "sep ira", "independent contractor", "gig income", "side hustle taxes", "self employment tax",
                     "no 401k self employed"],
        "summary": "W-2 is a job with tax withheld; 1099 is self-employment, with its own tax and its own — often bigger — retirement accounts.",
        "detail": (
            "A W-2 employee has tax and Social Security withheld from each paycheck and may have a "
            "401(k) at work. A 1099 contractor is paid gross, owes both halves of Social Security and "
            "Medicare (about 15% self-employment tax, half of it deductible), and has to pay estimated "
            "tax quarterly or face a penalty.\n\n"
            "The upside is the accounts. A solo 401(k) lets a self-employed person contribute as both "
            "employee and employer — often far more than a workplace plan allows — and a SEP-IRA is "
            "the simpler alternative at up to 25% of net earnings. Either fits into the same waterfall "
            "in place of the 401(k) steps. Side income alongside a W-2 job can open a solo 401(k) for "
            "just that income."
        ),
        "related": ["fica_explained", "contribution_limits_deep", "paycheck_withholding"],
        "glossary_terms": ["401k"],
    },
    "fica_explained": {
        "question": "What is FICA, and why is my paycheck smaller than my salary?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["fica", "social security tax", "medicare tax", "payroll tax", "why is my paycheck so small",
                     "what comes out of my paycheck", "paycheck deductions", "7.65%", "oasdi", "gross vs net"],
        "summary": "7.65% of pay for Social Security and Medicare, taken before income tax — your employer pays the same again.",
        "detail": (
            "FICA is the payroll tax funding Social Security (6.2%, up to an annual wage cap) and "
            "Medicare (1.45%, no cap). It comes off the top of every paycheck, separate from income "
            "tax, and your employer matches it invisibly. Together with federal and state income tax "
            "withholding, health insurance premiums, and any 401(k) deferral, it's why take-home pay "
            "is typically 65–75% of salary.\n\n"
            "Traditional 401(k) contributions reduce income tax but not FICA. HSA contributions "
            "through payroll reduce both — one of the reasons the HSA's tax treatment is uniquely "
            "good. The self-employed pay both halves themselves, which is the self-employment tax."
        ),
        "related": ["paycheck_withholding", "gross_vs_net", "w2_vs_1099"],
        "glossary_terms": ["take_home", "payroll_deferral", "hsa"],
    },
    "tax_advantaged_vs_taxable": {
        "question": "What does tax-advantaged mean, and why does the order matter?",
        "topic": "Taxes", "level": "basic",
        "keywords": ["tax advantaged", "tax-advantaged account", "why use retirement accounts", "why not just a brokerage",
                     "why not just use a regular brokerage account", "regular brokerage", "normal brokerage account",
                     "why bother with retirement accounts", "what's the point of a 401k",
                     "tax sheltered", "tax free growth", "why does account type matter", "difference between accounts"],
        "summary": "Accounts where growth isn't taxed as it happens — every year of shelter compounds, so they get filled first.",
        "detail": (
            "In a plain brokerage account, dividends are taxed every year and gains when you sell. In a "
            "401(k), IRA or HSA, none of that happens while the money's inside: it grows untouched, and "
            "tax is paid once — either going in (Roth) or coming out (traditional), or, for the HSA "
            "used on medical costs, never. Decades of not paying tax on the growth along the way is a "
            "large advantage, which is why these accounts sit above the taxable one in the waterfall.\n\n"
            "The trade is access: the money is meant to stay until 59½. So the order is: capture "
            "anything free (the match), then fill the sheltered accounts in order of how good their "
            "shelter is, then put the rest in taxable — which has no limits and no age rules, and "
            "isn't a bad account, just a less good one."
        ),
        "related": ["pretax_vs_posttax", "tax_drag", "what_is_taxable_account", "age_59_half_explained"],
        "glossary_terms": ["taxable_brokerage", "hsa"],
    },

    # =========================================================================
    # Debt and credit
    # =========================================================================

    "apr_vs_apy": {
        "question": "What's the difference between APR and APY?",
        "topic": "Debt and credit", "level": "basic",
        "keywords": ["apr vs apy", "apy", "what is apr", "what is apy", "interest rate vs apr", "annual percentage yield",
                     "annual percentage rate", "which is higher apr or apy", "savings account apy"],
        "summary": "APR is the stated rate; APY includes compounding — APY is what you actually earn or pay.",
        "detail": (
            "APR — annual percentage rate — is the simple yearly rate. APY — annual percentage yield — "
            "is what that rate becomes once interest compounds within the year. A 5% APR compounding "
            "monthly is about 5.12% APY. The gap is small at savings-account rates and larger on a "
            "credit card, where 24% APR compounding daily is about 27% APY.\n\n"
            "Banks quote savings accounts in APY because it's the bigger number; lenders quote loans in "
            "APR because it's the smaller one. When comparing two of the same thing, use the same "
            "measure. The rule the plan uses for debt — pay it off first above 7.5% — is in APR, "
            "matching how your statement shows it."
        ),
        "related": ["compound_interest", "high_yield_savings", "good_vs_bad_debt"],
        "glossary_terms": ["apr"],
    },
    "minimum_payments": {
        "question": "What happens if I only pay the minimum on a credit card?",
        "topic": "Debt and credit", "level": "basic",
        "keywords": ["minimum payment", "only pay the minimum", "minimum payment trap", "how long to pay off credit card",
                     "credit card interest", "how is credit card interest calculated", "paying minimum", "carrying a balance"],
        "summary": "The minimum is set so the balance barely moves — a $5,000 card can take over 15 years and double in cost.",
        "detail": (
            "A card's minimum payment is usually 1–2% of the balance plus interest, or $25, whichever "
            "is more. It's designed to be affordable, not to clear the debt: at 24% APR, a $5,000 "
            "balance paid at the minimum takes well over fifteen years and costs more in interest than "
            "the original balance. Most of each payment goes to interest, not principal.\n\n"
            "The way out is a fixed payment that doesn't shrink as the balance does. Paying $200 a "
            "month instead of the minimum clears the same $5,000 in about three years. The plan treats "
            "minimums as bills and puts any debt above 7.5% at step 3 — so the question is what extra "
            "you can put toward it, not whether to."
        ),
        "facts": [{"label": "$5,000 at 24%, minimum only", "value": "over 15 years, roughly $6,000 in interest"},
                  {"label": "$5,000 at 24%, $200 a month", "value": "about 3 years, roughly $2,000 in interest"}],
        "related": ["avalanche_vs_snowball", "apr_vs_apy", "credit_utilization"],
        "glossary_terms": ["apr"],
    },
    "avalanche_vs_snowball": {
        "question": "Avalanche or snowball — which order should I pay off debts?",
        "topic": "Debt and credit", "level": "basic",
        "keywords": ["avalanche", "snowball", "avalanche vs snowball", "debt snowball", "debt avalanche", "which debt first",
                     "smallest debt first or highest interest", "pay the smallest debt first", "highest interest debt first",
                     "highest interest first", "smallest balance first", "order to pay off debts", "multiple debts",
                     "dave ramsey snowball", "pay off which loan first"],
        "summary": "Avalanche (highest rate first) costs least; snowball (smallest balance first) keeps more people going.",
        "detail": (
            "With several debts, pay the minimum on all and throw everything extra at one. Avalanche "
            "picks the highest interest rate first, which is mathematically cheapest — you're always "
            "attacking the debt that costs most. Snowball picks the smallest balance first, so you "
            "clear a whole debt sooner and feel the progress.\n\n"
            "Avalanche is the right answer on paper and the plan orders your debts that way. But the "
            "gap between the two is often a few hundred dollars over the whole payoff, and the method "
            "that keeps you paying beats the one you abandon. If a quick win would keep you motivated, "
            "snowball is a perfectly respectable choice. What matters far more than the order is the "
            "extra payment."
        ),
        "related": ["minimum_payments", "good_vs_bad_debt", "when_debt_beats_investing"],
        "glossary_terms": ["apr"],
    },
    "credit_score_factors": {
        "question": "What actually affects my credit score?",
        "topic": "Debt and credit", "level": "basic",
        "keywords": ["credit score", "how to improve credit score", "what affects credit score", "fico", "credit report",
                     "build credit", "credit history", "hard inquiry", "does checking my score hurt it", "credit age",
                     "raise my credit score", "why did my score drop"],
        "summary": "Paying on time and keeping balances low are about two-thirds of it; the rest is age, mix and new applications.",
        "detail": (
            "Five things, in order of weight: payment history (35%) — never miss a payment; amounts owed "
            "(30%) — mainly how much of your card limits you're using; length of history (15%) — keep "
            "old accounts open; credit mix (10%) — a card plus a loan helps a little; and new credit "
            "(10%) — each application dings it briefly.\n\n"
            "Checking your own score never hurts it; only applications do. The fastest improvement for "
            "most people is paying card balances down before the statement date so the reported "
            "utilisation is low. Carrying a balance doesn't help your score — that's a myth that costs "
            "people interest. Paying in full every month is both the cheapest and the best for the score."
        ),
        "related": ["credit_utilization", "minimum_payments", "good_vs_bad_debt"],
        "glossary_terms": [],
    },
    "credit_utilization": {
        "question": "What is credit utilization?",
        "topic": "Debt and credit", "level": "basic",
        "keywords": ["credit utilization", "utilization ratio", "how much of my credit limit to use", "30% rule",
                     "keep balance under 30%", "credit limit", "statement balance", "pay before statement"],
        "summary": "The share of your card limits you're using — under 30% is fine, under 10% is best, and it resets monthly.",
        "detail": (
            "If your cards total $10,000 in limits and you owe $3,000 across them, your utilisation is "
            "30%. It's the second-biggest factor in your score and the easiest to move, because it has "
            "no memory: it's recalculated from whatever balance your card reports each month, usually "
            "the statement balance.\n\n"
            "So paying most of the balance before the statement closes — not just before the due date "
            "— makes the reported number small. Under 30% is the usual advice; under 10% scores best. "
            "A higher limit lowers utilisation without changing your spending, which is why asking for "
            "a limit increase can help, provided it doesn't tempt you to use it."
        ),
        "related": ["credit_score_factors", "minimum_payments"],
        "glossary_terms": [],
    },
    "good_vs_bad_debt": {
        "question": "Is there such a thing as good debt?",
        "topic": "Debt and credit", "level": "basic",
        "keywords": ["good debt", "bad debt", "good debt vs bad debt", "is a mortgage good debt", "is all debt bad",
                     "should i be debt free", "leverage", "cheap debt", "expensive debt", "is student debt bad"],
        "summary": "Debt is cheap or expensive, not good or bad — under about 7% and buying something lasting, it's fine to carry.",
        "detail": (
            "The useful question isn't moral, it's arithmetic: what does this debt cost, and what did "
            "it buy? A 6% mortgage on a house, a 5% loan on an education that raised your income — "
            "these cost less than investing is expected to return, and bought something durable. A "
            "24% card balance for a holiday is the opposite on both counts.\n\n"
            "The plan draws the line at 7.5%: above it, pay it off before investing beyond the match; "
            "below it, pay on schedule and invest alongside. Being entirely debt-free is a fine goal "
            "for the peace of mind, but rushing to clear a 4% mortgage while an IRA sits empty is "
            "leaving money on the table, and the math says so clearly."
        ),
        "related": ["when_debt_beats_investing", "avalanche_vs_snowball", "student_loans_basics"],
        "glossary_terms": ["apr"],
    },
    "when_debt_beats_investing": {
        "question": "When does paying off debt beat investing?",
        "topic": "Debt and credit", "level": "intermediate",
        "keywords": ["pay off debt or invest", "debt vs investing", "should i invest with debt", "guaranteed return of paying debt",
                     "7% rule debt", "invest or pay down mortgage", "pay extra on mortgage or invest", "pay off car or invest",
                     "extra money debt or 401k"],
        "summary": "When the debt's rate beats what investing is expected to earn — the plan draws that line at 7.5%.",
        "detail": (
            "Paying a dollar off a debt earns exactly its interest rate, guaranteed. Investing a dollar "
            "is expected to earn around 7% over the long run, not guaranteed, with bad years along the "
            "way. So a debt costing more than that is a better use of the dollar, and one costing much "
            "less is a worse one. The plan uses 7.5% as the line to leave a margin for the risk.\n\n"
            "One thing outranks both: an employer match, which is an immediate 50–100% return and "
            "beats any interest rate. Capture that, then attack the expensive debt, then everything "
            "else. The personal version of this question runs your actual debts through the rule; the "
            "scenario version lets you try one you haven't added yet."
        ),
        "facts": [{"label": "Paying off a 22% card", "value": "a guaranteed 22%"},
                  {"label": "Long-run stock market average", "value": "about 7% — not guaranteed"},
                  {"label": "A typical 50% employer match", "value": "an instant 50%"}],
        "related": ["good_vs_bad_debt", "avalanche_vs_snowball", "employer_match_deep"],
        "glossary_terms": ["apr", "employer_match"],
    },
    "student_loans_basics": {
        "question": "How do student loans work — federal versus private, and what are my options?",
        "topic": "Debt and credit", "level": "intermediate",
        "keywords": ["student loans", "federal student loans", "private student loans", "income driven repayment", "idr",
                     "save plan", "pslf", "public service loan forgiveness", "student loan forgiveness", "refinance student loans",
                     "subsidized vs unsubsidized", "student loan interest", "loan servicer", "should i pay off student loans early"],
        "summary": "Federal loans have income-based plans and forgiveness routes private loans don't — know which you have before refinancing.",
        "detail": (
            "Federal loans, which most students have, come with protections: payments can be set as a "
            "share of income, forgiven after 20–25 years on those plans or after 10 years of public "
            "service work, and paused in hardship. Rates are fixed and usually 4–8%. Private loans are "
            "ordinary bank loans — often a better rate for a strong borrower, but none of the safety "
            "net. Refinancing federal into private trades the protections away permanently.\n\n"
            "For paying them down, they're just debt with a rate: most federal loans sit below the 7.5% "
            "line, so the plan has you pay on schedule and invest alongside. Someone heading for "
            "public-service forgiveness should pay the *minimum*, since every extra dollar is one that "
            "would have been forgiven. Subsidised loans don't accrue interest while you're in school; "
            "unsubsidised ones do."
        ),
        "related": ["good_vs_bad_debt", "when_debt_beats_investing", "refinancing"],
        "glossary_terms": ["apr"],
    },
    "refinancing": {
        "question": "When does refinancing make sense?",
        "topic": "Debt and credit", "level": "intermediate",
        "keywords": ["refinance", "refinancing", "should i refinance", "lower my interest rate", "balance transfer",
                     "0% balance transfer", "consolidate debt", "debt consolidation", "refi", "refinance my mortgage",
                     "refinance car loan"],
        "summary": "When the new rate is enough lower to beat the fees — and, for federal student loans, only if you won't need the protections.",
        "detail": (
            "Refinancing replaces a loan with a cheaper one. It's worth it when the rate drop covers "
            "the cost of doing it: a mortgage refi has closing costs that take a year or two of "
            "savings to earn back, so it makes sense if you'll stay longer than that and the rate is "
            "at least half a point lower. Car and personal loans refinance cheaply if your credit has "
            "improved since you took them.\n\n"
            "For credit-card debt, a 0% balance-transfer card is the version that matters: move the "
            "balance, pay a 3–5% fee, and get 12–21 months interest-free to clear it — a good deal only "
            "if you actually pay it off in the window. Consolidation loans are similar and worth it "
            "only if the new rate is genuinely lower, not just the payment."
        ),
        "related": ["student_loans_basics", "minimum_payments", "credit_score_factors"],
        "glossary_terms": ["apr"],
    },

    # =========================================================================
    # Cash and banking
    # =========================================================================

    "emergency_fund_sizing": {
        "question": "How big should my emergency fund be, and where should it live?",
        "topic": "Cash and banking", "level": "basic",
        "keywords": ["emergency fund", "how much emergency fund", "3 months or 6 months", "rainy day fund", "where to keep emergency fund",
                     "emergency savings", "how much cash should i have", "safety net", "cash cushion", "should i invest my emergency fund",
                     "emergency fund too big"],
        "summary": "Three to six months of expenses, in a savings account, before any investing — it's what keeps a bad month from becoming debt.",
        "detail": (
            "An emergency fund is cash for the things that go wrong: the car, the job, the tooth. Three "
            "months of *expenses* — not income — is the floor; six is comfortable; more if your income "
            "is irregular or you're the only earner. It goes in a high-yield savings account: boring, "
            "instantly available, never invested, because the one time you need it might be the same "
            "week the market fell.\n\n"
            "It comes before investing in the waterfall for a reason — without it, the first emergency "
            "lands on a credit card at 24%, and the investing gets undone. Past the three-month floor "
            "the plan treats topping it up as a step alongside the others rather than ahead of a "
            "guaranteed employer match. A Roth IRA's contributions are a last-resort backstop, not a "
            "substitute."
        ),
        "related": ["high_yield_savings", "roth_withdrawal_ordering", "sinking_funds"],
        "glossary_terms": ["emergency_fund"],
    },
    "high_yield_savings": {
        "question": "What is a high-yield savings account?",
        "topic": "Cash and banking", "level": "basic",
        "keywords": ["high yield savings", "hysa", "best savings account", "savings account interest", "online savings account",
                     "where to keep cash", "ally", "marcus", "savings rate too low", "my bank pays nothing", "cash yield"],
        "summary": "A savings account at an online bank paying real interest — same insurance as your bank, often 10× the rate.",
        "detail": (
            "Big branch banks pay close to nothing on savings. Online banks — with no branches to run — "
            "pay a rate near what the Federal Reserve sets, which can be 4% or more when rates are up "
            "and 1–2% when they're down. Same FDIC insurance, same instant access, and moving money "
            "between it and your checking account takes a day or two.\n\n"
            "It's the right home for the emergency fund and for any cash with a purpose within a couple "
            "of years — a house deposit, a car. It's the wrong home for long-term money, because even a "
            "good savings rate roughly matches inflation and no more. Rates change; the difference "
            "between the best and the tenth-best is small, so pick a reputable one and stop looking."
        ),
        "related": ["emergency_fund_sizing", "money_market_funds", "cds_explained", "fdic_insurance"],
        "glossary_terms": ["emergency_fund"],
    },
    "cds_explained": {
        "question": "What is a CD, and when is one worth it?",
        "topic": "Cash and banking", "level": "basic",
        "keywords": ["cd", "certificate of deposit", "cd ladder", "cd rates", "lock in a rate", "cd vs savings",
                     "cd early withdrawal penalty", "should i buy a cd", "cd or treasury"],
        "summary": "A savings deposit locked for a set term at a fixed rate — worth it when you want a rate guaranteed.",
        "detail": (
            "A certificate of deposit is a bank deposit you agree not to touch for a fixed term — three "
            "months to five years — in exchange for a fixed rate, usually a little above a savings "
            "account. Withdraw early and you forfeit some interest. It's FDIC-insured like any deposit.\n\n"
            "It makes sense for money with a known date and a wish to lock today's rate before it falls "
            "— a down payment in eighteen months, say. It doesn't make sense for the emergency fund "
            "(you can't reach it) or for long-term money (it won't beat inflation by much). Treasury "
            "bills do the same job with no state tax and no early-withdrawal penalty if sold, and are "
            "often a slightly better version of the same idea."
        ),
        "related": ["high_yield_savings", "money_market_funds", "sinking_funds"],
        "glossary_terms": [],
    },
    "money_market_funds": {
        "question": "What is a money market fund?",
        "topic": "Cash and banking", "level": "intermediate",
        "keywords": ["money market fund", "money market", "settlement fund", "spaxx", "vmfxx", "cash in brokerage",
                     "where does uninvested cash sit", "core position", "sweep account", "money market vs savings"],
        "summary": "Where cash sits inside a brokerage account, earning a rate close to a savings account's.",
        "detail": (
            "Uninvested cash in a brokerage account usually lands in a money market fund — Fidelity's "
            "SPAXX, Vanguard's VMFXX — which holds very short-term government and bank debt and pays a "
            "rate close to what the Fed sets. It's designed to hold a $1 price and it's the account's "
            "\"cash\", but it isn't a bank deposit: it's SIPC-covered against the brokerage failing, not "
            "FDIC-insured against the fund losing value, which is extraordinarily rare but not zero.\n\n"
            "It's fine as a place for cash you're about to invest, and some people use it instead of a "
            "savings account. The thing to watch is the opposite: money that was *meant* to be invested "
            "sitting in the settlement fund for years because the purchase never happened. Opening the "
            "account and buying the fund are two separate steps."
        ),
        "related": ["high_yield_savings", "fdic_insurance", "what_is_a_brokerage"],
        "glossary_terms": [],
    },
    "fdic_insurance": {
        "question": "What does FDIC insurance actually cover?",
        "topic": "Cash and banking", "level": "basic",
        "keywords": ["fdic", "fdic insurance", "is my money safe in the bank", "bank failure", "250000 limit",
                     "sipc", "is my brokerage insured", "what if my bank fails", "ncua", "insured deposits"],
        "summary": "Bank deposits up to $250,000 per person per bank if the bank fails — not losses on investments.",
        "detail": (
            "The FDIC guarantees deposits — checking, savings, CDs — up to $250,000 per depositor, per "
            "bank, per ownership category. If the bank fails, you get your money, usually within days. "
            "Credit unions have the same through the NCUA. Joint accounts double the limit; more than "
            "that at one bank means spreading it across banks.\n\n"
            "Brokerage accounts are covered by SIPC instead, which returns your securities and cash if "
            "the *brokerage* fails or steals them — up to $500,000. Neither protects against the "
            "investments themselves falling, which isn't a failure, it's the market. The practical "
            "worry for most people is nil: keep under $250,000 at any one bank and it's simply safe."
        ),
        "related": ["high_yield_savings", "money_market_funds", "volatility_vs_risk"],
        "glossary_terms": [],
    },
    "inflation_explained": {
        "question": "Why does inflation matter for saving?",
        "topic": "Cash and banking", "level": "basic",
        "keywords": ["inflation", "why does inflation matter", "cash loses value", "purchasing power", "inflation and savings",
                     "is cash safe", "inflation rate", "cost of living", "money worth less", "2% inflation", "why invest at all"],
        "summary": "Prices rise about 2–3% a year, so cash quietly loses that much — it's why money has to grow just to stand still.",
        "detail": (
            "Inflation is the rate prices rise. At 2.5% a year — roughly the long-run average — a "
            "dollar buys about what 78 cents did a decade ago, and half what it did thirty years ago. "
            "Money in a drawer or a zero-interest account loses that much purchasing power every year "
            "without the number changing, which is what makes it feel safe and isn't.\n\n"
            "This is the case for investing at all: stocks have returned roughly 7% a year *after* "
            "inflation over long periods, while cash has returned roughly zero after it. It's also why "
            "the plan shows retirement figures in today's money — a million dollars in forty years buys "
            "what about $370,000 buys now, and planning in the raw number would overstate everything."
        ),
        "facts": [{"label": "$1 million in 40 years, at 2.5% inflation", "value": "buys about $372,000 of today's goods"},
                  {"label": "Long-run US stock return after inflation", "value": "about 7%"},
                  {"label": "Cash after inflation", "value": "about 0%"}],
        "related": ["real_vs_nominal", "volatility_vs_risk", "high_yield_savings"],
        "glossary_terms": ["todays_money"],
    },
    "real_vs_nominal": {
        "question": "What does 'real' versus 'nominal' mean?",
        "topic": "Cash and banking", "level": "intermediate",
        "keywords": ["real return", "nominal return", "real vs nominal", "inflation adjusted", "today's dollars", "future dollars",
                     "after inflation", "what's my real return", "constant dollars"],
        "summary": "Nominal is the raw number; real is after inflation — real is the one that tells you what you can buy.",
        "detail": (
            "A 7% nominal return with 2.5% inflation is about a 4.4% real return: that's the growth in "
            "what the money can actually purchase. Every long-term figure is more honest in real terms, "
            "which is why the plan's projections show both and compare in today's money.\n\n"
            "The mistake it prevents is being impressed by a big future number. A $2 million nest egg "
            "in 2065 sounds like wealth; in today's money it's about $750,000, which is a comfortable "
            "retirement, not a fortune. Working in real terms also makes the 4% rule and the "
            "25×-expenses rule come out right, since they were built on inflation-adjusted spending."
        ),
        "related": ["inflation_explained", "safe_withdrawal_rate", "compound_interest"],
        "glossary_terms": ["todays_money"],
    },
    "sinking_funds": {
        "question": "What is a sinking fund?",
        "topic": "Cash and banking", "level": "basic",
        "keywords": ["sinking fund", "saving for a specific goal", "save for a car", "save for a vacation", "save for a house",
                     "short term savings", "saving for something in 2 years", "separate savings buckets", "goal savings"],
        "summary": "Cash set aside monthly for a known future expense — so the car or the holiday doesn't raid the emergency fund.",
        "detail": (
            "A sinking fund is a named pot of savings for a specific thing with a rough date: $200 a "
            "month toward next summer's trip, $400 toward a car in three years. It's ordinary cash in a "
            "savings account — many online banks let you split one account into labelled buckets — "
            "and its whole purpose is separation. The emergency fund is for emergencies; a planned "
            "expense isn't one.\n\n"
            "Anything you'll spend within about five years belongs in cash or a CD, not invested, "
            "because a 30% market fall the year before you need it isn't a risk worth taking for a "
            "few percent of growth. Beyond five years, investing becomes reasonable. This is the one "
            "place where 'boring savings account' is the sophisticated answer."
        ),
        "related": ["emergency_fund_sizing", "high_yield_savings", "cds_explained"],
        "glossary_terms": ["emergency_fund"],
    },

    # =========================================================================
    # Income and planning
    # =========================================================================

    "gross_vs_net": {
        "question": "What's the difference between gross and net pay?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["gross vs net", "gross pay", "net pay", "take home pay", "what is take home", "salary vs take home",
                     "how much of my salary do i keep", "gross income", "net income", "after tax income"],
        "summary": "Gross is the salary; net is what lands in your account — usually 65–75% of it.",
        "detail": (
            "Gross pay is the number in the job offer. Net, or take-home, is what's left after federal "
            "and state income tax withholding, FICA, health insurance premiums, and any 401(k) or HSA "
            "contributions have come out. For most people that's two-thirds to three-quarters of gross.\n\n"
            "Two things to keep straight. Contribution limits and the employer match are calculated on "
            "gross. Your budget and your monthly plan have to fit inside net — which is why the "
            "schedule here works from take-home pay and why a 401(k) deferral doesn't show up as a "
            "transfer: it never reaches your account in the first place."
        ),
        "related": ["fica_explained", "paycheck_withholding", "savings_rate_explained"],
        "glossary_terms": ["take_home", "payroll_deferral"],
    },
    "paycheck_withholding": {
        "question": "How does paycheck withholding work, and why do I get a refund?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["withholding", "tax withholding", "why do i get a refund", "big tax refund", "owe taxes at filing",
                     "adjust withholding", "w-4", "w4", "too much tax taken out", "refund is bad", "how much tax to withhold"],
        "summary": "Your employer pays an estimate of your tax each paycheck; a refund means the estimate ran high all year.",
        "detail": (
            "Income tax is paid as you go: each paycheck, the employer withholds an amount toward your "
            "annual bill, based on the W-4 form you filled in. At filing time you settle the difference. "
            "A refund means you overpaid through the year and lent the government the money interest-"
            "free; owing means you underpaid.\n\n"
            "A large refund isn't a windfall, it's a sign to adjust the W-4 so more arrives each month "
            "— money that could have been in the plan all year. Withholding is also where a raise, a "
            "second job, or big investment income can catch people out, because the estimate doesn't "
            "know about them. Aiming for a small refund or a small bill is the goal."
        ),
        "related": ["gross_vs_net", "fica_explained", "marginal_vs_effective"],
        "glossary_terms": ["take_home"],
    },
    "budgeting_50_30_20": {
        "question": "What is the 50/30/20 budget?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["50/30/20", "50 30 20", "budget rule", "how to budget", "budgeting", "how much should i spend on rent",
                     "needs wants savings", "simple budget", "budget percentages", "how much should i save each month"],
        "summary": "Half of take-home for needs, 30% for wants, 20% for saving and debt — a starting shape, not a law.",
        "detail": (
            "The 50/30/20 rule splits after-tax income three ways: 50% to needs (rent, groceries, "
            "utilities, minimum debt payments), 30% to wants (everything optional), and 20% to saving "
            "and extra debt payoff. Its value is that it's simple enough to actually use, and it puts "
            "saving in the budget rather than leaving it to whatever's left.\n\n"
            "Treat the numbers as a starting point. In an expensive city, needs can be 60% and the "
            "adjustment comes from wants. For an ambitious retirement date, the 20% is the number to "
            "push — the savings rate is what moves the date most. What matters is that the saving is "
            "automatic and comes out first, which is what the schedule here is built to make happen."
        ),
        "related": ["savings_rate_explained", "gross_vs_net", "lifestyle_creep"],
        "glossary_terms": ["savings_rate", "take_home"],
    },
    "savings_rate_explained": {
        "question": "What savings rate do I need?",
        "topic": "Income and planning", "level": "intermediate",
        "keywords": ["savings rate", "what percent should i save", "how much to save for retirement", "15% rule", "save 15%",
                     "is saving 10% enough", "is saving 15% enough", "saving 10% of my income", "saving 20%",
                     "save 10%", "percent of income to save", "is 10% enough", "how much should i be saving", "savings percentage",
                     "what savings rate to retire early"],
        "summary": "Around 15% of income for a normal retirement age; the rate, not the return, is what moves the date.",
        "detail": (
            "Saving 15% of gross income from your twenties, invested in index funds, has historically "
            "been enough to retire around 65 at a similar standard of living. Starting later needs more "
            "— 20–25% from the mid-thirties — because the years of compounding are fewer. Include any "
            "employer match in the 15%.\n\n"
            "The reason to think in a percentage is that it travels: 15% means the same thing on any "
            "salary and rises with a raise automatically, which is why the plan lets you enter saving "
            "as a share of pay. And it's the lever that matters. A higher return is hoped for; a higher "
            "savings rate is chosen. Going from 10% to 20% moves a retirement date by roughly a decade; "
            "no fund choice comes close."
        ),
        "facts": [{"label": "Rough rate to retire at 65, starting at 25", "value": "15% of gross"},
                  {"label": "Starting at 35", "value": "about 20–25%"},
                  {"label": "Retiring in your 40s", "value": "50% or more"}],
        "related": ["budgeting_50_30_20", "compound_interest", "safe_withdrawal_rate", "lifestyle_creep"],
        "glossary_terms": ["savings_rate"],
    },
    "lifestyle_creep": {
        "question": "What is lifestyle creep?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["lifestyle creep", "lifestyle inflation", "spending rises with income", "got a raise but no more savings",
                     "where does my money go", "earn more save nothing", "keeping up", "save half of every raise"],
        "summary": "Spending that rises to meet every raise — the reason higher earners are often no closer to retiring.",
        "detail": (
            "Each raise brings a slightly nicer apartment, car, restaurant — and a year later the "
            "budget is exactly as tight as it was. That's lifestyle creep, and it's why income and "
            "wealth are so loosely connected: someone on $60,000 saving 20% is further ahead than "
            "someone on $150,000 saving 3%.\n\n"
            "The defence is to decide before the raise lands. A common rule is to direct half of every "
            "raise into saving and enjoy the other half, which lifts the savings rate every year while "
            "life still gets better. A percent-of-pay savings plan does part of this by itself, since "
            "the dollar amount rises with income. The scenario version of this — \"what if I saved an "
            "extra $200 a month\" — shows what each decision is worth."
        ),
        "related": ["savings_rate_explained", "budgeting_50_30_20"],
        "glossary_terms": ["savings_rate"],
    },
    "net_worth": {
        "question": "What is net worth, and should I track it?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["net worth", "how to calculate net worth", "assets minus liabilities", "negative net worth", "track net worth",
                     "what should my net worth be", "net worth by age", "am i on track"],
        "summary": "Everything you own minus everything you owe — the one number that shows the whole picture.",
        "detail": (
            "Add up what you own — cash, investments, retirement accounts, home equity — and subtract "
            "what you owe — cards, loans, mortgage. That's net worth. Negative is normal early on with "
            "student loans; the direction of travel matters more than the level. Checking it once a "
            "quarter is plenty.\n\n"
            "It's the right scoreboard because it's immune to the usual confusions: a raise spent is "
            "invisible to it, a debt paid down shows up exactly as much as an investment made. The "
            "rough benchmarks people quote — one times salary saved by 30, three times by 40 — are "
            "loose, but they point the right way. The plan's projection is the forward-looking version "
            "of the same number."
        ),
        "related": ["savings_rate_explained", "good_vs_bad_debt"],
        "glossary_terms": [],
    },
    "pay_frequency": {
        "question": "Does how often I'm paid change anything?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["paid biweekly", "paid twice a month", "pay frequency", "26 paychecks", "three paycheck month",
                     "semimonthly vs biweekly", "budget by paycheck", "per paycheck savings", "how much per paycheck"],
        "summary": "Biweekly means 26 checks a year, not 24 — two months a year have a third paycheck that's easy to save.",
        "detail": (
            "Paid every two weeks, you get 26 paychecks; twice a month, 24. The difference is two "
            "\"extra\" checks a year on the biweekly schedule, landing in whichever months have three "
            "Fridays. Budgets built on two checks a month treat those as found money — which makes "
            "them the easiest saving most people will ever do.\n\n"
            "It also changes the unit a plan should be written in. \"$300 a month\" is fuzzy on a "
            "biweekly schedule; \"$138 a paycheck\" is a standing transfer you set once. The schedule "
            "here converts everything into per-paycheck figures for that reason, and treats a 401(k) "
            "deferral as a percentage, since that's the box you fill in at work."
        ),
        "related": ["gross_vs_net", "budgeting_50_30_20"],
        "glossary_terms": ["take_home", "payroll_deferral"],
    },
    "what_to_do_with_a_raise": {
        "question": "I got a raise — what should I do with it?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["got a raise", "what to do with a raise", "new higher salary", "promotion money", "just got promoted",
                     "more money what now", "salary went up", "how to use a raise"],
        "summary": "Send at least half of it to the plan before you get used to it — then let the scenario show what that's worth.",
        "detail": (
            "The best moment to raise your savings rate is the payday before you notice the new "
            "number. Bump the 401(k) percentage, raise the IRA transfer, then enjoy the rest guilt-"
            "free. Half-to-savings is the usual rule; if you were already saving enough, the whole "
            "raise into the plan pulls the retirement date forward fast.\n\n"
            "Two mechanical things to check. A higher income can change your Roth IRA eligibility — "
            "the personal question \"can I contribute to a Roth\" re-checks it. And withholding may not "
            "keep pace, so the first tax return after a big raise can surprise you. Ask \"what if I "
            "made $X\" here and the plan re-runs your limits, eligibility and projection at the new "
            "figure."
        ),
        "related": ["lifestyle_creep", "savings_rate_explained", "paycheck_withholding"],
        "glossary_terms": ["savings_rate", "magi"],
    },
    "side_income": {
        "question": "What should I do with side income?",
        "topic": "Income and planning", "level": "intermediate",
        "keywords": ["side income", "side hustle", "freelance money", "extra income", "second job", "gig work", "uber income",
                     "etsy income", "what to do with side hustle money", "1099 side gig"],
        "summary": "Set aside a third for tax, then treat the rest as raise money — and know it opens a solo 401(k).",
        "detail": (
            "Side income arrives without tax withheld, so the first move is to put roughly 25–30% of "
            "it aside for federal, state and self-employment tax, and pay estimated tax quarterly once "
            "it's more than a few thousand a year. What's left is exactly like a raise: the more of it "
            "that goes to the plan before it becomes lifestyle, the better.\n\n"
            "It also unlocks accounts a W-2 job doesn't. Any self-employment income lets you open a "
            "solo 401(k) or SEP-IRA for that income alone, on top of your workplace plan — a "
            "substantial extra tax-advantaged space for someone whose day-job 401(k) is already full. "
            "Track the income and expenses from day one; it makes the tax side painless."
        ),
        "related": ["w2_vs_1099", "what_to_do_with_a_raise", "paycheck_withholding"],
        "glossary_terms": ["401k"],
    },
    "employer_match_deep": {
        "question": "How does an employer match work, and what is a true-up?",
        "topic": "Income and planning", "level": "basic",
        "keywords": ["employer match", "how does 401k match work", "50% up to 6%", "match formula", "get the full match",
                     "am i getting my match", "company match explained", "true up", "front loading 401k lose match",
                     "match per paycheck", "free money 401k"],
        "summary": "Free money added when you contribute — set your deferral to at least the matched percentage, spread across every paycheck.",
        "detail": (
            "A typical formula is \"50% of contributions up to 6% of pay\": put in 6% and your employer "
            "adds 3%, an instant 50% return before the money has earned anything. Put in 4% and you "
            "get 2% — you've left a third of the free money on the table. It's the single best return "
            "available anywhere, which is why capturing it is step 2 of the plan, ahead of paying off "
            "even expensive debt.\n\n"
            "One trap: most plans match per paycheck. Max out the 401(k) by June and you contribute "
            "nothing in July to December — and get no match for those months either, unless the plan "
            "has a \"true-up\". That's why the schedule here paces 401(k) money evenly across the year "
            "rather than front-loading it. Check your vesting schedule too; unvested match is forfeited "
            "if you leave early."
        ),
        "facts": [{"label": "50% up to 6%, on $80,000", "value": "$4,800 in, $2,400 free"},
                  {"label": "Contributing only 3%", "value": "$2,400 in, $1,200 free — half of it missed"}],
        "related": ["vesting_explained", "when_debt_beats_investing", "contribution_limits_deep"],
        "glossary_terms": ["employer_match", "vesting", "payroll_deferral"],
    },
    "contribution_limits_deep": {
        "question": "How do contribution limits work across accounts?",
        "topic": "Income and planning", "level": "intermediate",
        "keywords": ["contribution limits", "how do limits work", "separate limits", "combined limit", "401k and ira same year",
                     "can i max both", "over contributed", "excess contribution", "limit per person or per plan",
                     "two jobs 401k limit", "does the match count toward the limit"],
        "summary": "Each account type has its own limit; the match doesn't count against yours; two jobs share one 401(k) limit.",
        "detail": (
            "The 401(k), IRA and HSA limits are separate pots — filling one doesn't use up another, "
            "and you can max all three in the same year. Within the IRA, traditional and Roth share "
            "one combined limit. The employer match sits outside your 401(k) limit entirely, under a "
            "much higher overall cap that almost nobody hits.\n\n"
            "Two things people get wrong. The 401(k) limit is per *person*, not per plan, so two jobs "
            "in one year still share one allowance, and it's your job to keep the total under it. And "
            "the IRA limit is capped at earned income — a student who earned $3,000 can put in $3,000, "
            "not the statutory figure. Over-contribute and you file to pull the excess back out, with "
            "a penalty if you don't. The exact numbers are in the year's data file and the \"how much "
            "can I put in\" question applies them to you."
        ),
        "related": ["catch_up_contributions", "employer_match_deep", "w2_vs_1099"],
        "glossary_terms": ["contribution_limit", "catch_up", "employer_match"],
    },

    # =========================================================================
    # Health accounts and adjacent
    # =========================================================================

    "hdhp_explained": {
        "question": "What is a high-deductible health plan, and should I pick one?",
        "topic": "Health accounts and adjacent", "level": "basic",
        "keywords": ["hdhp", "high deductible health plan", "high deductible plan", "should i pick the hdhp", "ppo vs hdhp",
                     "open enrollment which plan", "cheaper premium higher deductible", "health plan choice", "hsa eligible plan"],
        "summary": "A plan with a lower premium and a higher deductible — it's the only kind that unlocks an HSA.",
        "detail": (
            "A high-deductible health plan charges less each month and more before coverage kicks in: "
            "the deductible is at least a few thousand dollars. In exchange, and only with this kind of "
            "plan, you can open a Health Savings Account, the best-taxed account that exists.\n\n"
            "Whether it's right depends on your health spending. For someone young and healthy who "
            "rarely sees a doctor, the lower premium plus the HSA usually wins clearly — and many "
            "employers put money into the HSA too. For someone with regular prescriptions or a "
            "planned surgery, a traditional plan's lower out-of-pocket ceiling can cost less overall. "
            "Compare the worst-case total for the year — premiums plus the out-of-pocket maximum — "
            "not just the premium."
        ),
        "related": ["deductibles_explained", "hsa_vs_fsa", "hsa_as_retirement_account"],
        "glossary_terms": ["hdhp", "hsa"],
    },
    "deductibles_explained": {
        "question": "What's the difference between a deductible, copay and out-of-pocket maximum?",
        "topic": "Health accounts and adjacent", "level": "basic",
        "keywords": ["deductible", "copay", "coinsurance", "out of pocket maximum", "out-of-pocket max", "how does a deductible work",
                     "what do i pay at the doctor", "health insurance terms", "premium vs deductible"],
        "summary": "Deductible is what you pay first; copays and coinsurance are your share after; the out-of-pocket max is the ceiling.",
        "detail": (
            "The premium is the monthly cost of having the plan. The deductible is what you pay out of "
            "pocket for care before the insurance pays anything — say the first $3,000 in a year. After "
            "that, you pay a copay (a fixed $30 per visit) or coinsurance (a fixed share, like 20%) and "
            "the plan pays the rest. The out-of-pocket maximum is the most you can pay in a year, all in; "
            "past it, the plan pays 100%.\n\n"
            "That maximum is the number to plan around: it's the worst case, and an emergency fund "
            "should be able to cover it. Preventive care — check-ups, vaccines — is usually free before "
            "the deductible on any plan. An HSA is designed to hold exactly the money that would go "
            "toward the deductible, tax-free."
        ),
        "related": ["hdhp_explained", "emergency_fund_sizing", "hsa_vs_fsa"],
        "glossary_terms": ["hdhp"],
    },
    "hsa_vs_fsa": {
        "question": "What's the difference between an HSA and an FSA?",
        "topic": "Health accounts and adjacent", "level": "basic",
        "keywords": ["hsa vs fsa", "fsa", "flexible spending account", "use it or lose it", "fsa vs hsa", "which is better hsa or fsa",
                     "can i have both hsa and fsa", "dependent care fsa", "limited purpose fsa"],
        "summary": "An HSA is yours forever and can be invested; an FSA is use-it-or-lose-it within the year.",
        "detail": (
            "Both let you pay medical costs with pre-tax money. The FSA is the older, weaker version: "
            "you set an amount at open enrollment, it's taken from pay, and whatever you don't spend by "
            "the year's end — beyond a small carryover — is forfeited. It doesn't require a particular "
            "health plan, and it's fine for predictable costs like glasses.\n\n"
            "The HSA needs a high-deductible plan and is a different animal: the money is yours "
            "permanently, rolls over forever, moves with you between jobs, can be invested, and grows "
            "and comes out untaxed for medical costs. You generally can't hold both, except a "
            "\"limited-purpose\" FSA for dental and vision alongside an HSA. If you're eligible for an "
            "HSA, it's not a close call."
        ),
        "related": ["hdhp_explained", "hsa_as_retirement_account", "deductibles_explained"],
        "glossary_terms": ["hsa", "hdhp"],
    },
    "hsa_as_retirement_account": {
        "question": "Why do people call the HSA a secret retirement account?",
        "topic": "Health accounts and adjacent", "level": "intermediate",
        "keywords": ["hsa retirement", "invest my hsa", "hsa triple tax", "triple tax advantage", "hsa after 65", "hsa as ira",
                     "pay medical out of pocket and save receipts", "hsa reimbursement later", "should i invest hsa",
                     "hsa stealth ira", "best account"],
        "summary": "Untaxed in, untaxed growing, untaxed out for medical — and after 65 it works like a traditional IRA for anything.",
        "detail": (
            "No other account is untaxed at all three stages. Contributions skip income tax *and* "
            "payroll tax when made through work; the balance can be invested and grows untaxed; and "
            "withdrawals for medical costs are untaxed at any age. After 65, withdrawals for anything "
            "else are simply taxed as income, like a traditional IRA — with no penalty — so the "
            "downside of over-saving in it is nil.\n\n"
            "The strategy that follows: contribute the max, invest it rather than leaving it in cash, "
            "pay today's medical bills from your regular money, and keep the receipts. There's no "
            "deadline on reimbursing yourself, so decades later you can withdraw the total of every "
            "receipt tax-free. Medical costs in retirement are large and this is the best way to "
            "pre-fund them, which is why the HSA sits at step 4, ahead of the IRA."
        ),
        "related": ["hsa_vs_fsa", "hdhp_explained", "medicare_gap", "tax_advantaged_vs_taxable"],
        "glossary_terms": ["hsa", "medicare"],
    },
    "term_vs_whole_life": {
        "question": "Term or whole life insurance?",
        "topic": "Health accounts and adjacent", "level": "basic",
        "keywords": ["life insurance", "term life", "whole life", "term vs whole life", "do i need life insurance", "universal life",
                     "is whole life a good investment", "is whole life insurance worth it", "whole life as an investment",
                     "life insurance as investment", "cash value", "how much life insurance", "permanent life insurance",
                     "iul", "indexed universal life"],
        "summary": "Term, almost always — cheap cover for the years someone depends on you; whole life is expensive and a poor investment.",
        "detail": (
            "Term life pays out if you die within the term — twenty or thirty years — and costs "
            "surprisingly little for a healthy thirty-year-old. Its job is to replace your income for "
            "the people who depend on it while they do: young children, a mortgage, a partner. If nobody "
            "depends on your income, you don't need it yet.\n\n"
            "Whole life, universal life and their variants bundle a much more expensive policy with a "
            "savings component, and are sold hard because the commissions are large. The savings part "
            "grows slowly and carries heavy fees; you'd nearly always do better buying term and "
            "investing the difference in the accounts this plan already orders. The honest rule: "
            "insurance for protection, investments for growth, and never the two in one product."
        ),
        "related": ["disability_insurance_basics", "what_insurance_is_for"],
        "glossary_terms": [],
    },
    "disability_insurance_basics": {
        "question": "Do I need disability insurance?",
        "topic": "Health accounts and adjacent", "level": "intermediate",
        "keywords": ["disability insurance", "long term disability", "short term disability", "income protection",
                     "what if i can't work", "ltd", "own occupation", "disability through work"],
        "summary": "Probably — your income is your biggest asset, and losing it to illness is far likelier than dying young.",
        "detail": (
            "A working adult is several times more likely to be unable to work for a year or more "
            "before 65 than to die before it. Disability insurance replaces a share of your income — "
            "typically 60% — if that happens. Many employers provide some long-term disability cover; "
            "check what it pays, for how long, and whether the premium is paid pre-tax (which makes "
            "the benefit taxable).\n\n"
            "If work provides little or none, an individual policy is worth pricing, especially for "
            "anyone whose household depends on one income. Look for \"own occupation\" cover, which "
            "pays if you can't do *your* job rather than any job. It's the least glamorous insurance "
            "and, after health, the most important — a plan that assumes forty years of earnings needs "
            "something protecting those earnings."
        ),
        "related": ["term_vs_whole_life", "what_insurance_is_for", "emergency_fund_sizing"],
        "glossary_terms": [],
    },
    "what_insurance_is_for": {
        "question": "What is insurance actually for, and what shouldn't I insure?",
        "topic": "Health accounts and adjacent", "level": "basic",
        "keywords": ["what insurance do i need", "insurance basics", "extended warranty", "phone insurance", "too much insurance",
                     "self insure", "which insurance is worth it", "renters insurance", "umbrella policy", "insurance i don't need"],
        "summary": "Insure against losses you couldn't absorb; self-insure the rest with your emergency fund.",
        "detail": (
            "Insurance transfers a risk you can't afford to someone who can pool it, and charges you "
            "more than the expected loss for the privilege. So it's worth it for catastrophes — a "
            "medical crisis, your house burning down, being sued, dying while your kids are small — "
            "and a bad deal for anything you could cover from savings. Extended warranties, phone "
            "insurance and travel add-ons are almost always the second kind.\n\n"
            "The list most people need: health, auto liability, renters or homeowners, term life if "
            "anyone depends on your income, and disability. An umbrella policy adds cheap liability "
            "cover once you have assets to protect. Raise the deductibles on all of them to what the "
            "emergency fund could pay — the premium savings are real, and the fund is what it's for."
        ),
        "related": ["term_vs_whole_life", "disability_insurance_basics", "emergency_fund_sizing"],
        "glossary_terms": ["emergency_fund"],
    },
    "what_is_taxable_account": {
        "question": "When should I open a taxable brokerage account?",
        "topic": "Investing basics", "level": "basic",
        "keywords": ["taxable brokerage", "taxable account", "when to open a brokerage account", "regular investment account",
                     "individual brokerage", "non retirement account", "invest outside retirement accounts",
                     "should i open a brokerage", "after maxing 401k and ira", "ive maxed my 401k and ira now what",
                     "maxed out everything now what", "what comes after maxing out", "maxed my retirement accounts"],
        "summary": "After the tax-advantaged accounts are full — or earlier if you'll need the money before 59½.",
        "detail": (
            "A taxable brokerage account is an ordinary investment account: no limit, no age rules, no "
            "tax break. You owe tax on dividends yearly and gains when you sell. It's step 7 of the "
            "plan, after everything with a tax advantage — but it isn't a consolation prize. It's where "
            "an early retiree's bridge money lives, where a house deposit five years out can sit, and "
            "where saving continues once the sheltered accounts are full.\n\n"
            "Hold broad stock index funds in it, since they're the most tax-efficient thing to own "
            "there, and hold them for over a year before selling to get the long-term gains rate. For "
            "most people it becomes relevant in their thirties; for a high earner or an early retiree, "
            "sooner. Same brokerages, same funds as the IRA — just a different wrapper."
        ),
        "related": ["tax_advantaged_vs_taxable", "capital_gains_short_vs_long", "tax_drag", "early_retirement_bridge"],
        "glossary_terms": ["taxable_brokerage", "capital_gains"],
    },
}

TOPIC_ORDER = [
    "Investing basics",
    "Retirement mechanics",
    "Taxes",
    "Debt and credit",
    "Cash and banking",
    "Income and planning",
    "Health accounts and adjacent",
]


# =============================================================================
# Declines — questions the app deliberately doesn't answer
# =============================================================================
# Two kinds. By design: things that would cross from education into direction, or
# need a professional. By capability: things that need live data we don't have.
# Both answer usefully — say why, and say what we *can* do instead.

DECLINES: dict[str, dict] = {
    "security_selection": {
        "kind": "design",
        "keywords": ["should i buy", "should i sell", "is it a good stock", "good stock", "which stock", "what stock",
                     "hot stock", "best stock", "stock pick", "stock tip", "buy nvidia", "buy tesla", "buy apple",
                     "buy amazon", "buy google", "buy microsoft", "nvda", "tsla", "aapl", "is bitcoin a good investment",
                     "should i buy bitcoin", "buy crypto", "invest in crypto", "dogecoin", "ethereum", "which coin",
                     "meme stock", "gamestop", "options trading", "day trading", "penny stocks", "what should i buy",
                     "best investment right now", "what's going to go up", "next big stock"],
        "summary": "This app explains how accounts and rules work — it doesn't pick investments.",
        "detail": (
            "Naming a stock or a coin to buy is investment advice, and it's a line this app stays on "
            "the educational side of on purpose: partly because personalised buy/sell direction is a "
            "regulated activity, and partly because nobody reliably picks winners, which is the whole "
            "argument for index funds. What it can do is show what a diversified, low-cost fund is, why "
            "single-company bets carry the risk they do, and how any money you have should flow through "
            "your accounts. If you're deciding between a specific stock and an index fund, the "
            "diversification entry is the honest version of that conversation."
        ),
        "redirect": ["what_to_invest_in", "index_funds_explained", "diversification"],
    },
    "market_prediction": {
        "kind": "design",
        "keywords": ["will the market crash", "is the market going to crash", "when will the market crash", "is a recession coming",
                     "what will the market do", "predict the market", "where is the market headed", "will stocks go up",
                     "will stocks go down", "is a crash coming", "what will interest rates do", "will rates go down",
                     "when will rates drop", "market forecast", "will there be a recession", "is the bubble going to pop"],
        "summary": "Nobody can predict the market — and the plan doesn't need anyone to.",
        "detail": (
            "No one — not economists, not fund managers, not this app — has a reliable record of "
            "calling crashes or recoveries in advance, and pretending otherwise would be the most "
            "harmful thing an app like this could do. The good news is that the plan doesn't depend on "
            "a forecast: it assumes the long-run average with three scenarios around it, and the "
            "advice is the same in a boom or a bust — keep the emergency fund, capture the match, keep "
            "contributing. What it *can* tell you is what to do when a crash arrives, and why waiting "
            "for one usually costs more than it saves."
        ),
        "redirect": ["market_timing", "bear_and_bull_markets", "dollar_cost_averaging"],
    },
    "tax_filing": {
        "kind": "design",
        "keywords": ["how do i file my taxes", "file my taxes", "which tax form", "what form do i need", "turbotax", "free file",
                     "do my taxes", "tax return help", "fill out my w-4", "how do i fill out", "amend my return", "irs letter",
                     "audit", "tax software", "do i need an accountant", "cpa", "claim my kid", "dependent on taxes",
                     "can i deduct my", "write off", "tax deduction for"],
        "summary": "Filing a return is a job for tax software or a preparer — this app explains the concepts underneath it.",
        "detail": (
            "How to fill in a form, which deductions you personally qualify for, and what to do about a "
            "letter from the IRS all depend on details of your return this app doesn't have, and getting "
            "them wrong has consequences. Free File, commercial software, or a preparer are the right "
            "tools. What this app does well is the concepts that tax software assumes you know: how "
            "brackets work, what marginal versus effective means, why a traditional contribution lowers "
            "your bill now and a Roth one doesn't, and how withholding produces a refund."
        ),
        "redirect": ["tax_brackets_explained", "marginal_vs_effective", "paycheck_withholding"],
    },
    "legal_estate": {
        "kind": "design",
        "keywords": ["do i need a will", "write a will", "trust", "living trust", "estate planning", "power of attorney",
                     "beneficiary", "who inherits", "probate", "divorce", "prenup", "bankruptcy", "should i file bankruptcy",
                     "lawsuit", "sue", "legal advice", "lawyer", "custody", "inheritance tax", "estate tax"],
        "summary": "Wills, trusts, divorce and bankruptcy are legal questions — a lawyer's, not a planner's.",
        "detail": (
            "Anything that turns on your state's law and your family's situation — wills, trusts, "
            "beneficiary designations, divorce, bankruptcy — needs someone licensed to advise on it, "
            "and the cost of a mistake is high. This app deliberately stays with the financial "
            "mechanics. Two things it can usefully say: retirement accounts pass by their beneficiary "
            "form regardless of a will, so it's worth checking those forms are current; and if debt "
            "is severe enough that bankruptcy is on the table, the debt entries here explain the "
            "interest mechanics but not the legal route."
        ),
        "redirect": ["good_vs_bad_debt", "rollovers"],
    },
    "insurance_product": {
        "kind": "design",
        "keywords": ["which insurance company", "best life insurance company", "which policy should i buy", "get a quote",
                     "insurance quote", "northwestern mutual", "state farm", "geico", "should i buy this policy",
                     "annuity", "should i buy an annuity", "fixed annuity", "variable annuity", "indexed annuity"],
        "summary": "Choosing a specific policy or annuity is a product recommendation — this app explains what the products are for.",
        "detail": (
            "Which company, which policy, and whether the one being sold to you is a good deal are "
            "product decisions this app doesn't make. What it can do is explain the shape: what term "
            "and whole life are and why term usually wins, what disability cover is for, and how to "
            "think about which risks are worth insuring at all. Annuities in particular are complex, "
            "high-commission products that sometimes make sense for someone already retired and "
            "rarely for anyone still saving — worth an independent, fee-only adviser's eye before "
            "signing."
        ),
        "redirect": ["term_vs_whole_life", "disability_insurance_basics", "what_insurance_is_for"],
    },
    "personal_directive": {
        "kind": "design",
        "keywords": ["what should i do with my life", "should i quit my job", "should i buy a house", "should i rent or buy",
                     "should i move", "should i go to grad school", "should i have kids", "should i get married",
                     "should i take this job", "buy a house or invest", "is now a good time to buy a house", "should i buy a car",
                     "lease or buy"],
        "summary": "The big life decisions are yours — but the plan can show you what each one does to the numbers.",
        "detail": (
            "Whether to buy a house, change careers or go back to school depends on far more than "
            "money, and this app won't pretend the spreadsheet decides. What it can do is make the "
            "financial side concrete so it's one clear input rather than a fog: ask what a different "
            "income does to the plan, what a lump sum for a deposit does, what retiring at a different "
            "age looks like, or what carrying a particular debt costs. Those scenarios run on your real "
            "numbers and show the trade-off in dollars and years, which is the part a planner can "
            "honestly contribute."
        ),
        "redirect": ["net_worth", "sinking_funds", "safe_withdrawal_rate"],
    },
    "live_data": {
        "kind": "capability",
        "keywords": ["what is the s&p at", "current price", "price of", "stock price", "how is the market today", "market today",
                     "current mortgage rates", "today's rates", "current interest rate", "fed rate", "what are rates right now",
                     "current cd rates", "best savings rate right now", "what's bitcoin at", "gold price", "exchange rate",
                     "how did the market do", "is the market up today", "dow jones today"],
        "summary": "There's no live market data here — the plan runs on your numbers and long-run assumptions, not today's prices.",
        "detail": (
            "This app doesn't connect to market feeds, so it can't tell you a price, an index level or "
            "today's mortgage rate; any figure it quoted would be stale or invented. That's deliberate: "
            "nothing in the plan depends on where the market is this afternoon. It uses long-run "
            "return assumptions you can change, the IRS limits for the year, and the balances and rates "
            "you've entered. For a rate or a price, your brokerage, bank or a news site has the live "
            "number — and the entries here explain what to do with it once you have it."
        ),
        "redirect": ["market_timing", "high_yield_savings", "apr_vs_apy"],
    },
    "plan_documents": {
        "kind": "capability",
        "keywords": ["what does my plan allow", "does my 401k allow", "my plan's rules", "my employer's plan", "what funds are in my 401k",
                     "my plan document", "does my company match", "does my company do a true up", "does my employer do a true up",
                     "does my employer match", "what does my company offer", "what's my vesting schedule", "check my benefits",
                     "what does my policy cover", "read my statement", "look at my account", "log into my", "my balance at fidelity"],
        "summary": "Your plan's specific rules live in its documents — this app can't read them, but it can tell you what to look for.",
        "detail": (
            "Whether your 401(k) allows after-tax contributions, what its vesting schedule is, which "
            "funds it offers, whether it has a true-up on the match — all of that is in your plan's "
            "summary document and benefits portal, and none of it is visible from here. What this app "
            "can do is tell you which questions matter and why: what a true-up is and why it changes "
            "how you pace contributions, what vesting means for when to leave, what an expense ratio "
            "is so you can judge the fund menu. Enter what you find on the Accounts page and the plan "
            "uses it."
        ),
        "redirect": ["employer_match_deep", "vesting_explained", "expense_ratios"],
    },
}


# --- public helpers ------------------------------------------------------------


def get(key: str) -> dict:
    entry = ENTRIES.get(key)
    if entry is None:
        raise KeyError(key)
    return {"key": key, **entry}


def index() -> list[dict]:
    """Grouped by topic in a deliberate order — the browse surface, mirroring qa.index()."""
    return [
        {
            "topic": topic,
            "entries": [
                {"key": key, "question": e["question"], "level": e["level"]}
                for key, e in ENTRIES.items()
                if e["topic"] == topic
            ],
        }
        for topic in TOPIC_ORDER
    ]
