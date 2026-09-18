"""The composer: what-ifs on a copy, every figure from the engine, assumptions on the
face of the answer."""

import copy

import pytest

import limits as L
import scenario
import slots
import store
from models import Account, AccountType, Debt, Goal, SavingsBasis, User


def rich() -> User:
    return User(
        age=40, income=120_000, annual_savings_capacity=30_000,
        goal=Goal(monthly_expenses=4_000, emergency_fund_months=6),
        accounts=[
            Account(type=AccountType.CASH, balance=30_000),
            Account(type=AccountType.TRADITIONAL_401K, balance=50_000, contributions_ytd=2_000,
                    employer_match_rate=0.5, employer_match_limit_pct=0.06),
            Account(type=AccountType.IRA, balance=10_000, contributions_ytd=1_000),
            Account(type=AccountType.HSA, balance=3_000, hdhp_enrolled=True),
            Account(type=AccountType.TAXABLE, balance=5_000),
        ],
        debts=[Debt("Credit card", 3_000, 0.22)],
    )


def run(sid, text, user=None):
    return scenario.run(sid, user or rich(), 2026, slots.extract(text))


def test_trial_never_mutates_the_original():
    u = rich()
    snapshot = copy.deepcopy(u)
    scenario.trial(u, add_debts=[Debt("x", 1000, 0.1)], income=200_000, annual_savings_capacity=1)
    assert u == snapshot


def test_income_trial_resyncs_a_percent_of_pay_plan():
    u = rich()
    u.savings_basis, u.savings_amount = SavingsBasis.PERCENT_OF_PAY, 0.10
    import pay
    pay.sync_capacity(u)
    assert u.annual_savings_capacity == 12_000
    t = scenario.trial(u, income=200_000)
    assert t.annual_savings_capacity == 20_000
    assert u.annual_savings_capacity == 12_000


def test_symmetric_simulation_favours_payoff_for_expensive_debt():
    sim = scenario.simulate_branches(8_000, 0.24, 160, 30_000, 98_000, 0.07, 27)
    assert sim["payoff_first"]["invested"] > sim["invest_now"]["invested"]


def test_symmetric_simulation_favours_investing_for_cheap_debt():
    sim = scenario.simulate_branches(35_000, 0.03, 340, 30_000, 98_000, 0.07, 27)
    assert sim["invest_now"]["invested"] > sim["payoff_first"]["invested"]


def test_both_routes_deploy_the_same_cash():
    """With a 0% loan and a 0% return, both routes must end with identical money."""
    sim = scenario.simulate_branches(12_000, 0.0, 200, 12_000, 0, 0.0, 10)
    a, b = sim["payoff_first"], sim["invest_now"]
    assert abs(a["invested"] - b["invested"]) < 1e-6


def test_debt_strategy_discloses_an_assumed_rate():
    r = run("debt_strategy", "How should I plan around my 35K of student debt?")
    labels = {a["label"] for a in r.assumptions}
    assert "Interest rate" in labels and "Minimum payment" in labels
    assert r.save_hint["path"] == "/api/debts"


def test_debt_strategy_uses_a_stated_rate():
    r = run("debt_strategy", "i have 35k in student loans at 4%")
    assert all(a["label"] != "Interest rate" for a in r.assumptions)
    assert "4%" in r.summary


def test_debt_strategy_on_stored_debt_has_no_save_hint():
    r = run("debt_strategy", "should i pay off my credit card")
    assert r.save_hint is None and "22%" in r.summary


def test_debt_strategy_asks_when_nothing_matches():
    u = rich()
    u.debts = []
    r = run("debt_strategy", "how should i handle my debt", u)
    assert isinstance(r, scenario.NeedsInput)
    r = run("debt_strategy", "how should i handle my student loans")
    assert isinstance(r, scenario.NeedsInput) and "student loan" in r.question


def test_threshold_comes_from_the_data_file():
    cutoff = L.load_limits(2026)["thresholds"]["high_interest_debt_apr"]
    r = run("debt_strategy", f"i owe 10k on a personal loan at {cutoff * 100 + 0.5}%")
    assert "step 3" in r.summary
    assert any(f"{cutoff * 100:g}%" in f["value"] for s in r.sections for f in s["facts"])


def test_windfall_allocates_down_the_waterfall_on_the_seed_profile():
    r = run("windfall", "i got 2 grand what do i do with it", store.seed_user())
    labels = [f["label"] for f in r.facts]
    assert labels[0].lower().startswith("your emergency fund")
    assert r.save_hint is None


def test_income_change_reports_roth_status_and_save_hint():
    r = run("income_change", "what if i made 200k")
    assert r.save_hint == {"label": "Set my income to $200,000", "method": "PATCH",
                           "path": "/api/profile", "body": {"income": 200_000}}
    assert any("Roth" in s["heading"] for s in r.sections)


def test_raise_forms():
    assert "$132,000" in run("income_change", "what if i got a 10% raise").summary
    assert "$125,000" in run("income_change", "what if i got a 5k raise").summary
    assert "$150,000" in run("income_change", "what if i got a raise to 150k").summary


def test_contribution_change_absolute_and_incremental():
    absolute = run("contribution_change", "what if i saved 300 a month")
    extra = run("contribution_change", "what if i saved an extra 300 a month")
    assert absolute.save_hint["body"]["savings_amount"] == 300
    assert extra.save_hint["body"]["savings_amount"] == 2_800
    assert "165%" in extra.summary


def test_retirement_age_scenario_and_validation():
    r = run("retirement_age", "can i retire at 55")
    assert "55" in r.summary and r.save_hint["path"] == "/api/goal"
    assert any("59½" in s["heading"] for s in r.sections)
    bad = run("retirement_age", "can i retire at 17")
    assert isinstance(bad, scenario.NeedsInput)
