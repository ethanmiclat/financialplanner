import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { Annotated } from '../components/Term'
import { Card, Disclosure, ErrorState, ScrollX, SegmentedTabs, Skeleton } from '../components/ui'
import { Bars, StackedBar } from '../components/viz'
import { TONE_CLASS, toneFor } from '../lib/tones'
import { money, percent } from '../lib/format'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const monthShort = (label) => label.split(' ')[0].slice(0, 3)

/** One move: what, how, and the per-payday figure — the number a standing transfer
 *  is actually set to. */
function Move({ move, glossary, tone }) {
  return (
    <li className="flex items-center gap-3 py-2.5">
      <span className={`size-2.5 shrink-0 rounded-sm ${tone}`} aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[0.9375rem] font-semibold text-ink">
          <Annotated text={move.label} glossary={glossary} />
        </span>
        <span className="block text-xs text-ink-faint">
          {move.payroll
            ? `Payroll${move.percent_of_pay ? ` · about ${percent(move.percent_of_pay, 1)} of pay` : ''}`
            : 'Transfer'}
          {' · '}<span className="tabular">{money(move.per_paycheck)}</span> a paycheck
          {move.completes && ' · finishes this month'}
        </span>
      </span>
      <span className="tabular shrink-0 font-bold text-ink">{money(move.amount)}</span>
    </li>
  )
}

/** Payday as a bar: bills, the plan, and what's left. */
function Paycheck({ pay, glossary }) {
  const known = pay.take_home != null
  const short = known && pay.free_to_spend < 0
  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-bold tracking-tight text-ink">Every payday</h2>
        <span className="text-sm text-ink-soft">{pay.label}</span>
      </div>
      {known ? (
        <>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-sm text-ink-soft">Take-home</span>
            <span className="tabular text-lg font-bold text-ink">{money(pay.take_home)}</span>
          </div>
          <div className="mt-2">
            <StackedBar
              height="h-4"
              segments={[
                { label: 'Bills', value: pay.bills, text: money(pay.bills), tone: 'faint' },
                { label: 'Your plan', value: pay.transfers, text: money(pay.transfers), tone: 'bright' },
                { label: 'Free to spend', value: Math.max(0, pay.free_to_spend), text: money(Math.max(0, pay.free_to_spend)), tone: 'soft' },
              ]}
            />
          </div>
          {short && (
            <p role="alert" className="mt-3 flex items-start gap-2 rounded-xl bg-alert-soft p-3 text-sm font-medium text-alert">
              <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
              This plan needs {money(-pay.free_to_spend)} more than your paycheck covers.
            </p>
          )}
          {pay.payroll_deferrals > 0 && (
            <p className="mt-3 text-xs leading-relaxed text-ink-faint">
              <Annotated text={`Plus ${money(pay.payroll_deferrals)} of payroll deferrals that never reach your account.`} glossary={glossary} />
            </p>
          )}
        </>
      ) : (
        <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-soft">
          <span className="tabular font-bold text-ink">{money(pay.transfers + pay.payroll_deferrals)}</span> comes out of each paycheck.{' '}
          <Link to="/you" className="font-semibold text-brand underline underline-offset-2">Add your take-home pay</Link> to see what's left.
        </p>
      )}
    </Card>
  )
}

export default function SchedulePage({ glossary }) {
  const [view, setView] = useState('chart')
  const [picked, setPicked] = useState(null)
  const { data, error, loading, reload } = useApi(() => api.schedule(12), [])

  if (loading) return <div className="space-y-4"><Skeleton className="h-48 w-full" /><Skeleton className="h-64 w-full" /></div>
  if (error) return <ErrorState error={error} onRetry={reload} />

  const moves = data.this_month?.moves ?? []
  const selected = data.months.find((m) => m.date === picked) ?? null
  const bars = data.months.map((m) => ({
    key: m.date, label: m.label, short: monthShort(m.label), value: m.total,
    marker: m.milestones.length ? m.milestones.join('; ') : null,
  }))

  return (
    <div className="space-y-4">
      <Link to="/" className="inline-flex min-h-11 items-center gap-1 text-[0.9375rem] font-semibold text-brand">
        <Icon name="chevronLeft" className="size-4" /> Your plan
      </Link>
      <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Month by month</h1>

      {!data.capacity_set && (
        <Card tone="brand" className="flex items-center justify-between gap-3 p-4">
          <p className="text-[0.9375rem] font-semibold text-ink">Tell us what you can save each month to make this your real schedule.</p>
          <Link to="/you" className="shrink-0 font-semibold text-brand">Set it</Link>
        </Card>
      )}

      <Card tone="brand" className="p-5">
        <p className="text-xs font-bold uppercase tracking-wide text-brand">{data.this_month?.label ?? 'This month'}</p>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-3">
          <p className="tabular text-3xl font-bold text-ink">{money(data.monthly_savings)}</p>
          {data.savings?.per_paycheck > 0 && (
            <p className="text-sm text-ink-soft">
              <span className="tabular font-semibold text-ink">{money(data.savings.per_paycheck)}</span> a paycheck
              {data.savings.percent_of_pay != null && <> · <span className="tabular font-semibold text-ink">{percent(data.savings.percent_of_pay, 1)}</span> of pay</>}
            </p>
          )}
        </div>
        {moves.length > 0 && (
          <>
            <div className="mt-3">
              <StackedBar
                legend={false}
                height="h-4"
                segments={moves.map((m, i) => ({ label: m.label, value: m.amount, text: money(m.amount), tone: toneFor(i) }))}
              />
            </div>
            <ul className="mt-1 divide-y divide-brand-border/40">
              {moves.map((m, i) => <Move key={m.rule_id + m.label} move={m} glossary={glossary} tone={TONE_CLASS[toneFor(i)]} />)}
            </ul>
          </>
        )}
      </Card>

      <Paycheck pay={data.paycheck} glossary={glossary} />

      <Card className="p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-bold tracking-tight text-ink">The next 12 months</h2>
          <SegmentedTabs
            label="View"
            value={view}
            onChange={setView}
            tabs={[{ id: 'chart', label: 'Chart', icon: 'chart' }, { id: 'table', label: 'Table', icon: 'table' }]}
          />
        </div>

        {view === 'chart' ? (
          <div className="mt-4">
            <Bars
              data={bars}
              format={(v) => (v >= 1000 ? `$${Math.round(v / 100) / 10}k` : money(v))}
              selected={picked}
              onSelect={(d) => setPicked((p) => (p === d.key ? null : d.key))}
              label="What you move each month, for the next twelve months"
            />
            <div className="mt-3 min-h-14 rounded-xl bg-surface-sunken px-4 py-3" aria-live="polite">
              {selected ? (
                <>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">{selected.label} · {money(selected.total)}</p>
                  <ul className="mt-1 text-sm text-ink-soft">
                    {selected.moves.map((mv) => (
                      <li key={mv.rule_id + mv.label} className="flex justify-between gap-3">
                        <span className="truncate">{mv.label}</span>
                        <span className="tabular shrink-0 font-semibold text-ink">{money(mv.amount)}</span>
                      </li>
                    ))}
                  </ul>
                  {selected.milestones.map((t) => (
                    <p key={t} className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-brand">
                      <Icon name="check" className="size-3.5" /> {t}
                    </p>
                  ))}
                </>
              ) : (
                <p className="text-sm text-ink-soft">Tap a month to see what moves and what finishes.</p>
              )}
            </div>
          </div>
        ) : (
          <ScrollX label="Month by month schedule" className="mt-3">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">What you move each month, and which steps finish</caption>
              <thead>
                <tr className="border-b border-line-strong">
                  <th scope="col" className="py-2 pr-3 font-semibold text-ink">Month</th>
                  <th scope="col" className="py-2 pr-3 text-right font-semibold text-ink">You move</th>
                  <th scope="col" className="py-2 font-semibold text-ink-soft">What happens</th>
                </tr>
              </thead>
              <tbody>
                {data.months.map((m) => (
                  <tr key={m.date} className="border-b border-line last:border-0">
                    <th scope="row" className="py-2.5 pr-3 align-top font-medium whitespace-nowrap text-ink-soft">{m.label}</th>
                    <td className="tabular py-2.5 pr-3 text-right align-top font-bold whitespace-nowrap text-ink">{money(m.total)}</td>
                    <td className="py-2.5 align-top text-ink-soft">
                      {m.milestones.length > 0
                        ? m.milestones.map((text) => (
                            <span key={text} className="flex items-center gap-1 font-semibold text-brand"><Icon name="check" className="size-3.5 shrink-0" /> {text}</span>
                          ))
                        : m.moves.map((mv) => mv.label).join(', ') || 'Nothing scheduled'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollX>
        )}
      </Card>

      <Card tone="sunken" className="p-5">
        <Disclosure label="How this schedule is built" tone="quiet">
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

      <p className="px-1 text-xs leading-relaxed text-ink-faint">{data.disclaimer}</p>
    </div>
  )
}
