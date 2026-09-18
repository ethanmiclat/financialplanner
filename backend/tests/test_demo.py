"""Demo mode: each visitor gets a private profile; the owner's is never touched."""

import json
import os
import time

import pytest


@pytest.fixture
def demo_app(tmp_path, monkeypatch):
    import store
    real = tmp_path / "real.json"
    monkeypatch.setattr(store, "STORE_PATH", real)
    monkeypatch.setenv("FP_DEMO", "1")
    monkeypatch.setenv("FP_DEMO_DIR", str(tmp_path / "demo"))
    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True)
    return flask_app, real


def _savings(c):
    return next(a for a in c.get("/api/accounts").get_json() if a["type"] == "cash")


def test_visitors_are_isolated_and_the_real_profile_is_untouched(demo_app):
    flask_app, real = demo_app
    alice, bob = flask_app.test_client(), flask_app.test_client()
    s = _savings(alice)
    alice.post("/api/activity", json={"kind": "add", "account_id": s["id"], "amount": 1_000})
    assert _savings(alice)["balance"] == 1_800
    assert _savings(bob)["balance"] == 800           # bob has his own seed
    assert not real.exists()                          # the owner's file never touched
    assert alice.get("/api/health").get_json()["demo"] is True


def test_a_visitor_keeps_their_profile_across_requests(demo_app):
    flask_app, _ = demo_app
    c = flask_app.test_client()
    c.patch("/api/profile", json={"income": 55_555})
    assert c.get("/api/profile").get_json()["income"] == 55_555


def test_the_page_load_issues_the_cookie_before_any_api_call(demo_app, tmp_path):
    flask_app, _ = demo_app
    c = flask_app.test_client()
    c.get("/")                                        # the HTML (or 404 without a build)
    assert c.get_cookie("footing_demo") is not None
    for _ in range(4):                                # the page's opening burst
        c.get("/api/profile")
    assert len(list((tmp_path / "demo").glob("*.json"))) == 1


def test_forged_cookies_get_a_fresh_sandbox(demo_app):
    flask_app, real = demo_app
    real.write_text("{}")
    c = flask_app.test_client()
    c.set_cookie("footing_demo", "../../real")
    assert c.get("/api/profile").get_json()["income"] == 13_500
    assert real.read_text() == "{}"


def test_sweep_drops_expired_and_overflowing_visitors(tmp_path, monkeypatch):
    import demo
    monkeypatch.setenv("FP_DEMO_DIR", str(tmp_path))
    monkeypatch.setattr(demo, "MAX_VISITORS", 2)
    now = time.time()
    for i, age in enumerate([0, 10, 20, demo.TTL_SECONDS + 5]):
        p = tmp_path / f"{i:032x}.json"
        p.write_text(json.dumps({}))
        os.utime(p, (now - age, now - age))
    assert demo.sweep(now) == 2                      # one expired, one over the cap
    assert sorted(p.name for p in tmp_path.glob("*.json")) == [f"{0:032x}.json", f"{1:032x}.json"]


def test_demo_off_uses_the_real_store(client):
    assert client.get("/api/health").get_json()["demo"] is False


def test_a_cross_site_frontend_is_identified_by_header_not_cookie(demo_app, tmp_path):
    """GitHub Pages calls the API from another domain, where Safari drops cookies. The
    header carries the visitor instead, and no cookie is issued alongside it."""
    flask_app, real = demo_app
    alice, bob = flask_app.test_client(), flask_app.test_client()
    a = {"X-Footing-Visitor": "a" * 32}
    s = next(x for x in alice.get("/api/accounts", headers=a).get_json() if x["type"] == "cash")
    r = alice.put(f"/api/accounts/{s['id']}", json={"balance": 4321}, headers=a)
    assert r.headers.get("Set-Cookie") is None
    assert _savings(bob)["balance"] != 4321
    back = next(x for x in bob.get("/api/accounts", headers=a).get_json() if x["type"] == "cash")
    assert back["balance"] == 4321                     # same header, same sandbox
    assert not real.exists()
    assert (tmp_path / "demo" / f"{'a' * 32}.json").exists()


def test_cors_can_be_limited_to_the_pages_origin(monkeypatch):
    monkeypatch.setenv("FP_CORS_ORIGINS", "https://ethanmiclat.github.io")
    import app as app_module
    c = app_module.create_app().test_client()
    ok = c.get("/api/health", headers={"Origin": "https://ethanmiclat.github.io"})
    assert ok.headers["Access-Control-Allow-Origin"] == "https://ethanmiclat.github.io"
    other = c.get("/api/health", headers={"Origin": "https://example.com"})
    assert "Access-Control-Allow-Origin" not in other.headers
