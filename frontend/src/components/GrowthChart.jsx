import { useId, useState } from 'react'
import { money } from '../lib/format'
import { ScrollX } from './ui'

/** Inline SVG line chart. No charting library: two series and under a hundred points
 *  don't justify 150KB of bundle, and hand-rolling it means the accessibility is right.
 *
 *  Series are distinguished by line style as well as colour (solid vs dashed), so
 *  the chart still reads for a colourblind viewer or in greyscale. The tables on the
 *  page are the real accessible fallback — the chart carries a summary label and the
 *  numbers live in the tables.
 *
 *  The line runs past retirement: the shaded band is the years the money is being
 *  spent rather than saved, which is where "will it last?" becomes visible.
 */
export default function GrowthChart({ series, retirementAge }) {
  const [hover, setHover] = useState(null)
  const gradientId = useId()

  const W = 640
  const H = 240
  const PAD = { top: 16, right: 12, bottom: 28, left: 56 }

  const maxV = Math.max(...series.map((p) => Math.max(p.following_plan, p.current_pace)), 1)
  const end = series[series.length - 1]
  const maxY = end.years || 1
  const retirement = series.find((p) => p.age === retirementAge)
  const retireYears = retirement?.years

  const x = (yrs) => PAD.left + (yrs / maxY) * (W - PAD.left - PAD.right)
  const y = (v) => H - PAD.bottom - (v / maxV) * (H - PAD.top - PAD.bottom)

  const path = (key) =>
    series.map((p, i) => `${i ? 'L' : 'M'}${x(p.years).toFixed(1)},${y(p[key]).toFixed(1)}`).join(' ')

  const areaPath =
    `${path('following_plan')} L${x(maxY)},${H - PAD.bottom} L${x(0)},${H - PAD.bottom} Z`

  // Round tick values to something a person would actually say out loud.
  const step = Math.pow(10, Math.floor(Math.log10(maxV)))
  const niceMax = Math.ceil(maxV / step) * step
  const ticks = [0, niceMax / 2, niceMax].filter((t) => t <= maxV * 1.15)
  const axisLabel = (t) =>
    t >= 1e6 ? `$${+(t / 1e6).toFixed(1)}M` : t >= 1000 ? `$${Math.round(t / 1000)}k` : `$${Math.round(t)}`

  // Label now, retirement and the end, plus round intervals that don't crowd them.
  const every = maxY > 50 ? 20 : maxY > 25 ? 10 : 5
  const clearOf = (years, other) => other == null || Math.abs(years - other) >= maxY / 12
  const xTicks = series.filter((p) =>
    p.years === 0 || p.years === maxY || p.years === retireYears ||
    (p.years % every === 0 && clearOf(p.years, retireYears) && clearOf(p.years, maxY) && clearOf(p.years, 0)),
  )

  const point = hover ?? retirement ?? end
  const summary = retirement && retirement.years < maxY
    ? `Following the plan it reaches ${money(retirement.following_plan)} at retirement, age ` +
      `${retirement.age}, then pays for retirement and stands at ${money(end.following_plan)} at age ${end.age}. `
    : `Following the plan it reaches ${money(end.following_plan)}, versus ${money(end.current_pace)} at your current pace. `

  return (
    <div>
      <ScrollX label="Growth chart">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-56 w-full min-w-[20rem]"
          role="img"
          aria-label={`Projected balance from age ${series[0].age} to ${end.age}. ${summary}The tables below list the figures.`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-brand-bright)" stopOpacity="0.22" />
              <stop offset="100%" stopColor="var(--color-brand-bright)" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {retireYears != null && retireYears < maxY && (
            <g>
              <rect x={x(retireYears)} y={PAD.top} width={x(maxY) - x(retireYears)}
                height={H - PAD.top - PAD.bottom} fill="var(--color-surface-sunken)" />
              <text x={x(retireYears) + 6} y={PAD.top + 13} fill="var(--color-ink-faint)" className="text-[11px]">
                retired
              </text>
            </g>
          )}

          {/* Grid lines sit well below the data in contrast so they never compete. */}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)}
                stroke="var(--color-line)" strokeWidth="1" />
              <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end"
                fill="var(--color-ink-faint)" className="text-[11px]" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {axisLabel(t)}
              </text>
            </g>
          ))}

          {xTicks.map((p) => (
            <text key={p.years} x={x(p.years)} y={H - 8}
              textAnchor={p.years === 0 ? 'start' : p.years === maxY ? 'end' : 'middle'}
              fill="var(--color-ink-faint)" className="text-[11px]">
              {p.years === 0 ? 'now' : `age ${p.age}`}
            </text>
          ))}

          {retireYears != null && (
            <line x1={x(retireYears)} x2={x(retireYears)} y1={PAD.top} y2={H - PAD.bottom}
              stroke="var(--color-brand)" strokeOpacity="0.45" strokeWidth="1" strokeDasharray="4 3" />
          )}

          <path d={areaPath} fill={`url(#${gradientId})`} />
          {/* Dashed = current pace, solid = the plan. Style, not just colour. */}
          <path d={path('current_pace')} fill="none" stroke="var(--color-ink-faint)" strokeWidth="2"
            strokeDasharray="5 4" strokeLinecap="round" />
          <path d={path('following_plan')} fill="none" stroke="var(--color-brand)" strokeWidth="2.5"
            strokeLinecap="round" />

          {hover && (
            <line x1={x(hover.years)} x2={x(hover.years)} y1={PAD.top} y2={H - PAD.bottom}
              stroke="var(--color-brand)" strokeWidth="1" strokeDasharray="3 3" />
          )}
          <circle cx={x(point.years)} cy={y(point.following_plan)} r="4.5"
            fill="var(--color-brand)" stroke="var(--color-surface)" strokeWidth="2" />

          {/* Full-height hit strips: a wide target per year beats a 4px dot. */}
          {series.map((p) => (
            <rect
              key={p.years}
              x={x(p.years) - (W - PAD.left - PAD.right) / maxY / 2}
              y={0}
              width={Math.max(6, (W - PAD.left - PAD.right) / maxY)}
              height={H}
              fill="transparent"
              onMouseEnter={() => setHover(p)}
              onMouseLeave={() => setHover(null)}
              onTouchStart={() => setHover(p)}
            />
          ))}
        </svg>
      </ScrollX>

      {/* Readout rather than a floating tooltip — it can't be clipped, it doesn't
          need hover, and it stays put on a touch screen. */}
      <div className="mt-2 rounded-xl bg-surface-sunken px-4 py-3" aria-hidden="true">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
          {point.years === 0 ? 'Today' : `In ${point.years} years — age ${point.age}`}
          {point.age === retirementAge ? ' · retirement' : point.phase === 'retired' ? ' · retired' : ''}
        </p>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-5 gap-y-1">
          <span className="flex items-baseline gap-2">
            <span className="inline-block h-0.5 w-4 rounded bg-brand" />
            <span className="text-sm text-ink-soft">Following your plan</span>
            <span className="tabular font-bold text-ink">{money(point.following_plan)}</span>
          </span>
          <span className="flex items-baseline gap-2">
            <span className="inline-block h-0.5 w-4 rounded border-t-2 border-dashed border-ink-faint" />
            <span className="text-sm text-ink-soft">Current pace</span>
            <span className="tabular font-semibold text-ink-soft">{money(point.current_pace)}</span>
          </span>
        </div>
        {point.phase === 'retired' && (
          <p className="mt-1 text-sm text-ink-soft">
            Spent from it over the year before:{' '}
            <span className="tabular font-semibold text-ink">{money(point.withdrawn)}</span>
          </p>
        )}
      </div>
    </div>
  )
}
