import { useEffect, useId, useState } from 'react'
import Icon from './Icon'

/** `tone` rather than a passed-in bg- class: two utilities of equal specificity
 *  resolve by CSS source order, not by the order they appear in the class string,
 *  so `<Card className="bg-brand-soft">` silently lost to the base `bg-surface`. */
const CARD_TONES = {
  surface: 'border-line bg-surface',
  sunken: 'border-line bg-surface-sunken',
  brand: 'border-brand-border bg-brand-soft',
  alert: 'border-alert-border bg-alert-soft',
}

export function Card({ className = '', tone = 'surface', as: As = 'div', ...rest }) {
  return (
    <As
      className={`rounded-[--radius-card] border ${CARD_TONES[tone]} ${className}`}
      {...rest}
    />
  )
}

export function Button({
  variant = 'primary', size = 'md', className = '', loading = false,
  children, icon, ...rest
}) {
  const variants = {
    // min-h-11 = 44px touch target on every variant, including on desktop.
    primary: 'bg-brand text-on-brand hover:bg-brand-hover disabled:bg-line-strong',
    secondary: 'bg-brand-soft text-brand hover:bg-brand-soft-hover border border-brand-border',
    ghost: 'text-ink-soft hover:bg-surface-sunken',
    danger: 'text-alert border border-alert-border hover:bg-alert-soft',
  }
  const sizes = { md: 'min-h-11 px-4 text-[0.9375rem]', sm: 'min-h-11 px-3 text-sm' }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading && (
        <span
          className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      )}
      {!loading && icon && <Icon name={icon} className="size-4" />}
      {children}
    </button>
  )
}

/** Progressive disclosure. Everything past the one-line decision is behind one of
 *  these, so a first-time reader is never handed three layers at once. */
export function Disclosure({ label, children, tone = 'default', defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const id = useId()
  const tones = {
    default: 'text-brand',
    quiet: 'text-ink-soft',
  }
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={id}
        className={`flex min-h-11 w-full items-start gap-1.5 text-left text-[0.9375rem] font-semibold cursor-pointer ${tones[tone]}`}
      >
        <Icon
          name="chevronDown"
          className={`mt-[0.3rem] size-4 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
        <span className="py-1.5">{label}</span>
      </button>
      {open && <div id={id} className="pb-1">{children}</div>}
    </div>
  )
}

export function Field({ label, hint, error, children, required }) {
  const id = useId()
  const hintId = `${id}-hint`
  const errId = `${id}-err`
  return (
    <div>
      <label htmlFor={id} className="block text-[0.9375rem] font-semibold text-ink">
        {label}
        {required && <span className="text-alert" aria-hidden="true"> *</span>}
        {required && <span className="sr-only"> (required)</span>}
      </label>
      {hint && (
        <p id={hintId} className="mt-0.5 text-sm text-ink-soft">{hint}</p>
      )}
      <div className="mt-1.5">
        {children({
          id,
          'aria-describedby': [hint && hintId, error && errId].filter(Boolean).join(' ') || undefined,
          'aria-invalid': error ? true : undefined,
        })}
      </div>
      {error && (
        <p id={errId} role="alert" className="mt-1.5 flex items-start gap-1.5 text-sm font-medium text-alert">
          <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}

/** Inputs are 48px tall and 16px text — under 16px, iOS Safari zooms the page on
 *  focus and the layout jumps. */
const inputBase =
  'w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 text-base text-ink placeholder:text-ink-faint focus:border-brand'

export function TextInput({ className = '', ...rest }) {
  return <input className={`${inputBase} ${className}`} {...rest} />
}

/** Fixed rows rather than autosize: a box that grows as you type shifts everything
 *  below it, and on a phone that's the submit button moving out from under a thumb. */
export function TextArea({ className = '', rows = 3, ...rest }) {
  return (
    <textarea
      rows={rows}
      className={`${inputBase} resize-y py-3 leading-relaxed ${className}`}
      {...rest}
    />
  )
}

export function MoneyInput({ className = '', ...rest }) {
  return (
    <div className="relative">
      <span
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base text-ink-soft"
        aria-hidden="true"
      >
        $
      </span>
      <input
        type="text"
        inputMode="decimal"
        className={`${inputBase} tabular pl-7 ${className}`}
        {...rest}
      />
    </div>
  )
}

/** Rates are typed as percentages ("7"), not fractions ("0.07"). */
export function PercentInput({ className = '', ...rest }) {
  return (
    <div className="relative">
      <input
        type="text"
        inputMode="decimal"
        className={`${inputBase} tabular pr-8 ${className}`}
        {...rest}
      />
      <span
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-base text-ink-soft"
        aria-hidden="true"
      >
        %
      </span>
    </div>
  )
}

export function Select({ className = '', children, ...rest }) {
  return (
    <select className={`${inputBase} cursor-pointer pr-8 ${className}`} {...rest}>
      {children}
    </select>
  )
}

export function Toggle({ checked, onChange, label, hint }) {
  return (
    <label className="flex min-h-11 cursor-pointer items-start gap-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 size-5 shrink-0 cursor-pointer accent-brand"
      />
      <span>
        <span className="block text-[0.9375rem] font-medium text-ink">{label}</span>
        {hint && <span className="block text-sm text-ink-soft">{hint}</span>}
      </span>
    </label>
  )
}

/** In-page sectioning. A real tablist: arrow keys move between tabs, the active
 *  one is marked by weight, background and aria-selected — never colour alone. */
export function SegmentedTabs({ tabs, value, onChange, label }) {
  const id = useId()
  function onKey(e, i) {
    const dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!dir) return
    e.preventDefault()
    const next = tabs[(i + dir + tabs.length) % tabs.length]
    onChange(next.id)
    document.getElementById(`${id}-${next.id}`)?.focus()
  }
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 rounded-xl bg-surface-sunken p-1">
      {tabs.map((t, i) => {
        const active = t.id === value
        return (
          <button
            key={t.id}
            id={`${id}-${t.id}`}
            role="tab"
            type="button"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => onKey(e, i)}
            className={`flex min-h-11 flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 text-sm font-semibold transition-colors duration-200 ${
              active ? 'bg-surface text-ink shadow-sm' : 'text-ink-soft hover:text-ink'
            }`}
          >
            {t.icon && <Icon name={t.icon} className="size-4 shrink-0" />}
            <span className="truncate">{t.label}</span>
            {t.count != null && (
              <span className={`tabular rounded-full px-1.5 text-xs ${active ? 'bg-brand-soft text-brand' : 'bg-surface text-ink-faint'}`}>
                {t.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

export function EmptyState({ icon = 'info', title, children, action }) {
  return (
    <Card className="px-6 py-10 text-center">
      <Icon name={icon} className="mx-auto size-8 text-ink-faint" />
      <h3 className="mt-3 font-semibold text-ink">{title}</h3>
      <p className="mx-auto mt-1 max-w-sm text-[0.9375rem] text-ink-soft">{children}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </Card>
  )
}

/** Skeletons rather than a spinner: the boxes reserve the real layout, so nothing
 *  shifts when the data lands. */
/** A horizontally scrolling region that a keyboard user can actually reach and
 *  scroll with the arrow keys. A bare `overflow-x-auto` div traps content for anyone
 *  not using a mouse or a touchscreen (WCAG 2.1.1). */
export function ScrollX({ label, className = '', children }) {
  return (
    <div
      tabIndex={0}
      role="group"
      aria-label={label}
      className={`overflow-x-auto focus-visible:outline-3 ${className}`}
    >
      {children}
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-lg bg-surface-sunken ${className}`} />
}

export function ErrorState({ error, onRetry }) {
  return (
    <Card tone="alert" className="p-5">
      <div className="flex items-start gap-3">
        <Icon name="alert" className="mt-0.5 size-5 shrink-0 text-alert" />
        <div>
          <h3 className="font-semibold text-ink">We couldn’t load this</h3>
          <p className="mt-1 text-[0.9375rem] text-ink-soft">
            {error?.message || 'Something went wrong.'} Make sure the backend is running
            on port 5001.
          </p>
          {onRetry && (
            <Button variant="secondary" size="sm" icon="refresh" className="mt-3" onClick={onRetry}>
              Try again
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

/** `action` puts one button in the toast — Undo, mostly — and holds the toast
 *  longer so there's time to reach it. `tone="error"` swaps the tick for a warning. */
export function Toast({ message, onDismiss, duration, action, tone = 'success' }) {
  const hold = duration ?? (action ? 7000 : 4000)
  // Auto-dismiss, so a confirmation doesn't sit on screen indefinitely. The timer is
  // keyed to the message so a second toast restarts it rather than inheriting the
  // first one's remaining time.
  useEffect(() => {
    if (!message) return
    const t = setTimeout(onDismiss, hold)
    return () => clearTimeout(t)
  }, [message, hold, onDismiss])

  if (!message) return null
  return (
    // pointer-events-none on the wrapper: a floating confirmation must never
    // intercept taps meant for the UI underneath it. Sits above the mobile
    // bottom bar and the Log button.
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-4 bottom-36 z-50 mx-auto flex max-w-sm items-center gap-2 rounded-xl bg-toast py-2 pl-4 pr-2 text-[0.9375rem] font-medium text-on-toast shadow-xl lg:bottom-6"
    >
      <Icon name={tone === 'error' ? 'alert' : 'check'} className={`size-5 shrink-0 ${tone === 'error' ? 'text-toast-alert' : 'text-toast-ok'}`} />
      <span className="flex-1 py-1">{message}</span>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="pointer-events-auto min-h-11 cursor-pointer rounded-lg px-3 font-bold text-toast-ok hover:bg-on-toast/10"
        >
          {action.label}
        </button>
      )}
      <button
        type="button"
        onClick={onDismiss}
        className="pointer-events-auto grid min-h-11 min-w-11 cursor-pointer place-items-center rounded-lg text-on-toast/80 hover:bg-on-toast/10 hover:text-on-toast"
        aria-label="Dismiss"
      >
        <Icon name="close" className="size-4" />
      </button>
    </div>
  )
}
