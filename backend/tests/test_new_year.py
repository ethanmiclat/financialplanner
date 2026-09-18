"""January 1: this year's contributions reset, the user ages a year, and next year's
IRS figures fall back to the latest on file until they're published."""

import pytest

import limits as L


@pytest.fixture
def at(monkeypatch):
    def set_today(iso):
        monkeypatch.setenv("FP_TODAY", iso)
    return set_today


def test_limits_for_an_unpublished_year_fall_back_and_say_so():
    data = L.load_limits(2027)
    assert data["provisional"] is True and data["based_on"] == 2026 and data["year"] == 2027
    assert data["ira"] == L.load_limits(2026)["ira"]
    assert not L.load_limits(2026).get("provisional")
    with pytest.raises(ValueError):
        L.load_limits(1999)


def test_new_year_resets_contributions_and_ages_the_user(rich_client, at):
    before = rich_client.get("/api/profile").get_json()
    assert before["plan_year"] == 2026
    at("2027-01-02")
    after = rich_client.get("/api/profile").get_json()
    assert after["plan_year"] == 2027
    assert after["age"] == before["age"] + 1
    assert all(a["contributions_ytd"] == 0 for a in after["accounts"])
    assert [a["balance"] for a in after["accounts"]] == [a["balance"] for a in before["accounts"]]
    entry = after["activity"][0]
    assert entry["kind"] == "new_year" and entry["target_name"] == "2027"


def test_rollover_happens_once(rich_client, at):
    rich_client.get("/api/profile")
    at("2027-01-02")
    rich_client.get("/api/profile")
    ira = next(a for a in rich_client.get("/api/accounts").get_json() if a["type"] == "ira")
    rich_client.post("/api/activity", json={"kind": "add", "account_id": ira["id"], "amount": 500})
    profile = rich_client.get("/api/profile").get_json()
    assert next(a for a in profile["accounts"] if a["type"] == "ira")["contributions_ytd"] == 500
    assert sum(e["kind"] == "new_year" for e in profile["activity"]) == 1


def test_the_plan_sees_the_room_open_up_again(rich_client, at):
    """Maxed HSA in 2026 is handled; on January 1 it's a to-do again."""
    hsa = next(a for a in rich_client.get("/api/accounts").get_json() if a["type"] == "hsa")
    rich_client.put(f"/api/accounts/{hsa['id']}", json={"contributions_ytd": 4_400})
    assert rich_client.get("/api/actions/R4_HSA").get_json()["actions"][0]["priority"] == "info"
    at("2027-01-02")
    body = rich_client.get("/api/actions/R4_HSA").get_json()
    assert body["year"] == 2027
    assert body["actions"][0]["priority"] == "high"


def test_new_year_undo_is_only_for_a_wrong_clock(rich_client, at):
    before = rich_client.get("/api/profile").get_json()
    at("2027-01-02")
    entry = rich_client.get("/api/profile").get_json()["activity"][0]
    # Still 2027: undoing would just roll over again on the next load.
    assert rich_client.delete(f"/api/activity/{entry['id']}").status_code == 409
    at("2026-12-31")          # the clock was wrong; now undo means something
    assert rich_client.delete(f"/api/activity/{entry['id']}").status_code == 200
    restored = rich_client.get("/api/profile").get_json()
    assert restored["age"] == before["age"]
    assert [a["contributions_ytd"] for a in restored["accounts"]] == \
        [a["contributions_ytd"] for a in before["accounts"]]


def test_skipping_years_ages_by_the_gap(rich_client, at):
    age = rich_client.get("/api/profile").get_json()["age"]
    at("2029-03-01")
    assert rich_client.get("/api/profile").get_json()["age"] == age + 3


def test_old_profiles_are_adopted_not_wiped(client, at):
    import json
    import store
    client.get("/api/profile")
    raw = json.loads(store.STORE_PATH.read_text())
    raw.pop("plan_year")
    raw["accounts"][1]["contributions_ytd"] = 300
    store.STORE_PATH.write_text(json.dumps(raw))
    profile = client.get("/api/profile").get_json()
    assert profile["plan_year"] == 2026
    assert profile["accounts"][1]["contributions_ytd"] == 300


def test_health_reports_provisional_limits(client, at):
    assert client.get("/api/health").get_json()["limits_provisional"] is False
    at("2027-02-01")
    body = client.get("/api/health").get_json()
    assert body["default_year"] == 2027 and body["limits_provisional"] is True
    assert body["limits_based_on"] == 2026


def test_full_profile_replace_keeps_the_history(client):
    savings = next(a for a in client.get("/api/accounts").get_json() if a["type"] == "cash")
    client.post("/api/activity", json={"kind": "add", "account_id": savings["id"], "amount": 5})
    profile = client.get("/api/profile").get_json()
    profile.pop("activity")
    client.put("/api/profile", json=profile)
    assert len(client.get("/api/activity").get_json()) == 1


# --- progress over time ---------------------------------------------------------

def test_every_save_records_todays_snapshot_once(client, at):
    client.get("/api/profile")                                   # seeds + saves
    savings = next(a for a in client.get("/api/accounts").get_json() if a["type"] == "cash")
    client.post("/api/activity", json={"kind": "add", "account_id": savings["id"], "amount": 200})
    points = client.get("/api/history").get_json()["points"]
    assert len(points) == 1                                      # same day: replaced
    p = points[0]
    assert p["date"] == "2026-09-17" and p["cash"] == 1_000
    assert p["net"] == round(p["owned"] - p["owed"], 2)
    assert p["invested"] == p["owned"] - p["cash"]


def test_history_grows_a_point_per_day(client, at):
    client.get("/api/profile")
    savings = next(a for a in client.get("/api/accounts").get_json() if a["type"] == "cash")
    at("2026-09-20")
    client.post("/api/activity", json={"kind": "add", "account_id": savings["id"], "amount": 100})
    at("2026-10-01")
    client.post("/api/activity", json={"kind": "add", "account_id": savings["id"], "amount": 100})
    body = client.get("/api/history").get_json()
    assert [p["date"] for p in body["points"]] == ["2026-09-17", "2026-09-20", "2026-10-01"]
    assert [p["cash"] for p in body["points"]] == [800, 900, 1_000]
    assert body["emergency_fund_target"] == 2_850


def test_reads_never_add_history(client, at):
    client.get("/api/profile")
    at("2026-12-01")
    client.get("/api/profile")
    client.get("/api/actions")
    assert len(client.get("/api/history").get_json()["points"]) == 1
