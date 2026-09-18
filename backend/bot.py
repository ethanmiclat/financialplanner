"""Free-text questions, answered without a language model.

Why pattern-matching rather than an LLM or embeddings: this app's whole design is that
every number is traceable to a rule. A model that composes answers can compose a
contribution limit that doesn't exist, and in a finance app that's the failure that
matters. So the bot never writes an answer — it *selects* one. Personal questions go to
`qa.py`, general ones to `knowledge.py`, and questions that carry a number of their own
("my 35K of student debt") go to `scenario.py`, which runs the engine on a copy. This
module only decides which, and how confident it is.

The confidence is part of the contract. Below a threshold the bot says "did you mean"
rather than guessing, and when an intent is clear but a number is missing it asks for
the number. An honest "I don't have that one" beats a fluent wrong answer.

Everything here is standard library. The matcher is IDF-weighted overlap on unigrams
and bigrams, with a hand-built alias map doing most of the real work — match quality
is almost entirely a property of that map, not the arithmetic.
"""

from __future__ import annotations

import difflib
import math
import re
from dataclasses import asdict

import content
import knowledge
import limits as L
import qa
import scenario
import slots as S
from models import User

STRONG = 0.55
WEAK = 0.25

# --- normalisation -------------------------------------------------------------

_CONTRACTIONS = {
    "what's": "what is", "whats": "what is", "how's": "how is", "hows": "how is",
    "where's": "where is", "who's": "who is", "that's": "that is", "there's": "there is",
    "it's": "it is", "i'm": "i am", "im": "i am", "i've": "i have", "ive": "i have",
    "i'd": "i would", "i'll": "i will", "can't": "cannot", "cant": "cannot",
    "won't": "will not", "wont": "will not", "don't": "do not", "dont": "do not",
    "doesn't": "does not", "doesnt": "does not", "isn't": "is not", "isnt": "is not",
    "shouldn't": "should not", "wouldn't": "would not", "couldn't": "could not",
    "didn't": "did not", "gonna": "going to", "wanna": "want to", "gotta": "got to",
    "u": "you", "ur": "your", "r": "are", "y": "why", "pls": "please", "plz": "please",
    "thx": "thanks", "ty": "thanks", "k": "ok", "b4": "before", "w/": "with", "w/o": "without",
    "&": "and", "+": "and", "vs": "versus", "vs.": "versus", "v.": "versus",
}

# Tokens that carry meaning as a unit and would be shredded by punctuation stripping.
_COMPOUNDS = [
    (r"401\s*\(\s*k\s*\)|401-k|401 k\b|four\s*o\s*one\s*k|four-oh-one-k|4o1k", "401k"),
    (r"403\s*\(\s*b\s*\)|403-b|403 b\b", "403b"),
    (r"457\s*\(\s*b\s*\)|457 b\b|457\b", "457b"),
    (r"72\s*\(\s*t\s*\)", "72t"),
    (r"s\s*&\s*p\s*500|s&p|sp\s*500|s and p 500|snp 500|sandp", "sp500"),
    (r"59\s*(?:½|1/2|and a half|\.5)", "59half"),
    (r"50\s*/\s*30\s*/\s*20|50-30-20|50 30 20", "fiftythirtytwenty"),
    (r"\b4\s*%\s*rule|4 percent rule|four percent rule", "fourpercentrule"),
    (r"\bw-?4\b", "w4"),
    (r"\bw-?2\b", "w2"),
    (r"\b1099s?\b", "1099"),
    (r"\bhigh[- ]yield\b", "highyield"),
    (r"\btarget[- ]date\b", "targetdate"),
    (r"\bdollar[- ]cost[- ]averag\w*", "dca"),
    (r"\bpre[- ]tax\b", "pretax"),
    (r"\bpost[- ]tax\b|\bafter[- ]tax\b", "posttax"),
    (r"\btax[- ]loss\b", "taxloss"),
    (r"\btax[- ]advantaged\b", "taxadvantaged"),
    (r"\bout[- ]of[- ]pocket\b", "outofpocket"),
    (r"\bside[- ]hustle\b", "sidehustle"),
    (r"\blump[- ]sum\b", "lumpsum"),
    (r"\bset[- ]and[- ]forget\b", "setandforget"),
    (r"\ball[- ]time[- ]high\b", "alltimehigh"),
    (r"\bcatch[- ]up\b", "catchup"),
    (r"\bback[- ]?door\b", "backdoor"),
    (r"\bphase[- ]?out\b", "phaseout"),
    (r"\btake[- ]home\b", "takehome"),
    (r"\bpay[- ]?check\b", "paycheck"),
    (r"\bmoney[- ]market\b", "moneymarket"),
    (r"\bbi[- ]weekly\b", "biweekly"),
    (r"\bsemi[- ]monthly\b", "semimonthly"),
    (r"\bmid[- ]cap\b", "midcap"), (r"\bsmall[- ]cap\b", "smallcap"), (r"\blarge[- ]cap\b", "largecap"),
    (r"\bex[- ]us\b", "exus"),
    (r"\bt[- ]bills?\b", "tbill"),
    (r"\bre[- ]?fi\b", "refinance"),
]
_COMPOUND_RES = [(re.compile(p, re.IGNORECASE), t) for p, t in _COMPOUNDS]

# Surface phrases → one canonical token. Applied longest-first so "roth ira" beats "ira".
# Both the query and every corpus entry pass through this, so the two sides agree.
ALIASES: dict[str, str] = {
    # accounts
    "work retirement plan": "401k", "workplace retirement plan": "401k", "workplace plan": "401k",
    "employer plan": "401k", "employer retirement plan": "401k", "work plan": "401k",
    "retirement plan at work": "401k", "my job's retirement": "401k", "job retirement account": "401k",
    "thrift savings plan": "401k", "tsp": "401k", "solo 401k": "solo401k", "roth 401k": "roth401k",
    "individual retirement account": "ira", "individual retirement arrangement": "ira",
    "roth ira": "rothira", "traditional ira": "tradira", "sep ira": "sepira", "simple ira": "ira",
    "health savings account": "hsa", "health savings": "hsa",
    "flexible spending account": "fsa", "flex spending": "fsa",
    "taxable brokerage account": "taxable", "taxable brokerage": "taxable", "taxable account": "taxable",
    "brokerage account": "brokerage", "regular investment account": "taxable",
    "non retirement account": "taxable", "individual brokerage": "taxable",
    "savings account": "savingsaccount", "checking account": "checking",
    "high yield savings account": "hysa", "highyield savings account": "hysa", "highyield savings": "hysa",
    "online savings account": "hysa", "online savings": "hysa",
    "certificate of deposit": "cd", "certificates of deposit": "cd",
    "money market fund": "moneymarket", "settlement fund": "moneymarket", "core position": "moneymarket",
    "health plan": "healthplan", "high deductible health plan": "hdhp", "high deductible plan": "hdhp",
    "high deductible": "hdhp",
    # match
    "employer match": "match", "company match": "match", "employer matching": "match",
    "401k match": "match", "matching contribution": "match", "matching contributions": "match",
    "free money from work": "match", "free money": "match", "the match": "match", "my match": "match",
    "full match": "match", "get the match": "match", "leaving match": "match",
    # funds
    "index fund": "indexfund", "index funds": "indexfund", "passive fund": "indexfund",
    "passive investing": "indexfund", "total market fund": "indexfund", "total market": "totalmarket",
    "whole market": "totalmarket", "sp500 fund": "sp500", "500 fund": "sp500",
    "mutual fund": "mutualfund", "mutual funds": "mutualfund",
    "exchange traded fund": "etf", "exchange traded funds": "etf", "etfs": "etf",
    "targetdate fund": "targetdate", "targetdate funds": "targetdate", "target retirement fund": "targetdate",
    "target retirement": "targetdate", "lifecycle fund": "targetdate",
    "2050 fund": "targetdate", "2055 fund": "targetdate", "2060 fund": "targetdate", "2065 fund": "targetdate",
    "expense ratio": "expenseratio", "expense ratios": "expenseratio", "fund fee": "expenseratio",
    "fund fees": "expenseratio", "management fee": "expenseratio", "management fees": "expenseratio",
    "fund cost": "expenseratio", "fund costs": "expenseratio", "fund expenses": "expenseratio",
    "fee drag": "expenseratio", "high fees": "expenseratio", "low cost fund": "expenseratio",
    "cheap fund": "expenseratio", "load fee": "expenseratio",
    "fractional share": "fractionalshares", "fractional shares": "fractionalshares",
    "partial share": "fractionalshares", "partial shares": "fractionalshares",
    "ticker symbol": "ticker", "ticker symbols": "ticker", "stock symbol": "ticker",
    "asset allocation": "allocation", "stock bond mix": "allocation", "portfolio mix": "allocation",
    "stock bond split": "allocation", "60/40": "allocation", "80/20": "allocation", "90/10": "allocation",
    "international stocks": "international", "foreign stocks": "international", "international fund": "international",
    "emerging markets": "international", "world fund": "international", "global fund": "international",
    "home bias": "international",
    "bear market": "bearmarket", "bull market": "bullmarket", "market crash": "crash", "stock market crash": "crash",
    "market correction": "correction",
    "risk tolerance": "risktolerance", "risk appetite": "risktolerance", "risk capacity": "risktolerance",
    "sequence risk": "sequencerisk", "sequence of returns": "sequencerisk", "sequence of return": "sequencerisk",
    "rule of 72": "ruleof72", "rule of seventy two": "ruleof72", "doubling time": "ruleof72",
    "compound interest": "compounding", "compound growth": "compounding", "interest on interest": "compounding",
    "growth on growth": "compounding", "snowball effect": "compounding",
    "market timing": "timing", "time the market": "timing", "timing the market": "timing",
    "buy the dip": "timing", "wait for a dip": "timing", "wait for the dip": "timing",
    "wait for a crash": "timing", "wait for the market": "timing", "wait for a drop": "timing",
    "wait for it to drop": "timing", "wait until": "waituntil", "good time to invest": "timing",
    "bad time to invest": "timing", "get in now": "timing", "alltimehigh": "timing",
    "rebalance": "rebalancing", "re-balance": "rebalancing", "portfolio drift": "rebalancing",
    "dividend": "dividends", "dividend yield": "dividends", "dividend stocks": "dividends",
    "qualified dividend": "qualifieddividends", "qualified dividends": "qualifieddividends",
    "ordinary dividend": "qualifieddividends", "ordinary dividends": "qualifieddividends",
    # retirement mechanics
    "59half": "59half", "fifty nine and a half": "59half", "before 59half": "59half",
    "early withdrawal": "earlywithdrawal", "early withdrawals": "earlywithdrawal", "withdraw early": "earlywithdrawal",
    "10% penalty": "earlywithdrawal", "ten percent penalty": "earlywithdrawal", "withdrawal penalty": "earlywithdrawal",
    "cash out": "earlywithdrawal", "take money out early": "earlywithdrawal", "hardship withdrawal": "earlywithdrawal",
    "rule of 55": "ruleof55", "rule of fifty five": "ruleof55",
    "required minimum distribution": "rmd", "required minimum distributions": "rmd", "rmds": "rmd",
    "minimum distribution": "rmd", "forced withdrawal": "rmd", "forced withdrawals": "rmd",
    "roll over": "rollover", "rolled over": "rollover", "rolling over": "rollover", "roll it over": "rollover",
    "rollovers": "rollover", "old 401k": "old401k", "previous employer": "old401k", "old job": "old401k",
    "left my job": "old401k", "changing jobs": "old401k", "former employer": "old401k", "leave my job": "leavejob",
    "vesting schedule": "vesting", "vested": "vesting", "unvested": "vesting", "cliff vesting": "vesting",
    "graded vesting": "vesting", "fully vested": "vesting",
    "social security": "socialsecurity", "ss benefits": "socialsecurity", "ssa": "socialsecurity",
    "full retirement age": "socialsecurity", "claim at 62": "socialsecurity", "claim at 70": "socialsecurity",
    "delay social security": "socialsecurity",
    "fourpercentrule": "fourpercentrule", "safe withdrawal rate": "fourpercentrule", "safe withdrawal": "fourpercentrule",
    "withdrawal rate": "fourpercentrule", "25x": "fourpercentrule", "25 times": "fourpercentrule",
    "twenty five times": "fourpercentrule", "retirement number": "fourpercentrule", "fire number": "fourpercentrule",
    "my number": "fourpercentrule", "how much do i need to retire": "fourpercentrule", "how much to retire": "fourpercentrule",
    "how much money to retire": "fourpercentrule", "how big a nest egg": "fourpercentrule", "nest egg": "nestegg",
    "roth conversion": "conversion", "roth conversions": "conversion", "convert to roth": "conversion",
    "conversion ladder": "conversion", "roth ladder": "conversion", "convert my ira": "conversion",
    "backdoor roth": "backdoor", "back door roth": "backdoor", "mega backdoor": "backdoor",
    "income too high for roth": "backdoor", "make too much for roth": "backdoor", "too much for a roth": "backdoor",
    "pro rata": "prorata", "pro-rata": "prorata", "prorata rule": "prorata", "aggregation rule": "prorata",
    "catchup contribution": "catchup", "catchup contributions": "catchup", "over 50 contribution": "catchup",
    "roth withdrawal": "rothwithdrawal", "withdraw roth contributions": "rothwithdrawal",
    "take contributions out of roth": "rothwithdrawal", "roth ordering": "rothwithdrawal",
    "roth 5 year rule": "rothwithdrawal", "five year rule": "fiveyearrule",
    "retire early": "earlyretirement", "early retirement": "earlyretirement", "financial independence": "earlyretirement",
    "fire": "earlyretirement", "lean fire": "earlyretirement", "fat fire": "earlyretirement", "coast fire": "coastfire",
    "barista fire": "earlyretirement", "bridge account": "bridge", "before medicare": "medicaregap",
    "health insurance before 65": "medicaregap", "medicare gap": "medicaregap", "cobra": "medicaregap",
    "aca marketplace": "medicaregap", "obamacare": "medicaregap",
    # taxes
    "marginal tax rate": "marginal", "marginal rate": "marginal", "effective tax rate": "effective",
    "effective rate": "effective", "tax bracket": "bracket", "tax brackets": "bracket", "brackets": "bracket",
    "what bracket am i in": "bracket", "higher bracket": "bracket", "bracket creep": "bracket",
    "standard deduction": "standarddeduction", "itemize": "itemized", "itemized deduction": "itemized",
    "itemized deductions": "itemized", "itemizing": "itemized",
    "tax deferred": "pretax", "tax-deferred": "pretax", "tax deductible": "pretax", "before tax": "pretax",
    "after tax": "posttax", "already taxed": "posttax",
    "roth or traditional": "rothvstrad", "roth vs traditional": "rothvstrad", "traditional or roth": "rothvstrad",
    "traditional vs roth": "rothvstrad", "roth versus traditional": "rothvstrad", "traditional versus roth": "rothvstrad",
    "roth vs trad": "rothvstrad", "tax now or later": "rothvstrad", "taxed now or later": "rothvstrad",
    "taxloss harvesting": "tlh", "tax loss harvesting": "tlh", "harvest losses": "tlh", "harvesting losses": "tlh",
    "wash sale": "washsale", "wash sales": "washsale", "30 day rule": "washsale", "thirty day rule": "washsale",
    "capital gain": "capitalgains", "capital gains": "capitalgains", "long term capital gains": "capitalgains",
    "short term capital gains": "capitalgains", "long term gains": "capitalgains", "short term gains": "capitalgains",
    "tax on gains": "capitalgains", "tax when i sell": "capitalgains", "profit from stocks": "capitalgains",
    "tax drag": "taxdrag", "asset location": "taxdrag", "tax efficient": "taxdrag", "tax-efficient": "taxdrag",
    "self employed": "selfemployed", "self-employed": "selfemployed", "self employment": "selfemployed",
    "independent contractor": "selfemployed", "freelance": "selfemployed", "freelancer": "selfemployed",
    "gig work": "selfemployed", "gig income": "selfemployed", "contractor": "selfemployed",
    "solo401k": "solo401k", "sepira": "sepira",
    "payroll tax": "fica", "payroll taxes": "fica", "social security tax": "fica", "medicare tax": "fica",
    "oasdi": "fica", "self employment tax": "fica",
    "taxadvantaged": "taxadvantaged", "tax sheltered": "taxadvantaged", "tax free growth": "taxadvantaged",
    "tax advantage": "taxadvantaged", "tax advantages": "taxadvantaged", "tax benefit": "taxadvantaged",
    # debt
    "annual percentage rate": "apr", "annual percentage yield": "apy", "interest rate": "interestrate",
    "interest rates": "interestrate",
    "minimum payment": "minimumpayment", "minimum payments": "minimumpayment", "pay the minimum": "minimumpayment",
    "paying the minimum": "minimumpayment", "only pay the minimum": "minimumpayment", "only paying the minimum": "minimumpayment",
    "carrying a balance": "minimumpayment", "carry a balance": "minimumpayment",
    "credit card interest": "creditcardinterest", "card interest": "creditcardinterest",
    "debt avalanche": "avalanche", "debt snowball": "snowball", "avalanche method": "avalanche",
    "snowball method": "snowball", "highest interest first": "avalanche", "smallest balance first": "snowball",
    "which debt first": "debtorder", "order to pay off": "debtorder", "pay off first": "debtorder",
    "multiple debts": "debtorder", "several debts": "debtorder",
    "credit score": "creditscore", "credit rating": "creditscore", "fico score": "creditscore", "fico": "creditscore",
    "credit report": "creditscore", "build credit": "creditscore", "credit history": "creditscore",
    "improve my credit": "creditscore", "raise my credit": "creditscore", "my credit": "creditscore",
    "credit utilization": "utilization", "credit utilisation": "utilization", "utilization ratio": "utilization",
    "credit limit": "creditlimit", "statement balance": "statementbalance",
    "good debt": "gooddebt", "bad debt": "baddebt", "debt free": "debtfree", "debt-free": "debtfree",
    "student loan": "studentloan", "student loans": "studentloan", "student debt": "studentloan",
    "college debt": "studentloan", "college loans": "studentloan", "school loans": "studentloan",
    "tuition debt": "studentloan", "my loans": "studentloan", "loan forgiveness": "forgiveness",
    "public service loan forgiveness": "forgiveness", "pslf": "forgiveness", "income driven repayment": "idr",
    "income based repayment": "idr", "save plan": "idr", "federal loans": "federalloans", "private loans": "privateloans",
    "credit card debt": "creditcard", "credit card": "creditcard", "credit cards": "creditcard", "card debt": "creditcard",
    "cc debt": "creditcard", "my card": "creditcard", "car loan": "carloan", "auto loan": "carloan",
    "car payment": "carloan", "car note": "carloan", "home loan": "mortgage", "house payment": "mortgage",
    "personal loan": "personalloan", "payday loan": "personalloan", "medical debt": "medicaldebt",
    "medical bills": "medicaldebt", "hospital bill": "medicaldebt",
    "balance transfer": "balancetransfer", "0% balance transfer": "balancetransfer", "zero percent card": "balancetransfer",
    "consolidate": "consolidation", "debt consolidation": "consolidation", "consolidation loan": "consolidation",
    "pay off debt or invest": "debtvsinvest", "debt or invest": "debtvsinvest", "pay debt or invest": "debtvsinvest",
    "invest or pay off debt": "debtvsinvest", "invest or pay down": "debtvsinvest", "debt vs investing": "debtvsinvest",
    "pay off or invest": "debtvsinvest", "pay down or invest": "debtvsinvest", "debt versus investing": "debtvsinvest",
    "pay extra on": "payextra", "pay extra toward": "payextra", "extra payment": "payextra", "extra payments": "payextra",
    "pay off faster": "payextra", "pay it off early": "payextra", "pay off early": "payextra",
    "pay down": "payoff", "paying down": "payoff", "pay off": "payoff", "paying off": "payoff", "payoff": "payoff",
    "get rid of": "payoff", "clear my": "payoff", "eliminate": "payoff", "knock out": "payoff", "tackle": "payoff",
    "attack": "payoff", "deal with": "handle", "plan around": "handle", "manage": "handle", "handle": "handle",
    "what do i do about": "handle", "what to do about": "handle", "what should i do about": "handle",
    # cash
    "emergency fund": "emergencyfund", "emergency savings": "emergencyfund", "rainy day fund": "emergencyfund",
    "rainy day": "emergencyfund", "safety net": "emergencyfund", "cash cushion": "emergencyfund",
    "cash reserve": "emergencyfund", "emergency money": "emergencyfund", "cash buffer": "emergencyfund",
    "3 months of expenses": "emergencyfund", "6 months of expenses": "emergencyfund", "three months of expenses": "emergencyfund",
    "six months of expenses": "emergencyfund", "months of expenses": "emergencyfund",
    "fdic": "fdic", "fdic insured": "fdic", "fdic insurance": "fdic", "sipc": "fdic", "ncua": "fdic",
    "bank failure": "fdic", "bank fails": "fdic", "is my money safe": "fdic",
    "purchasing power": "inflation", "cost of living": "inflation", "prices going up": "inflation",
    "real return": "realreturn", "nominal return": "realreturn", "real vs nominal": "realreturn",
    "inflation adjusted": "realreturn", "today's dollars": "todaysmoney", "todays dollars": "todaysmoney",
    "today's money": "todaysmoney", "todays money": "todaysmoney", "future dollars": "realreturn",
    "sinking fund": "sinkingfund", "sinking funds": "sinkingfund", "saving for a": "savingfor", "save for a": "savingfor",
    "saving up for": "savingfor", "save up for": "savingfor", "short term savings": "sinkingfund",
    "short term goal": "sinkingfund", "down payment": "downpayment", "house deposit": "downpayment",
    # income & planning
    "gross pay": "gross", "gross income": "gross", "gross salary": "gross", "net pay": "takehome", "net income": "takehome",
    "takehome pay": "takehome", "take home": "takehome", "after tax income": "takehome",
    "withholding": "withholding", "tax withholding": "withholding", "withheld": "withholding",
    "tax refund": "refund", "big refund": "refund", "get a refund": "refund", "owe taxes": "owetaxes", "owe the irs": "owetaxes",
    "fiftythirtytwenty": "fiftythirtytwenty", "50 30 20 rule": "fiftythirtytwenty", "budget rule": "fiftythirtytwenty",
    "how to budget": "budgeting", "make a budget": "budgeting", "budgeting": "budgeting", "budget": "budgeting",
    "savings rate": "savingsrate", "saving rate": "savingsrate", "percent of income": "savingsrate",
    "percent of my income": "savingsrate", "percentage of income": "savingsrate", "what percent should i save": "savingsrate",
    "how much should i save": "savingsrate", "how much should i be saving": "savingsrate", "15%": "savingsrate",
    "fifteen percent": "savingsrate", "save 15": "savingsrate", "save 10": "savingsrate", "is 10% enough": "savingsrate",
    "lifestyle creep": "lifestylecreep", "lifestyle inflation": "lifestylecreep", "spending creep": "lifestylecreep",
    "net worth": "networth", "assets minus liabilities": "networth", "am i on track": "ontrack",
    "on track": "ontrack",
    "pay frequency": "payfrequency", "paid biweekly": "payfrequency", "paid every two weeks": "payfrequency",
    "paid twice a month": "payfrequency", "26 paychecks": "payfrequency", "three paycheck month": "payfrequency",
    "per paycheck": "perpaycheck", "each paycheck": "perpaycheck", "every paycheck": "perpaycheck",
    "got a raise": "raise", "getting a raise": "raise", "new salary": "raise", "promotion": "raise", "promoted": "raise",
    "pay increase": "raise", "salary increase": "raise", "salary went up": "raise", "make more money": "raise",
    "sidehustle": "sidehustle", "side income": "sidehustle", "side gig": "sidehustle", "second job": "sidehustle",
    "extra income": "sidehustle", "freelance income": "sidehustle", "uber": "sidehustle", "doordash": "sidehustle",
    "etsy": "sidehustle",
    "contribution limit": "limits", "contribution limits": "limits", "annual limit": "limits", "yearly limit": "limits",
    "max out": "maxout", "maxing out": "maxout", "maxed out": "maxout", "max my": "maxout", "how much can i put in": "howmuchputin",
    "how much can i contribute": "howmuchputin", "how much am i allowed": "howmuchputin", "how much can i put": "howmuchputin",
    "over contribute": "excess", "over contributed": "excess", "excess contribution": "excess", "contributed too much": "excess",
    "true up": "trueup", "true-up": "trueup", "front load": "frontload", "front loading": "frontload",
    "front-load": "frontload",
    # health
    "flexible spending": "fsa", "use it or lose it": "fsa", "limited purpose fsa": "fsa", "dependent care fsa": "fsa",
    "triple tax": "tripletax", "triple tax advantage": "tripletax", "triple tax advantaged": "tripletax",
    "stealth ira": "tripletax", "secret retirement account": "tripletax", "invest my hsa": "investhsa",
    "save receipts": "investhsa", "reimburse myself": "investhsa", "hsa after 65": "investhsa",
    "outofpocket maximum": "oopmax", "outofpocket max": "oopmax", "outofpocket": "oopmax", "copay": "copay", "coinsurance": "copay",
    "open enrollment": "openenrollment", "ppo": "ppo", "hmo": "ppo",
    "life insurance": "lifeinsurance", "term life": "termlife", "whole life": "wholelife", "universal life": "wholelife",
    "permanent life": "wholelife", "cash value": "wholelife", "iul": "wholelife", "indexed universal life": "wholelife",
    "disability insurance": "disability", "long term disability": "disability", "short term disability": "disability",
    "income protection": "disability", "can't work": "disability", "cannot work": "disability", "own occupation": "disability",
    "extended warranty": "warranty", "phone insurance": "warranty", "renters insurance": "renters", "umbrella policy": "umbrella",
    "self insure": "selfinsure",
    "smallest debt first": "snowball", "smallest first": "snowball", "highest interest": "avalanche",
    "biggest interest first": "avalanche", "highest rate first": "avalanche",
    "saving 10%": "savingsrate", "save 10%": "savingsrate", "saving 15%": "savingsrate", "saving 20%": "savingsrate",
    "save 20%": "savingsrate", "saving 5%": "savingsrate", "10% of my income": "savingsrate", "15% of my income": "savingsrate",
    "20% of my income": "savingsrate", "% of my income": "savingsrate", "percent of my pay": "savingsrate",
    "50% up to 6%": "matchformula", "up to 6% of pay": "matchformula", "up to 6%": "matchformula", "match formula": "matchformula",
    "50% of the first 6%": "matchformula", "100% up to 3%": "matchformula", "dollar for dollar": "matchformula",
    "maxed": "maxout", "maxing": "maxout", "maxed everything": "maxout", "maxed my": "maxout",
    "long term": "longterm", "long-term": "longterm", "short term": "shortterm", "short-term": "shortterm",
    "where do i even start": "nextdollar", "how do i even start": "nextdollar", "where to even start": "nextdollar",
    "how many months": "monthscovered", "how many months of expenses": "monthscovered",
    # legal / employer references
    "do i need a will": "willdoc", "need a will": "willdoc", "write a will": "willdoc", "make a will": "willdoc",
    "have a will": "willdoc", "last will": "willdoc", "my will": "willdoc", "a will": "willdoc",
    "my company": "myemployer", "my employer": "myemployer", "my job": "myemployer", "my work": "myemployer",
    "my plan's": "myemployer", "my benefits": "myemployer",
    # first-person / generic
    "next dollar": "nextdollar", "where should my money go": "nextdollar", "where should the money go": "nextdollar",
    "what should i do first": "nextdollar", "what do i do first": "nextdollar", "where do i start": "nextdollar",
    "where to start": "nextdollar", "what's next": "nextdollar", "what next": "nextdollar", "next step": "nextdollar",
    "next move": "nextdollar", "what should i do next": "nextdollar", "what to do next": "nextdollar",
    "getting started": "nextdollar", "how do i start": "nextdollar", "how to start": "nextdollar",
    "just starting out": "nextdollar", "beginner": "nextdollar", "priority": "priority", "prioritize": "priority",
    "priorities": "priority", "the order": "order", "this order": "order", "what order": "order", "why this order": "order",
    "waterfall": "order", "why is it ordered": "order",
    "each month": "monthly", "every month": "monthly", "per month": "monthly", "a month": "monthly", "monthly plan": "monthly",
    "month to month": "monthly", "what do i do each month": "monthlyplan", "what do i actually do": "monthlyplan",
    "monthly schedule": "monthlyplan", "my schedule": "monthlyplan", "what to move": "monthlyplan",
    "can i retire": "canretire", "am i able to retire": "canretire", "will i be able to retire": "canretire",
    "on track to retire": "canretire", "enough to retire": "canretire", "when can i retire": "canretire",
    "am i going to be ok": "canretire", "will my money last": "canretire", "run out of money": "runout",
    "money run out": "runout", "money gonna run out": "runout", "outlive my money": "runout",
    "what changes if i retire": "retirechanges", "retire earlier or later": "retirechanges", "retire earlier": "retirechanges",
    "retire later": "retirechanges", "retire sooner": "retirechanges",
    "how much do i need to invest": "whatittakes", "how much do i need to save": "whatittakes", "what it takes": "whatittakes",
    "how much to get there": "whatittakes", "what does it take": "whatittakes",
    "am i missing": "missing", "leaving money on the table": "missing", "on the table": "missing",
    "what to invest in": "whatinvest", "what do i invest in": "whatinvest", "what should i invest in": "whatinvest",
    "what do i actually invest in": "whatinvest", "what funds": "whatinvest", "which funds": "whatinvest",
    "which fund": "whatinvest", "what fund": "whatinvest", "what do i buy": "whatinvest", "what should i buy": "whatinvest",
    "what to buy": "whatinvest", "how do i invest": "whatinvest", "how to invest": "whatinvest", "sitting in cash": "idlecash",
    "uninvested": "idlecash", "how is a taxable account taxed": "taxabletax", "taxed in a brokerage": "taxabletax",
    "tax on my brokerage": "taxabletax", "taxes on brokerage": "taxabletax",
    "can i do a roth": "canroth", "can i contribute to a roth": "canroth", "am i eligible for a roth": "canroth",
    "roth eligible": "canroth", "roth eligibility": "canroth", "qualify for a roth": "canroth", "allowed to do a roth": "canroth",
    "income limit for roth": "canroth", "roth income limit": "canroth", "roth income limits": "canroth",
    "what is a": "whatis", "what is an": "whatis", "what's a": "whatis", "what's an": "whatis", "what are": "whatis",
    "explain": "whatis", "define": "whatis", "meaning of": "whatis", "what does": "whatis", "how does": "howdoes",
    "how do": "howdoes", "tell me about": "whatis", "what is": "whatis",
}
_ALIAS_ITEMS = sorted(ALIASES.items(), key=lambda kv: -len(kv[0]))
_ALIAS_RES = [(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"), v) for k, v in _ALIAS_ITEMS]

STOPWORDS = {
    "what", "how", "should", "i", "my", "me", "a", "an", "the", "is", "are", "do", "does", "can",
    "could", "of", "to", "in", "for", "about", "if", "when", "will", "would", "it", "its", "this",
    "that", "be", "am", "was", "were", "have", "has", "had", "with", "on", "at", "by", "from", "and",
    "or", "but", "so", "as", "than", "then", "there", "here", "any", "some", "all", "just", "really",
    "please", "thanks", "ok", "okay", "hey", "hi", "hello", "yo", "um", "like", "lol", "you", "your",
    "we", "our", "they", "them", "their", "he", "she", "his", "her", "not", "no", "yes", "get", "got",
    "want", "need", "know", "think", "tell", "much", "many", "very", "into", "out", "up", "down",
    "also", "too", "even", "still", "way", "thing", "things", "stuff", "something", "anything",
    "one", "which", "who", "whom", "whose", "where", "why", "whatis", "howdoes", "versus", "vs", "even",
    "mean", "means", "meant", "supposed", "actually", "exactly", "basically", "literally", "kind", "sort",
}
# Words the stemmer must not touch (or that would collide when stripped).
_STEM_EXCEPTIONS = {
    "roth", "bonds", "stocks", "shares", "funds", "taxes", "fees", "rates", "gains", "losses",
    "debts", "loans", "savings", "earnings", "assets", "expenses", "wages", "yes", "this", "his",
    "ira", "hsa", "fsa", "etf", "sp500", "1099", "w2", "w4", "403b", "457b", "72t", "59half",
}
# Alias and compound tokens are already canonical; stemming "whatis" to "whati" would
# turn a stopword into a content word that matches every "what is" question. They
# also survive the numeric filter: "401k" is a word here, not a number.
_NO_STEM: frozenset[str] = frozenset(ALIASES.values()) | frozenset(t for _, t in _COMPOUNDS) | _STEM_EXCEPTIONS | {"401k", "403b", "457b", "529"}
_STEM_MAP = {
    "bonds": "bond", "stocks": "stock", "shares": "share", "funds": "fund", "taxes": "tax", "fees": "fee",
    "rates": "rate", "gains": "gain", "losses": "loss", "debts": "debt", "loans": "loan", "savings": "save",
    "saving": "save", "saved": "save", "saves": "save", "earnings": "earn", "assets": "asset", "expenses": "expense",
    "wages": "wage", "investing": "invest", "invested": "invest", "invests": "invest", "investment": "invest",
    "investments": "invest", "investor": "invest", "retiring": "retire", "retired": "retire", "retirement": "retire",
    "retires": "retire", "contributing": "contribute", "contributed": "contribute", "contribution": "contribute",
    "contributions": "contribute", "contributes": "contribute", "withdrawing": "withdraw", "withdrawal": "withdraw",
    "withdrawals": "withdraw", "withdrew": "withdraw", "paying": "pay", "paid": "pay", "pays": "pay", "payment": "pay",
    "payments": "pay", "owing": "owe", "owed": "owe", "owes": "owe", "buying": "buy", "bought": "buy", "buys": "buy",
    "selling": "sell", "sold": "sell", "sells": "sell", "growing": "grow", "grew": "grow", "grows": "grow", "growth": "grow",
    "earning": "earn", "earned": "earn", "earns": "earn", "making": "make", "made": "make", "makes": "make",
    "diversified": "diversify", "diversification": "diversify", "diversifying": "diversify", "diversifies": "diversify",
    "compounding": "compounding", "compounds": "compounding", "compounded": "compounding", "compound": "compounding",
    "inflationary": "inflation", "deductions": "deduction", "deductible": "deductible", "deductibles": "deductible",
    "dividends": "dividends", "insured": "insurance", "insure": "insurance", "insuring": "insurance",
    "refinanced": "refinance", "refinancing": "refinance", "consolidating": "consolidation", "consolidated": "consolidation",
    "budgeted": "budgeting", "budgets": "budgeting", "crashes": "crash", "crashed": "crash", "crashing": "crash",
    "timing": "timing", "converting": "conversion", "converted": "conversion", "convert": "conversion", "converts": "conversion",
    "married": "married", "younger": "young", "older": "old", "cheaper": "cheap", "cheapest": "cheap",
    "expensive": "expensive", "quitting": "quit", "leaving": "leave", "left": "leave",
}


def _stem(word: str) -> str:
    if word in _STEM_MAP:
        return _STEM_MAP[word]
    if word in _NO_STEM or len(word) < 5 or not word.isalpha():
        return word
    for suffix in ("ies", "ing", "ed", "es", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            stem = word[: -len(suffix)]
            if suffix == "ies":
                stem += "y"
            if suffix == "s" and word.endswith("ss"):
                return word
            return stem
    return word


def normalize(text: str) -> str:
    t = text.lower().strip()
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    for regex, token in _COMPOUND_RES:
        t = regex.sub(f" {token} ", t)
    words = []
    for w in re.split(r"\s+", t):
        w = w.strip()
        if not w:
            continue
        key = w.rstrip("?.!,;:")
        words.append(_CONTRACTIONS.get(key, key))
    t = " ".join(words)
    t = re.sub(r"\$\s*", "$", t)
    t = re.sub(r"[^a-z0-9$%./' ]+", " ", t)
    t = re.sub(r"(?<=[a-z])'s\b", "", t)
    t = re.sub(r"[./'](?=\s|$)|(?<=\s)[./']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def expand_aliases(norm: str) -> str:
    t = f" {norm} "
    for regex, token in _ALIAS_RES:
        t = regex.sub(f" {token} ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(text: str) -> list[str]:
    """Stemmed tokens, stopwords included (bigrams need adjacency)."""
    return [_stem(w) for w in expand_aliases(normalize(text)).split(" ") if w]


def _is_number(t: str) -> bool:
    """Money and plain numbers are slots, not vocabulary — but "401k" is a word."""
    return bool(re.fullmatch(r"[\d$%.,]+k?", t)) and t not in _NO_STEM


def _content_tokens(toks: list[str]) -> list[str]:
    return [t for t in toks if t not in STOPWORDS and not _is_number(t)]


def _bigrams(toks: list[str]) -> set[str]:
    out = set()
    for a, b in zip(toks, toks[1:]):
        if a in STOPWORDS and b in STOPWORDS:
            continue
        if _is_number(a) or _is_number(b):
            continue
        out.add(f"{a}_{b}")
    return out


# --- the corpus ----------------------------------------------------------------

_KIND_ORDER = {"scenario": 0, "decline": 1, "personal": 2, "general": 3}

_ENTITY_TOKENS = {
    "401k", "ira", "rothira", "tradira", "hsa", "fsa", "taxable", "brokerage", "roth", "traditional",
    "studentloan", "creditcard", "carloan", "mortgage", "personalloan", "medicaldebt", "match",
    "emergencyfund", "hysa", "cd", "moneymarket", "socialsecurity", "indexfund", "targetdate",
    "expenseratio", "dividends", "bond", "stock", "etf", "mutualfund", "sp500", "international",
}


class _Entry:
    __slots__ = ("id", "kind", "question", "topic", "unigrams", "bigrams", "canonical",
                 "entities", "related", "subject_kind")

    def __init__(self, id, kind, question, topic, phrases, related=(), subject_kind=None):
        self.id, self.kind, self.question, self.topic = id, kind, question, topic
        self.related = list(related)
        self.subject_kind = subject_kind
        uni, bi = set(), set()
        for phrase in phrases:
            toks = tokens(phrase)
            uni.update(_content_tokens(toks))
            bi.update(_bigrams(toks))
        self.unigrams, self.bigrams = uni, bi
        self.canonical = " ".join(tokens(question))
        self.entities = uni & _ENTITY_TOKENS


def _qa_entity(qid: str) -> set[str]:
    return {
        "what_is_401k": {"401k"}, "what_is_ira": {"ira"}, "what_is_hsa": {"hsa"},
        "what_is_taxable": {"taxable"}, "am_i_missing_match": {"401k", "match"},
        "can_i_do_roth": {"ira", "roth", "rothira"}, "roth_or_traditional": {"roth", "traditional"},
        "taxable_tax": {"taxable"},
    }.get(qid, set())


def _build_corpus() -> list[_Entry]:
    corpus: list[_Entry] = []
    for sid, sc in scenario.SCENARIOS.items():
        corpus.append(_Entry(sid, "scenario", sc["question"], sc["topic"],
                             [sc["question"], *sc["keywords"]]))
    for did, d in knowledge.DECLINES.items():
        corpus.append(_Entry(did, "decline", d["summary"], "Out of scope", d["keywords"], d["redirect"]))
    for qid, q in qa.QUESTIONS.items():
        e = _Entry(qid, "personal", q["question"], q["topic"], [q["question"], *_QA_KEYWORDS.get(qid, [])])
        e.entities |= _qa_entity(qid)
        corpus.append(e)
    for key, k in knowledge.ENTRIES.items():
        e = _Entry(key, "general", k["question"], k["topic"], [k["question"], *k["keywords"]],
                   k["related"])
        e.entities |= {g for g in k["glossary_terms"]} & _ENTITY_TOKENS
        corpus.append(e)
    return corpus


# Personal questions get the same treatment as knowledge entries: surface phrasings
# people actually type, so "am I leaving free money at work" finds the match question.
_QA_KEYWORDS: dict[str, list[str]] = {
    "next_dollar": ["where should my next dollar go", "what should i do first", "where do i start", "what's next",
                    "next step", "where should my money go", "what do i do with my money", "how do i start",
                    "what's my priority", "what should i focus on", "first thing to do", "what comes first",
                    "im new to this", "beginner", "just starting", "what should i prioritize"],
    "why_this_order": ["why is the order what it is", "why this order", "why match before debt", "why hsa before ira",
                       "why is the emergency fund first", "why is taxable last", "explain the order", "what's the logic",
                       "why is it ordered this way", "waterfall", "why that sequence", "reasoning behind the order"],
    "emergency_fund": ["do i have enough saved for emergencies", "is my emergency fund big enough", "enough emergency fund",
                       "how many months do i have", "am i covered for emergencies", "is my cash enough",
                       "do i have enough cash", "how much cash do i have saved", "my emergency fund",
                       "how many months of expenses do i have", "how many months am i covered for"],
    "debt_or_invest": ["should i pay off debt or invest", "debt or invest", "pay off my debts or invest",
                       "invest or pay down debt", "should i invest while in debt", "which of my debts to pay first",
                       "are my debts expensive", "do i have bad debt", "is my debt high interest",
                       "should i clear my debt first"],
    "how_much_per_month": ["what do i actually do each month", "monthly plan", "what do i move each month",
                           "how much per paycheck", "what's my schedule", "breakdown by paycheck", "what do i do on payday",
                           "monthly breakdown", "how much each month", "what transfers do i make"],
    "can_i_retire_when_i_want": ["can i retire at the age i want", "can i retire", "am i on track to retire",
                                 "will i have enough to retire", "is my plan enough", "will my money last",
                                 "am i going to be ok", "is my money gonna run out", "will i run out of money",
                                 "do i have enough for retirement", "am i on track", "is my retirement on track",
                                 "how am i doing", "will i make it", "am i saving enough for retirement"],
    "retirement_age_changes": ["what changes if i retire earlier or later", "retire earlier or later",
                               "what changes at different ages", "what happens if i retire early",
                               "what's different about retiring early", "milestones", "what ages matter",
                               "what happens at 65", "what happens at 59 1/2", "age milestones"],
    "what_it_takes": ["how much do i need to invest to get there", "how much do i need to save", "what does it take",
                      "how much per month to retire", "what would it take", "how much should i be putting away",
                      "how much to hit my goal", "what do i need to save to retire", "am i saving enough",
                      "coast number", "when could i stop saving"],
    "how_much_can_i_put_in": ["how much can i put in this year", "how much can i contribute", "what are my limits",
                              "contribution limits for me", "how much can i put in my 401k", "how much can i put in my ira",
                              "how much can i put in my hsa", "max i can contribute", "what's my limit", "my limits this year",
                              "how much am i allowed to contribute", "how much room do i have", "can i max out",
                              "can i max out everything", "can i max everything out", "what can i max out"],
    "can_i_do_roth": ["can i contribute to a roth ira", "can i do a roth", "am i eligible for a roth", "roth income limit",
                      "do i make too much for a roth", "is my income too high for roth", "roth phase out for me",
                      "can i open a roth", "am i allowed a roth ira", "do i qualify for a roth"],
    "am_i_missing_match": ["am i leaving employer match on the table", "am i getting my full match",
                           "am i missing match", "am i missing out on free money", "is my 401k contribution enough for the match",
                           "am i contributing enough to get the match", "leaving free money at work", "am i getting all my match",
                           "do i get the full match", "is my match maxed"],
    "roth_or_traditional": ["roth or traditional which should i pick", "roth or traditional for me", "should i do roth or traditional",
                            "which is better for me roth or traditional", "roth vs traditional for my situation",
                            "should my 401k be roth", "should i switch to roth", "traditional or roth ira for me",
                            "what about traditional", "what about roth", "or traditional", "or roth"],
    "what_to_invest_in": ["what do i actually invest in", "what should i invest in", "what funds should i pick",
                          "what do i buy in my ira", "which fund", "what should i buy", "what do i put in my 401k",
                          "what to hold", "is my money invested", "am i invested in the right things", "are my fees too high",
                          "is my fund too expensive", "what should i put my money in", "what should my 401k be invested in",
                          "how do i invest my ira"],
    "taxable_tax": ["how is a taxable account taxed", "taxes on my brokerage", "how are taxable accounts taxed",
                    "what tax do i pay on my brokerage", "tax on my taxable account", "how is my brokerage taxed"],
    "what_is_401k": ["what is a 401k", "explain 401k", "how does a 401k work", "401k explained", "401k basics",
                     "tell me about 401ks", "what's a 401k"],
    "what_is_ira": ["what is an ira", "explain ira", "how does an ira work", "ira explained", "ira basics",
                    "what's an ira", "tell me about iras", "what is a roth ira", "what is a traditional ira"],
    "what_is_hsa": ["what is an hsa", "explain hsa", "how does an hsa work", "hsa explained", "hsa basics", "what's an hsa",
                    "tell me about hsas"],
    "what_is_taxable": ["what is a taxable brokerage account", "what is a brokerage account", "explain taxable account",
                        "what's a taxable account", "taxable account basics", "what is a taxable account"],
}

CORPUS: list[_Entry] = _build_corpus()
_N = len(CORPUS)
_DF_UNI: dict[str, int] = {}
_DF_BI: dict[str, int] = {}
for _e in CORPUS:
    for _t in _e.unigrams:
        _DF_UNI[_t] = _DF_UNI.get(_t, 0) + 1
    for _t in _e.bigrams:
        _DF_BI[_t] = _DF_BI.get(_t, 0) + 1
VOCABULARY: frozenset[str] = frozenset(_DF_UNI)
_GLOSSARY_TOKENS: dict[str, str] = {}
for _gk, _g in content.GLOSSARY.items():
    _key_tokens = _content_tokens(tokens(_gk))
    if len(_key_tokens) == 1:
        _GLOSSARY_TOKENS.setdefault(_key_tokens[0], _gk)   # "roth" → roth, always
    for _t in _content_tokens(tokens(_g["term"])):
        # "money" from "Today's money" must not send every mention of money to that
        # definition; a term's loose words map only when they're distinctive.
        if _DF_UNI.get(_t, 0) <= 6:
            _GLOSSARY_TOKENS.setdefault(_t, _gk)


def _raw_phrases():
    for sc in scenario.SCENARIOS.values():
        yield sc["question"]; yield from sc["keywords"]
    for d in knowledge.DECLINES.values():
        yield from d["keywords"]
    for qid, q in qa.QUESTIONS.items():
        yield q["question"]; yield from _QA_KEYWORDS.get(qid, [])
    for k in knowledge.ENTRIES.values():
        yield k["question"]; yield from k["keywords"]
    yield from ALIASES.keys()
    for g in content.GLOSSARY.values():
        yield g["term"]


# Words as people type them, before aliasing or stemming — what typo repair matches
# against. Repairing "expence" to "expense" *before* the alias pass is what lets
# "expence ratio" become the single token the expense-ratio entry is indexed under.
RAW_VOCAB: frozenset[str] = frozenset(
    w for phrase in _raw_phrases() for w in normalize(phrase).split() if w.isalpha() and len(w) > 2
)


def _idf_uni(t: str) -> float:
    return math.log((_N + 1) / (_DF_UNI.get(t, 0) + 1)) + 1.0


def _idf_bi(t: str) -> float:
    return math.log((_N + 1) / (_DF_BI.get(t, 0) + 1)) + 1.0


# --- typo repair ---------------------------------------------------------------


def _repair(word: str) -> str | None:
    """Only for words of five-plus letters — shorter ones mangle ("roth" → "both")."""
    if len(word) < 5 or not word.isalpha() or word in RAW_VOCAB or word in STOPWORDS:
        return None
    close = difflib.get_close_matches(word, RAW_VOCAB, n=1, cutoff=0.8)
    return close[0] if close else None


# --- the query -----------------------------------------------------------------

_FIRST_PERSON = {"i", "my", "me", "mine", "im", "ive", "myself"}
_REFERENTIAL = re.compile(
    r"^(?:and |but |so |ok |okay )?(?:how much|how many|how long|when|which one|why|what age)\??$|"
    r"\b(what about|how about|and (?:what|how) about|instead|same for|what if it|that one|the other one|"
    r"the other|and that|what if i do|and if|but what if|or (?:the )?traditional|or (?:the )?roth|and traditional|"
    r"and roth|the second|the first|those|these|it|that|this|them|also|too)\b"
)


class Query:
    """normalize → repair typos → expand aliases → stem. Order matters: repair has to
    see the words as typed, and aliasing has to see them spelled right."""

    def __init__(self, text: str):
        self.text = text
        norm = normalize(text)
        words = norm.split()
        self.first_person = any(w in _FIRST_PERSON for w in words)
        fixed, corrections = [], []
        for w in words:
            fix = _repair(w)
            if fix:
                corrections.append({"from": w, "to": fix})
                fixed.append(fix)
            else:
                fixed.append(w)
        self.corrections = corrections
        repaired_text = " ".join(fixed)
        self.tokens = [_stem(w) for w in expand_aliases(repaired_text).split(" ") if w]
        self.raw_tokens = self.tokens
        self.repaired_set = {_stem(c["to"]) for c in corrections}
        self.content = _content_tokens(self.tokens)          # unfiltered — glossary fallback reads this
        self.unigrams = [t for t in self.content if t in VOCABULARY]
        self.unknown = [t for t in self.content
                        if t not in VOCABULARY and t not in _GLOSSARY_TOKENS and t not in RAW_VOCAB
                        and t.isalpha() and len(t) > 3]
        self.bigrams = {b for b in _bigrams(self.tokens) if b in _DF_BI}
        self.slots = S.extract(text)
        self.entities = {t for t in self.unigrams if t in _ENTITY_TOKENS}
        self.meaningful = len(set(self.unigrams)) + len(self.bigrams)
        self.referential = (len(set(self.unigrams)) < 5 and bool(_REFERENTIAL.search(norm)))
        self.normalized = " ".join(self.tokens)

    def weight(self) -> float:
        u = sum(_idf_uni(t) * (0.9 if t in self.repaired_set else 1.0) for t in set(self.unigrams))
        b = 1.5 * sum(_idf_bi(t) for t in self.bigrams)
        return u + b


def _score(q: Query, e: _Entry) -> float:
    denom = q.weight()
    if denom <= 0:
        return 0.0
    uni = sum(_idf_uni(t) * (0.9 if t in q.repaired_set else 1.0)
              for t in set(q.unigrams) if t in e.unigrams)
    bi = 1.5 * sum(_idf_bi(t) for t in q.bigrams if t in e.bigrams)
    return min(1.0, (uni + bi) / denom)


def _candidates(q: Query, user: User | None, context: dict | None) -> list[tuple[float, _Entry, dict]]:
    """Every entry scored. The tuple's first element is the *rank* (base + bonuses,
    unclamped, so bonuses can break ties); `notes["confidence"]` is the 0–1 figure
    shown to the user, and `notes["base"]` is the overlap alone."""
    ctx = context or {}
    prev_id, prev_topic = ctx.get("previous_id"), ctx.get("previous_topic")
    prev_related = set(ctx.get("previous_related") or [])
    prev_entity = ctx.get("previous_entity")
    inherit_entity = q.referential and not q.entities and prev_entity
    entities = q.entities | ({prev_entity} if inherit_entity else set())
    single = len(set(q.unigrams)) == 1 and not q.bigrams
    single_term = next(iter(q.unigrams), None) if single else None

    out = []
    for e in CORPUS:
        base = _score(q, e)
        bonus = 0.0
        notes = {}
        if e.kind == "scenario":
            sc = scenario.SCENARIOS[e.id]
            needs = sc["needs"](q.slots)
            ready = sc["slot_ready"](q.slots, user) if user is not None else False
            in_question = bool(q.slots.amounts or q.slots.ages
                               or (q.slots.rates and q.slots.mentions_increment))
            if not needs:
                base *= 0.6          # a scenario without its trigger signal is a weak reading
            elif ready and in_question:
                # A number in the sentence is the signal. "i got 10k, what do i do with
                # it" has almost no other words and is still clearly a scenario, and it
                # outweighs a knowledge entry that merely shares the entity word.
                base = max(base, 0.45)
                bonus += 0.35
                notes["slot_ready"] = True
            elif ready:
                # Ready only because the profile already holds a debt: a mild nudge, so
                # "why match before debt" still reads as the question it is.
                bonus += 0.15
                notes["slot_ready"] = True
            else:
                base = max(base, 0.30)
                notes["slot_ready"] = False
        if q.referential and prev_id and (e.id in prev_related or prev_id in e.related):
            # "what about traditional?" shares no word with "Roth or traditional — which
            # should I pick?" once aliasing runs. The previous turn is the overlap.
            base = max(base, 0.30)
        if base <= 0:
            continue
        if q.normalized == e.canonical:
            bonus += 0.15
        if entities & e.entities:
            bonus += 0.10
        if e.kind == "personal" and q.first_person:
            bonus += 0.10
        # Tiebreak: how much of the entry's own question the query covers. Two entries
        # that both contain every query word are separated by which one is *about* it.
        qtoks = set(_content_tokens(e.canonical.split()))
        coverage = (len(set(q.unigrams) & qtoks) / len(qtoks)) if qtoks else 0.0
        rank = base + bonus + 0.05 * coverage
        if single and not notes.get("slot_ready"):
            # One word matches every entry that mentions it. Only answer outright when
            # the entry's own question is about that word — and the word is distinctive,
            # not "work" — otherwise offer choices. A lone word is never enough to
            # refuse on, and a lone first-person word prefers the personal layer.
            df = _DF_UNI.get(single_term, 1)
            if e.kind == "decline":
                rank = min(rank, WEAK + 0.10)
            elif single_term in qtoks and (df <= 6 or single_term in _NO_STEM):
                rank = max(rank, STRONG + 0.05)
            elif q.first_person and e.kind == "personal":
                rank = max(min(rank, WEAK + 0.15), STRONG + 0.02)
            elif single_term in _GLOSSARY_TOKENS or df > 1:
                rank = min(rank, WEAK + 0.15)
        # Context is applied after the cap: "what about traditional?" is one word, and
        # the previous turn is precisely what makes it answerable.
        if q.referential and prev_id:
            if prev_topic and e.topic == prev_topic:
                rank += 0.15
            if e.id in prev_related or prev_id in e.related:
                rank += 0.20
        notes["base"] = round(base, 3)
        notes["confidence"] = round(min(1.0, rank), 2)
        out.append((rank, e, notes))
    out.sort(key=lambda r: (-r[0], _KIND_ORDER[r[1].kind], r[1].id))
    return out


# --- multi-part splitting ------------------------------------------------------

_SPLIT_RE = re.compile(r"\s+(?:and also|and then|and|also|plus|as well as)\s+|\?\s+(?=\w)|;\s*|,\s+and\s+")
_PROTECTED_PAIRS = [
    "stocks and bonds", "stock and bond", "roth and traditional", "traditional and roth",
    "avalanche and snowball", "snowball and avalanche", "debt and invest", "debt and investing",
    "401k and ira", "ira and 401k", "hsa and fsa", "fsa and hsa", "apr and apy", "term and whole",
    "gross and net", "needs and wants", "assets and liabilities", "buy and hold", "set and forget",
    "mutual funds and etfs", "etfs and mutual funds", "save and invest", "saving and investing",
    "spend and save", "income and expenses", "now and later", "earlier or later", "earlier and later",
    "pay off and invest", "invest and pay off",
]


def _split(text: str) -> list[str] | None:
    low = normalize(text)
    if any(p in low for p in _PROTECTED_PAIRS):
        return None
    parts = [p.strip(" ?.,") for p in _SPLIT_RE.split(text) if p and p.strip(" ?.,")]
    if len(parts) != 2:
        return None
    if any(len(_content_tokens(tokens(p))) < 1 for p in parts):
        return None
    return parts


# --- answering -----------------------------------------------------------------


def _general_answer(key: str) -> dict:
    k = knowledge.ENTRIES[key]
    a = qa.Answer(summary=k["summary"], detail=k["detail"], facts=list(k.get("facts") or []),
                  sources=[f"knowledge:{key}"], follow_ups=list(k["related"]), content_key=None)
    return asdict(a)


def _decline_answer(did: str) -> dict:
    d = knowledge.DECLINES[did]
    a = qa.Answer(summary=d["summary"], detail=d["detail"], facts=[],
                  sources=[f"decline:{did}"], follow_ups=list(d["redirect"]))
    return asdict(a)


def _glossary_answer(gk: str) -> dict:
    g = content.GLOSSARY[gk]
    a = qa.Answer(summary=g["short"], detail=g["more"], facts=[], sources=[f"glossary:{gk}"], follow_ups=[])
    return asdict(a)


def _question_for(ident: str) -> tuple[str, str] | None:
    if ident in qa.QUESTIONS:
        return "personal", qa.QUESTIONS[ident]["question"]
    if ident in knowledge.ENTRIES:
        return "general", knowledge.ENTRIES[ident]["question"]
    if ident in scenario.SCENARIOS:
        return "scenario", scenario.SCENARIOS[ident]["question"]
    return None


def _resolve_follow_ups(ids: list[str]) -> list[dict]:
    out = []
    for fid in ids:
        found = _question_for(fid)
        if found:
            out.append({"id": fid, "kind": found[0], "question": found[1]})
    return out


def _glossary_for(q: Query, answer: dict) -> list[dict]:
    seen, out = set(), []
    text = " ".join([answer.get("summary", ""), answer.get("detail", "")]).lower()
    for t in q.content:
        gk = _GLOSSARY_TOKENS.get(t)
        if gk and gk not in seen:
            seen.add(gk)
            out.append({"key": gk, **content.GLOSSARY[gk]})
    for gk, g in content.GLOSSARY.items():
        if gk in seen or len(out) >= 4:
            continue
        if g["term"].lower() in text:
            seen.add(gk)
            out.append({"key": gk, **g})
    return out[:4]


def _suggestions(cands, limit=3) -> list[dict]:
    out, seen = [], set()
    for score, e, _ in cands:
        if e.id in seen or e.kind == "decline":
            continue
        seen.add(e.id)
        out.append({"id": e.id, "kind": e.kind, "question": e.question, "confidence": round(score, 2)})
        if len(out) >= limit:
            break
    return out


def _result(q: Query, status: str, kind: str, ident: str | None, question: str, confidence: float,
            answer: dict | None, suggestions=(), follow_ups=(), extra=None) -> dict:
    r = {
        "status": status, "kind": kind, "id": ident, "question": question,
        "confidence": round(min(1.0, confidence), 2), "answer": answer,
        "suggestions": list(suggestions), "follow_ups": list(follow_ups),
        "glossary": _glossary_for(q, answer) if answer else [],
    }
    if extra:
        r.update(extra)
    return r


def _answer_one(text: str, user: User, year: int, context: dict | None) -> dict:
    q = Query(text)
    cands = _candidates(q, user, context)
    top = cands[0] if cands else None
    # Nothing meaningful at all — no vocabulary hit, no slots — is unmatched outright,
    # unless it's a bare follow-up ("how much?") that the previous turn makes whole.
    carried = q.referential and context and top and top[0] >= STRONG
    if not q.unigrams and not q.bigrams and not q.slots.amounts and not q.slots.ages and not carried:
        return _unmatched(q, cands)
    # "purple monkey dishwasher": one word fuzzy-repairs to "money" and the rest is
    # noise. When the words we couldn't place outnumber the ones we could, the
    # honest answer is that we didn't understand.
    if len(q.unknown) > len(set(q.unigrams)) and not q.slots.amounts and not q.slots.ages:
        return _unmatched(q, cands)

    # A bare glossary term ("phase out", "magi") wants its definition.
    if len(set(q.unigrams)) <= 1 and not q.bigrams and not q.slots.amounts and not q.slots.ages:
        for t in q.content:
            gk = _GLOSSARY_TOKENS.get(t)
            if gk and not (top and top[0] >= STRONG):
                g = content.GLOSSARY[gk]
                return _result(q, "answered", "glossary", gk, g["term"], STRONG, _glossary_answer(gk),
                               suggestions=_suggestions(cands), extra={"topic": "Glossary"})

    # A decline only wins when it is genuinely the best reading: top, with real overlap,
    # and not merely edging out a substantive answer on a bonus.
    runner_up = next((c for c in cands if c[1].kind != "decline"), None)
    if (top and top[1].kind == "decline" and top[2]["base"] >= WEAK
            and (runner_up is None or top[0] - runner_up[0] > 0.15)):
        e = top[1]
        return _result(q, "declined", "decline", e.id, e.question, top[0], _decline_answer(e.id),
                       suggestions=_suggestions(cands[1:]), follow_ups=_resolve_follow_ups(e.related),
                       extra={"redirects": _resolve_follow_ups(e.related)})

    if top and top[0] >= STRONG:
        return _deliver(q, top, cands, user, year)

    # A scenario whose trigger is present but whose number is missing: ask, don't guess.
    for score, e, notes in cands[:3]:
        if e.kind == "scenario" and notes.get("slot_ready") is False and score >= WEAK:
            return _needs_input(q, e, cands, user, year)

    if top and top[0] >= WEAK:
        # Try a two-part reading before settling for "did you mean".
        return _result(q, "ambiguous", top[1].kind, None, "", top[0], None,
                       suggestions=_suggestions(cands), extra={"prompt": "Did you mean one of these?"})
    return _unmatched(q, cands)


def _needs_input(q: Query, e: _Entry, cands, user, year) -> dict:
    res = scenario.run(e.id, user, year, q.slots)
    if isinstance(res, scenario.NeedsInput):
        return _result(q, "needs_input", "scenario", e.id, e.question, cands[0][0] if cands else 0.0, None,
                       suggestions=_suggestions([c for c in cands if c[1].id != e.id]),
                       extra={"prompt": res.question, "hint": res.hint, "missing": res.missing})
    return _deliver_composed(q, e, res, cands, cands[0][0] if cands else 0.0)


def _deliver(q: Query, top, cands, user: User, year: int) -> dict:
    score, e, notes = top
    if e.kind == "scenario":
        res = scenario.run(e.id, user, year, q.slots)
        if isinstance(res, scenario.NeedsInput):
            return _result(q, "needs_input", "scenario", e.id, e.question, score, None,
                           suggestions=_suggestions([c for c in cands if c[1].id != e.id]),
                           extra={"prompt": res.question, "hint": res.hint, "missing": res.missing})
        return _deliver_composed(q, e, res, cands, score)
    if e.kind == "personal":
        full = qa.ask(e.id, user, year)
        return _result(q, "answered", "personal", e.id, full["question"], score, full["answer"],
                       suggestions=_suggestions([c for c in cands if c[1].id != e.id]),
                       follow_ups=_resolve_follow_ups(full["answer"]["follow_ups"]),
                       extra={"topic": full["topic"]})
    if e.kind == "general":
        ans = _general_answer(e.id)
        return _result(q, "answered", "general", e.id, e.question, score, ans,
                       suggestions=_suggestions([c for c in cands if c[1].id != e.id]),
                       follow_ups=_resolve_follow_ups(ans["follow_ups"]),
                       extra={"topic": e.topic, "level": knowledge.ENTRIES[e.id]["level"]})
    return _result(q, "declined", "decline", e.id, e.question, score, _decline_answer(e.id),
                   follow_ups=_resolve_follow_ups(e.related), extra={"redirects": _resolve_follow_ups(e.related)})


def _deliver_composed(q: Query, e: _Entry, res: scenario.Composed, cands, score: float) -> dict:
    ans = asdict(res)
    return _result(q, "answered", "scenario", e.id, q.text.strip(), score, ans,
                   suggestions=_suggestions([c for c in cands if c[1].id != e.id]),
                   follow_ups=_resolve_follow_ups(res.follow_ups),
                   extra={"topic": e.topic, "slots": q.slots.to_dict()})


def _unmatched(q: Query, cands) -> dict:
    # Pure vocabulary questions fall through to the glossary before giving up.
    for t in q.content:
        gk = _GLOSSARY_TOKENS.get(t)
        if gk:
            g = content.GLOSSARY[gk]
            return _result(q, "answered", "glossary", gk, g["term"], STRONG, _glossary_answer(gk),
                           suggestions=_suggestions(cands), extra={"topic": "Glossary"})
    return _result(q, "unmatched", "none", None, "", 0.0, None, suggestions=_suggestions(cands),
                   extra={"prompt": "I don't have that one yet. Try one of these, or browse by topic below.",
                          "browse": qa.index(), "knowledge": knowledge.index()})


def _entity_of(result: dict, q: "Query") -> str | None:
    """What the exchange was about, for the next turn to inherit: the query's own
    entity if it named one, else the answered entry's."""
    if q.entities:
        return sorted(q.entities)[0]
    ident = result.get("id")
    for e in CORPUS:
        if e.id == ident:
            ents = sorted(e.entities)
            return ents[0] if ents else None
    return None


def _related_of(result: dict) -> list[str]:
    return [f["id"] for f in result.get("follow_ups", [])]


def answer(text: str, user: User, year: int = L.DEFAULT_YEAR, context: dict | None = None) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("Ask something first.")
    if len(text) > 500:
        raise ValueError("Keep it under 500 characters.")

    first = _answer_one(text, user, year, context)
    results = [first]
    multi = False
    # Two questions in one sentence get two answers — unless the sentence as a whole is
    # already an excellent single match, or splits a phrase that's really one concept.
    whole_conf = first["results"][0]["confidence"] if first.get("results") else first.get("confidence", 0)
    if whole_conf < 0.9 or first["status"] in ("ambiguous", "unmatched"):
        parts = _split(text)
        if parts:
            trial = [_answer_one(p, user, year, context) for p in parts]
            if all(r["status"] in ("answered", "declined", "needs_input") for r in trial) and \
                    len({r["id"] for r in trial}) == 2:
                results, multi = trial, True

    primary = next((r for r in results if r["status"] == "answered"), results[0])
    status = "answered" if any(r["status"] == "answered" for r in results) else results[0]["status"]
    q = Query(text)
    return {
        "status": status,
        "multi_part": multi,
        "corrections": q.corrections,
        "context": {
            "previous_id": primary.get("id"),
            "previous_kind": primary.get("kind"),
            "previous_topic": primary.get("topic"),
            "previous_entity": _entity_of(primary, q),
            "previous_related": _related_of(primary),
        },
        "results": results,
        "year": year,
        "disclaimer": content.DISCLAIMER,
    }


def suggest(text: str, limit: int = 3) -> list[dict]:
    q = Query(text)
    return _suggestions(_candidates(q, None, None), limit)


def explain(text: str, user: User | None = None, context: dict | None = None, top: int = 8) -> list[dict]:
    """Debugging aid: the top candidates with their scores. Not an API surface."""
    q = Query(text)
    return [{"id": e.id, "kind": e.kind, "score": round(s, 3), **n}
            for s, e, n in _candidates(q, user, context)[:top]]
