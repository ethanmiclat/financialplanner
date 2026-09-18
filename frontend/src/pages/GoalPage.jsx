import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { Annotated } from '../components/Term'
import { Card, Disclosure, ErrorState, Field, MoneyInput, Skeleton, TextInput } from '../components/ui'
import { Bars, Ring } from '../components/viz'
import { money, percent } from '../lib/format'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const GOALS = [
  { id: 'retirement', label: 'My retirement', icon: 'flag' },
  { id: 'amount', label: 'A number', icon: 'target' },
  { id: 'income', label: 'A monthly income', icon: 'calendar' },
]
const digits = (v) => String(v ?? '').replace(/[^0-9.]/g, '')

/** The same money in every unit; whichever one you'd act on is the right one. */
function Amounts({ amounts }) {
  const rows = [
    ['a month', amounts.monthly && money(amounts.monthly)],
    ['a year', amounts.annual && money(amounts.annual)],
    ['per paycheck', amounts.per_paycheck && money(amounts.per_paycheck)],
    ['of your pay', amounts.percent_of_pay != null && percent(amounts.percent_of_pay, 1)],
  ].filter(([, v]) => v)
  return (
    <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
      {rows.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-brand-border bg-surface p-3">
          <dt className="text-xs font-semibold text-ink-soft">{label}</dt>
          <dd className="tabular mt-0.5 text-lg font-bold text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Two bars, one scale: what you're doing now against what this needs. */
function NowVsNeeded({ current, required, extra }) {
  const max = Math.max(current.monthly, required.monthly, 1)
  const needsMore = extra.annual > 0
  const row = (label, value, tone) => (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-ink-soft">{label}</span>
        <span className="tabular font-bold text-ink">{money(value)} <span className="font-normal text-ink-faint">a month</span></span>
      </div>
      <div className="mt-1 h-3 overflow-hidden rounded-full bg-surface-sunken" aria-hidden="true">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${(value / max) * 100}%` }} />
      </div>
    </div>
  )
  return (
    <Card className="p-5">
      <h2 className="font-bold tracking-tight text-ink">Against what you do now</h2>
      <div className="mt-3 space-y-3">
        {row('Investing now', current.monthly, 'bg-ink-faint')}
        {row('This needs', required.monthly, needsMore ? 'bg-alert' : 'bg-brand-bright')}
      </div>
      <p className={`mt-3 text-[0.9375rem] font-semibold ${needsMore ? 'text-alert' : 'text-brand'}`}>
        {needsMore
          ? <>{money(extra.monthly)} more a month{extra.per_paycheck > 0 && <> — {money(extra.per_paycheck)} a paycheck</>}</>
          : 'Already covered'}
      </p>
      {needsMore && (
        <Link to="/you" className="mt-2 inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-brand">
          Change what you save <Icon name="arrowRight" className="size-4" />
        </Link>
      )}
    </Card>
  )
}

function Result({ data, glossary }) {
  const { required, current, extra, coast } = data
  const [wait, setWait] = useState('now')

  if (required.annual == null) {
    return (
      <Card tone="alert" className="p-5">
        <h2 className="flex items-center gap-2 text-lg font-bold text-ink"><Icon name="alert" className="size-5 shrink-0 text-alert" />No saving years left</h2>
        <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-soft">
          You're at the age you're planning to. The levers now are spending, when you claim Social Security, and how long the money has to last — on the <Link to="/projection" className="font-semibold text-brand underline underline-offset-2">projection page</Link>.
        </p>
      </Card>
    )
  }

  if (data.on_track) {
    return (
      <Card tone="brand" className="p-5">
        <p className="text-xs font-bold uppercase tracking-wide text-brand">{data.description}</p>
        <h2 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight text-ink"><Icon name="check" className="size-6 shrink-0 text-brand" />Nothing more needed</h2>
        <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-soft">
          The {money(data.already_have)} you have grows to {money(data.needed_at_target)} by {data.target_age} on its own.
        </p>
      </Card>
    )
  }

  const coastPct = coast.number > 0 ? Math.min(1, data.already_have / coast.number) : 0
  const waiting = [
    { key: 'now', label: 'Start now', short: 'Now', value: required.monthly, extra: 0 },
    ...data.cost_of_waiting.map((w) => ({
      key: String(w.wait_years), label: `Start in ${w.wait_years} ${w.wait_years === 1 ? 'year' : 'years'}`,
      short: `+${w.wait_years}y`, value: w.required.monthly, extra: w.extra_per_month,
    })),
  ]
  const picked = waiting.find((w) => w.key === wait) ?? waiting[0]

  return (
    <>
      <Card tone="brand" className="p-5">
        <p className="text-xs font-bold uppercase tracking-wide text-brand">{data.description}</p>
        <p className="tabular mt-1 text-3xl font-bold text-ink">{money(required.monthly)}</p>
        <p className="mt-0.5 text-sm text-ink-soft">a month for {data.years} {data.years === 1 ? 'year' : 'years'}, starting now</p>
        <Amounts amounts={required} />
      </Card>

      <NowVsNeeded current={current} required={required} extra={extra} />

      <Card className="p-5">
        <div className="flex items-center gap-4">
          <Ring value={coastPct} size={80} stroke={9} label={`${Math.round(coastPct * 100)}% of the way to the coast number`}>
            <span className="tabular text-sm font-bold text-ink">{Math.round(coastPct * 100)}%</span>
          </Ring>
          <div className="min-w-0 flex-1">
            <h2 className="font-bold tracking-tight text-ink"><Annotated text="The point you could stop" glossary={glossary} /></h2>
            <p className="tabular text-xl font-bold text-ink">{money(coast.number)}</p>
            <p className="mt-0.5 text-sm text-ink-soft">
              {coast.reached ? 'Already past it — everything from here is on top.'
                : coast.age != null ? `Around age ${coast.age} at your pace; compounding carries you from there.`
                  : 'Get here and compounding does the rest.'}
            </p>
          </div>
        </div>
      </Card>

      {data.cost_of_waiting.length > 0 && (
        <Card className="p-5">
          <h2 className="font-bold tracking-tight text-ink">What waiting costs</h2>
          <p className="mt-0.5 text-sm text-ink-soft">Same target, same deadline — a later start means a bigger monthly figure.</p>
          <div className="mt-4">
            <Bars data={waiting} format={(v) => money(v)} selected={wait} onSelect={(d) => setWait(d.key)} height={112}
              label="Monthly contribution needed if you start now, or one, three or five years later" />
          </div>
          <p className="mt-2 rounded-xl bg-surface-sunken px-4 py-2.5 text-sm text-ink-soft" aria-live="polite">
            <span className="font-semibold text-ink">{picked.label}:</span> <span className="tabular font-semibold text-ink">{money(picked.value)}</span> a month
            {picked.extra > 0 && <> — <span className="tabular font-semibold text-alert">{money(picked.extra)} more</span> than starting now</>}
          </p>
        </Card>
      )}
    </>
  )
}

export default function GoalPage({ glossary }) {
  const [draft, setDraft] = useState({ goal: 'retirement', amount: '', monthly: '', by_age: '' })
  const [params, setParams] = useState({ goal: 'retirement' })

  useEffect(() => {
    const t = setTimeout(() => setParams({
      goal: draft.goal,
      amount: draft.goal === 'amount' ? digits(draft.amount) : '',
      monthly: draft.goal === 'income' ? digits(draft.monthly) : '',
      by_age: digits(draft.by_age),
    }), 350)
    return () => clearTimeout(t)
  }, [draft])

  const key = JSON.stringify(params)
  const { data, error, loading, reload } = useApi(() => api.target(params), [key])
  const set = (k) => (v) => setDraft((d) => ({ ...d, [k]: v }))

  if (!data && loading) return <div className="space-y-4"><Skeleton className="h-40 w-full" /><Skeleton className="h-64 w-full" /></div>
  if (!data) return <ErrorState error={error} onRetry={reload} />

  return (
    <div className="space-y-4">
      <Link to="/" className="inline-flex min-h-11 items-center gap-1 text-[0.9375rem] font-semibold text-brand">
        <Icon name="chevronLeft" className="size-4" /> Your plan
      </Link>
      <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">What it takes</h1>

      <Card className="space-y-4 p-5">
        <fieldset>
          <div className="flex items-baseline justify-between gap-3">
            <legend className="text-[0.9375rem] font-semibold text-ink">Aim for</legend>
            <span role="status" className="text-xs font-semibold text-ink-faint">{loading ? 'Working it out…' : ''}</span>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {GOALS.map((g) => (
              <label key={g.id} className={`flex min-h-16 cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border px-2 py-2 text-center text-sm font-semibold transition-colors ${
                draft.goal === g.id ? 'border-brand-border bg-brand-soft text-brand' : 'border-line-strong text-ink-soft hover:bg-surface-sunken'
              }`}>
                <input type="radio" name="goal" value={g.id} checked={draft.goal === g.id} onChange={() => set('goal')(g.id)} className="sr-only" />
                <Icon name={g.icon} className="size-5" />
                {g.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          {draft.goal === 'amount' && (
            <Field label="How much?" hint="In today's money.">
              {(props) => <MoneyInput {...props} value={draft.amount} placeholder="1,000,000" onChange={(e) => set('amount')(e.target.value)} />}
            </Field>
          )}
          {draft.goal === 'income' && (
            <Field label="A month, in retirement" hint="In today's money.">
              {(props) => <MoneyInput {...props} value={draft.monthly} placeholder="5,000" onChange={(e) => set('monthly')(e.target.value)} />}
            </Field>
          )}
          <Field label="By age" error={error?.message} hint={`Blank uses your plan's age (${data.target_age}).`}>
            {(props) => (
              <TextInput {...props} type="text" inputMode="numeric" className="tabular" value={draft.by_age}
                placeholder={String(data.target_age)} onChange={(e) => set('by_age')(e.target.value)} />
            )}
          </Field>
        </div>
      </Card>

      <Result data={data} glossary={glossary} />

      {data.notes.length > 0 && (
        <Card tone="sunken" className="p-5">
          <Disclosure label="Worth knowing about this figure" tone="quiet">
            <ul className="mt-2 space-y-2">
              {data.notes.map((note, i) => (
                <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-ink-soft">
                  <Icon name="chevronRight" className="mt-0.5 size-4 shrink-0 text-ink-faint" />
                  <span><Annotated text={note} glossary={glossary} /></span>
                </li>
              ))}
            </ul>
          </Disclosure>
        </Card>
      )}

      <p className="px-1 text-xs leading-relaxed text-ink-faint">{data.disclaimer}</p>
    </div>
  )
}
