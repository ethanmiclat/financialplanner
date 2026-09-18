"""Flask API for the financial planner.

Owns the deterministic logic: the waterfall engine and the account content. Nothing
here calls an LLM, and no endpoint returns a directive to buy or sell anything — the
API surfaces mechanics, limits, and the rule that produced each recommendation.
"""

from __future__ import annotations

import math
import os

from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory

import bot
import demo
import content
import knowledge
import limits as L
import pay
import projection
import ledger
import qa
import retirement
import schedule as schedule_module
import store
import tax
import target
import waterfall
from models import (
    ActionStatus,
    Debt,
    SavingsBasis,
    account_from_dict,
    assumptions_from_dict,
    goal_from_dict,
    to_dict,
    user_from_dict,
)


def create_app() -> Flask:
    app = Flask(__name__)

    try:  # CORS only matters once the React frontend exists; don't hard-require it.
        from flask_cors import CORS

        # When the frontend is hosted elsewhere (GitHub Pages), FP_CORS_ORIGINS names
        # it, e.g. "https://ethanmiclat.github.io". Unset, any origin may call.
        origins = [o.strip() for o in os.environ.get("FP_CORS_ORIGINS", "").split(",") if o.strip()]
        CORS(app, origins=origins or "*")
    except ImportError:  # pragma: no cover
        pass

    # --- errors ---------------------------------------------------------------

    @app.errorhandler(400)
    def _bad_request(err):
        return jsonify({"error": str(getattr(err, "description", err))}), 400

    @app.errorhandler(404)
    def _not_found(err):
        return jsonify({"error": str(getattr(err, "description", "Not found"))}), 404

    @app.errorhandler(ValueError)
    def _value_error(err):
        return jsonify({"error": str(err)}), 400

    # --- demo mode ------------------------------------------------------------

    @app.before_request
    def _demo_visitor():
        if not demo.enabled():
            return
        # A frontend on another domain sends its id as a header: Safari (and soon
        # everyone) drops cross-site cookies. Same-origin, the cookie still works.
        header = request.headers.get(demo.HEADER)
        vid, new = demo.visitor_id(header or request.cookies.get(demo.COOKIE))
        g.demo_visitor, g.demo_new = vid, new and not header
        # The page load sets the cookie, so the burst of API calls that follows all
        # carries it — otherwise each would start a sandbox of its own.
        if request.path.startswith("/api/"):
            if new:
                demo.sweep()
            g.store_token = store.use_path(demo.path_for(vid))

    @app.after_request
    def _demo_cookie(response):
        if getattr(g, "demo_new", False):
            response.set_cookie(
                demo.COOKIE, g.demo_visitor, max_age=demo.TTL_SECONDS,
                httponly=True, samesite="Lax", secure=request.is_secure,
            )
        return response

    @app.teardown_request
    def _demo_done(_exc):
        token = g.pop("store_token", None)
        if token is not None:
            store._request_path.reset(token)

    def _year() -> int:
        return int(request.args.get("year", L.current_year()))

    def _body() -> dict:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object body")
        return data

    # --- meta -----------------------------------------------------------------

    @app.get("/api/health")
    def health():
        year = L.current_year()
        limits = L.load_limits(year)
        return jsonify({
            "status": "ok", "default_year": year,
            # The frontend shows a quiet note while next year's IRS figures are unpublished.
            "limits_provisional": bool(limits.get("provisional")),
            "limits_based_on": limits.get("based_on", year),
            "demo": demo.enabled(),
        })

    @app.get("/api/limits")
    def get_limits():
        year = _year()
        payload = dict(L.load_limits(year))
        age = request.args.get("age", type=int)
        if age is not None:
            payload["for_age"] = {
                "age": age,
                "elective_401k_limit": L.elective_401k_limit(age, year),
                "ira_limit": L.ira_limit(age, year),
                "hsa_self_only_limit": L.hsa_limit("self_only", age, year),
                "hsa_family_limit": L.hsa_limit("family", age, year),
            }
        payload["available_years"] = L.available_years()
        return jsonify(payload)

    # --- profile --------------------------------------------------------------

    @app.get("/api/profile")
    def get_profile():
        return jsonify(to_dict(store.load()))

    @app.put("/api/profile")
    def put_profile():
        """Full replace. Accepts the same shape GET returns."""
        body = _body()
        user = user_from_dict(body)
        # History isn't profile data. A replace that doesn't mention it keeps it.
        current = store.load()
        if "activity" not in body:
            user.activity = current.activity
        if "plan_year" not in body:
            user.plan_year = current.plan_year
        if "history" not in body:
            user.history = current.history
        return jsonify(to_dict(store.save(pay.sync_capacity(user))))

    @app.patch("/api/profile")
    def patch_profile():
        """Partial update of the user's own fields (not accounts/debts/goal)."""
        user = store.load()
        data = _body()
        editable = {
            "age", "income", "filing_status", "state", "magi", "has_401k_at_work",
            "expects_lower_bracket_in_retirement", "annual_savings_capacity",
            "savings_basis", "savings_amount",
            "pay_frequency", "take_home_per_paycheck",
        }
        unknown = set(data) - editable
        if unknown:
            raise ValueError(f"Not editable here: {', '.join(sorted(unknown))}")
        updated = user_from_dict(to_dict(user) | data)
        if "annual_savings_capacity" in data and not {"savings_basis", "savings_amount"} & set(data):
            # A yearly figure sent on its own — the projection page's "save as my plan".
            # Take it at face value rather than letting a remembered unit overwrite it.
            updated.savings_basis = SavingsBasis.YEARLY
            updated.savings_amount = data["annual_savings_capacity"]
        return jsonify(to_dict(store.save(pay.sync_capacity(updated))))

    @app.post("/api/profile/reset")
    def reset_profile():
        return jsonify(to_dict(store.reset()))

    @app.put("/api/goal")
    def put_goal():
        """Partial update — retirement age, spending, Social Security and the rest.
        Validated before saving, so a profile can't hold a plan that can't be run."""
        user = store.load()
        user.goal = goal_from_dict(to_dict(user.goal) | _body())
        retirement.validate(user)
        return jsonify(to_dict(store.save(user).goal))

    @app.put("/api/assumptions")
    def put_assumptions():
        """Partial update of the projection's guesses: returns, inflation, and how fast
        savings grow."""
        user = store.load()
        user.assumptions = assumptions_from_dict(to_dict(user.assumptions) | _body())
        retirement.validate(user)
        return jsonify(to_dict(store.save(user).assumptions))

    # --- accounts -------------------------------------------------------------

    @app.get("/api/accounts")
    def list_accounts():
        return jsonify(to_dict(store.load().accounts))

    @app.post("/api/accounts")
    def create_account():
        user = store.load()
        account = account_from_dict(_body())
        user.accounts.append(account)
        store.save(user)
        return jsonify(to_dict(account)), 201

    @app.put("/api/accounts/<account_id>")
    def update_account(account_id: str):
        user = store.load()
        for i, existing in enumerate(user.accounts):
            if existing.id == account_id:
                merged = to_dict(existing) | _body()
                merged["id"] = account_id
                user.accounts[i] = account_from_dict(merged)
                store.save(user)
                return jsonify(to_dict(user.accounts[i]))
        return jsonify({"error": f"No account {account_id}"}), 404

    @app.delete("/api/accounts/<account_id>")
    def delete_account(account_id: str):
        user = store.load()
        remaining = [a for a in user.accounts if a.id != account_id]
        if len(remaining) == len(user.accounts):
            return jsonify({"error": f"No account {account_id}"}), 404
        user.accounts = remaining
        store.save(user)
        return "", 204

    # --- debts ----------------------------------------------------------------

    @app.get("/api/debts")
    def list_debts():
        return jsonify(to_dict(store.load().debts))

    @app.post("/api/debts")
    def create_debt():
        user = store.load()
        debt = Debt(**_body())
        user.debts.append(debt)
        store.save(user)
        return jsonify(to_dict(debt)), 201

    @app.delete("/api/debts/<debt_id>")
    def delete_debt(debt_id: str):
        user = store.load()
        remaining = [d for d in user.debts if d.id != debt_id]
        if len(remaining) == len(user.debts):
            return jsonify({"error": f"No debt {debt_id}"}), 404
        user.debts = remaining
        store.save(user)
        return "", 204

    # --- activity: logging what happened --------------------------------------

    def _open_steps(user) -> dict[str, dict]:
        """Rule id → its first still-open action, in plan order."""
        steps: dict[str, dict] = {}
        for item in waterfall.prioritized(user, _year()):
            if item.priority.value != "info":
                steps.setdefault(item.rule_id, {
                    "rule_id": item.rule_id, "step": item.step, "title": item.title,
                    "amount": item.amount,
                })
        return steps

    def _effect(before: dict, after: dict) -> dict:
        """What the change did to the plan: which steps it finished, and what's next.
        Recomputed from the numbers, the same way the dashboard is."""
        return {
            "handled": [s for rid, s in before.items() if rid not in after],
            "reopened": [s for rid, s in after.items() if rid not in before],
            "next": next(iter(after.values()), None),
            "open_steps": len(after),
        }

    @app.get("/api/tax")
    def get_tax():
        """Roth or traditional, estimated: the federal rate on your next dollar now and
        in retirement. What-if fields ride along as query args, never saved."""
        user = store.load()
        overrides = {k: request.args.get(k) for k in ("income",) if request.args.get(k)}
        if overrides:
            user = projection.with_overrides(user, overrides)
        return jsonify(tax.compare(user, _year()) | {"disclaimer": content.DISCLAIMER})

    @app.get("/api/history")
    def get_history():
        """One point per day something changed. The emergency-fund target rides along
        so the chart can draw the line the cash is climbing toward."""
        user = store.load()
        points = [to_dict(h) | {"net": round(h.owned - h.owed, 2)} for h in user.history]
        return jsonify({
            "points": points,
            "emergency_fund_target": user.goal.emergency_fund_target,
        })

    @app.get("/api/activity")
    def list_activity():
        return jsonify(to_dict(store.load().activity))

    @app.post("/api/activity")
    def log_activity():
        """"I put $200 in savings" — applied as a movement, not a retyped total, and
        logged so it can be undone."""
        user = store.load()
        before = _open_steps(user)
        try:
            entry = ledger.record(user, _body())
        except LookupError as err:
            return jsonify({"error": str(err)}), 404
        store.save(user)
        return jsonify({"entry": to_dict(entry), "effect": _effect(before, _open_steps(user))}), 201

    @app.delete("/api/activity/<activity_id>")
    def undo_activity(activity_id: str):
        """Undo restores exactly the fields the entry changed, and refuses (409) if
        they've been changed again since."""
        user = store.load()
        before = _open_steps(user)
        try:
            entry = ledger.undo(user, activity_id, year=L.current_year())
        except LookupError as err:
            return jsonify({"error": str(err)}), 404
        except ledger.Conflict as err:
            return jsonify({"error": str(err)}), 409
        store.save(user)
        return jsonify({"undone": to_dict(entry), "effect": _effect(before, _open_steps(user))})

    # --- the engine -----------------------------------------------------------

    @app.get("/api/actions")
    def get_actions():
        """The prioritized action list — the dashboard's main payload."""
        year = _year()
        user = store.load()
        # order=priority is what a to-do list wants; order=waterfall (the default)
        # keeps the rule sequence, which is what the "why this order" explainer wants.
        if request.args.get("order") == "priority":
            # To-do order for what's open, then the settled steps in waterfall order —
            # `prioritized` alone drops those, and the dashboard counts them as done.
            items = waterfall.prioritized(user, year) + [
                i for i in waterfall.evaluate(user, year) if i.priority.value == "info"
            ]
        else:
            items = waterfall.evaluate(user, year)
        include_info = request.args.get("include_info", "true").lower() != "false"
        if not include_info:
            items = [i for i in items if i.priority.value != "info"]
        return jsonify({
            "year": year,
            "generated_for_user": user.id,
            "actions": to_dict(items),
            "disclaimer": content.DISCLAIMER,
        })

    @app.get("/api/actions/<rule_id>")
    def get_rule_actions(rule_id: str):
        """One rule in isolation — what it produced and what it used to decide."""
        rule = waterfall.RULES_BY_ID.get(rule_id)
        if rule is None:
            return jsonify({"error": f"No rule {rule_id}"}), 404
        year = _year()
        fn = waterfall.RULE_FUNCTIONS[rule.step - 1]
        return jsonify({
            "rule": {"id": rule.id, "step": rule.step, "name": rule.name},
            "year": year,
            "actions": to_dict(fn(store.load(), year)),
        })

    @app.post("/api/actions/<action_id>/status")
    def set_action_status(action_id: str):
        """Actions are regenerated from state on every request, so 'done' is a
        statement about the underlying numbers, not a stored flag. We recompute and
        report back whether the rule still fires."""
        status = ActionStatus(_body().get("status", "done"))
        year = _year()
        items = waterfall.evaluate(store.load(), year)
        match = next((i for i in items if i.id == action_id), None)
        if match is None:
            return jsonify({
                "error": (
                    "Action ids are regenerated each evaluation. Update the underlying "
                    "account or debt instead, then re-fetch /api/actions."
                )
            }), 409
        return jsonify({
            "requested_status": status.value,
            "still_recommended": match.priority.value != "info",
            "action": to_dict(match),
            "note": (
                "Recommendations are derived from your accounts, so marking one done means "
                "updating the balance or contribution that produced it."
            ),
        })

    @app.get("/api/plan")
    def get_plan():
        """Walk this year's savings capacity down the waterfall."""
        year = _year()
        user = store.load()
        return jsonify(waterfall.allocate(user, year) | {"year": year})

    @app.get("/api/projection")
    def get_projection():
        """What the plan is worth over time. Illustration, not forecast — the payload
        carries its own assumptions and disclaimer, and both must be displayed.

        Any of `projection.WHAT_IF_FIELDS` in the query string (retirement_age=50,
        return_rate=0.05, ...) is tried on a copy of the profile. Nothing is saved."""
        user = store.load()
        overrides = {k: v for k, v in request.args.items() if k in projection.WHAT_IF_FIELDS}
        if overrides:
            user = projection.with_overrides(user, overrides)
        scenario = request.args.get("scenario") or None
        return jsonify(projection.project(user, _year(), scenario))

    @app.get("/api/schedule")
    def get_schedule():
        """The year's plan as a calendar: what moves this month, what one payday looks
        like, and what the next `months` months do."""
        months = request.args.get("months", 12, type=int)
        return jsonify(schedule_module.schedule(store.load(), _year(), months))

    @app.get("/api/target")
    def get_target():
        """The plan run backwards: what reaching a number actually costs per year,
        per month and per paycheck.

        `goal=retirement` (the default) prices the retirement already on the profile;
        `goal=amount&amount=1000000` a nest egg in today's money; `goal=income&
        monthly=5000` a monthly income. `by_age` moves the deadline and `starting_in`
        delays the first contribution. Read-only — nothing is saved.
        """
        args = request.args

        def number(key: str) -> float | None:
            raw = args.get(key)
            if raw in (None, ""):
                return None
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(f"'{key}' must be a number.") from None
            if not math.isfinite(value):
                raise ValueError(f"'{key}' must be a number.")
            return value

        by_age = number("by_age")
        if by_age is not None and by_age != int(by_age):
            raise ValueError("Pick a whole-number age to reach it by.")
        return jsonify(target.estimate(
            store.load(), _year(),
            goal=args.get("goal") or "retirement",
            amount=number("amount"),
            monthly=number("monthly"),
            by_age=None if by_age is None else int(by_age),
            starting_in=number("starting_in") or 0.0,
        ))

    @app.get("/api/waterfall")
    def get_waterfall():
        return jsonify(content.waterfall_explainer(_year()))

    # --- content --------------------------------------------------------------

    @app.get("/api/content")
    def list_content():
        year = _year()
        user = store.load()
        return jsonify([
            {
                "key": key,
                "name": entry["name"],
                "tagline": entry["tagline"],
                "layer1": content.layer1(key, user, year),
            }
            for key, entry in content.CONTENT.items()
        ])

    @app.get("/api/content/<key>")
    def get_content(key: str):
        if key not in content.CONTENT:
            return jsonify({"error": f"No content for '{key}'"}), 404
        personalize = request.args.get("personalize", "true").lower() != "false"
        user = store.load() if personalize else None
        return jsonify(content.account_page(key, user, _year()))

    # --- structured Q&A (the second surface) ----------------------------------

    @app.get("/api/questions")
    def list_questions():
        """The browse surface: every question we can answer, grouped by topic."""
        return jsonify(qa.index())

    @app.get("/api/questions/<question_id>")
    def answer_question(question_id: str):
        """Answered from the user's own state — deterministic, no LLM involved."""
        try:
            return jsonify(qa.ask(question_id, store.load(), _year()))
        except KeyError:
            return jsonify({"error": f"No question '{question_id}'"}), 404

    @app.get("/api/glossary")
    def get_glossary():
        """Plain-language definitions for every term the UI uses."""
        return jsonify(content.GLOSSARY)

    @app.get("/api/learning-log")
    def list_learning_logs():
        return jsonify(content.LEARNING_LOGS)

    # --- free-text ask (the bot) ----------------------------------------------

    @app.post("/api/ask")
    def ask_free_text():
        """A typed question, answered without a language model.

        Personal questions route to `qa.py`, general ones to `knowledge.py`, and
        questions that carry their own number ("my 35K of student debt") to
        `scenario.py`, which runs the engine on a copy of the profile. Nothing is
        saved. `context` is whatever the previous response returned, so a follow-up
        like "what about traditional?" can resolve — the server keeps no state."""
        data = _body()
        question = data.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Ask something first.")
        year = int(data.get("year") or request.args.get("year") or L.current_year())
        context = data.get("context") if isinstance(data.get("context"), dict) else None
        return jsonify(bot.answer(question, store.load(), year, context))

    @app.get("/api/knowledge")
    def list_knowledge():
        """The general-knowledge browse surface, grouped by topic."""
        return jsonify(knowledge.index())

    @app.get("/api/knowledge/<key>")
    def get_knowledge(key: str):
        try:
            return jsonify(knowledge.get(key) | {"disclaimer": content.DISCLAIMER})
        except KeyError:
            return jsonify({"error": f"No entry '{key}'"}), 404

    # --- the built frontend -----------------------------------------------------
    # One service in production: Flask serves `npm run build`'s output, and any
    # non-API path falls through to index.html so client-side routes deep-link.
    dist = Path(os.environ.get("FP_DIST") or Path(__file__).resolve().parents[1] / "frontend" / "dist")
    if dist.is_dir():
        @app.get("/")
        @app.get("/<path:path>")
        def _frontend(path: str = ""):
            if path.startswith("api/"):
                return jsonify({"error": "Not found"}), 404
            if path and (dist / path).is_file():
                return send_from_directory(dist, path)
            return send_from_directory(dist, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
