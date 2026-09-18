import { Annotated } from './Term'
import { Button, Card } from './ui'

/** One renderer for every kind of answer — a canned question, a knowledge entry, a
 *  composed scenario, a decline. They all share the three layers (summary, why,
 *  specifics); scenarios add headed sections and a visible assumptions block, because
 *  an assumed interest rate changes the answer and mustn't be buried. */

function Paragraphs({ text, glossary, className = '' }) {
  if (!text) return null
  return text.split(/\n\n+/).map((para, i) => (
    <p key={i} className={`${className} ${i > 0 ? 'mt-3' : ''}`}>
      <Annotated text={para} glossary={glossary} />
    </p>
  ))
}

function FactList({ facts, glossary }) {
  if (!facts?.length) return null
  return (
    <dl className="divide-y divide-line">
      {facts.map((f, i) => (
        <div key={i} className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
          <dt className="text-sm font-medium text-ink-soft">{f.label}</dt>
          <dd className="tabular text-[0.9375rem] font-semibold text-ink sm:text-right">
            <Annotated text={f.value} glossary={glossary} />
          </dd>
        </div>
      ))}
    </dl>
  )
}

export default function AnswerBody({ answer, glossary, kind, onSave, saving }) {
  if (!answer) return null
  const sections = answer.sections || []
  const assumptions = answer.assumptions || []
  const isDecline = kind === 'decline'

  return (
    <div className="space-y-3">
      {/* Layer 1 — the answer in one line. */}
      <Card tone={isDecline ? 'sunken' : 'brand'} className="p-5">
        <p className="text-lg font-semibold leading-snug text-ink">
          <Annotated text={answer.summary} glossary={glossary} />
        </p>
      </Card>

      {/* Layer 2 — why. */}
      {answer.detail && (
        <Card className="p-5">
          <Paragraphs text={answer.detail} glossary={glossary} className="text-[1.0625rem] leading-relaxed text-ink" />
        </Card>
      )}

      {/* Composed scenarios: headed sections, each with its own numbers. */}
      {sections.map((s, i) => (
        <Card key={i} className="p-5">
          <h3 className="pb-1 font-bold tracking-tight text-ink">{s.heading}</h3>
          <Paragraphs text={s.body} glossary={glossary} className="text-[0.9375rem] leading-relaxed text-ink" />
          {s.facts?.length > 0 && <div className="mt-2"><FactList facts={s.facts} glossary={glossary} /></div>}
        </Card>
      ))}

      {/* Layer 3 — the specifics. Skipped when sections already carried them. */}
      {answer.facts?.length > 0 && sections.length === 0 && (
        <Card className="p-5">
          <h3 className="pb-1 font-bold tracking-tight text-ink">The specifics</h3>
          <FactList facts={answer.facts} glossary={glossary} />
        </Card>
      )}

      {/* What we had to assume. Visible, not tucked away — it's the hinge. */}
      {assumptions.length > 0 && (
        <Card tone="sunken" className="p-4">
          <h3 className="text-sm font-bold uppercase tracking-wide text-ink-faint">What this assumes</h3>
          <dl className="mt-2 space-y-2">
            {assumptions.map((a, i) => (
              <div key={i}>
                <div className="flex items-baseline justify-between gap-4">
                  <dt className="text-sm font-medium text-ink-soft">{a.label}</dt>
                  <dd className="tabular text-sm font-semibold text-ink">{a.value}</dd>
                </div>
                {a.note && <p className="mt-0.5 text-xs leading-relaxed text-ink-faint">{a.note}</p>}
              </div>
            ))}
          </dl>
        </Card>
      )}

      {answer.save_hint && onSave && (
        <Button variant="secondary" icon="check" loading={saving} onClick={() => onSave(answer.save_hint)} className="w-full sm:w-auto">
          {answer.save_hint.label}
        </Button>
      )}

      {answer.sources?.length > 0 && !isDecline && (
        <p className="px-1 text-xs leading-relaxed text-ink-faint">
          From{' '}
          {answer.sources.map((s, i) => (
            <span key={s}>{i > 0 && ', '}<span className="font-semibold">{s}</span></span>
          ))}
          . Fixed rules and written explanations, not a generated opinion.
        </p>
      )}
    </div>
  )
}
