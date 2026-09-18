# Free-Text Answer Bot — Implementation Plan

> **Status: implemented (2026-09-17).** This is the spec the build was made from; the
> as-built description lives in `README.md` ("The free-text bot") and the decisions in
> `financialplannerscope.md` ("Decisions made building the bot"). Two things went
> beyond the spec: a fifth scenario (retirement age), and a symmetric month-by-month
> simulation for the payoff-versus-invest comparison after the `future_value` shortcut
> proved to flatter cheap debt.

## Context

The app's second surface (`backend/qa.py`) answers 18 fixed questions, each a pure
function grounded in the user's stored numbers. You pick one off a list at `/ask`. Two
gaps: you can't type a question, and every question is about *your plan* — nothing
answers "what's an expense ratio?"

Closing those two gaps is a retrieval problem. But the bar for this bot is set by a
different kind of question:

> **"How should I plan around my 35K of student debt?"**

That question cannot be retrieved. It requires reading `$35,000` out of the sentence,
understanding it in the context of the whole plan, running the engine against it, and
composing an answer that did not exist beforehand. **This is the benchmark — the plan is
not done until this question is answered well.**

So the bot is two subsystems:

1. **Retrieval** — free text → the right pre-written answer. Handles "what's an expense
   ratio" and "how much can I put in my HSA".
2. **Scenario composition** — free text → extracted parameters → a what-if run on a copy
   of the profile → an answer assembled from engine output. Handles the benchmark.

Neither uses an LLM. The second one doesn't need to, because the engine already does the
reasoning — `waterfall.py`, `projection.py`, `schedule.py` and `retirement.py` produce
every number. The composer's job is to turn a sentence into engine inputs and engine
output into prose.

The load-bearing invariant throughout: **the bot never computes a financial figure.**
Retrieval selects; composition parameterizes and templates. Both delegate the arithmetic.
That makes a fabricated number structurally impossible.

Implemented by a separate agent from a cold start. **First step: overwrite `botplan.md`
at the repo root with this plan** — it was drafted before exploration and is wrong in
several details (it says 14 questions; there are 18, and it has no composer at all).

## Constraints

- No LLM, no external API, no network calls at runtime. No API credits exist.
- **No new Python dependencies.** `requirements.txt` stays `Flask`, `flask-cors`,
  `pytest`. Standard library only. `difflib` is stdlib and used deliberately.
- No new frontend dependencies.
- **Nothing is ever saved without an explicit action.** Scenarios run on a deep copy,
  exactly as `/api/target` and the projection what-ifs already do.
- **The server stays stateless.** Follow-up context comes from the client.
- Never answer confidently when uncertain — return candidates, or ask for the missing
  number.
- Scope is the bot. UI approachability work is a separate, later plan.

## What already exists (verified)

| Thing | Where | Note |
|---|---|---|
| `Answer` dataclass | `qa.py` | `summary`, `detail`, `facts`, `sources`, `follow_ups`, `content_key` |
| 18 personal questions | `qa.QUESTIONS` | 5 topics; 4 are `_explainer`-generated from `CONTENT` |
| `qa.ask(id, user, year)` | `qa.py` | Raises `KeyError` on unknown id |
| `CONTENT` (5), `LEARNING_LOGS` (5), `GLOSSARY` (33), `DISCLAIMER` | `content.py` | Learning logs are Ethan's own words — **leave untouched** |
| **`projection.with_overrides(user, overrides)`** | `projection.py` | `copy.deepcopy` + `setattr` + `R.validate`. **Scalars only** — cannot add a debt |
| `projection.WHAT_IF_FIELDS` | `projection.py` | `retirement_age`, `return_rate`, `annual_savings_capacity`, … — note **`income` is absent** |
| `waterfall.allocate(user, year)` / `prioritized(user, year)` | `waterfall.py` | Allocates capacity down the waterfall |
| `projection.project(user, year, scenario)` | `projection.py` | Growth, drawdown, readiness |
| `schedule.schedule(user, year, months)` | `schedule.py` | Monthly + per-paycheck moves |
| `pay.sync_capacity(user)` | `pay.py` | Recomputes capacity from basis + amount; **must re-run when income changes** |
| `Debt(name, balance, apr, minimum_payment)` | `models.py` | |
| `thresholds.high_interest_debt_apr` | `data/limits_2026.json` | **0.075** — read it, never hardcode |
| `_body()` / `_year()` | `app.py` | `_body()` raises `ValueError` → auto-400 |
| `Annotated`, `Card`, `Field`, `TextInput`, `Button`, `EmptyState`, `ErrorState`, `Toast` | `frontend/src/components/` | **No `TextArea` exists** |

**Critical:** the 33 glossary terms overlap heavily with obvious KB topics
(`expense_ratio`, `index_fund`, `compounding`, `capital_gains`, `apr`, `vesting`, `rmd`,
`emergency_fund`, …). The KB must **deepen** these, not duplicate them — glossary is
Layer 1 (one line), KB is Layer 2 (mechanics). Cross-link every one.

## Architecture

```
POST /api/ask  {"question": "...", "context": {...}?}
        │
        ▼  bot.answer(text, user, year, context=None)
        │
        ├─ normalize → alias-expand → tokenize → stem → difflib repair → uni+bigrams
        ├─ slots.extract(text)          →  amounts, rates, types, cadences, ages
        │
        ├─ score in ONE pass against four corpora:
        │    • scenario.SCENARIOS   4 parameterized  → runs the engine on a copy
        │    • qa.QUESTIONS        18 personal       → qa.ask()
        │    • knowledge.ENTRIES  ~80 general        → static
        │    • knowledge.DECLINES  ~8 refusals       → deliberate
        │
        ├─ a scenario wins only if its required slots are present
        │        └─ intent matched, slots missing → status "needs_input"
        │
        ├─ ≥0.55 answered │ 0.25–0.55 split-or-ambiguous │ <0.25 glossary-or-unmatched
```

`qa.py`, `content.py` and `projection.py` are **not rewritten**. Everything new sits in
front of them.

---

## File 1 — `backend/knowledge.py` (new)

Static general knowledge. No `User` argument — these answers are identical for everyone.
A Python module, not JSON, to match `content.py`: prose belongs in code, and the JSON
convention in `limits.py` is specifically for year-scoped IRS *numbers*. Where an entry
needs a limit, read it from `limits.py`.

```python
ENTRIES: dict[str, dict] = {
    "expense_ratio_deep": {
        "question": "What is an expense ratio and why does it matter?",
        "topic": "Investing basics",
        "level": "basic",                       # basic | intermediate
        "keywords": ["expense ratio", "fund fee", "management fee",
                     "how much do funds cost", "why are fees bad"],
        "summary": "The yearly percentage a fund charges you for running it.",
        "detail": "...one to three plain-English paragraphs, content.py voice...",
        "facts": [{"label": "Typical index fund", "value": "0.03% – 0.10%"}],
        "related": ["index_fund_deep", "compound_interest"],
        "glossary_terms": ["expense_ratio"],    # keys into content.GLOSSARY
    },
}
```

Reuse `qa.Answer` so one frontend component renders every answer kind. `facts` optional —
omit rather than pad. **No `layer3`** — breadth over depth here; the Foundational Five
pages remain the deep surface.

### Coverage (~80 entries)

- **Investing basics (20)** — compound interest, index funds, mutual fund vs ETF, expense
  ratios, target-date funds, diversification, asset allocation, stocks vs bonds,
  dollar-cost averaging, market timing, rebalancing, dividends, brokerages, total market
  vs S&P 500, international exposure, risk tolerance, volatility vs risk, bear/bull
  markets, fractional shares, tickers.
- **Retirement mechanics (14)** — 59½, early-withdrawal penalties, RMDs, rollovers,
  vesting, Social Security basics, the 4% rule, Roth conversions, backdoor Roth, pro-rata,
  catch-up contributions, Roth withdrawal ordering, rule of 55, rule of 72.
- **Taxes (12)** — marginal vs effective, how brackets work, standard deduction, pre- vs
  post-tax, tax-loss harvesting, wash sales, short vs long-term gains, qualified
  dividends, tax drag, W-2 vs 1099, FICA, tax-advantaged vs taxable.
- **Debt and credit (9)** — APR vs APY, minimum payments, avalanche vs snowball, credit
  score factors, utilization, good vs bad debt, student loans, refinancing, when paying
  debt beats investing.
- **Cash and banking (8)** — emergency fund sizing, HYSAs, CDs, money market funds, FDIC
  insurance, inflation, real vs nominal return, sinking funds.
- **Income and planning (10)** — gross vs net, withholding, the W-4, 50/30/20, savings
  rate, lifestyle creep, net worth, pay frequency, raises, side income.
- **Health accounts and adjacent (7)** — HDHPs, deductibles, HSA vs FSA, HSA as a
  retirement account, term vs whole life, disability basics, what insurance is for.

**Voice:** match `content.py` — plain English, concrete, no hedging, no "consult a
professional" filler (`DISCLAIMER` covers that globally, once). Define jargon on first
use. `detail` must exceed 80 characters; the existing suite uses that as its stub test.

**Leave `LEARNING_LOGS` untouched.** Those are Ethan's own words on the Foundational
Five; the KB is reference material. README should state the distinction.

### Declines

```python
DECLINES: dict[str, dict] = {
    "security_selection": {
        "keywords": ["should i buy", "is nvidia a good", "which stock", "hot stock",
                     "is bitcoin a good investment"],
        "summary": "This app explains how accounts work, not which investments to pick.",
        "detail": "...why the line exists — educational framing, not directive...",
        "redirect": ["what_to_invest_in", "index_fund_deep", "diversification"],
    },
}
```

**By design** — individual security selection; market predictions and crash timing; tax
preparation and filing; legal and estate questions; insurance product selection.
**By capability** — live prices, current rates, real-time market data, anything needing
their specific plan documents.

Each decline says what the app *does* cover and offers `redirect` ids. Nuance: *"should I
wait to invest until the market drops?"* is **not** a decline — route it to the
`market_timing` entry.

---

## File 2 — `backend/slots.py` (new)

Pulls structured parameters out of a sentence. Pure functions, no state, exhaustively
testable — this is what lets `"my 35K of student debt"` become `{amount: 35000, kind:
"student_loan"}`.

```python
@dataclass
class Slots:
    amounts: list[Amount]      # value + cadence + raw span
    rates: list[float]         # 0.0653 from "6.53%" / "at 6 percent"
    debt_kind: str | None      # student_loan | credit_card | auto | mortgage | personal | medical
    account_kind: str | None   # 401k | ira | hsa | taxable
    ages: list[int]            # "at 62", "by 40"
```

**Money** — `35k`, `$35,000`, `35,000`, `35000`, `$1.2m`, plus a small number-words table
for `thirty five thousand`. Suffixes: `k` ×1_000, `m` ×1_000_000.

**Cadence** — `a month` / `per month` / `monthly` / `a year` / `per paycheck` / `each
check`. Cadence is what distinguishes a **stock** from a **flow**, and that distinction
decides which scenario runs:

| Input | Reading |
|---|---|
| `"35k of student debt"` | balance — a stock |
| `"$300 a month"` | contribution — a flow |
| `"I make 75k"` | income — a flow, annual by default |

Rule: money **with** a cadence is a flow; money **without** a cadence plus a debt or
account word is a balance. Ambiguous cases resolve toward the scenario whose intent
scored highest, and the assumption is stated in the answer.

**Ages** — guard against reading `62` in `"at 62%"` as an age. Require no `%` adjacency
and a plausible range (18–100).

---

## File 3 — `backend/scenario.py` (new)

The composer. Turns slots into a what-if, runs the existing engine on a **deep copy**,
and assembles prose from the results.

### The trial copy

`projection.with_overrides()` handles scalar fields on `goal`/`assumptions`/`user` but
**cannot add a debt or an account**. Add a sibling in this module that reuses its
discipline (`copy.deepcopy` → mutate → `R.validate`):

```python
def trial(user: User, *, add_debts=None, add_accounts=None, **overrides) -> User:
    """A what-if copy. Never saved — the same discipline as /api/target."""
```

Delegate scalar overrides to `projection.with_overrides` rather than duplicating its
validation. **`income` is not in `WHAT_IF_FIELDS`** — extend that dict to include it, and
**re-run `pay.sync_capacity(trial)` after any income change**, or a percent-of-pay
savings basis will silently disagree with the new salary.

### Composed answer shape

Extends `qa.Answer` with two fields, so multi-part synthesis doesn't get crammed into one
`detail` string:

```python
sections: list[dict]    # [{heading, body, facts}] — the composed body
assumptions: list[dict] # [{label, value, note}] — what we filled in and why
save_hint: dict | None  # what committing this would write, and where
```

### Scenario registry

```python
SCENARIOS: dict[str, dict] = {
    "debt_strategy": {
        "intent_keywords": ["how should i plan around my debt", "manage my debt",
                            "pay off or invest", "what do i do about my loan", ...],
        "required": ["amount"],
        "optional": ["rate", "debt_kind"],
        "run": run_debt_strategy,
    },
    "windfall": {...},          # required: amount
    "income_change": {...},     # required: amount (flow)
    "contribution_change": {...},# required: amount (flow)
}
```

A scenario only wins if its `required` slots are present. Intent matched but slots
missing → `status: "needs_input"` with a specific question ("How much is it?"), never a
guess.

### `run_debt_strategy` — the benchmark

For `"How should I plan around my 35K of student debt?"`:

1. **Resolve the rate.** If not stated, use a typical-rate table by `debt_kind`
   (student ~6.5%, credit card ~23%, auto ~7.5%, mortgage ~6.5%, personal ~12%). Record
   it in `assumptions` with a note that it's the hinge of the whole answer and can be
   restated. Estimate `minimum_payment` from balance and kind if not given.
2. **Place it in the waterfall.** Compare against
   `limits.load_limits(year)["thresholds"]["high_interest_debt_apr"]` (**0.075**). Above
   it, rule 3 blocks investing; below, it sits after the IRA. Cite `R3_HIGH_INTEREST_DEBT`
   in `sources`. Never hardcode 7.5%.
3. **Run both branches** on trial copies: payoff-first (capacity to debt until cleared,
   then invest) versus minimum-only (invest the rest now). Use
   `projection.project()` for each and `schedule.schedule()` for the payoff month.
4. **Compute the break-even rate** — the APR at which the two branches cross, which is
   the assumed return. This is the real insight: below your expected return, investing
   wins in expectation; above it, payoff wins guaranteed. State both sides.
5. **Compose** summary + sections + facts + assumptions + `save_hint`.

Target shape of the composed answer:

> **Your $35,000 student loan sits below the line where paying it off first beats investing.**
>
> *Where it lands* — At an assumed 6.5%, it's under the 7.5% cutoff in step 3, so it
> doesn't block investing. Above 7.5% it would.
> *Payoff first* — clears in N months, then invests; ~$X by 67.
> *Minimum only* — invests now; ~$Y by 67.
> *The gap* — $Z, because the expected return exceeds 6.5%. At any rate above ~7%, it flips.
>
> Assumptions: rate assumed at 6.5% (not stated) · returns at the middling scenario
> Save hint: add a $35,000 student loan to your plan

### The other three

- **`windfall`** — build a trial with `annual_savings_capacity + amount`, run
  `waterfall.allocate()` on both, and **diff the allocations**. That shows exactly which
  steps the extra money fills and what's left over, straight from the engine.
- **`income_change`** — override `income`, re-run `pay.sync_capacity`, report what moves:
  IRA earned-income cap, Roth phase-out position, capacity, retirement date.
- **`contribution_change`** — override `annual_savings_capacity` (already a
  `WHAT_IF_FIELDS` key; multiply by 12 for a monthly cadence, or route through `pay.py`
  for a percent). Report the new schedule and timeline shift.

### Saving

**No new write endpoint.** `save_hint` describes the mutation and names the *existing*
endpoint that performs it (`POST /api/debts`, `PUT /api/profile`). The UI's "Save this to
my plan" button calls that endpoint directly. Keeps the write path, its validation, and
its tests exactly where they already are.

---

## File 4 — `backend/bot.py` (new)

Retrieval and routing. Pure standard library, deterministic. Open with a module docstring
in the house style, stating *why* it's pattern-matching rather than embeddings, and how it
guarantees it never fabricates a number.

**1. Normalize** — lowercase; expand contractions; preserve compound tokens before
stripping punctuation (`401(k)`→`401k`, `403(b)`→`403b`, `s&p 500`→`sp500`, `59½` and
`59 1/2`→`59.5`); strip punctuation; collapse whitespace. **Extract slots from the raw
text first**, before punctuation stripping destroys `$35,000`.

**2. Alias expansion** — curated `ALIASES`, applied longest-phrase-first so `"my work
retirement plan"` resolves before `"retirement"`.

```
401k           ← 401 k, four oh one k, work retirement, workplace plan, employer plan
ira            ← individual retirement, roth ira, traditional ira
hsa            ← health savings, triple tax
match          ← employer match, company match, free money, matching
emergency_fund ← rainy day, safety net, cash cushion
student_loan   ← student debt, student loans, college debt, my loans
```

**Alias quality is the product.** Match quality is almost entirely this map, not the
scoring maths. Budget effort accordingly.

**3. Tokenize, stem, drop stopwords** — hand-rolled suffix stemmer (`ing`, `ed`, `es`,
`s`, `ly`), minimum stem length 4, exception list. `taxes → tax` wanted; `roth → rot` not.
Stopwords: `what how should i my me a an the is are do does can could of to in for about
if when will would`. **Keep** `roth`, `traditional`, `early`, `late`, `before`, `after`.

**4. Typo repair** — build a module-level `VOCABULARY` of every stemmed corpus term. For
query tokens matching nothing:

```python
difflib.get_close_matches(token, VOCABULARY, n=1, cutoff=0.82)
```

Only for tokens of **5+ characters** — shorter ones mangle (`roth` → `both`). A repaired
token carries a **0.9 multiplier** so exact always outranks fuzzy. Collect into
`corrections` for the UI to show "showing results for…".

**5. Unigrams and bigrams** — build bigrams from adjacent stemmed tokens **before**
stopword removal (removing them first corrupts adjacency), then drop bigrams whose halves
are both stopwords.

```
score = ( Σ idf(u) matched unigrams  +  1.5 × Σ idf(b) matched bigrams )
        ───────────────────────────────────────────────────────────────
        ( Σ idf(u) query unigrams     +  1.5 × Σ idf(b) query bigrams  )
```

Normalized 0–1: the fraction of the query's meaningful weight the entry accounts for.
This is what stops an entry that merely contains "expense" and "ratio" in unrelated
sentences from outranking the real one. IDF computed across all corpora once at import,
cached at module level.

**6. Bonuses** — additive, clamped to 1.0:

| Bonus | When |
|---|---|
| `+0.20` | A scenario intent matches **and** its required slots are present |
| `+0.15` | Exact canonical-question match after normalization |
| `+0.10` | Detected account entity matches the entry's subject |
| `+0.10` | Personal entries, when the query contains `i`/`my`/`me`/`mine` |
| `+0.15` | Context: entry shares the previous answer's topic |
| `+0.20` | Context: entry id is in the previous answer's `related`/`follow_ups` |

The first-person bonus earns its place: "how much can **I** put in" wants their number;
"how much can you put in an HSA" wants a definition. The pronoun is the only difference.

**7. Follow-up context** — the server stores nothing. The client sends
`{"previous_id": ..., "previous_topic": ...}`. Applied **only** when the query looks
referential: fewer than 5 meaningful tokens **and** containing one of `what about`,
`and`, `that`, `it`, `this`, `instead`, `same for`, `how about`. Otherwise ignored
entirely, so a fresh question is never dragged toward the previous topic. A referential
query with **no entity of its own inherits the previous one** — that is the mechanic that
makes `"what about traditional?"` resolve after `can_i_do_roth`. Every response echoes a
`context` object for the next request.

**8. Multi-part splitting** — a **fallback, not the default**. If the whole query scores
≥ `STRONG`, never split; that is what protects `"should I pay off debt and invest?"`,
which matches `debt_or_invest` strongly as one question. Below `STRONG`, try splitting on
` and `, ` also `, ` plus `, `, and `, or a mid-string `?`. Accept only if the split point
is **not inside a known alias phrase** (guards "stocks and bonds", "Roth and
traditional", "avalanche and snowball"), **both halves independently clear `WEAK`**, and
it yields exactly **2 parts**.

**9. Route** — `STRONG = 0.55`, `WEAK = 0.25` as module constants, tunable against the
test table. Declines are checked **before** the strong branch and win ties. Before
returning `unmatched`, check `content.GLOSSARY` keys and `term` values — "what is a bond"
should return a definition, not nothing.

```python
def answer(text, user, year=L.DEFAULT_YEAR, context=None) -> dict
def suggest(text, limit=3) -> list[dict]
```

---

## File 5 — `backend/app.py` (edit)

New `# --- free-text ask ---` section, matching existing style (`@app.get`/`@app.post`,
docstrings explaining *why*, `DISCLAIMER` on every answer payload). No manual try/except
for validation — `_body()` raises `ValueError`, which the registered handler turns into a
400.

| Method | Path | |
|---|---|---|
| POST | `/api/ask` | `{question, year?, context?}` → `bot.answer(...)` |
| GET | `/api/knowledge` | `knowledge.index()` |
| GET | `/api/knowledge/<key>` | One entry; 404 in the existing shape |

POST for `/api/ask`: arbitrary text is safer in a body, it isn't cacheable, and it carries
the context object.

```json
{
  "status": "answered",
  "multi_part": false,
  "corrections": [{"from": "expence", "to": "expense"}],
  "context": {"previous_id": "debt_strategy", "previous_topic": "Debt"},
  "results": [{
    "status": "answered",
    "kind": "scenario",
    "id": "debt_strategy",
    "question": "How should I plan around my 35K of student debt?",
    "confidence": 0.78,
    "answer": {
      "summary": "...", "detail": "...", "facts": [], "sources": ["R3_HIGH_INTEREST_DEBT"],
      "sections": [{"heading": "Where it lands", "body": "...", "facts": []}],
      "assumptions": [{"label": "Interest rate", "value": "6.5%", "note": "not stated — assumed"}],
      "save_hint": {"label": "Add this $35,000 student loan to my plan",
                    "method": "POST", "path": "/api/debts",
                    "body": {"name": "Student loan", "balance": 35000, "apr": 0.065}}
    },
    "suggestions": [], "glossary": []
  }],
  "disclaimer": "..."
}
```

`results` is **always a list** — length 2 for an accepted split. Per-result `status` ∈
`answered | ambiguous | unmatched | declined | needs_input`; `kind` ∈ `scenario |
personal | general | glossary | decline`. Top-level `status` is `answered` if any result
is, else the first's. `confidence` is exposed deliberately, so the UI can say "closest
match" honestly.

---

## File 6 — Frontend

**`ui.jsx`** — add `TextArea`, built from the same shared `inputBase` as `TextInput`, with
`min-h-*`, `resize-y`, a fixed row count (not autosize — avoids layout jump) and
`text-base` (prevents iOS zoom-on-focus). Thread through `Field`'s render-prop.

**`AnswerBody.jsx`** (new) — extract the answer markup from `AskAnswer` so every answer
kind renders identically: Layer 1 `Card tone="brand"` summary, Layer 2 `Card` detail,
`facts` `<dl>`, sources footer. **Plus, when present:** `sections` as headed blocks, and
`assumptions` in a `Card tone="sunken"` — assumptions must be visible, not buried, since
an assumed interest rate changes the answer. All text through `<Annotated>`.

**`AskPage.jsx`** — rewrite `AskIndex`:
- `TextArea` in a `Field`, autofocused, placeholder "Ask anything — how should I plan around my 35K of student debt?"
- Submit button, not live search. Local `useState` for `submitting`/`transcript`/`error`,
  following `YouPage`'s `saving`/`saveError` precedent. **`useApi` is the wrong shape** —
  it fires on mount and dep change.
- **Send `context` from the last transcript entry** on every submit.
- Transcript newest last; map over `results` (two stacked answers for a split, with a
  quiet "You asked two things" label).
- `save_hint` → a secondary "Save this to my plan" `Button` that calls the named existing
  endpoint, then a `Toast` on success.
- `needs_input` → render the specific follow-up question with the input refocused.
- `corrections` → quiet "Showing results for *expense ratio*." above the answer.
- `ambiguous` → three tappable "Did you mean:" chips. `declined` → decline copy plus
  redirect chips. `unmatched` → `EmptyState` plus the browse list. **Never a dead end,
  never a fabricated answer.**
- Keep the browse-by-topic list, demoted below the input as "or browse by topic".

**`App.jsx`** — `AskIndex` currently does **not** receive `glossary` (only `AskAnswer`
does). It must now, since it renders answers.

**`lib/api.js`** — `ask: (question, context) => request('/ask', { method: 'POST', body: { question, context } })`,
plus `knowledge` / `knowledgeEntry`.

**`Term.jsx`** — `Annotated`'s pattern table maps ~30 terms to glossary ids. New KB
vocabulary needs patterns added or those terms won't be tappable.

Accessibility: transcript gets `aria-live="polite"`; reuse the global focus ring; only
`index.css` palette tokens, no ad hoc hex. Preserve zero WCAG A/AA violations.

---

## File 7 — Tests

`test_bot.py`, `test_slots.py`, `test_scenario.py`, `test_knowledge.py`, using the
existing `client`/`rich_client` fixtures. **Current suite is 200 passing — no
regressions.**

**The benchmark test, first and by name:**
```python
def test_benchmark_student_debt_question(rich_client):
    """The question this whole feature exists to answer."""
    body = rich_client.post("/api/ask", json={
        "question": "How should I plan around my 35K of student debt?"}).get_json()
    r = body["results"][0]
    assert r["kind"] == "scenario" and r["id"] == "debt_strategy"
    assert "$35,000" in r["answer"]["summary"]
    assert r["answer"]["assumptions"]            # the assumed rate is disclosed
    assert r["answer"]["save_hint"]["path"] == "/api/debts"
    assert "R3_HIGH_INTEREST_DEBT" in r["answer"]["sources"]
    assert len(r["answer"]["sections"]) >= 3
```

- **Slots** — `35k`, `$35,000`, `35,000`, `thirty five thousand`, `$1.2m` all parse.
  Cadence splits stock from flow: `"35k of student debt"` is a balance, `"$300 a month"`
  is a flow. `"at 62%"` does **not** parse `62` as an age.
- **Scenario purity** — after any scenario runs, the stored profile is **byte-identical**.
  Assert via `GET /api/profile` before and after. This is the safety property.
- **Scenario correctness** — a 23% credit card crosses the 0.075 cutoff and reports
  payoff-first; a 6.5% student loan does not. Assert the flip happens at the threshold
  read from `limits_2026.json`, not at a literal.
- **Needs-input** — `"how should I handle my student debt"` with no amount returns
  `needs_input` and asks for the balance; it does **not** invent one.
- **Matching table** — 60+ real phrasings, including slang ("free money from work" →
  `am_i_missing_match`) and indirect ones ("is my money gonna run out" →
  `can_i_retire_when_i_want`).
- **Typo repair** — `"expence ratio"`, `"divident"`, `"retirment"` resolve with a
  `corrections` entry. Negative: a 4-char typo is not repaired; `"roth"` never matches
  `"both"`.
- **Bigram precision** — `"expense ratio"` outranks an entry merely containing both words
  separately. Assert the ranking, not just the match.
- **Multi-part** — `"roth or traditional and how much can i put in"` → 2 results.
  **False-split guards, each explicit:** `"should i pay off debt and invest"` → 1;
  `"stocks and bonds"` → 1; `"avalanche and snowball"` → 1.
- **Follow-up context** — `can_i_do_roth` then `"what about traditional?"` resolves.
  Negatives: the same follow-up **without** context → `ambiguous`; a long non-referential
  question is **unaffected** by a supplied context.
- **Invariant** — bot-routed personal answers are identical to `qa.ask(id, user, year)`.
  The mechanical proof the bot selects but never computes.
- **Round-trip coverage** — every KB entry reachable by its canonical question and two
  alternate phrasings from its `keywords`. Forces alias quality.
- **Declines** — each pattern fires on 3+ phrasings; "should I wait for a market dip"
  routes to `market_timing`, *not* a decline.
- **Content integrity** — every `related` resolves; every `glossary_terms` key exists; no
  `detail` under 80 chars; no duplicate canonical questions.
- **Determinism** — identical output across repeated calls (guards set-iteration order
  leaking into ranking).

## Verification

```bash
cd /Users/ethanmic/FinancialPlanner
.venv/bin/python -m pytest backend/tests -q      # 200 + new, all green
.venv/bin/python backend/app.py                  # port 5001

A() { curl -s localhost:5001/api/ask -H 'Content-Type: application/json' -d "$1" | python -m json.tool; }

# THE BENCHMARK
A '{"question":"How should I plan around my 35K of student debt?"}'
#   → kind "scenario", sections, assumptions (rate disclosed), save_hint → POST /api/debts
curl -s localhost:5001/api/profile > /tmp/before.json
A '{"question":"How should I plan around my 35K of student debt?"}' > /dev/null
curl -s localhost:5001/api/profile | diff /tmp/before.json -   # MUST be empty

A '{"question":"i got 10k what do i do with it"}'   # windfall, allocation diff
A '{"question":"what if i made 75k"}'               # income_change
A '{"question":"what if i saved 300 a month"}'      # contribution_change
A '{"question":"how should i handle my student debt"}'  # needs_input, asks the balance
A '{"question":"whats an expence ratio"}'           # general + corrections
A '{"question":"stocks and bonds"}'                 # 1 result, NOT split
A '{"question":"should i buy nvidia"}'              # declined + redirects
A '{"question":"asdfgh qwerty"}'                    # unmatched + browse index
```

Then `cd frontend && npm run dev` and confirm at `/ask`: the benchmark question returns a
sectioned answer with visible assumptions and a working "Save this to my plan"; a
follow-up resolves; a two-part question stacks two answers; a typo shows the correction
line; ambiguous shows chips; declined explains itself; glossary terms are tappable.
`npm run lint` clean.

## Definition of done

- [ ] `botplan.md` overwritten with this plan
- [ ] **The benchmark question answered well**, with the purity test green
- [ ] `slots.py` — amounts, rates, kinds, cadences, ages, with stock/flow disambiguation
- [ ] `scenario.py` — `trial()` copy helper; 4 scenarios (debt strategy, windfall, income
      change, contribution change); `income` added to `WHAT_IF_FIELDS` with
      `pay.sync_capacity` re-run; `save_hint` pointing at existing write endpoints
- [ ] ~80 KB entries extending rather than duplicating the 33 glossary terms
- [ ] ~8 decline patterns across both buckets, each with redirects
- [ ] `bot.py` — stdlib only; difflib typo repair, bigram scoring, multi-part splitting
      with false-split guards, client-supplied follow-up context, `needs_input` routing
- [ ] Three endpoints live, following existing conventions
- [ ] Every test group above green; full suite green, no regressions
- [ ] `AskPage` rewritten; `AnswerBody` extracted with `sections` + `assumptions`;
      `TextArea` added; `glossary` threaded to `AskIndex`; context sent on submit;
      save-to-plan wired to existing endpoints
- [ ] `README.md` API table and Q&A section updated; KB noted as distinct from the
      learning logs
- [ ] Decisions appended to `financialplannerscope.md`
