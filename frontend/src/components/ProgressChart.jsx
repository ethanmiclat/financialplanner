import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import { SegmentedTabs } from './ui'
import { money } from '../lib/format'

/** What you've actually done, as opposed to GrowthChart's what-could-happen. One point
 *  per day something changed, placed on a real date axis — a month of silence then
 *  three updates in a week should look like that, not like four even steps. */

const METRICS = [
  { id: 'net', label: 'Net worth', icon: 'trending', key: 'net', blurb: 'What you own minus what you owe' },
  { id: 'cash', label: 'Cash', icon: 'shield', key: 'cash', blurb: 'Your emergency fund — cash in savings' },
  { id: 'owed', label: 'Debt', icon: 'creditCard', key: 'owed', blurb: 'Everything you owe', lowerIsBetter: true },
]
const day = (iso) => new Date(`${iso}T12:00:00`)
const short = (iso) => day(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
const long = (iso) => day(iso).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
const axis = (t) => {
  const a = Math.abs(t)
  const s = a >= 1e6 ? `$${+(a / 1e6).toFixed(1)}M` : a >= 1000 ? `$${+(a / 1000).toFixed(a >= 10000 ? 0 : 1)}k` : `$${Math.round(a)}`
  return t < 0 ? `−${s}` : s
}
const signed = (n) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${money(Math.abs(n))}`

function Chart({ points, metric, target }) {
  const [hover, setHover] = useState(null)
  // Drawn at its real pixel width, so 11px labels are 11px on a phone too — a fixed
  // viewBox scaled down to 360px wide shrinks them to about 6.
  const box = useRef(null)
  const [W, setW] = useState(600)
  useEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const H = 200
  const PAD = { top: 20, right: 12, bottom: 26, left: 52 }
  const vals = points.map((p) => p[metric.key])
  const lo = Math.min(0, ...vals)
  const hi = Math.max(...vals, target ?? 0, 1)
  const span = hi - lo || 1
  const t0 = day(points[0].date).getTime()
  const t1 = day(points[points.length - 1].date).getTime()
  const x = (iso) => PAD.left + ((day(iso).getTime() - t0) / (t1 - t0 || 1)) * (W - PAD.left - PAD.right)
  const y = (v) => H - PAD.bottom - ((v - lo) / span) * (H - PAD.top - PAD.bottom)
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.date).toFixed(1)},${y(p[metric.key]).toFixed(1)}`).join(' ')
  const ticks = [...new Set([lo, 0, hi].map((v) => Math.round(v)))]
  const shown = hover ?? points[points.length - 1]
  const mid = points[Math.floor(points.length / 2)]

  return (
    <>
      <div ref={box}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block" role="img"
          aria-label={`${metric.label} from ${long(points[0].date)} to ${long(points[points.length - 1].date)}: ${money(vals[0])} to ${money(vals[vals.length - 1])}.`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--color-line)" strokeWidth={t === 0 && lo < 0 ? 1.5 : 1} />
              <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fill="var(--color-ink-faint)" className="text-[11px]" style={{ fontVariantNumeric: 'tabular-nums' }}>{axis(t)}</text>
            </g>
          ))}
          {target > 0 && (
            <g>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(target)} y2={y(target)} stroke="var(--color-brand)" strokeOpacity="0.6" strokeDasharray="5 4" />
              <text x={W - PAD.right} y={y(target) - 6} textAnchor="end" fill="var(--color-brand)" className="text-[11px] font-semibold">goal {axis(target)}</text>
            </g>
          )}
          {[points[0], mid, points[points.length - 1]].filter((p, i, a) => a.findIndex((q) => q.date === p.date) === i).map((p, i, a) => (
            <text key={p.date} x={x(p.date)} y={H - 8} textAnchor={i === 0 ? 'start' : i === a.length - 1 ? 'end' : 'middle'}
              fill="var(--color-ink-faint)" className="text-[11px]">{short(p.date)}</text>
          ))}
          <path d={line} fill="none" stroke={metric.lowerIsBetter ? 'var(--color-alert)' : 'var(--color-brand)'} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {points.map((p) => (
            <circle key={p.date} cx={x(p.date)} cy={y(p[metric.key])} r={p === shown ? 5 : 3}
              fill={metric.lowerIsBetter ? 'var(--color-alert)' : 'var(--color-brand)'} stroke="var(--color-surface)" strokeWidth="2" />
          ))}
          {points.map((p, i) => {
            const prev = i ? x(points[i - 1].date) : PAD.left
            const next = i < points.length - 1 ? x(points[i + 1].date) : W - PAD.right
            const cx = x(p.date)
            return (
              <rect key={`hit-${p.date}`} x={(prev + cx) / 2} y={0} width={Math.max(6, (next + cx) / 2 - (prev + cx) / 2)} height={H}
                fill="transparent" onMouseEnter={() => setHover(p)} onMouseLeave={() => setHover(null)} onTouchStart={() => setHover(p)} />
            )
          })}
        </svg>
      </div>
      <p className="mt-2 flex flex-wrap items-baseline justify-between gap-2 rounded-xl bg-surface-sunken px-4 py-2.5 text-sm" aria-hidden="true">
        <span className="text-ink-soft">{long(shown.date)}</span>
        <span className="tabular font-bold text-ink">{money(shown[metric.key])}</span>
      </p>
    </>
  )
}

export default function ProgressChart({ history }) {
  const [id, setId] = useState('net')
  const metric = METRICS.find((m) => m.id === id)
  const points = history?.points ?? []
  const target = id === 'cash' ? history?.emergency_fund_target : null
  const first = points[0]
  const last = points[points.length - 1]
  const change = first && last ? last[metric.key] - first[metric.key] : 0
  const good = metric.lowerIsBetter ? change < 0 : change > 0

  return (
    <div>
      <SegmentedTabs label="What to chart" value={id} onChange={setId}
        tabs={METRICS.map((m) => ({ id: m.id, label: m.label, icon: m.icon }))} />
      {!last ? (
        <p className="mt-4 text-sm text-ink-soft">Your chart starts with your next update.</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">{metric.blurb}</p>
              <p className="tabular text-2xl font-bold text-ink">{money(last[metric.key])}</p>
            </div>
            {points.length > 1 && change !== 0 && (
              <p className={`tabular inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-bold ${good ? 'bg-brand-soft text-brand' : 'bg-alert-soft text-alert'}`}>
                <Icon name={good ? 'trending' : 'alert'} className="size-4" />
                {signed(change)} since {short(first.date)}
              </p>
            )}
          </div>
          {points.length > 1 ? (
            <div className="mt-3"><Chart points={points} metric={metric} target={target} /></div>
          ) : (
            // One point isn't a line. Say what it will become instead of drawing a dot.
            <div className="mt-3 flex items-center gap-3 rounded-xl border border-dashed border-line-strong px-4 py-4">
              <Icon name="chart" className="size-6 shrink-0 text-ink-faint" />
              <p className="text-sm leading-relaxed text-ink-soft">
                This is day one — {long(last.date)}. Each day you log something adds a point, and the line starts on the next one.
                {target > 0 && <> Your goal is <span className="tabular font-semibold text-ink">{money(target)}</span>.</>}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
