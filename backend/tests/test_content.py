import content
from models import Account, AccountType, FilingStatus, Goal, HsaCoverage, User

FOUNDATIONAL_FIVE = {"401k", "ira", "hsa", "taxable", "index_funds"}


def test_all_five_have_all_three_layers():
    assert set(content.CONTENT) == FOUNDATIONAL_FIVE
    for key in FOUNDATIONAL_FIVE:
        page = content.account_page(key)
        assert page["layer1"]["decision"]
        assert len(page["layer2"]["why"]) > 200        # a real paragraph, not a stub
        assert len(page["layer3"]["details"]) >= 5
        assert page["disclaimer"] is content.DISCLAIMER


def test_every_account_type_has_a_learning_log():
    assert set(content.LEARNING_LOGS) == FOUNDATIONAL_FIVE
    for log in content.LEARNING_LOGS.values():
        assert log["summary"] and len(log["body"]) > 400


def test_layer1_uses_the_users_numbers():
    user = User(
        age=34, income=100_000, filing_status=FilingStatus.SINGLE,
        goal=Goal(monthly_expenses=4_000),
        accounts=[
            Account(type=AccountType.TRADITIONAL_401K, employer_match_rate=0.5,
                    employer_match_limit_pct=0.06, contributions_ytd=0),
            Account(type=AccountType.HSA, hdhp_enrolled=True,
                    hsa_coverage=HsaCoverage.SELF_ONLY, contributions_ytd=400),
        ],
    )
    assert "$3,000" in content.layer1("401k", user)     # unclaimed match
    assert "$4,000" in content.layer1("hsa", user)      # 4,400 - 400 of room


def test_layer1_high_earner_points_at_the_backdoor():
    user = User(age=40, income=400_000, filing_status=FilingStatus.SINGLE)
    assert "backdoor" in content.layer1("ira", user).lower()


def test_layer3_numbers_track_the_seed_data():
    numbers = content.key_numbers("401k")
    assert numbers["base_employee_deferral"] == 24_500
    assert content.key_numbers("hsa")["family"] == 8_750


def test_waterfall_explainer_covers_every_rule():
    import waterfall as W

    explained = {s["rule_id"] for s in content.waterfall_explainer()["steps"]}
    assert explained == {r.id for r in W.RULES}


def test_content_is_educational_not_directive():
    """Legal framing from the scope doc: mechanics, not 'buy this'."""
    banned = ("you should buy", "we recommend buying", "sell your", "guaranteed profit")
    for key in FOUNDATIONAL_FIVE:
        blob = (content.CONTENT[key]["layer2"] + " ".join(content.CONTENT[key]["layer3"])
                + content.LEARNING_LOGS[key]["body"]).lower()
        for phrase in banned:
            assert phrase not in blob


def test_glossary_covers_the_jargon_the_ui_shows():
    required = {
        "401k", "ira", "roth", "traditional", "hsa", "hdhp", "employer_match",
        "taxable_brokerage", "index_fund", "target_date_fund", "expense_ratio",
        "magi", "phase_out", "backdoor_roth", "emergency_fund", "apr",
    }
    assert required <= set(content.GLOSSARY)


def test_glossary_entries_are_short_enough_to_read_inline():
    for key, entry in content.GLOSSARY.items():
        assert entry["term"] and entry["short"] and entry["more"]
        assert len(entry["short"]) <= 100, f"{key} short definition is too long for a tooltip"
