"""The federal tax estimate behind Roth-or-traditional. Figures checked by hand
against the 2026 tables (Rev. Proc. 2025-32)."""

import pytest

import tax
from models import FilingStatus, Goal, User


@pytest.mark.parametrize("taxable, owed, rate", [
    (0, 0, 0.0),
    (-5_000, 0, 0.0),
    (12_400, 1_240, 0.12),                 # exactly the top of 10%: next dollar is 12%
    (50_000, 5_752, 0.12),                 # 1,240 + 37,600 × 12%
    (100_000, 16_712, 0.22),
    (1_000_000, 1_000_000 * 0.37 - (1_000_000 * 0.37 - tax.tax_on(1_000_000, "single", 2026)), 0.37),
])
def test_single_brackets(taxable, owed, rate):
    assert tax.tax_on(taxable, "single", 2026) == pytest.approx(owed)
    assert tax.marginal_rate(taxable, "single", 2026) == rate


def test_joint_brackets_are_wider():
    assert tax.marginal_rate(60_000, "married_filing_jointly", 2026) == 0.12
    assert tax.marginal_rate(60_000, "single", 2026) == 0.22


def test_standard_deduction_and_65_plus():
    assert tax.standard_deduction("single", 2026) == 16_100
    assert tax.standard_deduction("single", 2026, age=66) == 18_150
    assert tax.standard_deduction("married_filing_jointly", 2026, age=66) == 33_850


@pytest.mark.parametrize("ss, other, taxable", [
    (24_000, 0, 0),                        # provisional 12k: none taxed
    (24_000, 16_000, 1_500),               # provisional 28k: half the excess over 25k
    (30_000, 40_000, 22_350),              # 85%(55k−34k) + 4,500
    (30_000, 200_000, 25_500),             # capped at 85% of benefits
])
def test_social_security_taxation(ss, other, taxable):
    assert tax.taxable_social_security(ss, other, "single", 2026) == pytest.approx(taxable)


def _user(**kw):
    base = dict(age=30, income=100_000, filing_status=FilingStatus.SINGLE,
                goal=Goal(monthly_expenses=4_000))
    base.update(kw)
    return User(**base)


def test_student_under_the_deduction_pays_zero_now_so_roth():
    c = tax.compare(_user(income=13_500, goal=Goal(monthly_expenses=950,
                                                   retirement_monthly_spending=2_000)), 2026)
    assert c["now"]["marginal_rate"] == 0.0
    assert c["retirement"]["marginal_rate"] == 0.10
    assert c["verdict"] == "roth" and c["per_1000"] == -100


def test_high_earner_retiring_modestly_goes_traditional():
    c = tax.compare(_user(income=180_000, goal=Goal(monthly_expenses=5_000,
                                                    social_security_monthly=2_500)), 2026)
    assert c["now"]["marginal_rate"] == 0.24
    assert c["retirement"]["marginal_rate"] == 0.12
    assert c["verdict"] == "traditional" and c["per_1000"] == 120


def test_a_tie_goes_to_roth():
    c = tax.compare(_user(income=40_000, goal=Goal(monthly_expenses=3_000)), 2026)
    assert c["now"]["marginal_rate"] == c["retirement"]["marginal_rate"] == 0.12
    assert c["verdict"] == "roth"


def test_the_users_own_answer_wins_but_the_estimate_is_still_shown():
    c = tax.compare(_user(expects_lower_bracket_in_retirement=False), 2026)
    assert c["verdict"] == "roth" and c["estimated_verdict"] == "traditional"
    assert c["overridden"] is True


def test_no_spending_figure_means_no_verdict():
    c = tax.compare(_user(goal=Goal()), 2026)
    assert c["retirement"] is None and c["verdict"] == "unknown"
    assert tax.expects_lower(_user(goal=Goal()), 2026) is None


def test_the_ira_step_explains_with_both_rates(rich_client):
    """rich_client: $120k single ($103,900 taxable), $4k a month → 22% now, 12% later."""
    rich_client.patch("/api/profile", json={"expects_lower_bracket_in_retirement": None})
    detail = rich_client.get("/api/actions/R5_IRA").get_json()["actions"][0]["detail"]
    assert "22%" in detail and "12%" in detail


def test_tax_endpoint_and_what_if(client):
    body = client.get("/api/tax").get_json()
    assert body["now"]["marginal_rate"] == 0.0 and body["verdict"] == "roth"
    rich = client.get("/api/tax?income=250000").get_json()
    assert rich["now"]["marginal_rate"] == 0.32
    assert client.get("/api/profile").get_json()["income"] == 13_500     # never saved
