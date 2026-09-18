import Icon from './Icon'
import { Annotated } from './Term'
import { Button, Card, Disclosure, ScrollX } from './ui'
import { formatInput, labelFor, money } from '../lib/format'
import { presetFor, useLog } from '../lib/logContext'

/** Priority is communicated three ways at once — an icon, a word, and a color —
 *  because color alone fails for colorblind readers and in bright sunlight. */
const PRIORITY = {
  blocking: { label: 'Do this first', icon: 'alert', chip: 'bg-alert-soft text-alert border-alert-border' },
  high:     { label: 'High impact',   icon: 'star',  chip: 'bg-brand-soft text-brand border-brand-border' },
  medium:   { label: 'When you can',  icon: 'clock', chip: 'bg-surface-sunken text-ink-soft border-line-strong' },
  low:      { label: 'Later',         icon: 'clock', chip: 'bg-surface-sunken text-ink-faint border-line' },
  info:     { label: 'Nothing to do', icon: 'check', chip: 'bg-surface-sunken text-ink-soft border-line' },
}

function NumbersTable({ inputs }) {
  const rows = Object.entries(inputs).filter(([, v]) => typeof v !== 'object' || v === null)
  const nested = Object.entries(inputs).filter(([, v]) => v && typeof v === 'object' && !Array.isArray(v))

  return (
    <ScrollX label="The numbers behind this recommendation" className="mt-2">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">The exact numbers behind this recommendation</caption>
        <tbody>
          {rows.map(([key, value]) => (
            <tr key={key} className="border-b border-line last:border-0">
              <th scope="row" className="py-2 pr-4 font-medium text-ink-soft">{labelFor(key)}</th>
              <td className="tabular py-2 text-right font-semibold text-ink whitespace-nowrap">
                {formatInput(key, value)}
              </td>
            </tr>
          ))}
          {nested.flatMap(([parent, obj]) =>
            Object.entries(obj)
              .filter(([, v]) => typeof v !== 'object')
              .map(([key, value]) => (
                <tr key={`${parent}.${key}`} className="border-b border-line last:border-0">
                  <th scope="row" className="py-2 pr-4 font-medium text-ink-soft">{labelFor(key)}</th>
                  <td className="tabular py-2 text-right font-semibold text-ink whitespace-nowrap">
                    {formatInput(key, value)}
                  </td>
                </tr>
              )),
          )}
        </tbody>
      </table>
    </ScrollX>
  )
}

/** Collapsed, a card is one line and a number — the decision. Everything past that
 *  (why, and the arithmetic) is behind a single tap, and the list opens one card at a
 *  time so a first-time reader is never handed ten explanations at once. */
export default function ActionCard({ action, glossary, index, open = false, onToggle, id }) {
  const p = PRIORITY[action.priority] || PRIORITY.medium
  const isInfo = action.priority === 'info'
  const hasNumbers = action.inputs && Object.keys(action.inputs).length > 0
  const panelId = `${id || action.id}-panel`
  const { openLog } = useLog()
  const preset = presetFor(action)

  return (
    <Card
      as="li"
      id={id}
      tone={isInfo ? 'sunken' : 'surface'}
      className={`${action.priority === 'blocking' ? 'border-alert-border' : ''} ${open ? 'ring-2 ring-brand-soft' : ''}`}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full cursor-pointer items-start gap-3 p-4 text-left sm:p-5"
      >
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold ${p.chip}`}>
              <Icon name={p.icon} className="size-3.5" />
              {p.label}
            </span>
            {typeof index === 'number' && !isInfo && (
              <span className="text-xs font-semibold text-ink-faint">#{index}</span>
            )}
          </span>
          {/* Layer 1 — the decision, in one line. */}
          <span className="mt-2 block text-[1.0625rem] font-bold leading-snug tracking-tight text-ink">
            <Annotated text={action.title} glossary={glossary} />
          </span>
          {action.amount != null && !isInfo && (
            <span className="tabular mt-1 block text-2xl font-bold text-brand">{money(action.amount)}</span>
          )}
        </span>
        <Icon
          name="chevronDown"
          className={`mt-1 size-5 shrink-0 text-ink-faint transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div id={panelId} className="border-t border-line px-4 pb-4 sm:px-5 sm:pb-5">
          {/* Layer 2 — why, in plain English. */}
          <p className="pt-3 text-[0.9375rem] leading-relaxed text-ink-soft">
            <Annotated text={action.detail} glossary={glossary} />
          </p>
          {/* The way out of the card: did it? Say so, and the plan moves on. */}
          {preset && (
            <Button variant="secondary" icon="check" onClick={() => openLog(preset)} className="mt-3 w-full sm:w-auto">
              {preset.kind === 'pay' ? 'I made a payment' : preset.kind === 'invest' ? 'I invested it' : 'I put money in'}
            </Button>
          )}
          {/* Layer 3 — the arithmetic, so nothing is a black box. */}
          {hasNumbers && (
            <div className="mt-2">
              <Disclosure label="See the numbers" tone="quiet">
                <NumbersTable inputs={action.inputs} />
                <p className="mt-3 rounded-lg bg-surface-sunken px-3 py-2 text-xs leading-relaxed text-ink-faint">
                  Rule <span className="font-semibold">{action.rule_id}</span> — “{action.rule_name}”.
                  A fixed rule applied to the numbers above, not a guess.
                </p>
              </Disclosure>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
