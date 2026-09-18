"""Retirement age as a real setting: the maths, the advice it drives, the what-if
projection, and the endpoints that save it."""

import pytest

import projection as P
import retirement as R
import waterfall as W
from models import Account, AccountType, Assumptions, Goal, Priority, User


def make_user(goal=None, **kw) -> User:
    defaults = dict(
        age=35, income=90_000, annual_savings_capacity=15_000,
        accounts=[
            Account(type=AccountType.CASH, balance=20_000),     # past the 6-month target
            Account(type=AccountType.IRA, balance=40_000, contributions_ytd=7_000),
        ],
    )
    defaults.update(kw)
    goal_fields = {"monthly_expenses": 3_000, "emergency_fund_months": 6, "retirement_age": 67}
    goal_fields.update(goal or {})
    return User(goal=Goal(**goal_fields), **defaults)


def ready(user: User) -> dict:
    investing = W.annual_investing(user, 2026)
    return R.readiness(user, 2026, R.invested_balance(user), investing["total"],
                       investing["years_until_investing"])


def r9(user: User):
    return W.rule_retirement_age(user, 2026)


# --- the maths -----------------------------------------------------------------


def test_social_security_factor_matches_ssa():
    assert R.social_security_factor(62) == pytest.approx(0.70)
    assert R.social_security_factor(64) == pytest.approx(0.80)
    assert R.social_security_factor(67) == pytest.approx(1.00)
    assert R.social_security_factor(70) == pytest.approx(1.24)


def test_rmd_age_follows_birth_year():
    assert R.rmd_age(make_user(age=70), 2026) == 73    # born 1956
    assert R.rmd_age(make_user(age=40), 2026) == 75    # born 1986


def test_growing_contributions_match_a_year_by_year_sum():
    balance = 0.0
    for year in range(10):
        balance = balance * 1.07 + 1_000 * 1.03 ** year
    assert R.future_value(0, 1_000, 0.07, 10, growth=0.03) == pytest.approx(balance)
    assert R.contributions_paid(1_000, 10, growth=0.03) == pytest.approx(
        sum(1_000 * 1.03 ** y for y in range(10)))


def test_needed_is_a_plain_sum_when_real_returns_are_zero():
    user = make_user(goal={"retirement_age": 65},
                     assumptions=Assumptions(retirement_return_rate=0.025, inflation=0.025))
    assert R.needed_at_retirement(user) == pytest.approx(36_000 * 30)       # 65 to 95


def test_social_security_only_reduces_the_need_from_the_claim_age():
    zero_real = Assumptions(retirement_return_rate=0.025, inflation=0.025)
    without = make_user(goal={"retirement_age": 60}, assumptions=zero_real)
    with_ss = make_user(goal={"retirement_age": 60, "social_security_monthly": 2_000,
                              "social_security_claim_age": 67}, assumptions=zero_real)
    saved = R.needed_at_retirement(without) - R.needed_at_retirement(with_ss)
    assert saved == pytest.approx(24_000 * (95 - 67))


# --- readiness -----------------------------------------------------------------


def test_retiring_earlier_means_less_saved_and_more_needed():
    early, late = ready(make_user(goal={"retirement_age": 50})), ready(make_user())
    assert early["projected_at_retirement"] < late["projected_at_retirement"]
    assert early["needed_at_retirement"] > late["needed_at_retirement"]


def test_the_extra_savings_figure_actually_closes_the_gap():
    user = make_user(goal={"retirement_age": 45})
    r = ready(user)
    assert r["status"] == "short"
    closed = R.readiness(user, 2026, R.invested_balance(user),
                         15_000 + r["extra_savings_per_year"], 0.0)
    assert closed["funded_ratio"] == pytest.approx(1.0, abs=0.002)


def test_earliest_age_is_affordable_and_the_year_before_is_not():
    user = make_user()
    earliest = ready(user)["earliest_retirement_age"]
    assert earliest is not None and earliest > user.age
    user.goal.retirement_age = earliest
    assert ready(user)["status"] == "on_track"
    user.goal.retirement_age = earliest - 1
    assert ready(user)["status"] != "on_track"


def test_sustainable_spending_is_exactly_what_the_plan_pays_for():
    user = make_user(goal={"retirement_age": 45})
    user.goal.retirement_monthly_spending = ready(user)["sustainable_monthly_spending"]
    assert ready(user)["funded_ratio"] == pytest.approx(1.0, abs=0.01)


def test_money_runs_out_only_when_short():
    assert ready(make_user())["money_lasts_to_age"] is None
    short = ready(make_user(goal={"retirement_age": 45}))
    assert 45 <= short["money_lasts_to_age"] < 95


def test_raising_savings_each_year_grows_the_plan():
    rising = make_user(assumptions=Assumptions(contribution_growth=0.03))
    assert ready(rising)["projected_at_retirement"] > ready(make_user())["projected_at_retirement"]


# --- rule 9: the age changes the advice ----------------------------------------


def test_bridge_only_applies_before_59_and_a_half():
    assert R.bridge(make_user(goal={"retirement_age": 60}))["applies"] is False
    bridge = R.bridge(make_user(goal={"retirement_age": 50}))
    assert bridge["applies"] is True and bridge["bridge_years"] == 9.5


def test_rule_of_55_counts_the_401k_you_leave():
    plan = Account(type=AccountType.TRADITIONAL_401K, balance=100_000, contributions_ytd=10_000)
    accounts = [Account(type=AccountType.CASH, balance=20_000), plan]
    assert R.bridge(make_user(goal={"retirement_age": 56}, accounts=accounts))[
        "reachable_401k_by_retirement"] > 0
    assert R.bridge(make_user(goal={"retirement_age": 54}, accounts=accounts))[
        "reachable_401k_by_retirement"] == 0


def test_early_retiree_saves_reachable_money_after_the_ira_and_before_extra_401k():
    user = make_user(
        goal={"retirement_age": 50},
        accounts=[
            Account(type=AccountType.CASH, balance=20_000),
            Account(type=AccountType.TRADITIONAL_401K, balance=30_000, contributions_ytd=5_400,
                    employer_match_rate=0.5, employer_match_limit_pct=0.06,
                    employer_match_received_ytd=2_700),
            Account(type=AccountType.IRA, balance=40_000),
        ],
    )
    bridge = next(i for i in r9(user) if i.amount)
    assert bridge.priority is Priority.HIGH
    assert bridge.account_type is AccountType.TAXABLE
    order = [i.rule_id for i in W.prioritized(user)]
    assert order.index("R5_IRA") < order.index("R9_RETIREMENT_AGE") < order.index("R6_REMAINING_401K")
    funded = [s["rule_id"] for s in W.allocate(user)["steps"]]
    assert funded.index("R9_RETIREMENT_AGE") < funded.index("R6_REMAINING_401K")


def test_retiring_before_65_flags_health_coverage():
    item = next(i for i in r9(make_user(goal={"retirement_age": 60})) if "Medicare" in i.title)
    assert item.inputs["years_without_medicare"] == 5


def test_working_past_the_rmd_age_is_flagged():
    items = r9(make_user(age=60, goal={"retirement_age": 76}))
    assert any("Required withdrawals" in i.title for i in items)


def test_a_conventional_age_is_informational():
    items = r9(make_user())
    assert len(items) == 1 and items[0].priority is Priority.INFO


# --- rule 10: does it add up ---------------------------------------------------


def test_readiness_puts_a_number_on_every_lever():
    item = W.rule_readiness(make_user(goal={"retirement_age": 45}))[0]
    assert item.priority is Priority.HIGH
    assert item.amount == item.inputs["extra_savings_per_year"]
    assert "retire at" in item.detail and "a month in retirement" in item.detail


def test_on_track_is_informational():
    rich = make_user(accounts=[Account(type=AccountType.CASH, balance=20_000),
                               Account(type=AccountType.IRA, balance=3_000_000)])
    assert W.rule_readiness(rich)[0].priority is Priority.INFO


def test_missing_spending_asks_for_it():
    item = W.rule_readiness(make_user(goal={"monthly_expenses": 0}))[0]
    assert item.priority is Priority.LOW and "spend" in item.title


def test_readiness_is_not_funded_from_this_years_capacity():
    steps = W.allocate(make_user(goal={"retirement_age": 45}))["steps"]
    assert all(s["rule_id"] != "R10_READINESS" for s in steps)


# --- validation and what-ifs ---------------------------------------------------


@pytest.mark.parametrize("goal, assumptions, message", [
    ({"retirement_age": 10}, {}, "retirement age"),
    ({"retirement_age": 70, "plan_to_age": 70}, {}, "last past age 70"),
    ({"social_security_claim_age": 61}, {}, "between ages 62 and 70"),
    ({"retirement_monthly_spending": -1}, {}, "can't be negative"),
    ({}, {"return_rate": 0.30}, "return while saving"),
    ({}, {"inflation": -0.01}, "inflation"),
])
def test_settings_that_cannot_be_planned_are_rejected(goal, assumptions, message):
    user = make_user(goal=goal, assumptions=Assumptions(**assumptions))
    with pytest.raises(ValueError, match=message):
        R.validate(user)


def test_what_if_never_touches_the_saved_profile():
    user = make_user()
    trial = P.with_overrides(user, {"retirement_age": "50", "retirement_monthly_spending": ""})
    assert trial.goal.retirement_age == 50 and trial.goal.retirement_monthly_spending is None
    assert user.goal.retirement_age == 67


@pytest.mark.parametrize("overrides", [
    {"age": "30"}, {"retirement_age": "soon"}, {"retirement_age": "50.5"},
    {"return_rate": "inf"}, {"plan_to_age": "40"}, {"retirement_age": ""},
])
def test_what_if_rejects_bad_input(overrides):
    with pytest.raises(ValueError):
        P.with_overrides(make_user(), overrides)


def test_projection_follows_the_chosen_retirement_age():
    result = P.project(P.with_overrides(make_user(), {"retirement_age": "50"}))
    assert result["points"][-1]["age"] == 50 and result["points"][-1]["is_retirement"]
    phases = {p["age"]: p["phase"] for p in result["series"]}
    assert phases[50] == "saving" and phases[51] == "retired"
    assert result["series"][-1]["age"] == 95
    assert result["retirement"]["retirement_age"] == 50


@pytest.mark.parametrize("retirement_age", [67, 45])
def test_readiness_agrees_with_the_chart(retirement_age):
    user = make_user(goal={"retirement_age": retirement_age})
    result = P.project(user)
    n = result["years_to_retirement"]
    at_retirement = result["series"][n]["following_plan"] / (1 + user.assumptions.inflation) ** n
    assert at_retirement == pytest.approx(result["retirement"]["projected_at_retirement"], abs=2)
    assert result["retirement"]["plan_runs_out_age"] == result["retirement"]["money_lasts_to_age"]


def test_own_return_assumption_becomes_the_default_scenario():
    user = make_user(assumptions=Assumptions(return_rate=0.06))
    result = P.project(user)
    assert result["scenario"] == "yours" and result["scenarios"]["yours"]["rate"] == 0.06
    standard = P.project(make_user())
    assert standard["scenario"] == "middling" and "yours" not in standard["scenarios"]


# --- endpoints -----------------------------------------------------------------


def test_goal_endpoint_saves_retirement_settings_and_validates(client):
    saved = client.put("/api/goal", json={
        "retirement_age": 50, "plan_to_age": 90, "social_security_monthly": 1_800,
    }).get_json()
    assert saved["retirement_age"] == 50 and saved["plan_to_age"] == 90
    assert client.get("/api/profile").get_json()["goal"]["social_security_monthly"] == 1_800

    bad = client.put("/api/goal", json={"retirement_age": 10})
    assert bad.status_code == 400 and "retirement age" in bad.get_json()["error"]
    assert client.get("/api/profile").get_json()["goal"]["retirement_age"] == 50


def test_assumptions_endpoint_merges_and_validates(client):
    body = client.put("/api/assumptions", json={"return_rate": 0.06}).get_json()
    assert body["return_rate"] == 0.06 and body["inflation"] == 0.025
    assert client.put("/api/assumptions", json={"inflation": 0.5}).status_code == 400


def test_projection_what_if_is_not_saved(client):
    assert client.get("/api/projection?retirement_age=50").get_json()["retirement_age"] == 50
    assert client.get("/api/profile").get_json()["goal"]["retirement_age"] == 67
    assert client.get("/api/projection?retirement_age=abc").status_code == 400
    assert client.get("/api/projection?plan_to_age=40").status_code == 400


def test_action_list_includes_the_retirement_rules(client):
    ids = {a["rule_id"] for a in client.get("/api/actions").get_json()["actions"]}
    assert {"R9_RETIREMENT_AGE", "R10_READINESS"} <= ids
