import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AnswerBody from '../components/AnswerBody'
import Icon from '../components/Icon'
import { Button, Card, ErrorState, Field, Skeleton, TextArea, Toast } from '../components/ui'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

function QuestionLink({ id, children, className = '' }) {
  // A real link, not a button: every canned answer gets its own URL, so the browser's
  // back button walks back through the questions and any answer can be shared.
  return (
    <Link
      to={`/ask/${id}`}
      className={`flex min-h-12 w-full cursor-pointer items-center justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-left text-[0.9375rem] font-medium text-ink transition-colors duration-200 hover:border-brand-border hover:bg-brand-soft ${className}`}
    >
      <span>{children}</span>
      <Icon name="chevronRight" className="size-4 shrink-0 text-ink-faint" />
    </Link>
  )
}

function Chip({ onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="min-h-11 cursor-pointer rounded-xl border border-brand-border bg-brand-soft px-3 py-2 text-left text-sm font-semibold text-brand transition-colors duration-200 hover:bg-brand-soft-hover"
    >
      {children}
    </button>
  )
}

function ChipRow({ label, items, onPick }) {
  if (!items?.length) return null
  return (
    <div>
      <p className="px-1 pb-2 text-sm font-bold uppercase tracking-wide text-ink-faint">{label}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((s) => (
          <Chip key={s.id || s.question} onClick={() => onPick(s.question)}>{s.question}</Chip>
        ))}
      </div>
    </div>
  )
}

const EXAMPLES = [
  'How should I plan around my 35K of student debt?',
  'How much can I put in my HSA this year?',
  'What if I saved an extra $200 a month?',
  'Should I wait for the market to drop before investing?',
  'What is an expense ratio?',
  'Can I retire at 60?',
]

/** One exchange in the transcript: what was asked, and everything that came back. */
function Exchange({ entry, glossary, onAsk, onSave, saving }) {
  const { question, response, error, pending } = entry

  return (
    <article className="space-y-3">
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-md bg-toast px-4 py-2.5 text-[0.9375rem] leading-relaxed text-on-toast">
          {question}
        </p>
      </div>

      {pending && <Skeleton className="h-40 w-full" />}
      {error && <ErrorState error={error} />}

      {response && (
        <div className="space-y-4">
          {response.corrections?.length > 0 && (
            <p className="px-1 text-sm text-ink-soft">
              Showing results for{' '}
              <em className="font-semibold not-italic text-ink">
                {response.corrections.map((c) => c.to).join(', ')}
              </em>
            </p>
          )}
          {response.multi_part && (
            <p className="px-1 text-sm text-ink-soft">You asked two things — here they are in order.</p>
          )}

          {response.results.map((r, i) => (
            <div key={i} className="space-y-3">
              {r.status === 'answered' && (
                <>
                  {response.multi_part && (
                    <h2 className="px-1 text-sm font-bold uppercase tracking-wide text-ink-faint">{r.question}</h2>
                  )}
                  <AnswerBody answer={r.answer} glossary={glossary} kind={r.kind} onSave={onSave} saving={saving} />
                  <ChipRow label="You might ask next" items={r.follow_ups} onPick={onAsk} />
                </>
              )}

              {r.status === 'declined' && (
                <>
                  <AnswerBody answer={r.answer} glossary={glossary} kind="decline" />
                  <ChipRow label="What I can help with instead" items={r.redirects} onPick={onAsk} />
                </>
              )}

              {r.status === 'needs_input' && (
                <Card tone="brand" className="p-5">
                  <p className="text-lg font-semibold leading-snug text-ink">{r.prompt}</p>
                  {r.hint && <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-soft">{r.hint}</p>}
                </Card>
              )}

              {r.status === 'ambiguous' && (
                <Card className="p-5">
                  <p className="font-semibold text-ink">{r.prompt || 'Did you mean one of these?'}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {r.suggestions.map((s) => (
                      <Chip key={s.id} onClick={() => onAsk(s.question)}>{s.question}</Chip>
                    ))}
                  </div>
                </Card>
              )}

              {r.status === 'unmatched' && (
                <Card className="p-5">
                  <p className="font-semibold text-ink">{r.prompt}</p>
                  {r.suggestions?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {r.suggestions.map((s) => (
                        <Chip key={s.id} onClick={() => onAsk(s.question)}>{s.question}</Chip>
                      ))}
                    </div>
                  )}
                  <p className="mt-3 text-sm text-ink-soft">Or browse the questions by topic below.</p>
                </Card>
              )}
            </div>
          ))}

          <p className="px-1 text-xs leading-relaxed text-ink-faint">{response.disclaimer}</p>
        </div>
      )}
    </article>
  )
}

export function AskIndex({ glossary }) {
  const { data: topics, error: topicsError, loading: topicsLoading, reload } = useApi(api.questions, [])
  const [draft, setDraft] = useState('')
  const [transcript, setTranscript] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const inputRef = useRef(null)
  const endRef = useRef(null)

  // useApi fires on mount and on dep change; a typed question wants a deliberate
  // submit, so this is manual state — the same shape as YouPage's save flow.
  const ask = useCallback(async (text) => {
    const question = (text || '').trim()
    if (!question || submitting) return
    const last = transcript[transcript.length - 1]
    const context = last?.response?.context || null
    const id = Date.now()
    setTranscript((t) => [...t, { id, question, pending: true }])
    setDraft('')
    setSubmitting(true)
    try {
      const response = await api.ask(question, context)
      setTranscript((t) => t.map((e) => (e.id === id ? { id, question, response } : e)))
    } catch (error) {
      setTranscript((t) => t.map((e) => (e.id === id ? { id, question, error } : e)))
    } finally {
      setSubmitting(false)
      inputRef.current?.focus()
    }
  }, [submitting, transcript])

  const save = useCallback(async (hint) => {
    setSaving(true)
    try {
      await api.call(hint.method, hint.path, hint.body)
      setToast('Saved to your plan.')
    } catch (error) {
      setToast(error.message || 'Could not save.')
    } finally {
      setSaving(false)
    }
  }, [])

  useEffect(() => {
    if (transcript.length) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [transcript])

  function onSubmit(e) {
    e.preventDefault()
    ask(draft)
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      ask(draft)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Ask</h1>
        <p className="mt-1 text-[0.9375rem] leading-relaxed text-ink-soft">
          Type a question in your own words. Answers about your plan use your actual
          numbers; a question with a number in it — "my 35K of student debt" — gets
          run as a what-if without changing anything until you say so.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-3">
        <Field label="Your question" hint="Enter sends; Shift+Enter for a new line.">
          {(props) => (
            <TextArea
              {...props}
              ref={inputRef}
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="How should I plan around my 35K of student debt?"
              maxLength={500}
            />
          )}
        </Field>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" loading={submitting} disabled={!draft.trim()} icon="chevronRight">
            Ask
          </Button>
          {transcript.length > 0 && (
            <Button type="button" variant="ghost" size="sm" onClick={() => setTranscript([])}>
              Clear
            </Button>
          )}
        </div>
      </form>

      {transcript.length === 0 && (
        <div>
          <p className="px-1 pb-2 text-sm font-bold uppercase tracking-wide text-ink-faint">Try one</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((q) => <Chip key={q} onClick={() => ask(q)}>{q}</Chip>)}
          </div>
        </div>
      )}

      <div aria-live="polite" className="space-y-8">
        {transcript.map((entry) => (
          <Exchange
            key={entry.id}
            entry={entry}
            glossary={glossary}
            onAsk={ask}
            onSave={save}
            saving={saving}
          />
        ))}
        <div ref={endRef} />
      </div>

      <section aria-labelledby="browse" className="space-y-5 border-t border-line pt-6">
        <h2 id="browse" className="px-1 text-sm font-bold uppercase tracking-wide text-ink-faint">
          Or browse by topic
        </h2>
        {topicsLoading && <div className="space-y-3">{[0, 1].map((i) => <Skeleton key={i} className="h-32 w-full" />)}</div>}
        {topicsError && <ErrorState error={topicsError} onRetry={reload} />}
        {topics?.map((topic) => (
          <div key={topic.topic}>
            <h3 className="px-1 pb-2 text-sm font-semibold text-ink-soft">{topic.topic}</h3>
            <ul className="space-y-2">
              {topic.questions.map((q) => (
                <li key={q.id}><QuestionLink id={q.id}>{q.question}</QuestionLink></li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <Toast message={toast} onDismiss={() => setToast(null)} />
    </div>
  )
}

export function AskAnswer({ glossary }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, reload } = useApi(() => api.question(id), [id])

  if (loading) return <Skeleton className="h-96 w-full" />
  if (error) {
    return (
      <div className="space-y-4">
        <ErrorState error={error} onRetry={reload} />
        <button onClick={() => navigate('/ask')} className="min-h-11 cursor-pointer text-[0.9375rem] font-semibold text-brand">
          Back to all questions
        </button>
      </div>
    )
  }

  const { answer } = data

  return (
    <article className="space-y-4">
      <Link to="/ask" className="inline-flex min-h-11 items-center gap-1 text-[0.9375rem] font-semibold text-brand">
        <Icon name="chevronLeft" className="size-4" /> Ask anything
      </Link>

      <h1 className="text-xl font-bold leading-snug tracking-tight text-ink sm:text-2xl">{data.question}</h1>

      <AnswerBody answer={answer} glossary={glossary} kind="personal" />

      {data.follow_ups.length > 0 && (
        <section aria-labelledby="followups">
          <h2 id="followups" className="px-1 pb-2 text-sm font-bold uppercase tracking-wide text-ink-faint">
            You might ask next
          </h2>
          <ul className="space-y-2">
            {data.follow_ups.map((f) => (
              <li key={f.id}><QuestionLink id={f.id}>{f.question}</QuestionLink></li>
            ))}
          </ul>
        </section>
      )}

      {answer.content_key && (
        <Link
          to={`/learn/${answer.content_key}`}
          className="flex min-h-12 items-center justify-between gap-3 rounded-xl border border-brand-border bg-brand-soft px-4 py-3 font-semibold text-brand transition-colors duration-200 hover:bg-brand-soft-hover"
        >
          <span className="flex items-center gap-2"><Icon name="book" className="size-4" />Read the full explanation</span>
          <Icon name="chevronRight" className="size-4 shrink-0" />
        </Link>
      )}

      <p className="px-1 text-xs leading-relaxed text-ink-faint">{data.disclaimer}</p>
    </article>
  )
}
