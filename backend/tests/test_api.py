def test_health(client):
    assert client.get("/api/health").get_json()["default_year"] == 2026


def test_profile_seeds_on_first_read(client):
    """The shipped demo is a 20-year-old student on a part-time minimum-wage job."""
    profile = client.get("/api/profile").get_json()
    assert profile["age"] == 20
    assert profile["income"] == 13_500
    assert profile["has_401k_at_work"] is False
    assert {a["type"] for a in profile["accounts"]} == {"cash", "ira"}
    assert profile["goal"]["emergency_fund_target"] == 2_850


def test_profile_patch_and_persistence(client):
    client.patch("/api/profile", json={"income": 250_000})
    assert client.get("/api/profile").get_json()["income"] == 250_000


def test_profile_patch_rejects_non_editable_fields(client):
    r = client.patch("/api/profile", json={"accounts": []})
    assert r.status_code == 400 and "accounts" in r.get_json()["error"]


def test_account_crud(client):
    created = client.post("/api/accounts", json={
        "type": "taxable", "nickname": "Second brokerage", "balance": 500,
    })
    assert created.status_code == 201
    account_id = created.get_json()["id"]

    updated = client.put(f"/api/accounts/{account_id}", json={"balance": 900})
    assert updated.get_json()["balance"] == 900

    assert client.delete(f"/api/accounts/{account_id}").status_code == 204
    assert client.delete(f"/api/accounts/{account_id}").status_code == 404


def test_actions_are_ordered_and_traceable(rich_client):
    body = rich_client.get("/api/actions").get_json()
    actions = body["actions"]
    assert body["disclaimer"]
    assert all(a["rule_id"] and a["rule_name"] for a in actions)

    # Default order is waterfall order (what the "why this order" explainer wants).
    actionable = [a for a in actions if a["priority"] != "info"]
    steps = [a["step"] for a in actionable]
    assert steps == sorted(steps)
    assert any(a["rule_id"] == "R3_HIGH_INTEREST_DEBT" for a in actionable)


def test_actions_priority_order_puts_blocking_first(rich_client):
    """?order=priority is what the dashboard uses: a blocking item can't sit behind
    lower-urgency ones just because its rule is numbered later."""
    actions = rich_client.get("/api/actions?order=priority").get_json()["actions"]
    assert actions[0]["rule_id"] == "R3_HIGH_INTEREST_DEBT"   # the 22% card
    assert actions[0]["priority"] == "blocking"
    # Settled steps follow every open one, so the dashboard can count them as done.
    kinds = [a["priority"] == "info" for a in actions]
    assert kinds == sorted(kinds) and any(kinds)


def test_actions_can_hide_informational_items(client):
    body = client.get("/api/actions?include_info=false").get_json()
    assert all(a["priority"] != "info" for a in body["actions"])


def test_single_rule_endpoint_shows_its_inputs(rich_client):
    body = rich_client.get("/api/actions/R4_HSA").get_json()
    assert body["rule"]["step"] == 4
    assert body["actions"][0]["inputs"]["annual_limit"] == 4_400
    assert rich_client.get("/api/actions/NOPE").status_code == 404


def test_actions_react_to_state_changes(rich_client):
    """Update the underlying account; the recommendation changes. No stored flags."""
    hsa = next(a for a in rich_client.get("/api/accounts").get_json() if a["type"] == "hsa")
    assert rich_client.get("/api/actions/R4_HSA").get_json()["actions"][0]["priority"] == "high"

    rich_client.put(f"/api/accounts/{hsa['id']}", json={"contributions_ytd": 4_400})
    after = rich_client.get("/api/actions/R4_HSA").get_json()["actions"][0]
    assert after["priority"] == "info" and "maxed" in after["title"]


def test_plan_allocates_capacity_down_the_waterfall(rich_client):
    plan = rich_client.get("/api/plan").get_json()
    assert plan["annual_savings_capacity"] == 30_000
    assert plan["allocated"] + plan["unallocated"] == 30_000
    # Cash covers 7.5 months, so the 22% card is the only blocking item; it's funded
    # first, then the guaranteed employer match.
    funded = [s["rule_id"] for s in plan["steps"] if s["funded"]]
    assert funded[:2] == ["R3_HIGH_INTEREST_DEBT", "R2_EMPLOYER_MATCH"]


def test_limits_endpoint_is_data_driven(client):
    body = client.get("/api/limits?age=61").get_json()
    assert body["401k"]["employee_deferral"] == 24_500
    assert body["for_age"]["elective_401k_limit"] == 35_750
    assert body["available_years"] == [2026]


def test_content_endpoints(client):
    listing = client.get("/api/content").get_json()
    assert len(listing) == 5

    page = client.get("/api/content/hsa").get_json()
    assert page["layer2"]["why"]
    assert page["layer3"]["numbers"]["your_self_only_limit"] == 4_400
    assert page["learning_log"]["summary"]

    assert client.get("/api/content/crypto").status_code == 404


def test_debts(client):
    created = client.post("/api/debts", json={"name": "Card 2", "balance": 800, "apr": 0.19})
    assert created.status_code == 201
    assert any(d["name"] == "Card 2" for d in client.get("/api/debts").get_json())
    assert client.delete(f"/api/debts/{created.get_json()['id']}").status_code == 204


def test_reset_restores_the_seed(client):
    client.patch("/api/profile", json={"income": 1})
    assert client.post("/api/profile/reset").get_json()["income"] == 13_500


def test_bad_json_body_is_a_400(client):
    assert client.patch("/api/profile", data="not json",
                        content_type="application/json").status_code == 400


def test_glossary_endpoint(client):
    glossary = client.get("/api/glossary").get_json()
    assert glossary["hsa"]["short"]
    assert glossary["employer_match"]["term"] == "Employer match"


def test_questions_index(client):
    topics = client.get("/api/questions").get_json()
    assert [t["topic"] for t in topics][0] == "Getting started"
    assert any(q["id"] == "next_dollar" for t in topics for q in t["questions"])


def test_question_answer_is_grounded_in_the_profile(rich_client):
    body = rich_client.get("/api/questions/how_much_can_i_put_in").get_json()
    # Age 40 with a self-only HSA: 24,500 + 7,500 + 4,400.
    assert "$36,400" in body["answer"]["summary"]
    assert body["follow_ups"]
    assert body["disclaimer"]


def test_question_answer_tracks_account_changes(rich_client):
    before = rich_client.get("/api/questions/am_i_missing_match").get_json()
    assert "capture" in before["answer"]["summary"].lower()

    plan = next(a for a in rich_client.get("/api/accounts").get_json() if a["type"] == "401k")
    rich_client.put(f"/api/accounts/{plan['id']}", json={"contributions_ytd": 20_000})
    after = rich_client.get("/api/questions/am_i_missing_match").get_json()
    assert "Full employer match captured" in after["answer"]["summary"]


def test_unknown_question_is_404(client):
    assert client.get("/api/questions/nope").status_code == 404


def test_projection_endpoint_tells_the_compounding_story(client):
    """Seed profile is a student: small contributions, decades of growth."""
    body = client.get("/api/projection").get_json()
    retirement = body["points"][-1]
    assert retirement["age"] == 67
    assert retirement["growth_by_then"] > retirement["contributed_by_then"]
    assert body["assumptions"] and body["disclaimer"]


def test_projection_scenarios(client):
    cautious = client.get("/api/projection?scenario=cautious").get_json()
    strong = client.get("/api/projection?scenario=strong").get_json()
    assert strong["points"][-1]["following_plan"] > cautious["points"][-1]["following_plan"]
    assert client.get("/api/projection?scenario=nonsense").status_code == 400
