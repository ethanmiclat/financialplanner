import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import Icon from './Icon'

/** A jargon word the reader can tap for a plain-English definition.
 *
 *  This is the core accommodation for the audience: nobody has to already know what
 *  "MAGI" or "expense ratio" means to use the app. It's a real <button>, so it works
 *  by keyboard and announces itself to a screen reader — never a hover-only tooltip,
 *  which would be unusable on a phone.
 *
 *  Presentation splits by width because an anchored popover next to a word that sits
 *  near the right edge gets clipped off-screen on a phone. Under 640px it's a bottom
 *  sheet (portalled to body, always fully visible, in thumb reach); above that it's
 *  anchored to the word, flipping to right-aligned in the right half of the screen. */
export default function Term({ id, glossary, children }) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState(null)
  const [isSmall, setIsSmall] = useState(
    () => typeof window !== 'undefined' && window.innerWidth < 640,
  )
  const entry = glossary?.[id]
  const panelId = useId()
  const wrapRef = useRef(null)
  const triggerRef = useRef(null)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 639px)')
    const on = (e) => setIsSmall(e.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])

  const close = useCallback(() => {
    setOpen(false)
    triggerRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!open) return
    const onDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target) &&
          !e.target.closest?.('[data-term-sheet]')) {
        setOpen(false)
      }
    }
    const onKey = (e) => { if (e.key === 'Escape') close() }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, close])

  /** Fixed coordinates for the desktop popover, clamped to the viewport: left-aligned
   *  to the word, flipped right when that would run off the edge, and flipped above
   *  when there isn't room below. */
  const place = useCallback(() => {
    const el = triggerRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const W = 320
    const MARGIN = 12
    const left = Math.min(Math.max(MARGIN, r.left), window.innerWidth - W - MARGIN)
    const spaceBelow = window.innerHeight - r.bottom
    setPos({ left, top: r.bottom + 8, bottom: r.top - 8, flip: spaceBelow < 220 })
  }, [])

  function toggle() {
    if (!open) place()
    setOpen((v) => !v)
  }

  // The popover is portalled out of the card, so it has to track the word on scroll.
  useEffect(() => {
    if (!open || isSmall) return
    const on = () => place()
    window.addEventListener('scroll', on, true)
    window.addEventListener('resize', on)
    return () => {
      window.removeEventListener('scroll', on, true)
      window.removeEventListener('resize', on)
    }
  }, [open, isSmall, place])

  // Below every hook, not above: an early return before `place` and the scroll effect
  // changes how many hooks run between a word that has a definition and one that
  // doesn't, which is what React's rules-of-hooks forbids.
  if (!entry) return <>{children}</>

  const body = (
    <>
      <span className="block font-semibold text-ink">{entry.term}</span>
      <span className="mt-1 block text-[0.9375rem] leading-relaxed text-ink">{entry.short}</span>
      <span className="mt-2 block text-sm leading-relaxed text-ink-soft">{entry.more}</span>
    </>
  )

  return (
    <span className="relative inline-block" ref={wrapRef}>
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        className="text-brand font-semibold underline decoration-brand-border decoration-2 underline-offset-2 hover:decoration-brand cursor-pointer transition-colors"
      >
        {children || entry.term}
        <Icon name="info" className="inline size-3.5 ml-0.5 -translate-y-px" />
        <span className="sr-only">, show definition</span>
      </button>

      {open && isSmall &&
        createPortal(
          <div data-term-sheet className="fixed inset-0 z-50 flex flex-col justify-end">
            {/* Scrim strong enough to isolate the sheet, and tappable to dismiss. */}
            <button
              type="button"
              className="absolute inset-0 cursor-pointer bg-black/50"
              aria-label="Close definition"
              onClick={close}
            />
            <div
              id={panelId}
              role="dialog"
              aria-modal="true"
              aria-label={`What ${entry.term} means`}
              className="relative rounded-t-2xl border-t border-line bg-surface p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl"
            >
              <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line-strong" aria-hidden="true" />
              {body}
              <button
                type="button"
                onClick={close}
                className="mt-4 flex min-h-12 w-full cursor-pointer items-center justify-center gap-1.5 rounded-xl bg-brand-soft font-semibold text-brand"
              >
                Got it
              </button>
            </div>
          </div>,
          document.body,
        )}

      {/* Portalled to <body>: an ancestor with `overflow: hidden` (an action card,
          a scroll container) would otherwise clip the definition mid-sentence. */}
      {open && !isSmall && pos &&
        createPortal(
          <span
            id={panelId}
            role="dialog"
            aria-label={`What ${entry.term} means`}
            data-term-sheet
            style={
              pos.flip
                ? { left: pos.left, bottom: window.innerHeight - pos.bottom }
                : { left: pos.left, top: pos.top }
            }
            className="fixed z-50 block w-80 max-w-[calc(100vw-1.5rem)] rounded-xl border border-line-strong bg-surface p-4 text-left shadow-xl"
          >
            {body}
            <button
              type="button"
              onClick={close}
              className="mt-3 inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-brand cursor-pointer"
            >
              <Icon name="close" className="size-4" /> Close
            </button>
          </span>,
          document.body,
        )}
    </span>
  )
}

/** Scans a plain sentence for known glossary terms and wraps the first occurrence
 *  of each. Keeps the copy in the backend free of markup. */
export function Annotated({ text, glossary }) {
  if (!glossary || !text) return <>{text}</>

  const patterns = [
    [/\b401\(k\)\b/, '401k'], [/\bRoth IRA\b/, 'roth'], [/\bIRA\b/, 'ira'],
    [/\bHSA\b/, 'hsa'], [/\bHDHP\b/, 'hdhp'], [/\bhigh-deductible health plan\b/i, 'hdhp'],
    [/\bemployer match\b/i, 'employer_match'], [/\bmatch\b/i, 'employer_match'],
    [/\btaxable brokerage\b/i, 'taxable_brokerage'], [/\bindex funds?\b/i, 'index_fund'],
    [/\btarget-date funds?\b/i, 'target_date_fund'], [/\bexpense ratio\b/i, 'expense_ratio'],
    [/\bMAGI\b/, 'magi'], [/\bphase-out\b/i, 'phase_out'], [/\bbackdoor\b/i, 'backdoor_roth'],
    [/\bemergency fund\b/i, 'emergency_fund'], [/\bAPR\b/, 'apr'],
    [/\bcatch-up\b/i, 'catch_up'], [/\bcapital gains\b/i, 'capital_gains'],
    [/\bvested?\b/i, 'vesting'],
    [/\btake-home( pay)?\b/i, 'take_home'], [/\bpayroll deferrals?\b/i, 'payroll_deferral'],
    [/\b59½/, 'age_59_half'], [/\bRule of 55\b/i, 'rule_of_55'],
    [/\bRoth conversion ladder\b/i, 'roth_conversion_ladder'], [/\b72\(t\)/, 'sepp_72t'],
    [/\brequired (minimum )?(withdrawals|distributions?)\b/i, 'rmd'],
    [/\bMedicare\b/, 'medicare'], [/\bSocial Security\b/, 'social_security'],
    [/\btoday['’]s money\b/i, 'todays_money'],
    [/\bsavings rate\b/i, 'savings_rate'],
    [/\bcoast number\b/i, 'coast_number'], [/\bpoint you could stop\b/i, 'coast_number'],
    [/\bcompounding\b/i, 'compounding'],
  ]

  const used = new Set()
  let nodes = [text]

  for (const [re, id] of patterns) {
    if (used.has(id) || !glossary[id]) continue
    let done = false
    nodes = nodes.flatMap((node) => {
      if (done || typeof node !== 'string') return [node]
      const m = node.match(re)
      if (!m) return [node]
      done = true
      used.add(id)
      const i = m.index
      return [
        node.slice(0, i),
        <Term key={`${id}-${i}`} id={id} glossary={glossary}>{m[0]}</Term>,
        node.slice(i + m[0].length),
      ]
    })
  }

  return <>{nodes.map((n, i) => (typeof n === 'string' ? <span key={i}>{n}</span> : n))}</>
}
