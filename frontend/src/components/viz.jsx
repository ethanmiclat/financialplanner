import { useId } from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon'

/** Small hand-rolled visuals, sharing one rule with GrowthChart: no charting library,
 *  every mark also readable without colour, and every visual carries a text summary
 *  for screen readers. Tone names map to literal classes so Tailwind can see them. */

const FILL = {
  brand: 'bg-brand',
  bright: 'bg-brand-bright',
  soft: 'bg-brand-soft',
  ink: 'bg-ink',
  faint: 'bg-ink-faint',
  line: 'bg-line-strong',
  alert: 'bg-alert',
  alertSoft: 'bg-alert-soft',
}
const SWATCH = FILL

/** One horizontal bar split into labelled parts. Direct labels underneath, so the
 *  reader never has to match a colour to a legend. */
export function StackedBar({ segments, height = 'h-3', legend = true, label }) {
  const shown = segments.filter((s) => s.value > 0)
  const total = shown.reduce((sum, s) => sum + s.value, 0) || 1
  return (
    <div>
      <div
        className={`flex ${height} overflow-hidden rounded-full bg-surface-sunken`}
        role="img"
        aria-label={label || shown.map((s) => `${s.label}: ${s.text ?? s.value}`).join(', ')}
      >
        {shown.map((s) => (
          <div
            key={s.label}
            className={`${FILL[s.tone] || FILL.brand} transition-[width] duration-300`}
            style={{ width: `${(s.value / total) * 100}%` }}
          />
        ))}
      </div>
      {legend && (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1" aria-hidden="true">
          {shown.map((s) => (
            <li key={s.label} className="flex items-center gap-1.5 text-sm">
              <span className={`inline-block size-2.5 rounded-sm ${SWATCH[s.tone] || SWATCH.brand}`} />
              <span className="text-ink-soft">{s.label}</span>
              {s.text && <span className="tabular font-semibold text-ink">{s.text}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** A ring that fills to `value` (0–1). The figure sits in the middle, so the ring is
 *  decoration around a number rather than the only carrier of it. */
export function Ring({ value, size = 96, stroke = 10, tone = 'brand', children, label }) {
  const v = Math.max(0, Math.min(1, value ?? 0))
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const strokeClass = tone === 'alert' ? 'stroke-alert' : tone === 'ink' ? 'stroke-ink' : 'stroke-brand-bright'
  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="stroke-surface-sunken" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} strokeLinecap="round"
          className={`${strokeClass} transition-[stroke-dashoffset] duration-500`}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - v)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      {/* A flex column, not a grid: grid made each child its own row and pushed them to
          the top and bottom edges of the ring instead of stacking them in the middle. */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5 text-center leading-none" aria-hidden="true">
        {children}
      </div>
    </div>
  )
}

/** Vertical bars with the value written on each one. For a dozen points or fewer —
 *  months, waiting years — where a table would be the alternative. Tap a bar to
 *  select it; the caller shows the detail. */
export function Bars({ data, format = (v) => v, selected, onSelect, height = 128, label, highlightKey }) {
  const max = Math.max(...data.map((d) => d.value), 1)
  const id = useId()
  return (
    <div role="group" aria-label={label}>
      <ul className="flex items-end gap-1.5" style={{ height }}>
        {data.map((d, i) => {
          const isSel = selected != null ? selected === d.key : false
          const h = Math.max(4, (d.value / max) * (height - 28))
          const hi = highlightKey ? d[highlightKey] : d.marker
          return (
            <li key={d.key ?? i} className="flex min-w-0 flex-1 flex-col items-center justify-end">
              <span className={`tabular mb-1 text-[0.6875rem] font-semibold ${isSel ? 'text-ink' : 'text-ink-faint'}`}>
                {d.value > 0 ? format(d.value) : ''}
              </span>
              <button
                type="button"
                onClick={onSelect ? () => onSelect(d) : undefined}
                aria-pressed={onSelect ? isSel : undefined}
                aria-label={`${d.label}: ${format(d.value)}${hi ? `, ${typeof hi === 'string' ? hi : 'milestone'}` : ''}`}
                aria-describedby={hi ? `${id}-m` : undefined}
                className={`relative w-full min-h-1 cursor-pointer rounded-t-md transition-colors duration-200 ${
                  isSel ? 'bg-brand' : hi ? 'bg-brand-bright' : 'bg-brand-border hover:bg-brand-bright'
                } ${onSelect ? '' : 'cursor-default'}`}
                style={{ height: h }}
              >
                {hi && (
                  <span className="absolute -top-1.5 left-1/2 grid size-3 -translate-x-1/2 place-items-center rounded-full bg-brand text-on-brand">
                    <Icon name="check" className="size-2" />
                  </span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
      <ul className="mt-1 flex gap-1.5" aria-hidden="true">
        {data.map((d, i) => (
          <li key={d.key ?? i} className="min-w-0 flex-1 truncate text-center text-[0.6875rem] text-ink-faint">
            {d.short ?? d.label}
          </li>
        ))}
      </ul>
      {data.some((d) => d.marker) && (
        <p id={`${id}-m`} className="mt-1 text-xs text-ink-faint">
          <span className="mr-1 inline-grid size-3 place-items-center rounded-full bg-brand align-middle text-on-brand">
            <Icon name="check" className="size-2" />
          </span>
          a step finishes that month
        </p>
      )}
    </div>
  )
}

const STATUS = {
  done: { ring: 'border-brand bg-brand text-on-brand', icon: 'check', line: 'bg-brand' },
  current: { ring: 'border-brand bg-surface text-brand ring-4 ring-brand-soft', icon: null, line: 'bg-line' },
  todo: { ring: 'border-line-strong bg-surface text-ink-faint', icon: null, line: 'bg-line' },
  skip: { ring: 'border-line bg-surface-sunken text-ink-faint', icon: 'minus', line: 'bg-line' },
}

/** The waterfall as a picture: a numbered rail with done / current / upcoming states.
 *  Each row is a button when the caller gives it somewhere to go. */
export function Stepper({ steps }) {
  return (
    <ol className="relative">
      {steps.map((s, i) => {
        const st = STATUS[s.status] || STATUS.todo
        const last = i === steps.length - 1
        const Row = s.onClick ? 'button' : 'div'
        return (
          <li key={s.key ?? i} className="relative flex gap-3">
            {!last && <span className={`absolute left-[15px] top-8 h-[calc(100%-1.25rem)] w-0.5 ${st.line}`} aria-hidden="true" />}
            <span
              className={`tabular relative z-10 mt-1 grid size-8 shrink-0 place-items-center rounded-full border-2 text-xs font-bold ${st.ring}`}
              aria-hidden="true"
            >
              {st.icon ? <Icon name={st.icon} className="size-4" /> : s.n}
            </span>
            <Row
              type={s.onClick ? 'button' : undefined}
              onClick={s.onClick}
              className={`mb-1 min-h-11 min-w-0 flex-1 rounded-xl px-2 py-1.5 text-left ${
                s.onClick ? 'cursor-pointer transition-colors duration-200 hover:bg-surface-sunken' : ''
              }`}
            >
              <span className="flex items-baseline justify-between gap-3">
                <span className={`text-[0.9375rem] font-semibold ${s.status === 'todo' ? 'text-ink-soft' : 'text-ink'}`}>
                  {s.title}
                  <span className="sr-only">
                    {s.status === 'done' ? ', handled' : s.status === 'current' ? ', do this next' : ''}
                  </span>
                </span>
                {s.right && <span className="tabular shrink-0 text-sm font-bold text-brand">{s.right}</span>}
              </span>
              {s.sub && <span className="block text-sm text-ink-faint">{s.sub}</span>}
              {s.pct != null && (
                <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-surface-sunken" aria-hidden="true">
                  <span className="block h-full rounded-full bg-brand-bright" style={{ width: `${Math.round(s.pct * 100)}%` }} />
                </span>
              )}
            </Row>
          </li>
        )
      })}
    </ol>
  )
}

/** A number with a caption, optionally a link. The unit of the stat strips. */
export function Stat({ label, value, sub, icon, tone = 'surface', to, onClick, children }) {
  const inner = (
    <>
      <span className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-wide text-ink-faint">{label}</span>
        {icon && <Icon name={icon} className="size-4 text-ink-faint" />}
      </span>
      {children ?? <span className="tabular mt-1 block text-2xl font-bold leading-tight text-ink">{value}</span>}
      {sub && <span className="mt-0.5 block text-sm text-ink-soft">{sub}</span>}
      {(to || onClick) && (
        <span className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-brand">
          See it <Icon name="arrowRight" className="size-3.5" />
        </span>
      )}
    </>
  )
  const cls = `block min-h-24 w-full rounded-[--radius-card] border p-4 text-left ${
    tone === 'brand' ? 'border-brand-border bg-brand-soft' : tone === 'alert' ? 'border-alert-border bg-alert-soft' : 'border-line bg-surface'
  } ${to || onClick ? 'cursor-pointer transition-colors duration-200 hover:border-brand-border' : ''}`
  if (to) return <Link to={to} className={cls}>{inner}</Link>
  if (onClick) return <button type="button" onClick={onClick} className={cls}>{inner}</button>
  return <div className={cls}>{inner}</div>
}
