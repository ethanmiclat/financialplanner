"""Reading the numbers out of a sentence.

"How should I plan around my 35K of student debt?" contains an amount, a kind of
debt, and no interest rate. Before the engine can run that as a what-if, somebody has
to turn the sentence into `{amount: 35000, debt_kind: "student_loan"}`. That's all
this module does — pure functions from text to structured slots, no state, no
guessing beyond what the words say.

The one judgement call is stock versus flow. "$300 a month" is money that moves;
"35k of debt" is money that sits. The cadence word is the tell, so an amount is tagged
with the cadence found next to it (or none), and the composer reads that tag rather
than re-deriving it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- amounts -----------------------------------------------------------------

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALE_WORDS = {
    "hundred": 100, "thousand": 1_000, "grand": 1_000, "k": 1_000,
    "million": 1_000_000, "mil": 1_000_000, "m": 1_000_000, "mm": 1_000_000,
}

# "$35,000", "35k", "35K", "$1.2m", "1,200", "35 thousand", "35 grand"
_AMOUNT_RE = re.compile(
    r"""
    (?<![\w.])                                  # not glued to a word
    \$?\s*
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)
    \s*
    (?P<scale>k|m|mm|mil|million|thousand|grand|hundred)?\b
    (?!\s*%)                                    # "62%" is a rate, not money
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Spelled-out amounts: "thirty five thousand", "twelve hundred", "two grand".
_WORDS_RE = re.compile(
    r"\b((?:%s)(?:[\s-](?:%s))?)\s+(hundred|thousand|grand|million)\b"
    % ("|".join(_NUMBER_WORDS), "|".join(_NUMBER_WORDS)),
    re.IGNORECASE,
)

_CADENCES = [
    # order matters: longer phrases first so "per paycheck" beats "per"
    (r"(?:per|a|each|every)\s+(?:pay\s*check|paycheck|pay\s*period|pay)\b|/\s*paycheck", "per_paycheck"),
    (r"(?:per|a|each|every)\s+(?:two\s+weeks?|2\s+weeks?|fortnight)\b|bi-?weekly", "biweekly"),
    (r"(?:per|a|each|every)\s+week\b|weekly|/\s*w(?:ee)?k", "weekly"),
    (r"(?:per|a|each|every)\s+(?:month|mo)\b|monthly|/\s*mo(?:nth)?", "monthly"),
    (r"(?:per|a|each|every)\s+(?:year|yr)\b|yearly|annually|annual|/\s*y(?:ea)?r|a\s+year", "yearly"),
]
_CADENCE_RES = [(re.compile(p, re.IGNORECASE), c) for p, c in _CADENCES]

CADENCE_PER_YEAR = {
    "per_paycheck": None,     # depends on the user's pay frequency
    "biweekly": 26, "weekly": 52, "monthly": 12, "yearly": 1,
}


@dataclass
class Amount:
    value: float
    cadence: str | None        # None = a balance / lump sum (a stock, not a flow)
    raw: str
    start: int                 # character offset in the original text
    end: int

    @property
    def is_flow(self) -> bool:
        return self.cadence is not None


def _to_number(num: str, scale: str | None) -> float:
    value = float(num.replace(",", ""))
    if scale:
        value *= _SCALE_WORDS[scale.lower()]
    return value


def _cadence_near(text: str, end: int) -> str | None:
    """A cadence word within a few tokens after the amount ("$300 a month") or
    immediately before it ("monthly $300")."""
    after = text[end:end + 24]
    before = text[max(0, end - 40):end]
    for regex, cadence in _CADENCE_RES:
        if regex.match(after.lstrip()) or regex.search(after[:16]):
            return cadence
    for regex, cadence in _CADENCE_RES:
        if regex.search(before[-14:]):
            return cadence
    return None


def amounts(text: str) -> list[Amount]:
    found: list[Amount] = []
    taken: list[tuple[int, int]] = []

    for m in _WORDS_RE.finditer(text):
        words = re.split(r"[\s-]+", m.group(1).lower())
        base = sum(_NUMBER_WORDS[w] for w in words if w in _NUMBER_WORDS)
        value = base * _SCALE_WORDS[m.group(2).lower()]
        found.append(Amount(value, _cadence_near(text, m.end()), m.group(0), m.start(), m.end()))
        taken.append((m.start(), m.end()))

    for m in _AMOUNT_RE.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        num, scale = m.group("num"), m.group("scale")
        # "401k", "403b", "457b", "529" are account types, never money.
        if num in ("401", "403", "457", "529") and (scale or "").lower() in ("k", "b", ""):
            continue
        # A bare small integer with no $ and no scale is usually an age or a year,
        # not money ("retire at 55", "in 2030"). Money needs a $, a scale, a comma,
        # a decimal, or four-plus digits.
        bare = "$" not in m.group(0) and not scale and "," not in num and "." not in num
        cadence = _cadence_near(text, m.end())
        if bare and len(num) < 4 and cadence is None:
            continue
        if bare and 1900 <= float(num) <= 2100 and re.search(r"\b(in|by|year|until)\s*$", text[:m.start()].lower()):
            continue   # "by 2040"
        value = _to_number(num, scale)
        found.append(Amount(value, cadence, m.group(0).strip(), m.start(), m.end()))

    found.sort(key=lambda a: a.start)
    return found


# --- rates and ages ------------------------------------------------------------

_RATE_RE = re.compile(
    r"(?<![\w.])(\d{1,2}(?:\.\d+)?)\s*(?:%|percent|pct)|"
    # The trailing lookahead also rejects a following decimal, or "at 6.5%" backtracks
    # to "at 6" to dodge the "%" and reads 6% instead of letting the first branch see 6.5%.
    r"\bat\s+(\d{1,2}(?:\.\d+)?)\b(?!\s*(?:years?|yrs?|k\b|,\d|%|percent|pct)|\.\d)",
    re.IGNORECASE,
)


def rates(text: str) -> list[float]:
    out = []
    for m in _RATE_RE.finditer(text):
        raw = m.group(1) or m.group(2)
        if raw is None:
            continue
        value = float(raw)
        # "at 62" is an age, not a rate; "at 6" or "at 6.5" reads as a rate.
        if m.group(2) is not None and value >= 18 and value == int(value):
            continue
        # An explicit "%" can be any share ("62% in stocks"); a bare "at N" reads as a
        # rate only when it's plausibly one.
        limit = 100 if m.group(1) is not None else 60
        if 0 < value <= limit:
            out.append(round(value / 100, 6))
    return out


_AGE_RE = re.compile(
    r"\b(?:at|by|until|till|when i(?:'m| am)?|turn(?:ing)?|age|aged|retire(?:d|ing)?(?:\s+at)?)\s+(\d{2})\b(?!\s*(?:%|k\b|,|\.\d|\s*percent))",
    re.IGNORECASE,
)


def ages(text: str) -> list[int]:
    out = []
    for m in _AGE_RE.finditer(text):
        value = int(m.group(1))
        if 18 <= value <= 100:
            out.append(value)
    return out


# --- kinds ---------------------------------------------------------------------

_DEBT_KINDS = [
    ("student_loan", r"student|college|tuition|grad school|sallie|navient|fafsa|loan forgiveness"),
    ("credit_card", r"credit card|cc debt|card debt|visa|mastercard|amex|discover card|my card"),
    ("auto", r"car loan|auto loan|car payment|vehicle|truck loan|car note"),
    ("mortgage", r"mortgage|home loan|house payment"),
    ("medical", r"medical debt|medical bill|hospital bill"),
    ("personal", r"personal loan|payday|bnpl|buy now pay later|affirm|klarna|family loan"),
]
_DEBT_KIND_RES = [(k, re.compile(p, re.IGNORECASE)) for k, p in _DEBT_KINDS]
_DEBT_GENERIC_RE = re.compile(r"\b(debt|loan|owe|owing|balance on|paying off|pay off|payoff)\b", re.IGNORECASE)

_ACCOUNT_KINDS = [
    ("401k", r"401\s*\(?k\)?|403\s*\(?b\)?|457\b|tsp\b|work(?:place)? (?:retirement )?plan|employer plan"),
    ("ira", r"\bira\b|roth\b|traditional\b|individual retirement"),
    ("hsa", r"\bhsa\b|health savings"),
    ("taxable", r"taxable|brokerage|robinhood|fidelity account|vanguard account|schwab account"),
    ("cash", r"savings account|checking|hysa|high[- ]yield|emergency fund|cash"),
]
_ACCOUNT_KIND_RES = [(k, re.compile(p, re.IGNORECASE)) for k, p in _ACCOUNT_KINDS]

_INCOME_RE = re.compile(
    r"\b(make|makes|making|made|earn|earns|earning|earned|salary|salaried|income|paid|"
    r"pay ?check|wage|wages|raise|promotion|promoted|new job|got a job|job offer|"
    r"take[- ]home|comp\b|compensation)\b",
    re.IGNORECASE,
)
_WINDFALL_RE = re.compile(
    r"\b(bonus|inherit\w*|windfall|gift(?:ed)?|lump sum|tax refund|refund|settlement|"
    r"lottery|came into|got (?:some|a bunch of|extra)|extra (?:cash|money)|found money|"
    r"sold my|sale of|payout|severance|stimulus|won|prize)\b",
    re.IGNORECASE,
)
_INCREMENT_RE = re.compile(
    r"\b(extra|more|additional|on top|bump|increase|add another|another|boost|"
    r"raise(?!\s+(?:to|it to|my income to))|promotion|up my|upped|more each|more per|more a)\b",
    re.IGNORECASE,
)
_SAVE_RE = re.compile(
    r"\b(save|saved|saves|saving|savings|put away|put aside|set aside|contribute|"
    r"contributed|contributing|contribution|contributions|invest|invested|investing|"
    r"stash|sock away|budget|budgeting)\b",
    re.IGNORECASE,
)


@dataclass
class Slots:
    amounts: list[Amount] = field(default_factory=list)
    rates: list[float] = field(default_factory=list)
    ages: list[int] = field(default_factory=list)
    debt_kind: str | None = None
    mentions_debt: bool = False
    account_kind: str | None = None
    mentions_income: bool = False
    mentions_windfall: bool = False
    mentions_saving: bool = False
    mentions_increment: bool = False

    # --- convenience views the composer reads --------------------------------

    @property
    def balances(self) -> list[Amount]:
        return [a for a in self.amounts if not a.is_flow]

    @property
    def flows(self) -> list[Amount]:
        return [a for a in self.amounts if a.is_flow]

    @property
    def amount(self) -> float | None:
        return self.amounts[0].value if self.amounts else None

    @property
    def rate(self) -> float | None:
        return self.rates[0] if self.rates else None

    @property
    def age(self) -> int | None:
        return self.ages[0] if self.ages else None

    @property
    def has_entity(self) -> bool:
        return bool(self.debt_kind or self.account_kind or self.mentions_debt)

    def to_dict(self) -> dict:
        return {
            "amounts": [{"value": a.value, "cadence": a.cadence, "raw": a.raw} for a in self.amounts],
            "rates": self.rates,
            "ages": self.ages,
            "debt_kind": self.debt_kind,
            "account_kind": self.account_kind,
            "mentions_debt": self.mentions_debt,
            "mentions_income": self.mentions_income,
            "mentions_windfall": self.mentions_windfall,
            "mentions_saving": self.mentions_saving,
            "mentions_increment": self.mentions_increment,
        }


def extract(text: str) -> Slots:
    s = Slots(amounts=amounts(text), rates=rates(text), ages=ages(text))
    for kind, regex in _DEBT_KIND_RES:
        if regex.search(text):
            s.debt_kind = kind
            break
    s.mentions_debt = bool(s.debt_kind or _DEBT_GENERIC_RE.search(text))
    for kind, regex in _ACCOUNT_KIND_RES:
        if regex.search(text):
            s.account_kind = kind
            break
    s.mentions_income = bool(_INCOME_RE.search(text))
    s.mentions_windfall = bool(_WINDFALL_RE.search(text))
    s.mentions_saving = bool(_SAVE_RE.search(text))
    s.mentions_increment = bool(_INCREMENT_RE.search(text))
    return s
