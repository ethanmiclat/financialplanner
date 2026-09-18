import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Icon from './Icon'
import { Button, Field, MoneyInput, Toast, Toggle } from './ui'
import { ACCOUNT_ICONS, ACCOUNT_LABELS, money } from '../lib/format'
import { api } from '../lib/api'
import { LogContext } from '../lib/logContext'
import { notifyDataChanged } from '../lib/useApi'

/** Four things that happen to money. Each names itself the way you'd say it out
 *  loud, so there's no need to know what "contribution" or "principal" means. */
const KINDS = [
  { id: 'add', label: 'I added money', sub: 'a deposit or contribution', icon: 'plus', on: 'account' },
  { id: 'pay', label: 'I paid a debt', sub: 'toward a card or loan', icon: 'creditCard', on: 'debt' },
  { id: 'withdraw', label: 'I took money out', sub: 'spent or moved it', icon: 'minus', on: 'account' },
  { id: 'set_balance', label: 'A balance changed', sub: 'check a statement', icon: 'refresh', on: 'both' },
  // Only offered when some account actually has cash waiting to be invested.
  { id: 'invest', label: 'I invested cash', sub: 'bought a fund with it', icon: 'trending', on: 'idle' },
]
const AMOUNT_LABEL = {
  add: 'How much did you add?',
  pay: 'How much did you pay?',
  withdraw: 'How much came out?',
  set_balance: 'What is the balance now?',
  invest: 'How much did you invest?',
}
// Rounded to cents: balances minus fund values leave float dust (333.33000000000004).
const idleOf = (a) => (a.type !== 'cash' ? Math.round((a.uninvested_cash || 0) * 100) / 100 : 0)
const num = (v) => {
  const n = parseFloat(String(v).replace(/[^0-9.]/g, ''))
  return Number.isFinite(n) ? n : null
}
const nameOf = (t) => t.nickname || t.name || ACCOUNT_LABELS[t.type]

/** Tiles for a single choice, as real radio inputs so arrow keys and screen
 *  readers treat them as one group. */
function Choice({ name, checked, onChange, children, className = '' }) {
  return (
    <label className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors duration-200 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-brand ${
      checked ? 'border-brand-border bg-brand-soft' : 'border-line-strong hover:bg-surface-sunken'
    } ${className}`}>
      <input type="radio" name={name} checked={checked} onChange={onChange} className="sr-only" />
      {children}
    </label>
  )
}

function Sheet({ preset, onClose, onSaved }) {
  const [targets, setTargets] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [kind, setKind] = useState(preset.kind || null)
  const [targetKey, setTargetKey] = useState(null)       // 'account:<id>' | 'debt:<id>'
  const [amount, setAmount] = useState(preset.amount ? String(Math.round(preset.amount * 100) / 100) : '')
  const [counts, setCounts] = useState(true)
  const [invested, setInvested] = useState(true)
  const [fund, setFund] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const headingRef = useRef(null)
  const amountRef = useRef(null)

  useEffect(() => {
    Promise.all([api.accounts(), api.debts()])
      .then(([accounts, debts]) => {
        setTargets({ accounts, debts })
        // Resolve the preset to one concrete account or debt, if it names one.
        const acct = accounts.find((a) => a.id === preset.accountId)
          || (preset.accountType && preset.kind === 'invest' && accounts.find((a) => a.type === preset.accountType && idleOf(a) > 1))
          || (preset.accountType && accounts.find((a) => a.type === preset.accountType))
        const debt = debts.find((d) => d.id === preset.debtId)
          || (preset.debtName && debts.find((d) => d.name === preset.debtName))
        if (debt && (preset.kind === 'pay' || preset.kind === 'set_balance')) setTargetKey(`debt:${debt.id}`)
        else if (acct) {
          setTargetKey(`account:${acct.id}`)
          if (preset.kind === 'invest' && !preset.amount && idleOf(acct) > 0) setAmount(String(idleOf(acct)))
        }
      })
      .catch(setLoadError)
  }, [preset])

  // Focus the heading on open, close on Escape, and don't let the page behind scroll.
  useEffect(() => {
    headingRef.current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = prev }
  }, [onClose])

  const kindDef = KINDS.find((k) => k.id === kind)
  const anyIdle = targets?.accounts.some((a) => idleOf(a) > 1)
  const kinds = KINDS.filter((k) => k.id !== 'invest' || anyIdle || kind === 'invest')
  const options = useMemo(() => {
    if (!targets || !kindDef) return []
    const accts = targets.accounts.map((a) => ({ key: `account:${a.id}`, kind: 'account', item: a }))
    const debts = targets.debts.map((d) => ({ key: `debt:${d.id}`, kind: 'debt', item: d }))
    if (kindDef.on === 'account') return accts
    if (kindDef.on === 'debt') return debts.filter((d) => d.item.balance > 0)
    if (kindDef.on === 'idle') return accts.filter((a) => idleOf(a.item) > 1)
    return [...accts, ...debts]
  }, [targets, kindDef])
  const target = options.find((o) => o.key === targetKey) || null

  function pickKind(id) {
    setKind(id)
    setError(null)
    // Keep the chosen account if the new kind still applies to it.
    const def = KINDS.find((k) => k.id === id)
    if (target && def.on !== 'both' && def.on !== target.kind) setTargetKey(null)
    if (id === 'invest' && target && idleOf(target.item) <= 1) setTargetKey(null)
  }
  function pickTarget(key) {
    setTargetKey(key)
    // "All of it" is almost always the answer, so start there.
    const picked = options.find((o) => o.key === key)
    if (kind === 'invest' && picked) setAmount(String(idleOf(picked.item)))
    setError(null)
    setTimeout(() => amountRef.current?.focus(), 0)
  }

  const value = num(amount)
  const idle = target ? idleOf(target.item) : 0
  const before = kind === 'invest' ? idle : target?.item.balance ?? 0
  const needsFund = kind === 'invest' && target && !(target.item.holdings?.length)
  const after = value == null ? null
    : kind === 'invest' ? idle - value
    : kind === 'add' ? before + value
    : kind === 'withdraw' ? before - value
    : kind === 'pay' ? Math.max(0, before - value)
    : value
  const tooMuch = (kind === 'withdraw' || kind === 'invest') && value != null && value > before + 0.005
  const isInvestAcct = target?.kind === 'account' && target.item.type !== 'cash'
  const valid = kind && target && value != null && (kind === 'set_balance' || value > 0) && !tooMuch && !(needsFund && !fund.trim())

  async function submit(e) {
    e.preventDefault()
    if (!valid) return
    setSaving(true)
    setError(null)
    try {
      const body = { kind, amount: value, [`${target.kind}_id`]: target.item.id }
      if (kind === 'add' && isInvestAcct) {
        body.counts_as_contribution = counts
        body.invested = invested
      }
      if (kind === 'invest' && fund.trim()) body.fund = fund.trim()
      const result = await api.logActivity(body)
      onSaved(result, { name: nameOf(target.item), after, target: target.kind, kind, amount: value })
    } catch (err) {
      setError(err)
      setSaving(false)
    }
  }

  const stepNo = (n) => (
    <span className="tabular grid size-6 shrink-0 place-items-center rounded-full bg-brand text-xs font-bold text-on-brand" aria-hidden="true">{n}</span>
  )

  return (
    <div className="fixed inset-0 z-60 flex items-end justify-center bg-black/50 sm:items-center sm:p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="log-title"
        onSubmit={submit}
        className="flex max-h-[92dvh] w-full max-w-lg flex-col rounded-t-2xl bg-surface shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center gap-3 border-b border-line px-5 py-3">
          <h2 id="log-title" ref={headingRef} tabIndex={-1} className="flex-1 text-lg font-bold tracking-tight text-ink outline-none">
            Log an update
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className="grid size-11 cursor-pointer place-items-center rounded-xl text-ink-soft hover:bg-surface-sunken">
            <Icon name="close" className="size-5" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          {/* 1 — what happened */}
          <fieldset>
            <legend className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">{stepNo(1)} What happened?</legend>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {kinds.map((k) => (
                <Choice key={k.id} name="log-kind" checked={kind === k.id} onChange={() => pickKind(k.id)} className="flex-col items-start gap-1">
                  <Icon name={k.icon} className={`size-5 ${kind === k.id ? 'text-brand' : 'text-ink-soft'}`} />
                  <span className={`text-sm font-bold ${kind === k.id ? 'text-brand' : 'text-ink'}`}>{k.label}</span>
                  <span className="text-xs text-ink-faint">{k.sub}</span>
                </Choice>
              ))}
            </div>
          </fieldset>

          {/* 2 — where */}
          {kind && (
            <fieldset>
              <legend className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">{stepNo(2)} {kindDef.on === 'debt' ? 'Which debt?' : kindDef.on === 'idle' ? 'Where is the cash?' : 'Which account?'}</legend>
              {loadError && <p role="alert" className="mt-2 text-sm text-alert">{loadError.message}</p>}
              {!targets && !loadError && <div className="mt-2 h-28 animate-pulse rounded-xl bg-surface-sunken" />}
              {targets && options.length === 0 && (
                <p className="mt-2 rounded-xl bg-surface-sunken px-4 py-3 text-sm text-ink-soft">
                  {kindDef.on === 'debt' ? 'Nothing owed on file — every debt is paid off.' : 'No accounts yet. Add one on the Accounts page first.'}
                </p>
              )}
              <div className="mt-2 space-y-2">
                {options.map((o) => (
                  <Choice key={o.key} name="log-target" checked={targetKey === o.key} onChange={() => pickTarget(o.key)}>
                    <span className={`grid size-9 shrink-0 place-items-center rounded-lg ${o.kind === 'debt' ? 'bg-alert-soft text-alert' : 'bg-brand-soft text-brand'}`}>
                      <Icon name={o.kind === 'debt' ? 'creditCard' : ACCOUNT_ICONS[o.item.type]} className="size-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold text-ink">{nameOf(o.item)}</span>
                      <span className="block text-xs text-ink-faint">{o.kind === 'debt' ? 'You owe' : ACCOUNT_LABELS[o.item.type]}</span>
                    </span>
                    {kind === 'invest' ? (
                      <span className="shrink-0 text-right">
                        <span className="tabular block font-bold text-ink">{money(idleOf(o.item))}</span>
                        <span className="block text-xs text-ink-faint">not invested</span>
                      </span>
                    ) : (
                      <span className="tabular shrink-0 font-bold text-ink">{money(o.item.balance)}</span>
                    )}
                    {targetKey === o.key && <Icon name="check" className="size-5 shrink-0 text-brand" />}
                  </Choice>
                ))}
              </div>
            </fieldset>
          )}

          {/* 3 — how much */}
          {target && (
            <div className="space-y-3">
              <Field label={<span className="flex items-center gap-2">{stepNo(3)} {AMOUNT_LABEL[kind]}</span>}
                error={tooMuch ? (kind === 'invest'
                  ? `Only ${money(before, { cents: true })} in ${nameOf(target.item)} is uninvested.`
                  : `There's only ${money(before, { cents: true })} in ${nameOf(target.item)}.`) : null}>
                {(props) => (
                  <MoneyInput {...props} ref={amountRef} value={amount} placeholder="0" autoComplete="off"
                    onChange={(e) => setAmount(e.target.value)} />
                )}
              </Field>

              {/* Shortcuts for the amounts people most often mean. */}
              <div className="flex flex-wrap gap-2">
                {preset.amount > 0 && kind !== 'set_balance' && kind !== 'invest' && (
                  <button type="button" onClick={() => setAmount(String(Math.round(preset.amount * 100) / 100))}
                    className="min-h-11 cursor-pointer rounded-full border border-brand-border bg-brand-soft px-3 text-sm font-semibold text-brand">
                    {money(preset.amount)} · what this step needs
                  </button>
                )}
                {kind === 'invest' && idle > 0 && (
                  <button type="button" onClick={() => setAmount(String(idle))}
                    className="min-h-11 cursor-pointer rounded-full border border-line-strong px-3 text-sm font-semibold text-ink-soft hover:bg-surface-sunken">
                    All of it · {money(idle)}
                  </button>
                )}
                {kind === 'pay' && before > 0 && (
                  <button type="button" onClick={() => setAmount(String(before))}
                    className="min-h-11 cursor-pointer rounded-full border border-line-strong px-3 text-sm font-semibold text-ink-soft hover:bg-surface-sunken">
                    Paid it all · {money(before)}
                  </button>
                )}
              </div>

              {kind === 'add' && isInvestAcct && (
                <div className="space-y-3 rounded-xl bg-surface-sunken p-3">
                  <Toggle checked={counts} onChange={setCounts}
                    label="Counts toward this year's limit"
                    hint="Turn off for a rollover or a transfer from another retirement account." />
                  {target.item.holdings?.length > 0 && (
                    <Toggle checked={invested} onChange={setInvested}
                      label="It's invested in a fund"
                      hint="Turn off if it's still sitting as cash in the account." />
                  )}
                </div>
              )}

              {kind === 'invest' && (needsFund ? (
                <Field label="Which fund did you buy?" hint="The ticker or name, like VTI or a target-date fund.">
                  {(props) => (
                    <input {...props} value={fund} onChange={(e) => setFund(e.target.value)} placeholder="VTI" autoComplete="off"
                      className="w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 text-base text-ink placeholder:text-ink-faint focus:border-brand" />
                  )}
                </Field>
              ) : target.item.holdings.length > 1 ? (
                <Field label="Which fund did you buy?">
                  {(props) => (
                    <select {...props} value={fund || target.item.holdings[0].symbol} onChange={(e) => setFund(e.target.value)}
                      className="w-full min-h-12 cursor-pointer rounded-xl border border-line-strong bg-surface px-3 text-base text-ink focus:border-brand">
                      {target.item.holdings.map((h) => <option key={h.id} value={h.symbol}>{h.symbol}{h.name ? ` — ${h.name}` : ''}</option>)}
                    </select>
                  )}
                </Field>
              ) : (
                <p className="text-sm text-ink-soft">
                  Goes into <span className="font-semibold text-ink">{target.item.holdings[0].name || target.item.holdings[0].symbol}</span>, the fund this account holds.
                </p>
              ))}

              {/* The result before you commit to it. */}
              {after != null && (
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border border-line px-4 py-3 text-[0.9375rem]" aria-live="polite">
                  <span className="font-semibold text-ink">{kind === 'invest' ? 'Not invested' : nameOf(target.item)}</span>
                  <span className="tabular text-ink-faint line-through decoration-1">{money(before)}</span>
                  <Icon name="arrowRight" className="size-4 text-ink-faint" />
                  <span className={`tabular font-bold ${tooMuch ? 'text-alert' : 'text-brand'}`}>{money(Math.max(0, after))}</span>
                  {kind === 'invest' && after <= 0.005 && <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand">all working</span>}
                  {kind === 'pay' && after <= 0 && <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand">paid off</span>}
                </p>
              )}
            </div>
          )}

          {error && (
            <p role="alert" className="flex items-start gap-2 text-sm font-medium text-alert">
              <Icon name="alert" className="mt-0.5 size-4 shrink-0" />{error.message} Nothing was saved.
            </p>
          )}
        </div>

        <div className="flex flex-col gap-2 border-t border-line px-5 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:flex-row-reverse">
          <Button type="submit" loading={saving} disabled={!valid} className="sm:flex-1">Save update</Button>
          <Button type="button" variant="ghost" onClick={onClose} className="sm:flex-1">Cancel</Button>
        </div>
      </form>
    </div>
  )
}

/** Owns the sheet and its confirmation, so any page can open it with a preset and
 *  every page refreshes when it saves. */
export function LogProvider({ children }) {
  const [preset, setPreset] = useState(null)
  const [toast, setToast] = useState(null)
  const returnFocus = useRef(null)

  const openLog = useCallback((p = {}) => {
    returnFocus.current = document.activeElement
    setPreset(p)
  }, [])
  const close = useCallback(() => {
    setPreset(null)
    setTimeout(() => returnFocus.current?.focus?.(), 0)
  }, [])
  const dismiss = useCallback(() => setToast(null), [])

  async function undo(id) {
    try {
      await api.undoActivity(id)
      notifyDataChanged()
      setToast({ message: 'Undone — back to how it was.' })
    } catch (err) {
      setToast({ message: err.message, tone: 'error' })
    }
  }

  function saved(result, { name, after, target, kind, amount }) {
    close()
    notifyDataChanged()
    const handled = result.effect.handled
    const status = kind === 'invest' ? `${money(amount)} invested in ${name}`
      : target === 'debt' && after <= 0 ? `${name} is paid off` : `${name} is now ${money(Math.max(0, after))}`
    const extra = handled.length
      ? ` · step ${handled.map((h) => h.step).join(' and ')} handled`
      : ''
    setToast({ message: `${status}${extra}`, action: { label: 'Undo', onClick: () => undo(result.entry.id) } })
  }

  return (
    <LogContext.Provider value={{ openLog }}>
      {children}
      {preset && <Sheet preset={preset} onClose={close} onSaved={saved} />}
      <Toast message={toast?.message} tone={toast?.tone} action={toast?.action} onDismiss={dismiss} />
    </LogContext.Provider>
  )
}
