"""Contribution limits, phase-outs and thresholds — loaded from data, never hardcoded.

Next year's IRS update should be a new JSON file in data/, not a code change.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def today() -> date:
    """The date the plan is running on. FP_TODAY pins it (YYYY-MM-DD) — tests use it so
    the suite doesn't change behaviour on January 1, and it's how to preview a new
    year without waiting for one."""
    pinned = os.environ.get("FP_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()


def now() -> datetime:
    """Timestamps on the same clock as `today()`: the pinned date, the real time."""
    return datetime.combine(today(), datetime.now().time())


def current_year() -> int:
    return today().year


# The fallback for engine functions called without a year. Routes don't rely on it —
# they ask `current_year()` per request, so a server left running over New Year's
# moves with the calendar.
DEFAULT_YEAR = current_year()


@lru_cache(maxsize=None)
def load_limits(year: int = DEFAULT_YEAR) -> dict:
    """The IRS figures for `year`.

    The IRS publishes next year's numbers in October or November, so for a few months
    — and every January until someone adds the file — the plan runs in a year with no
    data. Rather than fail, it uses the latest year on file and says so: `provisional`
    is true and `based_on` names the year the numbers came from. Limits only ever rise
    with inflation, so last year's are a safe floor, never an overstatement.
    """
    path = DATA_DIR / f"limits_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    known = available_years()
    if not known or year < known[0]:
        raise ValueError(f"No limit data on file for {year}")
    latest = max(y for y in known if y < year)
    data = dict(load_limits(latest))
    data.update(year=year, provisional=True, based_on=latest)
    return data


def is_provisional(year: int) -> bool:
    return bool(load_limits(year).get("provisional"))


def available_years() -> list[int]:
    return sorted(int(p.stem.split("_")[1]) for p in DATA_DIR.glob("limits_*.json"))


def _catch_up(tiers: list[dict], age: int) -> int:
    """Catch-up amounts are age-banded (the 60-63 401k band is not monotonic)."""
    for tier in tiers:
        if age < tier["min_age"]:
            continue
        if tier["max_age"] is None or age <= tier["max_age"]:
            return tier["amount"]
    return 0


def elective_401k_limit(age: int, year: int = DEFAULT_YEAR) -> int:
    """Employee deferral limit including any age-based catch-up."""
    data = load_limits(year)["401k"]
    return data["employee_deferral"] + _catch_up(data["catch_up_tiers"], age)


def catch_up_401k(age: int, year: int = DEFAULT_YEAR) -> int:
    return _catch_up(load_limits(year)["401k"]["catch_up_tiers"], age)


def catch_up_must_be_roth(
    age: int, prior_year_wages_from_employer: float | None, year: int = DEFAULT_YEAR
) -> bool:
    """2026 rule: catch-up contributions must be Roth if prior-year wages from that
    employer exceeded the threshold. Unknown wages => False (don't assert what we
    can't know)."""
    data = load_limits(year)["401k"]
    if catch_up_401k(age, year) == 0 or prior_year_wages_from_employer is None:
        return False
    return prior_year_wages_from_employer > data[
        "mandatory_roth_catchup_prior_year_wage_threshold"
    ]


def ira_limit(age: int, year: int = DEFAULT_YEAR,
              earned_income: float | None = None) -> int:
    """Combined traditional + Roth IRA limit for the year.

    You can't contribute more than you earned. That never binds for a high earner, but
    it's the operative limit for a student on a part-time wage — pass `earned_income`
    wherever the user's income is known.
    """
    data = load_limits(year)["ira"]
    statutory = data["combined_limit"] + _catch_up(data["catch_up_tiers"], age)
    if earned_income is None:
        return statutory
    return int(min(statutory, max(0, earned_income)))


def hsa_limit(coverage: str, age: int, year: int = DEFAULT_YEAR) -> int:
    data = load_limits(year)["hsa"]
    if coverage not in ("self_only", "family"):
        raise ValueError(f"Unknown HSA coverage: {coverage}")
    return data[coverage] + _catch_up(data["catch_up_tiers"], age)


def roth_ira_eligibility(
    magi: float, filing_status: str, age: int, year: int = DEFAULT_YEAR,
    earned_income: float | None = None,
) -> dict:
    """Direct Roth IRA contribution capacity after the MAGI phase-out.

    Returns the allowed dollar amount plus the phase-out band used, so the UI can
    show its work instead of just a number.
    """
    data = load_limits(year)["ira"]
    band = data["roth_magi_phaseout"].get(filing_status)
    if band is None:
        raise ValueError(f"Unknown filing status: {filing_status}")

    full_limit = ira_limit(age, year, earned_income)
    start, end = band["start"], band["end"]

    if magi < start:
        allowed, status = full_limit, "full"
    elif magi >= end:
        allowed, status = 0, "phased_out"
    else:
        remaining_fraction = (end - magi) / (end - start)
        # IRS rounds the reduced limit up to the nearest $10, floor of $200 unless zero.
        allowed = int(-(-(full_limit * remaining_fraction) // 10) * 10)
        allowed = min(max(allowed, 200), full_limit)
        status = "partial"

    return {
        "allowed": allowed,
        "full_limit": full_limit,
        "status": status,
        "phaseout_start": start,
        "phaseout_end": end,
        "magi": magi,
        "backdoor_available": status != "full",
    }
