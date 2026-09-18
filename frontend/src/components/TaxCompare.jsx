import Icon from './Icon'
import Term from './Term'
import { money } from '../lib/format'

/** Roth or traditional, as two numbers side by side: the federal rate on your next
 *  dollar now, and on the dollar you'd withdraw in retirement. Whichever is lower is
 *  when you'd rather pay the tax — that's the whole decision. */
const pct = (r) => `${Math.round(r * 100)}%`

function RateBar({ label, sub, rate, max, lower }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-semibold text-ink">{label}</span>
        <span className={`tabular text-xl font-bold ${lower ? 'text-brand' : 'text-ink'}`}>{pct(rate)}</span>
      </div>
      <div className="mt-1 h-3 overflow-hidden rounded-full bg-surface-sunken" aria-hidden="true">
        <div className={`h-full rounded-full ${lower ? 'bg-brand-bright' : 'bg-ink-faint'}`}
          style={{ width: `${Math.max(3, (rate / max) * 100)}%` }} />
      </div>
      <p className="mt-1 text-xs text-ink-faint">{sub}</p>
    </div>
  )
}

export default function TaxCompare({ data, glossary }) {
  if (!data) return <div className="h-44 animate-pulse rounded-xl bg-surface-sunken" />
  const { now, retirement: later, estimated_verdict: est, per_1000: per } = data
  if (!later) {
    return (
      <p className="rounded-xl bg-surface-sunken px-4 py-3 text-sm text-ink-soft">
        Your next dollar is taxed at about <span className="font-semibold text-ink">{pct(now.marginal_rate)}</span> today.
        Add what you spend a month (on the Saving tab) and we can estimate the retirement side.
      </p>
    )
  }
  const max = Math.max(now.marginal_rate, later.marginal_rate, 0.12)
  const roth = est === 'roth'
  const tie = now.marginal_rate === later.marginal_rate
  return (
    <div className="space-y-4">
      <div className={`flex items-start gap-3 rounded-xl px-4 py-3 ${roth ? 'bg-brand-soft' : 'bg-surface-sunken'}`}>
        <Icon name={roth ? 'check' : 'info'} className={`mt-0.5 size-5 shrink-0 ${roth ? 'text-brand' : 'text-ink-soft'}`} />
        <p className="text-[0.9375rem] leading-relaxed text-ink">
          <span className="font-bold">
            {roth ? <Term id="roth" glossary={glossary}>Roth</Term> : <Term id="traditional" glossary={glossary}>Traditional</Term>} comes out ahead on your numbers.
          </span>{' '}
          <span className="text-ink-soft">
            {tie
              ? 'The rates match, and a tie leans Roth: no required withdrawals later.'
              : roth
                ? 'Your rate is lower now, so paying the tax now is cheaper.'
                : 'Your rate is higher now, so the deduction is worth more today.'}
            {per ? <> About <span className="tabular font-semibold text-ink">{money(Math.abs(per))}</span> better per $1,000 saved.</> : null}
          </span>
        </p>
      </div>
      <RateBar label="Your rate now" rate={now.marginal_rate} max={max} lower={now.marginal_rate < later.marginal_rate || (tie && roth)}
        sub={now.taxable > 0
          ? `${money(now.gross)} income, ${money(now.taxable)} after the standard deduction`
          : `${money(now.gross)} income is under the ${money(now.deduction)} standard deduction — no federal income tax`} />
      <RateBar label="In retirement (estimate)" rate={later.marginal_rate} max={max} lower={later.marginal_rate < now.marginal_rate}
        sub={`Spending ${money(later.spending / 12)} a month${later.social_security ? `, ${money(later.social_security / 12)} of it from Social Security` : ''}, in today's money`} />
      <p className="text-xs leading-relaxed text-ink-faint">
        Federal income tax only, on {data.year}'s brackets. Assumes retirement spending beyond Social Security comes from pre-tax
        accounts — what a traditional dollar would face. Splitting between both is always a reasonable hedge.
      </p>
    </div>
  )
}
