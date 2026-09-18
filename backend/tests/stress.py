"""Tuning harness: run the whole phrasing corpus and print every miss with the top
candidates, so an alias or keyword can be added and the run repeated.

    .venv/bin/python backend/tests/stress.py            # summary + misses
    .venv/bin/python backend/tests/stress.py -v         # every row
    .venv/bin/python backend/tests/stress.py "free text" # explain one query
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

import bot  # noqa: E402
import phrasings as P  # noqa: E402
from models import Account, AccountType, Debt, Goal, User  # noqa: E402


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


def run(verbose: bool = False) -> int:
    user = rich_user()
    misses = []
    total = 0

    def check(text, expect_status, expect_kind, expect_id, ctx=None):
        nonlocal total
        total += 1
        r = None
        try:
            r = bot.answer(text, user, 2026, ctx)
        except ValueError:
            got = ("error", None, None, 0)
        else:
            top = r["results"][0]
            got = (top["status"], top["kind"], top["id"], top["confidence"])
        ok = (got[0] == expect_status) and (expect_kind is None or got[1] == expect_kind) \
            and (expect_id is None or got[2] == expect_id)
        if verbose or not ok:
            mark = "ok " if ok else "MISS"
            print(f"{mark} {text!r:62} want {expect_status}/{expect_kind}/{expect_id}  got {got[0]}/{got[1]}/{got[2]}@{got[3]}")
            if not ok:
                misses.append(text)
                for c in bot.explain(text, user, ctx)[:4]:
                    print(f"        {c['id']:<32} {c['kind']:<9} rank={c['score']} base={c['base']}")
        return r

    for text, kind, ident in P.PERSONAL + P.GENERAL + P.SCENARIO + P.GLOSSARY:
        check(text, "answered", kind, ident)
    for text, kind, ident in P.DECLINE:
        check(text, "declined", kind, ident)
    for text, _, ident in P.NEEDS_INPUT:
        check(text, "needs_input", "scenario", ident)
    for text, status, _ in P.AMBIGUOUS:
        check(text, "ambiguous", None, None)
    for text, status, _ in P.UNMATCHED:
        check(text, status, None, None)

    for text, ids in P.MULTI:
        total += 1
        r = bot.answer(text, user, 2026)
        got = [x["id"] for x in r["results"]]
        if not (r["multi_part"] and got == ids):
            misses.append(text)
            print(f"MISS multi {text!r}: want {ids} got {got} multi={r['multi_part']}")
    for text in P.NO_SPLIT:
        total += 1
        r = bot.answer(text, user, 2026)
        if r["multi_part"]:
            misses.append(text)
            print(f"MISS no-split {text!r}: split into {[x['id'] for x in r['results']]}")
    for first, follow, ident in P.FOLLOW_UPS:
        total += 1
        r1 = bot.answer(first, user, 2026)
        r2 = bot.answer(follow, user, 2026, r1["context"])
        got = r2["results"][0]["id"]
        if got != ident:
            misses.append(follow)
            print(f"MISS follow-up {first!r} -> {follow!r}: want {ident} got {got}/{r2['results'][0]['status']}")
            for c in bot.explain(follow, user, r1["context"])[:4]:
                print(f"        {c['id']:<32} rank={c['score']} base={c['base']}")
    for text, fixed in P.TYPOS:
        total += 1
        r = bot.answer(text, user, 2026)
        if fixed not in {c["to"] for c in r["corrections"]}:
            misses.append(text)
            print(f"MISS typo {text!r}: want {fixed!r} corrections={r['corrections']}")

    print(f"\n{total - len(misses)}/{total} passed, {len(misses)} misses")
    return len(misses)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] != "-v":
        text = " ".join(args)
        r = bot.answer(text, rich_user(), 2026)
        print(f"status={r['status']} multi={r['multi_part']} corrections={r['corrections']}")
        for x in r["results"]:
            print(f"  {x['status']}/{x['kind']}/{x['id']}@{x['confidence']}  {x.get('question','')}")
        print("candidates:")
        for c in bot.explain(text, rich_user()):
            print(f"  {c['id']:<32} {c['kind']:<9} rank={c['score']} base={c['base']} {c}")
        q = bot.Query(text)
        print("tokens:", q.tokens, "| unigrams:", q.unigrams, "| bigrams:", sorted(q.bigrams), "| unknown:", q.unknown)
        sys.exit(0)
    sys.exit(1 if run(verbose="-v" in args) else 0)
