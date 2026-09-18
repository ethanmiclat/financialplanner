import { useEffect, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import GrowthChart from '../components/GrowthChart'
import Icon from '../components/Icon'
import { Annotated } from '../components/Term'
import {
  Button, Card, ErrorState, Field, MoneyInput, ScrollX, SegmentedTabs, Select, Skeleton, Toast,
} from '../components/ui'
import { Ring } from '../components/viz'
import { money } from '../lib/format'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const GOAL_KEYS = [
  'retirement_age', 'plan_to_age', 'retirement_monthly_spending',
  'social_security_monthly', 'social_security_claim_age',
]
const MONEY_KEYS = new Set(['retirement_monthly_spending', 'social_security_monthly', 'annual_savings_capacity'])

const ageLabel = (age) => (age === 59.5 ? '59½' : String(age))
const rateLabel = (rate) => `${+(rate * 100).toFixed(1)}%`

function clean(draft) {
  return Object.fromEntries(
    Object.entries(draft).map(([k, v]) => [k, MONEY_KEYS.has(k) ? String(v).replace(/[^0-9.]/g, '') : v]),
  )
}

function Lever({ text, onTry }) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-line bg-surface py-1.5 pl-3 pr-1.5">
      <span className="text-[0.9375rem] font-medium text-ink">{text}</span>
      <Button type="button" variant="secondary" size="sm" onClick={onTry} className="shrink-0">Try it</Button>
    </li>
  )
}

/** The answer first, as a ring: how far the plan gets toward the retirement picked.
 *  Short of it, three levers, each tryable in place — the page doesn't pick one. */
function Readiness({ r, baseSavings, onTry }) {
  if (r.status === 'no_spending_info') {
    return (
      <Card tone="brand" className="flex items-center justify-between gap-3 p-4">
        <p className="text-[0.9375rem] font-semibold text-ink">Add what you'll spend in retirement to check whether {r.retirement_age} works.</p>
        <Link to="/you" className="shrink-0 font-semibold text-brand">Add it</Link>
      </Card>
    )
  }
  const onTrack = r.status === 'on_track'
  const retired = r.years_to_retirement === 0
  const pct = Math.round(r.funded_ratio * 100)
  const lasts = r.plan_runs_out_age ?? r.money_lasts_to_age
  const earliest = r.earliest_retirement_age

  return (
    <Card tone={onTrack ? 'brand' : r.status === 'close' ? 'surface' : 'alert'} className="p-5">
      <div className="flex items-center gap-4">
        <Ring value={Math.min(1, r.funded_ratio)} size={96} stroke={11} tone={onTrack ? 'brand' : 'alert'} label={`${pct}% funded`}>
          <span className="tabular text-xl font-bold leading-none text-ink">{pct}%</span>
          <span className="text-[0.625rem] font-semibold uppercase tracking-wide text-ink-faint">funded</span>
        </Ring>
        <div className="min-w-0 flex-1">
          <p className={`text-xs font-bold uppercase tracking-wide ${onTrack ? 'text-brand' : 'text-alert'}`}>
            {retired ? 'Your retirement' : `Retiring at ${r.retirement_age}`}
          </p>
          <p className="mt-0.5 text-xl font-bold tracking-tight text-ink">
            {onTrack ? 'On track' : lasts ? `Runs out around ${lasts}` : 'Just short'}
          </p>
          <p className="mt-0.5 text-sm text-ink-soft">
            {money(r.retirement_spending_annual / 12)} a month{onTrack ? ` until ${r.plan_to_age}` : `, needs to last to ${r.plan_to_age}`}
          </p>
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-line bg-surface p-3">
          <dt className="text-xs font-semibold text-ink-soft">{retired ? 'You have' : `By ${r.retirement_age}`}</dt>
          <dd className="tabular mt-0.5 text-lg font-bold text-ink">{money(r.projected_at_retirement)}</dd>
        </div>
        <div className="rounded-xl border border-line bg-surface p-3">
          <dt className="text-xs font-semibold text-ink-soft">Needed to last to {r.plan_to_age}</dt>
          <dd className="tabular mt-0.5 text-lg font-bold text-ink">{money(r.needed_at_retirement)}</dd>
        </div>
      </dl>

      {!onTrack && (
        <ul className="mt-4 space-y-2">
          {r.extra_savings_per_year != null && (
            <Lever text={`Save ${money(r.extra_savings_per_year)} more a year`}
              onTry={() => onTry({ annual_savings_capacity: Math.round(baseSavings + r.extra_savings_per_year) })} />
          )}
          {earliest != null && earliest > r.retirement_age && (
            <Lever text={`Retire at ${earliest} instead`} onTry={() => onTry({ retirement_age: earliest })} />
          )}
          {r.sustainable_monthly_spending != null && (
            <Lever text={`Spend ${money(r.sustainable_monthly_spending)} a month`}
              onTry={() => onTry({ retirement_monthly_spending: r.sustainable_monthly_spending })} />
          )}
        </ul>
      )}
      {onTrack && !retired && earliest != null && earliest < r.retirement_age && (
        <ul className="mt-4"><Lever text={`Could support retiring at ${earliest}`} onTry={() => onTry({ retirement_age: earliest })} /></ul>
      )}
      {!r.social_security_provided && (
        <p className="mt-3 text-xs text-ink-soft">
          No Social Security counted. <Link to="/you" className="font-semibold text-brand underline underline-offset-2">Add your estimate</Link>.
        </p>
      )}
    </Card>
  )
}

function WhatIf({ settings, draft, setDraft, error, updating, saving, onSave, onReset, currentContributions }) {
  const rangeId = useId()
  const val = (k) => (k in draft ? draft[k] : settings[k])
  const set = (k) => (v) => setDraft((d) => ({ ...d, [k]: v }))
  const ra = Number(val('retirement_age'))
  const planTo = Number(val('plan_to_age'))
  const minAge = Math.max(18, settings.age)
  const maxAge = Math.max(minAge, Math.min(85, planTo - 1))
  const setAge = (a) => set('retirement_age')(Math.min(maxAge, Math.max(minAge, a)))
  const planToOptions = [...new Set([85, 90, 95, 100, 105, 110, planTo])].filter((a) => a > Math.max(ra, settings.age)).sort((a, b) => a - b)
  const dirty = Object.keys(draft).length > 0
  const [more, setMore] = useState(false)

  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="flex items-center gap-2 font-bold tracking-tight text-ink"><Icon name="sliders" className="size-5 text-brand" /> Try a different plan</h2>
        <span role="status" className="text-xs font-semibold text-ink-faint">{updating ? 'Updating…' : ''}</span>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor={rangeId} className="text-[0.9375rem] font-semibold text-ink">Retire at</label>
          <div className="flex items-center gap-1">
            <Button type="button" variant="secondary" size="sm" icon="minus" className="min-w-11" aria-label="Retire a year earlier" disabled={ra <= minAge} onClick={() => setAge(ra - 1)} />
            <span className="tabular w-12 text-center text-2xl font-bold text-ink" aria-hidden="true">{ra}</span>
            <Button type="button" variant="secondary" size="sm" icon="plus" className="min-w-11" aria-label="Retire a year later" disabled={ra >= maxAge} onClick={() => setAge(ra + 1)} />
          </div>
        </div>
        <input id={rangeId} type="range" min={minAge} max={maxAge} step={1} value={ra} onChange={(e) => setAge(Number(e.target.value))}
          aria-valuetext={`Age ${ra}`} className="mt-2 h-11 w-full cursor-pointer accent-brand" />
        <div className="tabular flex justify-between text-xs text-ink-faint" aria-hidden="true"><span>{minAge}</span><span>{maxAge}</span></div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Field label="Spend a month in retirement">
          {(props) => (
            <MoneyInput {...props} value={val('retirement_monthly_spending') ?? ''}
              placeholder={`Same as now (${settings.retirement_monthly_spending_effective.toLocaleString('en-US')})`}
              onChange={(e) => set('retirement_monthly_spending')(e.target.value)} />
          )}
        </Field>
        <Field label="Save each year">
          {(props) => (
            <MoneyInput {...props} value={val('annual_savings_capacity') ?? ''}
              placeholder={Math.round(currentContributions).toLocaleString('en-US')}
              onChange={(e) => set('annual_savings_capacity')(e.target.value)} />
          )}
        </Field>
      </div>

      <button type="button" onClick={() => setMore((v) => !v)} aria-expanded={more}
        className="mt-3 inline-flex min-h-11 cursor-pointer items-center gap-1 text-sm font-semibold text-brand">
        <Icon name="chevronDown" className={`size-4 transition-transform ${more ? 'rotate-180' : ''}`} /> More levers
      </button>
      {more && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Money should last until">
            {(props) => (
              <Select {...props} value={planTo} onChange={(e) => set('plan_to_age')(Number(e.target.value))}>
                {planToOptions.map((a) => <option key={a} value={a}>Age {a}</option>)}
              </Select>
            )}
          </Field>
          <Field label="Claim Social Security at">
            {(props) => (
              <Select {...props} value={val('social_security_claim_age')} onChange={(e) => set('social_security_claim_age')(Number(e.target.value))}>
                {[62, 63, 64, 65, 66, 67, 68, 69, 70].map((a) => <option key={a} value={a}>Age {a}</option>)}
              </Select>
            )}
          </Field>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-4 flex items-start gap-2 text-sm font-medium text-alert">
          <Icon name="alert" className="mt-0.5 size-4 shrink-0" />{error.message}
        </p>
      )}
      {dirty && (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" onClick={onSave} loading={saving} disabled={!!error} icon="check">Save as my plan</Button>
          <Button type="button" variant="ghost" onClick={onReset}>Reset</Button>
        </div>
      )}
      <p className="mt-2 text-xs text-ink-faint">Nothing is saved until you say so.</p>
    </Card>
  )
}

export default function ProjectionPage({ glossary }) {
  const [scenario, setScenario] = useState(null)
  const [draft, setDraft] = useState({})
  const [whatIf, setWhatIf] = useState({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [toast, setToast] = useState(null)
  const [tab, setTab] = useState('ages')

  useEffect(() => {
    const t = setTimeout(() => setWhatIf(clean(draft)), 350)
    return () => clearTimeout(t)
  }, [draft])

  const whatIfKey = JSON.stringify(whatIf)
  const { data, error, loading, reload } = useApi(() => api.projection(scenario, whatIf), [scenario, whatIfKey])

  if (!data && loading) return <div className="space-y-4"><Skeleton className="h-48 w-full" /><Skeleton className="h-72 w-full" /></div>
  if (!data) return <ErrorState error={error} onRetry={reload} />

  const tryOut = (changes) => setDraft((d) => ({ ...d, ...changes }))
  const reset = () => { setDraft({}); setWhatIf({}) }

  async function save() {
    setSaving(true); setSaveError(null)
    try {
      const values = clean(draft)
      const toValue = (k) => (values[k] === '' ? null : Number(values[k]))
      const goal = Object.fromEntries(GOAL_KEYS.filter((k) => k in values).map((k) => [k, toValue(k)]))
      if (Object.keys(goal).length) await api.putGoal(goal)
      if ('annual_savings_capacity' in values) await api.patchProfile({ annual_savings_capacity: toValue('annual_savings_capacity') })
      reset()
      setToast('Saved — your whole plan now uses these numbers')
    } catch (err) { setSaveError(err) } finally { setSaving(false) }
  }

  const nothingInvested = data.planned_annual_contributions.total === 0 && data.starting_balance === 0
  const baseSavings = data.settings.annual_savings_capacity ?? data.current_annual_contributions

  return (
    <div className="space-y-4">
      <Link to="/" className="inline-flex min-h-11 items-center gap-1 text-[0.9375rem] font-semibold text-brand">
        <Icon name="chevronLeft" className="size-4" /> Your plan
      </Link>
      <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">What this adds up to</h1>

      {nothingInvested && (
        <Card tone="brand" className="flex items-center justify-between gap-3 p-4">
          <p className="text-[0.9375rem] font-semibold text-ink">Tell us what you could save each year to see where it gets to.</p>
          <Link to="/you" className="shrink-0 font-semibold text-brand">Add it</Link>
        </Card>
      )}

      <Readiness r={data.retirement} baseSavings={baseSavings} onTry={tryOut} />

      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3">
          <h2 className="font-bold tracking-tight text-ink">How it grows, then how it's spent</h2>
          <SegmentedTabs
            label="Market return assumption"
            value={data.scenario}
            onChange={setScenario}
            tabs={Object.entries(data.scenarios).map(([key, s]) => ({ id: key, label: key === 'yours' ? `${rateLabel(s.rate)} yours` : rateLabel(s.rate) }))}
          />
        </div>
        <GrowthChart series={data.series} retirementAge={data.retirement_age} />
        <p className="mt-2 text-xs text-ink-faint">{data.scenarios[data.scenario].label}, every year until you retire.</p>
      </Card>

      <WhatIf settings={data.settings} draft={draft} setDraft={setDraft} error={error || saveError}
        updating={loading} saving={saving} onSave={save} onReset={reset} currentContributions={data.current_annual_contributions} />

      <SegmentedTabs label="Detail" value={tab} onChange={setTab} tabs={[
        { id: 'ages', label: 'Ages', icon: 'flag' },
        { id: 'table', label: 'Figures', icon: 'table' },
        { id: 'assume', label: 'Assumes', icon: 'info' },
      ]} />

      {tab === 'ages' && (
        <Card className="p-5">
          <ol className="space-y-3">
            {data.milestones.map((m) => (
              <li key={`${m.kind}-${m.age}`} className="flex gap-3">
                <span className={`tabular grid h-7 min-w-11 shrink-0 place-items-center rounded-full px-2 text-xs font-bold ${m.kind === 'retire' ? 'bg-brand text-on-brand' : 'bg-brand-soft text-brand'}`}>
                  {ageLabel(m.age)}
                </span>
                <span>
                  <span className="block text-[0.9375rem] font-semibold text-ink"><Annotated text={m.label} glossary={glossary} /></span>
                  <span className="block text-sm leading-relaxed text-ink-soft"><Annotated text={m.detail} glossary={glossary} /></span>
                </span>
              </li>
            ))}
          </ol>
        </Card>
      )}

      {tab === 'table' && (
        <Card className="p-5">
          <ScrollX label="Projected balance by year">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Projected balance following your plan versus your current pace</caption>
              <thead>
                <tr className="border-b border-line-strong">
                  <th scope="col" className="py-2 pr-3 font-semibold text-ink">When</th>
                  <th scope="col" className="py-2 pr-3 text-right font-semibold text-ink">Your plan</th>
                  <th scope="col" className="py-2 text-right font-semibold text-ink-soft">Current pace</th>
                </tr>
              </thead>
              <tbody>
                {data.points.map((p) => (
                  <tr key={p.years} className="border-b border-line last:border-0">
                    <th scope="row" className="py-2.5 pr-3 align-top font-medium text-ink-soft">
                      <span className="block whitespace-nowrap">Age {p.age}</span>
                      {p.is_retirement && <span className="mt-0.5 inline-block rounded-full bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand">retirement</span>}
                    </th>
                    <td className="py-2.5 pr-3 text-right whitespace-nowrap">
                      <span className="tabular block font-bold text-ink">{money(p.following_plan)}</span>
                      <span className="tabular block text-xs text-ink-faint">{money(p.following_plan_todays_money)} today</span>
                    </td>
                    <td className="tabular py-2.5 text-right align-top text-ink-soft whitespace-nowrap">{money(p.current_pace)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollX>
        </Card>
      )}

      {tab === 'assume' && (
        <Card tone="sunken" className="p-5">
          <ul className="space-y-2">
            {data.assumptions.map((a, i) => (
              <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-ink-soft">
                <Icon name="chevronRight" className="mt-0.5 size-4 shrink-0 text-ink-faint" />
                <span><Annotated text={a} glossary={glossary} /></span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <p className="px-1 text-xs leading-relaxed text-ink-faint">{data.disclaimer}</p>
      <Toast message={toast} onDismiss={() => setToast(null)} />
    </div>
  )
}
