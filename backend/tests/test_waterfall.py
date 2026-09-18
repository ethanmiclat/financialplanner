import pytest

import waterfall as W
from models import (
    Account,
    AccountType,
    Debt,
    FilingStatus,
    Goal,
    Holding,
    HsaCoverage,
    Priority,
    User,
)


def base_user(**kw) -> User:
    defaults = dict(
        age=34,
        income=100_000,
        filing_status=FilingStatus.SINGLE,
        goal=Goal(monthly_expenses=4_000, emergency_fund_months=6),
        accounts=[Account(type=AccountType.CASH, balance=24_000)],
    )
    defaults.update(kw)
    return User(**defaults)


def ids(items):
    return [i.rule_id for i in items]


def first(items, rule_id):
    return next(i for i in items if i.rule_id == rule_id)


# --- rule 1 -------------------------------------------------------------------


def test_thin_cash_blocks_investing():
    user = base_user(accounts=[Account(type=AccountType.CASH, balance=5_000)])
    item = W.rule_emergency_fund(user)[0]
    assert item.priority is Priority.BLOCKING
    assert item.amount == pytest.approx(7_000)   # 3 months (12k) - 5k


def test_between_floor_and_target_is_not_blocking():
    user = base_user(accounts=[Account(type=AccountType.CASH, balance=16_000)])
    item = W.rule_emergency_fund(user)[0]
    assert item.priority is Priority.MEDIUM
    assert item.amount == pytest.approx(8_000)


def test_funded_emergency_fund_is_informational():
    assert W.rule_emergency_fund(base_user())[0].priority is Priority.INFO


def test_missing_expenses_blocks_with_a_question():
    user = base_user(goal=Goal(monthly_expenses=0))
    assert W.rule_emergency_fund(user)[0].priority is Priority.BLOCKING


# --- rule 2 -------------------------------------------------------------------


def test_unclaimed_match_is_quantified():
    plan = Account(
        type=AccountType.TRADITIONAL_401K,
        employer_match_rate=0.5,
        employer_match_limit_pct=0.06,
        contributions_ytd=2_000,
    )
    user = base_user(accounts=[Account(type=AccountType.CASH, balance=24_000), plan])
    item = W.rule_employer_match(user)[0]
    assert item.amount == pytest.approx(4_000)                     # 6% of 100k - 2k
    assert item.inputs["unclaimed_match"] == pytest.approx(2_000)  # at 50%
    assert item.priority is Priority.HIGH


def test_full_match_captured_is_informational():
    plan = Account(
        type=AccountType.TRADITIONAL_401K,
        employer_match_rate=0.5,
        employer_match_limit_pct=0.06,
        contributions_ytd=6_000,
    )
    user = base_user(accounts=[plan])
    assert W.rule_employer_match(user)[0].priority is Priority.INFO


# --- rule 3 -------------------------------------------------------------------


def test_only_debt_above_the_cutoff_fires():
    user = base_user(debts=[
        Debt("Card", 4_000, 0.24),
        Debt("Auto", 20_000, 0.049),
    ])
    items = W.rule_high_interest_debt(user)
    assert len(items) == 1
    assert "Card" in items[0].title
    assert items[0].priority is Priority.BLOCKING     # >=15% APR


def test_debt_sorted_by_apr_descending():
    user = base_user(debts=[
        Debt("Cheaper card", 1_000, 0.09),
        Debt("Expensive card", 1_000, 0.27),
    ])
    items = W.rule_high_interest_debt(user)
    assert [i.inputs["apr"] for i in items] == [0.27, 0.09]


# --- rule 4 -------------------------------------------------------------------


def test_hsa_requires_hdhp():
    user = base_user(accounts=[Account(type=AccountType.HSA, hdhp_enrolled=False)])
    assert W.rule_hsa(user)[0].priority is Priority.INFO


def test_hsa_room_uses_coverage_and_age():
    hsa = Account(type=AccountType.HSA, hdhp_enrolled=True,
                  hsa_coverage=HsaCoverage.FAMILY, contributions_ytd=1_000)
    user = base_user(age=56, accounts=[hsa])
    item = W.rule_hsa(user)[0]
    assert item.inputs["annual_limit"] == 9_750       # 8,750 + 1,000 catch-up
    assert item.amount == pytest.approx(8_750)
    assert item.inputs["catch_up_included"] == 1_000


# --- rule 5 -------------------------------------------------------------------


def test_ira_limit_is_shared_across_accounts():
    user = base_user(accounts=[
        Account(type=AccountType.IRA, contributions_ytd=4_000),
        Account(type=AccountType.IRA, contributions_ytd=3_500),
    ])
    assert W.rule_ira(user)[0].priority is Priority.INFO   # 7,500 used


def test_high_earner_gets_the_backdoor_explanation():
    user = base_user(income=400_000)
    item = W.rule_ira(user)[0]
    assert "backdoor" in item.detail.lower()
    assert item.inputs["roth_eligibility"]["status"] == "phased_out"


def test_low_earner_gets_full_roth():
    item = W.rule_ira(base_user(income=80_000))[0]
    assert item.inputs["roth_eligibility"]["allowed"] == 7_500


def test_magi_overrides_income_for_the_phaseout():
    user = base_user(income=400_000, magi=90_000)
    assert W.rule_ira(user)[0].inputs["roth_eligibility"]["status"] == "full"


# --- rule 6 -------------------------------------------------------------------


def test_401k_room_is_per_person_not_per_plan():
    user = base_user(accounts=[
        Account(type=AccountType.TRADITIONAL_401K, contributions_ytd=15_000),
        Account(type=AccountType.TRADITIONAL_401K, contributions_ytd=5_000),
    ])
    item = W.rule_remaining_401k(user)[0]
    assert item.amount == pytest.approx(4_500)   # 24,500 - 20,000


def test_mandatory_roth_catchup_is_surfaced():
    plan = Account(type=AccountType.TRADITIONAL_401K,
                   prior_year_wages_from_employer=200_000)
    user = base_user(age=55, accounts=[plan])
    item = W.rule_remaining_401k(user)[0]
    assert item.inputs["catch_up_must_be_roth"] is True
    assert "Roth" in item.detail


# --- rule 7 -------------------------------------------------------------------


def test_taxable_waits_for_sheltered_room():
    item = W.rule_taxable(base_user())[0]
    assert item.priority is Priority.LOW
    assert item.inputs["remaining_tax_advantaged_room"] > 0


def test_taxable_activates_once_sheltered_space_is_full():
    user = base_user(
        age=34,
        accounts=[
            Account(type=AccountType.CASH, balance=24_000),
            Account(type=AccountType.IRA, contributions_ytd=7_500),
        ],
        has_401k_at_work=False,
    )
    item = W.rule_taxable(user)[0]
    assert item.inputs["remaining_tax_advantaged_room"] == 0
    assert item.priority is Priority.MEDIUM


# --- rule 8 -------------------------------------------------------------------


def test_uninvested_cash_is_flagged():
    ira = Account(type=AccountType.IRA, balance=10_000,
                  holdings=[Holding("VTI", value=4_000, expense_ratio=0.0003)])
    items = W.rule_vehicle(base_user(accounts=[ira]))
    assert items[0].amount == pytest.approx(6_000)
    assert items[0].priority is Priority.HIGH


def test_expensive_fund_is_flagged_with_its_annual_cost():
    taxable = Account(type=AccountType.TAXABLE, balance=10_000,
                      holdings=[Holding("PRICEY", value=10_000, expense_ratio=0.0095)])
    item = W.rule_vehicle(base_user(accounts=[taxable]))[0]
    assert item.inputs["annual_cost"] == pytest.approx(95)


def test_clean_portfolio_produces_no_vehicle_work():
    ira = Account(type=AccountType.IRA, balance=10_000,
                  holdings=[Holding("VTI", value=10_000, expense_ratio=0.0003)])
    items = W.rule_vehicle(base_user(accounts=[ira]))
    assert all(i.priority is Priority.INFO for i in items)


# --- engine -------------------------------------------------------------------


def test_every_rule_reports_something_every_time():
    """The dashboard should never have a silent gap — a rule that doesn't apply says so."""
    for user in (base_user(), base_user(income=400_000, age=61, accounts=[])):
        produced = {i.rule_id for i in W.evaluate(user)}
        assert produced == {r.id for r in W.RULES}


def test_ordering_is_blocking_first_then_waterfall_step():
    user = base_user(
        accounts=[Account(type=AccountType.CASH, balance=1_000)],
        debts=[Debt("Card", 5_000, 0.25)],
    )
    items = W.evaluate(user)
    actionable = [i for i in items if i.priority is not Priority.INFO]
    assert actionable[0].rule_id == "R1_EMERGENCY_FUND"
    steps = [i.step for i in actionable]
    assert steps == sorted(steps)
    assert all(i.priority is Priority.INFO for i in items[len(actionable):])


def test_every_action_is_traceable_to_a_rule():
    for item in W.evaluate(base_user()):
        assert item.rule_id in W.RULES_BY_ID
        assert item.rule_name and item.title and item.detail


def test_allocation_fills_the_waterfall_in_order():
    user = base_user(
        annual_savings_capacity=10_000,
        accounts=[
            Account(type=AccountType.CASH, balance=24_000),
            Account(type=AccountType.TRADITIONAL_401K, employer_match_rate=1.0,
                    employer_match_limit_pct=0.04),
            Account(type=AccountType.HSA, hdhp_enrolled=True),
        ],
    )
    plan = W.allocate(user)
    assert plan["allocated"] == pytest.approx(10_000)
    assert plan["unallocated"] == pytest.approx(0)
    funded = [s for s in plan["steps"] if s["funded"]]
    assert funded[0]["rule_id"] == "R2_EMPLOYER_MATCH"       # match before HSA
    assert funded[0]["funded"] == pytest.approx(4_000)
    assert funded[1]["rule_id"] == "R4_HSA"
    assert funded[1]["funded"] == pytest.approx(4_400)
    assert funded[-1]["fully_funded"] is False               # capacity ran out


def test_allocation_without_capacity_reports_need_only():
    plan = W.allocate(base_user())
    assert plan["annual_savings_capacity"] is None
    assert all(s["funded"] is None for s in plan["steps"])


def test_partial_emergency_fund_does_not_outrank_the_match():
    """Past the 3-month floor the top-up is a MEDIUM, so a guaranteed match gets
    funded first even though it sits lower in the waterfall."""
    user = base_user(
        annual_savings_capacity=5_000,
        accounts=[
            Account(type=AccountType.CASH, balance=16_000),   # 4 months: over floor
            Account(type=AccountType.TRADITIONAL_401K, employer_match_rate=1.0,
                    employer_match_limit_pct=0.03),
        ],
    )
    funded = [s for s in W.allocate(user)["steps"] if s["funded"]]
    assert funded[0]["rule_id"] == "R2_EMPLOYER_MATCH"


def test_blocking_emergency_fund_still_outranks_everything():
    user = base_user(
        annual_savings_capacity=5_000,
        accounts=[
            Account(type=AccountType.CASH, balance=2_000),
            Account(type=AccountType.TRADITIONAL_401K, employer_match_rate=1.0,
                    employer_match_limit_pct=0.03),
        ],
    )
    funded = [s for s in W.allocate(user)["steps"] if s["funded"]]
    assert funded[0]["rule_id"] == "R1_EMERGENCY_FUND"


def test_no_workplace_plan_still_reports():
    """A part-time or hourly worker with no 401(k) must not see step 2 vanish."""
    user = base_user(has_401k_at_work=False, accounts=[])
    items = W.rule_employer_match(user)
    assert len(items) == 1
    assert items[0].priority is Priority.INFO
    assert items[0].inputs["has_401k_at_work"] is False


def test_every_rule_reports_for_a_minimal_starter_profile():
    """The shipped seed is a student with no 401(k) and no HSA — every rule still speaks."""
    user = base_user(has_401k_at_work=False, income=13_500,
                     accounts=[Account(type=AccountType.CASH, balance=800)])
    assert {i.rule_id for i in W.evaluate(user)} == {r.id for r in W.RULES}


def test_ira_room_is_capped_by_earned_income():
    user = base_user(income=4_000, accounts=[Account(type=AccountType.CASH, balance=24_000)])
    item = W.rule_ira(user)[0]
    assert item.amount == pytest.approx(4_000)
    assert item.inputs["capped_by_earned_income"] is True
    assert item.inputs["statutory_limit"] == 7_500


def test_earned_income_cap_is_explained_not_just_applied():
    user = base_user(income=4_000, accounts=[Account(type=AccountType.CASH, balance=24_000)])
    detail = W.rule_ira(user)[0].detail
    assert "than you earned" in detail
    # And it stays quiet when the cap doesn't bind.
    assert "than you earned" not in W.rule_ira(base_user(income=80_000))[0].detail
