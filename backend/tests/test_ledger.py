"""Logging what happened: movements change balances the way the rules read them,
every entry can be undone exactly, and undo never clobbers a newer change."""

import pytest


def _acct(client, nickname):
    return next(a for a in client.get("/api/accounts").get_json() if a["nickname"] == nickname)


def _debt(client, name):
    return next(d for d in client.get("/api/debts").get_json() if d["name"] == name)


def _log(client, **body):
    return client.post("/api/activity", json=body)


def test_adding_to_savings_moves_the_emergency_fund(client):
    """The seed: $800 cash against a $950 × 3 target. The emergency-fund step should
    see the deposit immediately — that's the whole point of logging it."""
    savings = _acct(client, "Savings")
    r = _log(client, kind="add", account_id=savings["id"], amount=2_100)
    assert r.status_code == 201
    body = r.get_json()
    assert _acct(client, "Savings")["balance"] == 2_900
    assert body["entry"]["changes"] == {"balance": [800, 2_900]}
    assert "R1_EMERGENCY_FUND" in [s["rule_id"] for s in body["effect"]["handled"]]
    assert body["effect"]["next"] is not None


def test_cash_deposit_never_counts_as_a_contribution(client):
    savings = _acct(client, "Savings")
    _log(client, kind="add", account_id=savings["id"], amount=50, counts_as_contribution=True)
    assert _acct(client, "Savings")["contributions_ytd"] == 0


def test_ira_deposit_counts_toward_the_limit_and_is_invested(client):
    ira = _acct(client, "Roth IRA")
    _log(client, kind="add", account_id=ira["id"], amount=100)
    after = _acct(client, "Roth IRA")
    assert after["balance"] == 550
    assert after["contributions_ytd"] == 550
    assert after["holdings"][0]["value"] == 400
    assert after["uninvested_cash"] == ira["uninvested_cash"]   # new money didn't idle


def test_rollover_can_opt_out_of_the_limit_and_stay_uninvested(client):
    ira = _acct(client, "Roth IRA")
    _log(client, kind="add", account_id=ira["id"], amount=100,
         counts_as_contribution=False, invested=False)
    after = _acct(client, "Roth IRA")
    assert after["contributions_ytd"] == 450
    assert after["uninvested_cash"] == ira["uninvested_cash"] + 100


def test_withdraw_takes_idle_cash_before_funds(client):
    ira = _acct(client, "Roth IRA")          # 450 balance, 300 invested, 150 idle
    _log(client, kind="withdraw", account_id=ira["id"], amount=250)
    after = _acct(client, "Roth IRA")
    assert after["balance"] == 200
    assert after["holdings"][0]["value"] == 200   # 150 from idle, 100 from the fund
    assert after["contributions_ytd"] == 450      # withdrawing doesn't un-contribute


def test_cannot_withdraw_more_than_the_balance(client):
    savings = _acct(client, "Savings")
    r = _log(client, kind="withdraw", account_id=savings["id"], amount=10_000)
    assert r.status_code == 400
    assert _acct(client, "Savings")["balance"] == 800


def test_set_balance_keeps_the_uninvested_share(client):
    ira = _acct(client, "Roth IRA")
    _log(client, kind="set_balance", account_id=ira["id"], amount=900)
    after = _acct(client, "Roth IRA")
    assert after["balance"] == 900
    assert after["holdings"][0]["value"] == pytest.approx(600)


def test_paying_off_the_card_clears_the_debt_step(client):
    card = _debt(client, "Credit card")
    body = _log(client, kind="pay", debt_id=card["id"], amount=1_000).get_json()
    assert body["entry"]["amount"] == 350              # capped at what was owed
    assert _debt(client, "Credit card")["balance"] == 0
    assert "R3_HIGH_INTEREST_DEBT" in [s["rule_id"] for s in body["effect"]["handled"]]
    assert _log(client, kind="pay", debt_id=card["id"], amount=10).status_code == 400


def test_undo_restores_exactly(client):
    before = client.get("/api/profile").get_json()
    ira = _acct(client, "Roth IRA")
    entry = _log(client, kind="add", account_id=ira["id"], amount=123.45).get_json()["entry"]
    r = client.delete(f"/api/activity/{entry['id']}")
    assert r.status_code == 200
    after = client.get("/api/profile").get_json()
    assert after["accounts"] == before["accounts"]
    assert after["activity"] == []


def test_undo_refuses_after_a_newer_change(client):
    savings = _acct(client, "Savings")
    first = _log(client, kind="add", account_id=savings["id"], amount=100).get_json()["entry"]
    _log(client, kind="add", account_id=savings["id"], amount=50)
    r = client.delete(f"/api/activity/{first['id']}")
    assert r.status_code == 409
    assert _acct(client, "Savings")["balance"] == 950


def test_undo_in_reverse_order_works(client):
    savings = _acct(client, "Savings")
    a = _log(client, kind="add", account_id=savings["id"], amount=100).get_json()["entry"]
    b = _log(client, kind="add", account_id=savings["id"], amount=50).get_json()["entry"]
    assert client.delete(f"/api/activity/{b['id']}").status_code == 200
    assert client.delete(f"/api/activity/{a['id']}").status_code == 200
    assert _acct(client, "Savings")["balance"] == 800


def test_undo_after_the_account_is_removed_is_a_conflict(client):
    savings = _acct(client, "Savings")
    entry = _log(client, kind="add", account_id=savings["id"], amount=100).get_json()["entry"]
    client.delete(f"/api/accounts/{savings['id']}")
    assert client.delete(f"/api/activity/{entry['id']}").status_code == 409


def test_log_is_newest_first(client):
    savings = _acct(client, "Savings")
    _log(client, kind="add", account_id=savings["id"], amount=1, note="first")
    _log(client, kind="add", account_id=savings["id"], amount=2, note="second")
    notes = [a["note"] for a in client.get("/api/activity").get_json()]
    assert notes == ["second", "first"]


@pytest.mark.parametrize("body, status", [
    ({"kind": "add", "amount": 10}, 400),                                  # no target
    ({"kind": "add", "account_id": "nope", "amount": 10}, 404),
    ({"kind": "teleport", "account_id": "x", "amount": 10}, 400),
    ({"kind": "add", "account_id": "x", "amount": -5}, 400),
    ({"kind": "add", "account_id": "x", "amount": "lots"}, 400),
    ({"kind": "add", "account_id": "x", "amount": 0}, 400),
])
def test_bad_requests(client, body, status):
    if body.get("account_id") == "x":
        body["account_id"] = _acct(client, "Savings")["id"]
    assert _log(client, **body).status_code == status


def test_debts_reject_account_kinds(client):
    card = _debt(client, "Credit card")
    assert _log(client, kind="add", debt_id=card["id"], amount=5).status_code == 400


def test_unknown_undo_is_404(client):
    assert client.delete("/api/activity/nope").status_code == 404


def test_old_profiles_without_a_log_still_load(client, tmp_path):
    import json
    import store
    raw = json.loads(store.STORE_PATH.read_text()) if store.STORE_PATH.exists() else None
    client.get("/api/profile")
    raw = json.loads(store.STORE_PATH.read_text())
    raw.pop("activity", None)
    store.STORE_PATH.write_text(json.dumps(raw))
    assert client.get("/api/activity").get_json() == []


def test_invest_clears_the_idle_cash_warning(client):
    ira = _acct(client, "Roth IRA")                  # $150 of $450 sitting as cash
    before = client.get("/api/actions/R8_VEHICLE").get_json()["actions"]
    assert any("uninvested" in a["title"] for a in before)
    body = _log(client, kind="invest", account_id=ira["id"], amount=150).get_json()
    after = _acct(client, "Roth IRA")
    assert after["balance"] == 450 and after["uninvested_cash"] == 0
    assert after["holdings"][0]["value"] == 450
    assert "R8_VEHICLE" in [s["rule_id"] for s in body["effect"]["handled"]]


def test_invest_cannot_exceed_the_idle_cash(client):
    ira = _acct(client, "Roth IRA")
    assert _log(client, kind="invest", account_id=ira["id"], amount=200).status_code == 400
    savings = _acct(client, "Savings")
    assert _log(client, kind="invest", account_id=savings["id"], amount=10).status_code == 400


def test_invest_with_no_funds_recorded_creates_one_and_undo_removes_it(client):
    acct = client.post("/api/accounts", json={"type": "taxable", "nickname": "Brokerage", "balance": 1_000}).get_json()
    assert _log(client, kind="invest", account_id=acct["id"], amount=1_000).status_code == 400  # needs a fund
    entry = _log(client, kind="invest", account_id=acct["id"], amount=1_000, fund="vti").get_json()["entry"]
    after = _acct(client, "Brokerage")
    assert after["holdings"][0]["symbol"] == "VTI" and after["uninvested_cash"] == 0
    assert client.delete(f"/api/activity/{entry['id']}").status_code == 200
    assert _acct(client, "Brokerage")["holdings"] == []


def test_invest_names_an_existing_fund(client):
    ira = _acct(client, "Roth IRA")
    _log(client, kind="invest", account_id=ira["id"], amount=50, fund="vttsx")
    assert _acct(client, "Roth IRA")["holdings"][0]["value"] == 350
