import pytest

import qa
from models import (
    Account, AccountType, Debt, FilingStatus, Goal, Holding, HsaCoverage, User,
)


def base_user(**kw) -> User:
    defaults = dict(
        age=34, income=100_000, filing_status=FilingStatus.SINGLE,
        goal=Goal(monthly_expenses=4_000),
        accounts=[Account(type=AccountType.CASH, balance=24_000)],
    )
    defaults.update(kw)
    return User(**defaults)


def test_every_question_answers_for_any_user():
    """No question may blow up or come back empty, whatever state the user is in —
    including a brand-new profile with nothing filled in."""
    users = [
        base_user(),
        User(age=22, income=0),                                   # empty profile
        base_user(age=61, income=400_000, annual_savings_capacity=50_000),
        base_user(debts=[Debt("Card", 5_000, 0.24)]),
    ]
    for user in users:
        for qid in qa.QUESTIONS:
            result = qa.ask(qid, user)
            assert result["answer"]["summary"], f"{qid} produced no summary"
            assert len(result["answer"]["detail"]) > 80, f"{qid} detail is a stub"
            assert result["answer"]["sources"], f"{qid} is untraceable"


def test_follow_ups_all_resolve():
    """A dead link in the Q&A tree is a dead end for the user."""
    for qid in qa.QUESTIONS:
        for follow in qa.ask(qid, base_user())["follow_ups"]:
            assert follow["id"] in qa.QUESTIONS
            assert follow["question"]


def test_index_covers_every_question_exactly_once():
    listed = [q["id"] for topic in qa.index() for q in topic["questions"]]
    assert sorted(listed) == sorted(qa.QUESTIONS)
    assert [t["topic"] for t in qa.index()] == qa.TOPIC_ORDER


def test_next_dollar_matches_the_waterfall():
    """The Q&A and the dashboard must never disagree about what comes next."""
    import waterfall as W

    user = base_user(
        accounts=[Account(type=AccountType.CASH, balance=2_000)],
        debts=[Debt("Card", 5_000, 0.25)],
    )
    answer = qa.ask("next_dollar", user)["answer"]
    assert answer["summary"] == W.prioritized(user)[0].title
    assert answer["sources"] == [W.prioritized(user)[0].rule_id]


def test_roth_answer_tracks_income():
    low = qa.ask("can_i_do_roth", base_user(income=80_000))["answer"]
    assert low["summary"].startswith("Yes")

    high = qa.ask("can_i_do_roth", base_user(income=400_000))["answer"]
    assert "backdoor" in high["detail"].lower()

    mid = qa.ask("can_i_do_roth", base_user(income=160_000))["answer"]
    assert mid["summary"].startswith("Partly")


def test_roth_or_traditional_uses_the_users_own_answer():
    lower = qa.ask("roth_or_traditional", base_user(expects_lower_bracket_in_retirement=True))
    assert "traditional is the better fit" in lower["answer"]["summary"]

    higher = qa.ask("roth_or_traditional", base_user(expects_lower_bracket_in_retirement=False))
    assert "Roth is the better fit" in higher["answer"]["summary"]

    # No answer given: the estimate decides. $100k is 22% now; $4k a month in
    # retirement is 12% — traditional.
    estimated = qa.ask("roth_or_traditional", base_user())
    assert "traditional comes out ahead" in estimated["answer"]["summary"]

    # Nothing to estimate the retirement side from.
    blank = qa.ask("roth_or_traditional", base_user(goal=Goal()))
    assert "tax rate now against in retirement" in blank["answer"]["summary"]


def test_debt_question_flips_on_the_cutoff():
    expensive = qa.ask("debt_or_invest", base_user(debts=[Debt("Card", 4_000, 0.24)]))
    assert "Pay off Card first" in expensive["answer"]["summary"]

    cheap = qa.ask("debt_or_invest", base_user(debts=[Debt("Auto", 4_000, 0.04)]))
    assert cheap["answer"]["summary"].startswith("Invest")


def test_what_to_invest_in_flags_idle_cash_first():
    ira = Account(type=AccountType.IRA, balance=10_000,
                  holdings=[Holding("VTI", value=3_000, expense_ratio=0.0003)])
    answer = qa.ask("what_to_invest_in", base_user(accounts=[ira]))["answer"]
    assert "$7,000" in answer["summary"]


def test_explainer_questions_reuse_the_content_module():
    """"What is an HSA?" must not be a second copy of the explanation."""
    import content

    hsa = Account(type=AccountType.HSA, hdhp_enrolled=True,
                  hsa_coverage=HsaCoverage.SELF_ONLY, contributions_ytd=400)
    user = base_user(accounts=[hsa])
    answer = qa.ask("what_is_hsa", user)["answer"]
    assert answer["detail"] == content.CONTENT["hsa"]["layer2"]
    assert answer["summary"] == content.layer1("hsa", user)


def test_unknown_question_raises():
    with pytest.raises(KeyError):
        qa.ask("what_are_rsus", base_user())
