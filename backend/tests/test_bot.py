"""The free-text bot: routing, honesty, and the one invariant that matters — it
selects and parameterises, but never computes a number itself."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bot
import knowledge
import phrasings as P
import qa
import scenario
from models import Account, AccountType, Debt, Goal, User


def rich_user() -> User:
    return User(
        age=40, income=120_000, annual_savings_capacity=30_000,
        goal=Goal(monthly_expenses=4_000, emergency_fund_months=6),
        accounts=[
            Account(type=AccountType.CASH, nickname="Savings", balance=30_000),
            Account(type=AccountType.TRADITIONAL_401K, nickname="Work 401(k)", balance=50_000,
                    contributions_ytd=2_000, employer_match_rate=0.5, employer_match_limit_pct=0.06),
            Account(type=AccountType.IRA, nickname="Roth IRA", balance=10_000, contributions_ytd=1_000),
            Account(type=AccountType.HSA, nickname="HSA", balance=3_000, hdhp_enrolled=True),
            Account(type=AccountType.TAXABLE, nickname="Brokerage", balance=5_000),
        ],
        debts=[Debt("Credit card", 3_000, 0.22)],
    )


def top(text, user=None, ctx=None):
    return bot.answer(text, user or rich_user(), 2026, ctx)["results"][0]


# --- the benchmark --------------------------------------------------------------


def test_benchmark_student_debt_question(rich_client):
    """The question this whole feature exists to answer."""
    body = rich_client.post("/api/ask", json={
        "question": "How should I plan around my 35K of student debt?"}).get_json()
    assert body["status"] == "answered"
    r = body["results"][0]
    assert r["kind"] == "scenario" and r["id"] == "debt_strategy"
    a = r["answer"]
    assert "$35,000" in a["summary"]
    assert a["assumptions"], "the assumed rate must be disclosed"
    assert any(x["label"] == "Interest rate" for x in a["assumptions"])
    assert a["save_hint"]["path"] == "/api/debts" and a["save_hint"]["body"]["balance"] == 35000
    assert "R3_HIGH_INTEREST_DEBT" in a["sources"]
    assert len(a["sections"]) >= 3
    assert body["disclaimer"]


def test_scenarios_never_touch_the_stored_profile(rich_client):
    """The safety property: every scenario runs on a copy."""
    before = rich_client.get("/api/profile").get_json()
    for q in ["How should I plan around my 35K of student debt?", "i got 10k what do i do with it",
              "what if i made 75k", "what if i saved 300 a month", "can i retire at 55"]:
        assert rich_client.post("/api/ask", json={"question": q}).status_code == 200
    after = rich_client.get("/api/profile").get_json()
    assert json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)


def test_debt_verdict_flips_at_the_threshold_from_the_data_file():
    """The 7.5% line is read from limits_2026.json, not hardcoded."""
    import limits as L
    cutoff = L.load_limits(2026)["thresholds"]["high_interest_debt_apr"]
    below = top(f"i owe 10k on a personal loan at {cutoff * 100 - 1:.0f}%")["answer"]
    above = top(f"i owe 10k on a personal loan at {cutoff * 100 + 1:.0f}%")["answer"]
    assert "below the line" in below["summary"]
    assert "step 3" in above["summary"]


def test_intent_without_a_number_asks_rather_than_guesses():
    r = top("how should i handle my student debt")
    assert r["status"] == "needs_input" and r["id"] == "debt_strategy"
    assert "how much" in r["prompt"].lower()
    assert r["answer"] is None


# --- the matching table ---------------------------------------------------------


@pytest.mark.parametrize("text,kind,ident", P.ALL_ROUTED, ids=[t for t, _, _ in P.ALL_ROUTED])
def test_matching_table(text, kind, ident):
    r = top(text)
    assert r["status"] == "answered", (r["status"], r["kind"], r["id"])
    assert r["kind"] == kind and r["id"] == ident, (r["kind"], r["id"])


@pytest.mark.parametrize("text", [t for t, _, _ in P.AMBIGUOUS])
def test_ambiguous_returns_choices_not_an_answer(text):
    r = top(text)
    assert r["status"] == "ambiguous"
    assert r["answer"] is None and len(r["suggestions"]) >= 2


def test_gibberish_is_unmatched_with_a_browse_list():
    r = top("purple monkey dishwasher")
    assert r["status"] == "unmatched" and r["answer"] is None
    assert r["browse"] and r["knowledge"]


def test_empty_question_is_a_400(client):
    assert client.post("/api/ask", json={"question": "   "}).status_code == 400
    assert client.post("/api/ask", json={}).status_code == 400


# --- honesty rules --------------------------------------------------------------


def test_waiting_for_a_dip_is_answered_not_declined():
    r = top("should i wait for the market to drop before investing")
    assert r["status"] == "answered" and r["id"] == "market_timing"


def test_each_decline_fires_on_several_phrasings():
    for did in knowledge.DECLINES:
        hits = [t for t, k, i in P.DECLINE if i == did]
        assert len(hits) >= 2, did
        for text in hits:
            r = top(text)
            assert r["status"] == "declined" and r["id"] == did, (text, r["status"], r["id"])
            assert r["redirects"], text


def test_personal_answers_are_identical_to_qa_ask():
    """The invariant: routed through the bot, a personal answer is byte-for-byte what
    qa.ask() returns. The bot selects; it never recomputes."""
    user = rich_user()
    for text, qid in [("how much can i put in my hsa", "how_much_can_i_put_in"),
                      ("am i leaving employer match on the table", "am_i_missing_match"),
                      ("where should my next dollar go", "next_dollar")]:
        r = top(text, user)
        assert r["id"] == qid
        assert r["answer"] == qa.ask(qid, user, 2026)["answer"]


def test_output_is_deterministic():
    a = bot.answer("what is an expense ratio and should i wait for a dip", rich_user(), 2026)
    b = bot.answer("what is an expense ratio and should i wait for a dip", rich_user(), 2026)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# --- typo repair ----------------------------------------------------------------


@pytest.mark.parametrize("text,fixed", P.TYPOS)
def test_typos_are_repaired_and_reported(text, fixed):
    r = bot.answer(text, rich_user(), 2026)
    assert fixed in {c["to"] for c in r["corrections"]}


def test_short_words_are_never_fuzzy_matched():
    assert bot._repair("roth") is None
    assert bot._repair("both") is None
    assert not bot.answer("roth", rich_user(), 2026)["corrections"]


# --- bigrams --------------------------------------------------------------------


def test_phrase_order_carries_weight():
    """Bigrams: "hold for a year" is the capital-gains phrase and is recognised as one;
    the same words scrambled share no phrase with any entry and rank it less clearly."""
    ordered, scrambled = bot.Query("hold for a year"), bot.Query("year a for hold")
    assert ordered.bigrams and not scrambled.bigrams
    ranked = bot.explain("hold for a year")
    assert ranked[0]["id"] == "capital_gains_short_vs_long"
    margin_ordered = ranked[0]["score"] - ranked[1]["score"]
    ranked_s = bot.explain("year a for hold")
    margin_scrambled = ranked_s[0]["score"] - ranked_s[1]["score"]
    assert margin_ordered >= margin_scrambled


# --- multi-part -----------------------------------------------------------------


@pytest.mark.parametrize("text,ids", P.MULTI, ids=[t for t, _ in P.MULTI])
def test_two_questions_get_two_answers(text, ids):
    r = bot.answer(text, rich_user(), 2026)
    assert r["multi_part"] and [x["id"] for x in r["results"]] == ids


@pytest.mark.parametrize("text", P.NO_SPLIT)
def test_single_concepts_are_never_split(text):
    r = bot.answer(text, rich_user(), 2026)
    assert not r["multi_part"], [x["id"] for x in r["results"]]


# --- follow-up context ----------------------------------------------------------


@pytest.mark.parametrize("first,follow,ident", P.FOLLOW_UPS)
def test_follow_up_resolves_with_context(first, follow, ident):
    user = rich_user()
    r1 = bot.answer(first, user, 2026)
    r2 = bot.answer(follow, user, 2026, r1["context"])
    assert r2["results"][0]["id"] == ident


def test_bare_follow_up_is_only_answerable_with_context():
    """"how much?" on its own is nothing. After "can I contribute to a Roth IRA?" it is
    the limits question — the previous turn is the entire meaning."""
    user = rich_user()
    alone = bot.answer("how much?", user, 2026)["results"][0]
    assert alone["status"] in ("unmatched", "ambiguous")
    ctx = bot.answer("can i contribute to a roth ira", user, 2026)["context"]
    after = bot.answer("how much?", user, 2026, ctx)["results"][0]
    assert after["status"] == "answered" and after["id"] == "how_much_can_i_put_in"


def test_previous_entity_comes_from_the_question():
    ctx = bot.answer("How should I plan around my 35K of student debt?", rich_user(), 2026)["context"]
    assert ctx["previous_entity"] == "studentloan"


def test_context_does_not_hijack_a_fresh_question():
    user = rich_user()
    ctx = bot.answer("can i contribute to a roth ira", user, 2026)["context"]
    r = bot.answer("how big should my emergency fund be and where should it live", user, 2026, ctx)
    assert r["results"][0]["id"] == "emergency_fund_sizing"


def test_context_is_echoed_for_the_next_turn(rich_client):
    body = rich_client.post("/api/ask", json={"question": "what is an expense ratio"}).get_json()
    assert body["context"]["previous_id"] == "expense_ratios"
    assert body["context"]["previous_topic"] == "Investing basics"


# --- round-trip coverage --------------------------------------------------------


def test_every_knowledge_entry_is_reachable_by_its_own_question():
    misses = []
    for key, e in knowledge.ENTRIES.items():
        r = top(e["question"])
        if not (r["status"] == "answered" and r["id"] == key):
            misses.append((key, r["kind"], r["id"]))
    assert not misses, misses


def test_every_knowledge_entry_is_reachable_by_two_of_its_keywords():
    weak = []
    for key, e in knowledge.ENTRIES.items():
        hits = sum(1 for kw in e["keywords"] if (r := top(kw))["status"] == "answered" and r["id"] == key)
        if hits < 2:
            weak.append((key, hits))
    assert not weak, weak


def test_every_personal_question_is_reachable_by_its_own_text():
    for qid, q in qa.QUESTIONS.items():
        r = top(q["question"])
        assert r["status"] == "answered" and r["id"] == qid, (qid, r["kind"], r["id"])


# --- the knowledge endpoints ----------------------------------------------------


def test_knowledge_endpoints(client):
    idx = client.get("/api/knowledge").get_json()
    assert [t["topic"] for t in idx] == knowledge.TOPIC_ORDER
    assert sum(len(t["entries"]) for t in idx) == len(knowledge.ENTRIES)
    one = client.get("/api/knowledge/expense_ratios").get_json()
    assert one["key"] == "expense_ratios" and one["disclaimer"]
    assert client.get("/api/knowledge/nope").status_code == 404
