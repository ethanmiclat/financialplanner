# Financial Planner — v1 backend

Scope 1 of `financialplannerscope.md`: the deterministic engine and the content, no UI.
Everything the frontend will need is behind a JSON API.

## Run it

Two processes. Backend first — the frontend proxies `/api` to it.

```bash
# Backend — http://localhost:5001
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd backend && ../.venv/bin/python app.py
../.venv/bin/python -m pytest tests -q       # 672 tests

# Frontend — http://localhost:5173
cd frontend && npm install && npm run dev
```

First request seeds a demo profile into `backend/data/profile.json`
(`POST /api/profile/reset` restores it; `FP_STORE` overrides the path).

| Env var | |
|---|---|
| `FP_STORE` | Where the single-user profile lives |
| `FP_TODAY` | Pin the date (`2027-01-05`) — the tests use it, and it previews a new year |
| `FP_DEMO=1` | Public demo: every visitor gets a private sandbox profile (keyed by an `X-Footing-Visitor` header or a cookie, expires after a day, capped at 500); `FP_STORE` is never read |
| `FP_DEMO_DIR` | Where demo sandboxes go (default: the system temp dir) |
| `FP_CORS_ORIGINS` | Comma-separated origins allowed to call the API (default: any) |
| `VITE_API_BASE`, `FP_BASE` | Frontend build only: the API's origin, and the path the site is served under |

## Deploy

**Live setup: frontend on GitHub Pages, API on PythonAnywhere.** Pages only serves
static files, so the Flask engine runs on PythonAnywhere's free tier, which, unlike
Render's free plan, never sleeps, so there's no cold start.

- `.github/workflows/pages.yml` builds the React app on every push to `main` and
  publishes it to `https://ethanmiclat.github.io/financialplanner/`. It sets Vite's
  base path to the repo name and copies `index.html` to `404.html`, so a refresh on
  `/accounts` still boots the app.
- The build points the frontend at the API through `VITE_API_BASE` (the repo
  variable `API_BASE`, defaulting to `https://ethanmiclat.pythonanywhere.com`).
- Demo visitors are told apart by an `X-Footing-Visitor` header holding an id kept in
  `localStorage`, not a cookie: Safari drops cookies on cross-site requests.
  `FP_CORS_ORIGINS` limits which site may call the API.

### One-time setup

**GitHub Pages:** repo Settings → Pages → Source: **GitHub Actions**. The next push
to `main` deploys.

**PythonAnywhere** (free "Beginner" account):

1. In a Bash console:
   ```bash
   git clone https://github.com/ethanmiclat/financialplanner.git
   cd financialplanner
   mkvirtualenv footing --python=python3.13   # or the newest 3.1x offered
   pip install -r requirements.txt
   ```
2. Web tab → **Add a new web app** → Manual configuration → the same Python version.
3. Set **Virtualenv** to `/home/ethanmiclat/.virtualenvs/footing`.
4. Open the **WSGI configuration file** link and replace its contents with
   `deploy/pythonanywhere_wsgi.py`.
5. **Reload**. `https://ethanmiclat.pythonanywhere.com/api/health` should say
   `"demo": true`.

To update the API later: `cd financialplanner && git pull`, then Reload. Free web
apps must be extended every three months (a button on the Web tab; they email a
reminder first), or they're switched off until you click it.

### Other ways to run it

One service, one origin: Flask serves the built frontend itself when `frontend/dist`
exists. `Dockerfile` builds the React app and runs gunicorn with demo mode on;
`render.yaml` is a ready Render blueprint (free plan, which sleeps when idle, so the
first visit after a while takes ~30s).

```bash
docker build -t footing . && docker run -p 8000:8000 footing   # http://localhost:8000
```

Demo mode is on in every public setup deliberately: a portfolio link shouldn't
expose the owner's numbers or let visitors overwrite them. Each visitor starts from
the seed student and can reset with "Start over".

## The year, and progress over time

The plan is always for the current calendar year (`limits.current_year()`), not a
constant. On the first load of a new year the store rolls over: this year's
contributions and match go back to $0 and the user ages a year — logged as a
`new_year` history entry. Until the IRS publishes the new year's numbers (each
October/November), `load_limits` falls back to the latest file with
`provisional: true`; limits only rise, so that never overstates anyone's room.
Adding next year is still a new `data/limits_YYYY.json`, not a code change.

Every save also records a daily snapshot (owned, owed, cash) — the "Over time" chart
on the Accounts page. Reads never add one.

## Roth or traditional

`tax.py` estimates the federal rate on your next dollar now (income less the standard
deduction) and in retirement (spending beyond Social Security as pre-tax withdrawals,
plus the taxable share of Social Security under §86), on the year's brackets in the
limits file. Lower now → Roth; lower later → traditional; a tie leans Roth. The IRA
step, the bot and the You page all use it; the user's own answer still overrides.
Federal only, standard deduction only — it decides which bracket the next dollar is
in, which is the whole question, not a tax return.

The demo is a **20-year-old college student on a part-time minimum-wage job** —
$13,500 a year, $800 saved, a small Roth IRA, a $350 credit card at 27% and a
subsidised student loan at 6.5%. Chosen over a high earner because it exercises the
branches that matter for someone starting out (no 401(k) offered, no HSA, one debt
above the high-interest cutoff and one below) and because it makes the projection tell
the truth: small amounts, decades of compounding. Behaviour tests use a `rich_client`
fixture instead, so the seed can change freely without breaking them.

## Layout

| File | Role |
|---|---|
| `backend/data/limits_2026.json` | Every IRS number. Next year is a new file, not a code change. |
| `backend/limits.py` | Limit/phase-out lookups: age-banded catch-ups, Roth MAGI phase-out. |
| `backend/models.py` | `User`, `Account`, `Holding`, `Debt`, `Goal`, `ActionItem`, `LearningLog`. |
| `backend/waterfall.py` | The 10 rules + the engine. Pure functions, no I/O. |
| `backend/retirement.py` | Retirement-age maths: readiness, the pre-59½ bridge, Social Security, RMDs, milestones. |
| `backend/schedule.py` | The year's plan as a calendar: this month's moves, one payday, the next 12 months. |
| `backend/pay.py` | Pay frequency, and one saving figure expressed in every unit someone might use. |
| `backend/target.py` | The plan run backwards: what reaching a number costs per year, month and paycheck. |
| `backend/content.py` | Layer 1/2/3 copy, learning logs, and the plain-English glossary. |
| `backend/qa.py` | The structured Q&A layer — 18 questions, each a pure function. |
`backend/bot.py` — the free-text bot: routes a typed question to the right answer, no LLM
`backend/knowledge.py` — ~85 general-finance explanations plus the questions the bot declines
`backend/slots.py` — reads amounts, rates, ages and debt/account kinds out of a sentence
`backend/scenario.py` — runs a typed number as a what-if on a copy and composes the answer
| `backend/projection.py` | Compound-growth projections. Illustration, not forecast. |
| `backend/store.py` | Single-user JSON persistence (auth deferred per the scope doc). |
| `backend/app.py` | Flask routes. |
| `frontend/` | React + Vite + Tailwind v4 UI. See **Frontend** below. |

## The waterfall

Ten rules, evaluated in order. Every rule reports on every run — one that doesn't apply
says so rather than going silent, so the dashboard never has an unexplained gap.

| Step | Rule | Fires when |
|---|---|---|
| 1 | `R1_EMERGENCY_FUND` | Cash under 3 months of expenses blocks investing; under target is a top-up |
| 2 | `R2_EMPLOYER_MATCH` | Deferrals below the full-match threshold |
| 3 | `R3_HIGH_INTEREST_DEBT` | Any debt above 7.5% APR (≥15% is blocking) |
| 4 | `R4_HSA` | HDHP enrolled and room left |
| 5 | `R5_IRA` | Room left; branches on the Roth phase-out into direct / partial / backdoor |
| 6 | `R6_REMAINING_401K` | Deferral room left; flags the 2026 mandatory-Roth catch-up rule |
| 7 | `R7_TAXABLE` | Activates once tax-advantaged room hits zero |
| 8 | `R8_VEHICLE` | Uninvested cash inside an investment account, or a fund over 0.50% ER |
| 9 | `R9_RETIREMENT_AGE` | Retiring before 59½ (reachable "bridge" money), before 65 (health coverage), past the RMD age, or past 65 with an HSA |
| 10 | `R10_READINESS` | The plan doesn't pay for the chosen age — quantifies save more / retire later / spend less |

Step 8 is the Foundational Five's fifth item (index/target-date funds) as a rule. It runs
alongside the others rather than after them: a funded account holding cash isn't investing.

Every `ActionItem` carries `rule_id`, `rule_name`, `step`, and an `inputs` dict with the
exact numbers used — so a recommendation is always traceable to a rule and its math, which
is both the honesty requirement and the legal framing from the scope doc.

`GET /api/plan` walks `annual_savings_capacity` down the list. Funding order is
`(priority, step)`, not step alone: an emergency fund already past the 3-month floor is a
MEDIUM top-up and does not outrank a guaranteed employer match.

## The Q&A layer

The scope's second surface. `backend/qa.py` holds 18 questions people actually ask,
each answered by a pure function reading the same models, limits and rules as the
dashboard — no LLM, no external API, no generated financial explanation to vet. Every
answer carries `sources` (the rule ids or content keys behind it) and `follow_ups`, so
the tree is browsable and nothing is a black box. "What is an HSA?" reads straight from
`content.py`, so the Q&A and the Learn pages can't drift apart.

## The free-text bot

`POST /api/ask` takes a question in the user's own words and answers it without a
language model. `backend/bot.py` scores the question against four corpora at once —
the 18 personal questions, ~85 general-knowledge entries in `backend/knowledge.py`, a
set of deliberate declines, and the glossary — using IDF-weighted overlap on unigrams
and bigrams, a large hand-built alias map, and `difflib` for typos. Below a confidence
threshold it returns "did you mean" candidates rather than a guess.

A question that carries its own number — *"How should I plan around my 35K of student
debt?"* — goes to `backend/scenario.py`: `backend/slots.py` reads the amount, rate and
kind out of the sentence, the scenario runs the engine on a deep copy of the profile,
and the answer is composed from what comes back, with every assumption (an unstated
interest rate, say) listed on its face. Five scenarios: debt strategy, windfall, income
change, contribution change, retirement age. Nothing is saved; a `save_hint` names the
existing endpoint that would do it. An intent with no number ("how should I handle my
student debt") asks for the number instead of inventing one.

Two-part questions get two answers; a follow-up like "what about traditional?" resolves
against the previous answer's `context`, which the client sends back — the server keeps
no state. The knowledge base is reference material and is distinct from
`content.LEARNING_LOGS`, which stays in Ethan's own words.

The phrasing corpus the bot is tuned against is `backend/tests/phrasings.py`;
`backend/tests/stress.py` runs it and prints every miss with the top candidates.

## Projections

`GET /api/projection?scenario=cautious|middling|strong` returns milestone `points`
(5/10/20 years plus however long until retirement) and a yearly `series` for the chart,
comparing *following the plan* against *your current pace*.

The series runs past retirement to `plan_to_age` (default 95): growth while saving, then
withdrawals of the retirement spending, less Social Security from the claim age. The
payload's `retirement` block answers "does it last?" in today's money, and `milestones`
lists the ages that matter (59½, 62, 65, claim age, RMD age).

Everything is the user's to set. Retirement age, plan-to age, retirement spending and
Social Security live on `Goal`; return while saving, return in retirement, inflation and
yearly savings growth live on `User.assumptions`. Any of those (plus
`annual_savings_capacity`) can be passed as query parameters —
`/api/projection?retirement_age=50&return_rate=0.05` — to try a what-if on a copy of the
profile without saving it. The age thresholds are data, in `limits_2026.json` under `ages`.

Two modelling decisions worth knowing:

- **One-off costs are a delay, not a permanent drain.** Clearing a card and filling an
  emergency fund consume the first year or two of savings capacity. Treating them as
  recurring produced "you invest $0 a year, forever" — wrong, and the exact opposite of
  what the feature is for. They're modelled as `years_until_investing` instead.
- **Three return scenarios, never one.** A single confident line reads as a promise.
  The payload also carries its own `assumptions` and `disclaimer`, and the UI displays
  the assumptions expanded by default — a projection without them is a lie.

## The schedule

`backend/schedule.py` turns the year's plan into something you can follow on payday:
`this_month` (each move with its monthly and per-paycheck amount), `paycheck` (take-home
minus bills minus transfers = what's left to spend), and `months` (the next twelve, with
a milestone the month a step finishes).

Targets come from `W.prioritized()`, so the schedule and the dashboard can't disagree.
Each rule has a *mode*: `asap` fills a finite gap as fast as the money allows (emergency
fund, debt), `spread` paces payroll money across the remaining months of the year,
`recurring` is a standing monthly amount, and `sink` (taxable) absorbs the rest. Annual
room refills on 1 January.

Two modelling decisions, both stated in the payload's `notes`:

- **Minimum debt payments are bills, not savings decisions.** A balance moves by interest
  minus the minimum each month; savings capacity is what's left after them.
- **Payroll money only moves on payday.** 401(k) lines are paced rather than
  front-loaded — in a plan with no true-up, filling the limit early can cost match in the
  months that follow. Deferrals are also *not* subtracted from take-home pay, because
  they never reach the account.

## Saving in whatever unit you think in

One number is stored — `annual_savings_capacity`, which every rule reads. But nobody
thinks in it, so `User` also carries `savings_basis` (`yearly` / `monthly` /
`per_paycheck` / `percent_of_pay`) and `savings_amount`, the figure as typed.
`pay.sync_capacity()` derives the yearly number from those two on every write, which
means the pair can't drift apart *and* a percent-of-pay plan follows a raise or a change
of pay frequency without being retyped. `pay.amounts()` hands any figure back in all
four units at once, plus its share of gross and of take-home.

## Reaching a number

`GET /api/target` runs the plan backwards. Everything else asks "where does this get
me?"; this asks "what does that take?" — the question people actually arrive with.

Three kinds of target: `goal=retirement` prices the retirement already on the profile,
`goal=amount&amount=1000000` a nest egg in today's money, `goal=income&monthly=5000` a
monthly income. `by_age` moves the deadline, `starting_in` delays the first
contribution.

A contribution is linear in the final balance, so the required amount is just the
shortfall divided by what one dollar a year grows into — the same growing-annuity
closed form the projection uses, solved for the contribution. The answer comes back in
every unit (`required`), next to what they're already doing (`current`) and the
difference (`extra`).

Two things it reports that a bare number doesn't:

- **The coast number.** The balance where compounding alone carries you to the target,
  with `age` for when the current plan reaches it. It reframes the task: the hard part
  usually ends years before the target does.
- **The cost of waiting.** The same target started 1, 3 and 5 years later. The deadline
  doesn't move, so the monthly figure does.

`notes` says when the figure won't work and why — more than you earn, more than your
tax-advantaged room, more than your take-home covers, or resting on a Social Security
estimate we don't have. Nothing is saved; an estimate is a question, not a change of plan.

## API

| Method | Path | |
|---|---|---|
| GET | `/api/health` | Current year, whether its limits are provisional, demo mode |
| GET | `/api/limits?year=&age=` | Seed table, plus this age's limits |
| GET/PUT/PATCH | `/api/profile` | PATCH is user fields only |
| POST | `/api/profile/reset` | |
| PUT | `/api/goal` | Partial; includes retirement age, spending, Social Security. Validated |
| PUT | `/api/assumptions` | Partial; returns, inflation, savings growth. Validated |
| GET/POST | `/api/accounts` | |
| PUT/DELETE | `/api/accounts/<id>` | |
| GET/POST | `/api/debts`, DELETE `/api/debts/<id>` | |
| GET/POST | `/api/activity` | Log a movement — `{kind: add\|withdraw\|pay\|set_balance, account_id\|debt_id, amount}`. Applied as arithmetic (a deposit also counts toward this year's limit), logged, and answered with the plan steps it finished |
| GET | `/api/history` | Daily snapshots for the progress chart, plus the emergency-fund target |
| GET | `/api/tax?income=` | Roth or traditional: both marginal rates and the verdict; `income` is a what-if, never saved |
| DELETE | `/api/activity/<id>` | Undo: restores exactly the fields that entry changed; 409 if they've changed again since |
| GET | `/api/actions?order=priority` | The action list (`order=priority` for the to-do view) |
| GET | `/api/actions/<rule_id>` | One rule, with its inputs |
| GET | `/api/plan` | Capacity allocated down the waterfall |
| GET | `/api/projection?scenario=&retirement_age=…` | Growth and drawdown, readiness, milestones; what-if params aren't saved |
| GET | `/api/schedule?months=` | This month's moves, one payday, the next 1–24 months |
| GET | `/api/target?goal=&amount=&monthly=&by_age=&starting_in=` | What reaching a number costs per year, month and paycheck |
| GET | `/api/questions`, `/api/questions/<id>` | The structured Q&A layer |
| POST | `/api/ask` | Free text in; `{question, context?}` → routed answer(s), suggestions, `context` for the next turn |
| GET | `/api/knowledge`, `/api/knowledge/<key>` | The general-knowledge entries, grouped by topic |
| GET | `/api/glossary` | Plain-English definitions for every term the UI uses |
| GET | `/api/waterfall` | Why the order is the order |
| GET | `/api/content`, `/api/content/<key>` | Layer 1/2/3 per account type |
| GET | `/api/learning-log` | Source content behind the Layer 2 copy |

Content keys: `401k`, `ira`, `hsa`, `taxable`, `index_funds`.

`GET /api/content/<key>` returns `layer1.decision` (one line, using the user's own
numbers), `layer2.why` (a paragraph of mechanics), and `layer3` (edge cases plus the hard
numbers). `?personalize=false` returns the generic version.

## Frontend

Mobile-first React + Vite + Tailwind v4. Five destinations — exactly at the bottom-bar
ceiling, which is why the labels are one short word each: **Plan**, **Accounts**,
**Ask**, **Learn**, **You**. Projections live at `/projection`, the month-by-month
schedule at `/schedule` and the goal estimator at `/goal`, all three reached from cards
on the Plan page rather than becoming a sixth, seventh and eighth nav item. The three
cards answer the three different questions in order: what do I do, what is it worth,
and what would it take.

### Design decisions

**Palette — white + green.** Tokens live in `src/index.css` under `@theme`. Every
foreground/background pair was measured with a contrast script, not eyeballed, and
`ink-faint` is solved against the *darkest* surface it lands on (`surface-sunken`),
not against white — solving against white alone let small labels fail in place. The
green is split by job: `brand` (#04724d, 6.0:1) is the only green allowed on text and
icons; `brand-bright` (3.8:1) is for fills and progress bars behind white text.
`axe-core` reports zero WCAG 2.1 A/AA violations across all six routes at 375px and
1440px.

**Typography — Plus Jakarta Sans.** Friendly enough for an anxious first-time reader,
not so rounded it reads as a children's product — this is people's retirement money.
16px minimum on inputs so iOS Safari doesn't zoom-and-jump on focus.

**Built for someone who doesn't know the vocabulary.** This drove most of the UI:

- *Layered disclosure everywhere.* An action card shows one line — the decision — and
  nothing else. "Why this matters" opens the plain-English paragraph; "See the numbers"
  opens the arithmetic plus the `rule_id` that produced it. Nobody is handed three
  layers at once, and nothing is a black box.
- *Tappable glossary.* `Annotated` scans backend copy for jargon and wraps the first
  occurrence of each term in a real `<button>` (`src/components/Term.jsx`). Under 640px
  it opens a bottom sheet — thumb-reachable, and it can't clip off-screen the way an
  anchored popover does next to a word near the right edge. Above 640px it anchors to
  the word and flips alignment in the right half of the viewport.
- *Priority reads three ways.* Icon + word + color ("Do this first", "High impact"),
  never color alone.
- *The header leads with the next single action*, not a 0% progress bar.
- *Forms validate on blur*, not per keystroke, with a persistent hint under every input
  and errors next to the field that caused them.

**The chart is hand-rolled inline SVG.** Two series and ~50 points don't justify a
charting library, and writing it directly meant the accessibility could be right: the
series differ by line style as well as colour (solid vs dashed), the readout sits below
the chart rather than in a floating tooltip that can't survive a touchscreen, hit
targets are full-height strips rather than 4px dots, and the milestone table is the
real screen-reader path — the SVG carries a summary label and the numbers live in the
table.

**Ordering.** The engine returns waterfall order, which is right for the explainer but
wrong for a to-do list — a card badged "Do this first" would sit third behind two
lower-urgency items. `PlanPage` re-sorts by `(priority, step)`, matching how `/api/plan`
allocates money. Cards are labelled "#N on your list" rather than "Step N", because the
rule copy already uses "step" for waterfall position and the two numberings diverge.

### Verified

**September 2026 re-run** (after the logging, new-year, progress, tax and dark-mode
work): `axe-core` reports zero WCAG 2.1 A/AA violations on all 8 routes plus the
History tab, the log sheet and the Roth-or-traditional card — in light and dark, at
375 and 1280px. It caught one: `ink-faint` on the pale-green selected tile was 4.3:1,
now darkened to pass on every background it lands on.

Earlier:

Playwright, across the 10 routes that existed at the time, at 320 / 375 / 768 / 1440px.
`/schedule` and `/goal` have been driven at 375 and 1280px for layout and console errors
but **have not been through `axe-core` yet**:

- `axe-core` — zero WCAG 2.1 A/AA violations.
- No horizontal page overflow, no console errors.
- Touch targets ≥44px; disclosures keyboard-reachable and Enter-operable.
- Glossary popovers checked against every clipping ancestor and both viewport edges.
- Horizontally scrolling regions are focusable (`ScrollX`), so keyboard users can
  reach them.
- `prefers-reduced-motion` honoured.
- End-to-end: add account → confirm dialog → delete; every Q&A answer rendered and
  every follow-up link resolved; browser back walks the question history.

## Notes for the frontend

- Actions are derived from state on every request, not stored. Marking one "done" means
  changing the account or debt that produced it — `POST /api/actions/<id>/status`
  recomputes and tells you whether the rule still fires rather than setting a flag.
- `priority` is `blocking | high | medium | low | info`; `info` items are the "this rule
  doesn't apply to you, here's why" cards and sort last.
- `content.DISCLAIMER` ships on every content and action payload. It should be visible.

## Deliberately not here

Auth/multi-user, the React dashboard, the structured Q&A UI, and everything in the scope
doc's v2+ list (RSUs, options, alternatives, document parsing).
