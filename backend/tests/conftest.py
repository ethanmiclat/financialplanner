import os
import sys
from pathlib import Path

# Pin the calendar before any backend module reads it: the suite is written against
# 2026's figures and must not change behaviour on January 1.
os.environ.setdefault("FP_TODAY", "2026-09-17")

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


@pytest.fixture
def client(tmp_path, monkeypatch):
    import store

    monkeypatch.setattr(store, "STORE_PATH", tmp_path / "profile.json")
    import app as app_module

    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def rich_client(client):
    """A client whose profile has every account type populated.

    Behaviour tests use this rather than the demo seed, so changing the seed profile
    (which is marketing/onboarding copy, not a fixture) can't break them.
    """
    client.put("/api/profile", json={
        "age": 40,
        "income": 120_000,
        "filing_status": "single",
        "annual_savings_capacity": 30_000,
        "has_401k_at_work": True,
        "goal": {"monthly_expenses": 4_000, "emergency_fund_months": 6},
        "accounts": [
            {"type": "cash", "nickname": "Savings", "balance": 30_000},
            {"type": "401k", "nickname": "Work 401(k)", "balance": 50_000,
             "contributions_ytd": 2_000, "employer_match_rate": 0.5,
             "employer_match_limit_pct": 0.06},
            {"type": "ira", "nickname": "Roth IRA", "balance": 10_000,
             "contributions_ytd": 1_000},
            {"type": "hsa", "nickname": "HSA", "balance": 3_000,
             "contributions_ytd": 0, "hdhp_enrolled": True,
             "hsa_coverage": "self_only"},
            {"type": "taxable", "nickname": "Brokerage", "balance": 5_000},
        ],
        "debts": [{"name": "Credit card", "balance": 3_000, "apr": 0.22}],
    })
    return client
