import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ActionCard from '../components/ActionCard'
import Icon from '../components/Icon'
import { Button, Card, ErrorState, SegmentedTabs, Skeleton } from '../components/ui'
import { Ring, Stepper } from '../components/viz'
import { money } from '../lib/format'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'
import { presetFor, useLog } from '../lib/logContext'

function PlanSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-36 w-full" />
      <div className="grid grid-cols-3 gap-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      <Skeleton className="h-72 w-full" />
    </div>
  )
}

/** The one thing to do next, and a button that takes you to it. Progress is a ring,
 *  not a sentence — and it's about steps settled, so a new profile isn't greeted
 *  with "0%" as its first word. */
function Hero({ next, settled, total, onGo }) {
  const pct = total ? settled / total : 0
  const { openLog } = useLog()
  const preset = presetFor(next)
  return (
    <Card tone="brand" className="p-5">
      <div className="flex items-center gap-4">
        <Ring value={pct} size={84} stroke={9} label={`${settled} of ${total} steps handled`}>
          <span className="tabular text-lg font-bold leading-none text-ink">{settled}<span className="text-ink-faint">/{total}</span></span>
          <span className="text-[0.625rem] font-semibold uppercase tracking-wide text-ink-faint">handled</span>
        </Ring>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wide text-brand">
            {next ? 'Do this next' : 'All steps handled'}
          </p>
          <h1 className="mt-0.5 text-lg font-bold leading-snug tracking-tight text-ink sm:text-xl">
            {next ? next.title : 'Your plan is fully funded for this year'}
          </h1>
          {next?.amount != null && (
            <p className="tabular mt-0.5 text-2xl font-bold text-brand">{money(next.amount)}</p>
          )}
        </div>
      </div>
      {next && (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <Button onClick={onGo} icon="arrowRight" className="w-full sm:w-auto">
            Show me how
          </Button>
          {preset && (
            <Button variant="secondary" icon="check" onClick={() => openLog(preset)} className="w-full sm:w-auto">
              {preset.kind === 'pay' ? 'I made a payment' : preset.kind === 'invest' ? 'I invested it' : 'I put money in'}
            </Button>
          )}
        </div>
      )}
    </Card>
  )
}

/** Shown once per year, for the first few weeks after January 1: the reset is
 *  automatic, and a to-do list that suddenly grew back needs a reason. */
const seen = (key) => { try { return localStorage.getItem(key) === '1' } catch { return false } }

function NewYear() {
  const { data } = useApi(api.activity, [])
  const [now] = useState(() => Date.now())
  const [dismissed, setDismissed] = useState(false)
  const entry = data?.find((e) => e.kind === 'new_year')
  if (!entry) return null
  const key = `footing:new-year-${entry.target_name}`
  const fresh = now - new Date(entry.date).getTime() < 45 * 864e5
  if (!fresh || dismissed || seen(key)) return null
  const dismiss = () => {
    try { localStorage.setItem(key, '1') } catch { /* private mode: dismiss for this visit only */ }
    setDismissed(true)
  }
  return (
    <Card tone="brand" className="flex items-start gap-3 p-4">
      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand text-on-brand">
        <Icon name="calendar" className="size-5" />
      </span>
      <div className="min-w-0 flex-1">
        <h2 className="font-bold tracking-tight text-ink">Welcome to {entry.target_name}</h2>
        <p className="mt-0.5 text-sm leading-relaxed text-ink-soft">
          Yearly limits reset on January 1, so what you put in last year no longer counts. Steps you'd
          finished may be back on the list — that's new room, not lost progress.
        </p>
      </div>
      <button type="button" onClick={dismiss} aria-label="Dismiss"
        className="grid size-11 shrink-0 cursor-pointer place-items-center rounded-xl text-ink-soft hover:bg-surface">
        <Icon name="close" className="size-4" />
      </button>
    </Card>
  )
}

/** Three tiles, three questions: what is it worth, what do I do on payday, what would
 *  it take. Each is a door to the page that answers it — a number and a caption, not a
 *  paragraph. */
function StatTiles() {
  const projection = useApi(() => api.projection(), [])
  const schedule = useApi(() => api.schedule(1), [])
  const target = useApi(() => api.target(), [])

  const p = projection.data
  const last = p?.points[p.points.length - 1]
  const r = p?.retirement
  const s = schedule.data
  const t = target.data
  const funded = r && r.status !== 'no_spending_info' ? r.funded_ratio : null

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Link to="/projection" className="block rounded-[--radius-card] border border-line bg-surface p-4 transition-colors duration-200 hover:border-brand-border">
        <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wide text-ink-faint">
          Worth by {last?.age ?? '—'} <Icon name="trending" className="size-4" />
        </span>
        <span className="mt-2 flex items-center gap-3">
          {funded != null ? (
            <Ring value={Math.min(1, funded)} size={52} stroke={7} tone={funded >= 1 ? 'brand' : 'alert'} label={`${Math.round(funded * 100)}% funded`}>
              <span className="tabular text-xs font-bold text-ink">{Math.round(funded * 100)}%</span>
            </Ring>
          ) : (
            <Icon name="chart" className="size-8 text-ink-faint" />
          )}
          <span className="min-w-0">
            <span className="tabular block truncate text-xl font-bold leading-tight text-ink">
              {last ? money(last.following_plan) : '—'}
            </span>
            <span className="block text-sm text-ink-soft">
              {funded == null ? 'following the plan' : funded >= 1 ? `on track for ${r.retirement_age}` : `of the way to ${r.retirement_age}`}
            </span>
          </span>
        </span>
      </Link>

      <Link to="/schedule" className="block rounded-[--radius-card] border border-line bg-surface p-4 transition-colors duration-200 hover:border-brand-border">
        <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wide text-ink-faint">
          Each month <Icon name="calendar" className="size-4" />
        </span>
        <span className="tabular mt-2 block text-xl font-bold leading-tight text-ink">
          {s ? money(s.monthly_savings) : '—'}
        </span>
        <span className="block text-sm text-ink-soft">
          {s?.this_month?.moves?.length
            ? `${money(s.paycheck.transfers + s.paycheck.payroll_deferrals)} a paycheck · ${s.this_month.moves.length} ${s.this_month.moves.length === 1 ? 'move' : 'moves'}`
            : 'set a monthly figure'}
        </span>
      </Link>

      <Link to="/goal" className="block rounded-[--radius-card] border border-line bg-surface p-4 transition-colors duration-200 hover:border-brand-border">
        <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wide text-ink-faint">
          What it takes <Icon name="target" className="size-4" />
        </span>
        <span className="tabular mt-2 block text-xl font-bold leading-tight text-ink">
          {t?.required?.monthly != null ? `${money(t.required.monthly)}` : t?.on_track ? 'Covered' : '—'}
        </span>
        <span className="block text-sm text-ink-soft">
          {t?.required?.monthly != null
            ? (t.extra?.monthly > 0 ? `a month · ${money(t.extra.monthly)} more than now` : 'a month · already covered')
            : 'work back from a number'}
        </span>
      </Link>
    </div>
  )
}

/** The waterfall drawn as a rail. Status comes from the actions the engine emitted:
 *  a step whose rule fired is upcoming, the first of those is current, the rest are
 *  handled. Tap a step to jump to its card. */
function Waterfall({ steps, actions, plan, onPick }) {
  const byRule = {}
  for (const a of actions) (byRule[a.rule_id] ||= []).push(a)
  const funded = Object.fromEntries((plan?.steps ?? []).map((s) => [s.rule_id, s]))
  const isTodo = (s) => (byRule[s.rule_id] || []).some((a) => a.priority !== 'info')
  const firstTodo = steps.findIndex(isTodo)
  const rows = steps.map((s, i) => {
    const items = byRule[s.rule_id] || []
    const todo = isTodo(s)
    const status = !todo ? 'done' : i === firstTodo ? 'current' : 'todo'
    const f = funded[s.rule_id]
    const amount = items.find((a) => a.priority !== 'info')?.amount
    return {
      key: s.rule_id, n: s.step, title: s.title, status,
      right: status !== 'done' && amount ? money(amount) : null,
      sub: status === 'done' ? 'Handled' : f?.funded != null ? `${money(f.funded)} of ${money(f.needed)} this year` : null,
      pct: f?.funded != null && status !== 'done' ? Math.min(1, f.funded / f.needed) : null,
      onClick: todo ? () => onPick(items.find((a) => a.priority !== 'info')) : undefined,
    }
  })
  return <Stepper steps={rows} />
}

export default function PlanPage({ glossary }) {
  const actions = useApi(api.actions, [])
  const plan = useApi(api.plan, [])
  const waterfall = useApi(api.waterfall, [])
  const health = useApi(api.health, [])
  const [tab, setTab] = useState('steps')
  const [openId, setOpenId] = useState(null)

  useEffect(() => {
    if (openId && tab === 'todo') {
      document.getElementById(`action-${openId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [openId, tab])

  if (actions.loading) return <PlanSkeleton />
  if (actions.error) return <ErrorState error={actions.error} onRetry={actions.reload} />

  const all = actions.data.actions
  const todo = all.filter((a) => a.priority !== 'info')
  const settled = all.filter((a) => a.priority === 'info')
  // The ring counts steps, not action items: one step can emit several (a card and a
  // loan), and it's handled only when none of them is still open.
  const stepIds = [...new Set(all.map((a) => a.rule_id))]
  const openIds = new Set(todo.map((a) => a.rule_id))
  const stepsDone = stepIds.filter((id) => !openIds.has(id)).length
  const pick = (action) => { if (!action) return; setTab('todo'); setOpenId(action.id) }

  return (
    <div className="space-y-4">
      <NewYear />
      <Hero next={todo[0]} settled={stepsDone} total={stepIds.length} onGo={() => pick(todo[0])} />
      <StatTiles />

      <SegmentedTabs
        label="Plan sections"
        value={tab}
        onChange={setTab}
        tabs={[
          { id: 'steps', label: 'The steps', icon: 'layers' },
          { id: 'todo', label: 'To do', icon: 'list', count: todo.length },
          { id: 'done', label: 'Handled', icon: 'check', count: settled.length },
        ]}
      />

      {tab === 'steps' && (
        <Card className="p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="font-bold tracking-tight text-ink">In this order</h2>
            {plan.data?.annual_savings_capacity != null ? (
              <span className="tabular text-sm text-ink-soft">
                {money(plan.data.annual_savings_capacity)} a year
              </span>
            ) : (
              <Link to="/you" className="text-sm font-semibold text-brand">Set what you can save</Link>
            )}
          </div>
          <div className="mt-4">
            {waterfall.data ? (
              <Waterfall steps={waterfall.data.steps} actions={all} plan={plan.data} onPick={pick} />
            ) : (
              <Skeleton className="h-64 w-full" />
            )}
          </div>
          {plan.data?.unallocated > 0 && (
            <p className="mt-3 rounded-lg bg-brand-soft px-3 py-2 text-sm text-brand">
              <span className="tabular font-bold">{money(plan.data.unallocated)}</span> left after every step — into a taxable account.
            </p>
          )}
          <p className="mt-3 text-xs text-ink-faint">
            Guaranteed returns first, then the best tax treatment. Tap a step to see what to do.
          </p>
        </Card>
      )}

      {tab === 'todo' && (
        todo.length ? (
          <ul className="space-y-3">
            {todo.map((action, i) => (
              <ActionCard
                key={action.id}
                id={`action-${action.id}`}
                action={action}
                glossary={glossary}
                index={i + 1}
                open={openId === action.id}
                onToggle={() => setOpenId((v) => (v === action.id ? null : action.id))}
              />
            ))}
          </ul>
        ) : (
          <Card tone="brand" className="p-5 text-center">
            <Icon name="check" className="mx-auto size-8 text-brand" />
            <p className="mt-2 font-semibold text-ink">Nothing left to do this year.</p>
          </Card>
        )
      )}

      {tab === 'done' && (
        <ul className="space-y-3">
          {settled.map((action) => (
            <ActionCard
              key={action.id}
              id={`action-${action.id}`}
              action={action}
              glossary={glossary}
              open={openId === action.id}
              onToggle={() => setOpenId((v) => (v === action.id ? null : action.id))}
            />
          ))}
        </ul>
      )}

      {health.data?.limits_provisional && (
        <p className="flex items-start gap-2 rounded-xl bg-surface-sunken px-4 py-3 text-sm text-ink-soft">
          <Icon name="info" className="mt-0.5 size-4 shrink-0 text-ink-faint" />
          <span>
            The IRS hasn't published {health.data.default_year}'s limits yet — it does each fall. Until then the
            plan uses {health.data.limits_based_on}'s, which only ever go up, so nothing here overstates your room.
          </span>
        </p>
      )}
      <p className="px-1 pt-2 text-xs leading-relaxed text-ink-faint">{actions.data.disclaimer}</p>
    </div>
  )
}
