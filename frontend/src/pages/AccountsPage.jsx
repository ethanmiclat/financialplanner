import { useCallback, useState } from 'react'
import Icon from '../components/Icon'
import ProgressChart from '../components/ProgressChart'
import Term from '../components/Term'
import {
  Button, Card, EmptyState, ErrorState, Field, MoneyInput, SegmentedTabs, Select, Skeleton, Toast, Toggle,
} from '../components/ui'
import { StackedBar } from '../components/viz'
import { ACCOUNT_ICONS, ACCOUNT_LABELS, money, percent } from '../lib/format'
import { api } from '../lib/api'
import { notifyDataChanged, useApi } from '../lib/useApi'
import { useLog } from '../lib/logContext'

const TYPE_HELP = {
  '401k': 'The retirement account through your job.',
  ira: 'A retirement account you opened yourself.',
  hsa: 'A health savings account, paired with a high-deductible health plan.',
  taxable: 'A regular investment account with no special tax rules.',
  cash: 'Checking or savings — where your emergency fund lives.',
}
const TYPE_ICON = ACCOUNT_ICONS
const TYPE_TONE = { '401k': 'brand', ira: 'bright', hsa: 'ink', taxable: 'faint', cash: 'line' }
const HIGH_APR = 0.075

const num = (v) => {
  const n = parseFloat(String(v).replace(/[^0-9.-]/g, ''))
  return Number.isFinite(n) ? n : 0
}

/** The picture first: what you own, what you owe, and how it's split. */
function Overview({ accounts, debts }) {
  const { openLog } = useLog()
  const assets = accounts.reduce((s, a) => s + a.balance, 0)
  const owed = debts.reduce((s, d) => s + d.balance, 0)
  const byType = {}
  for (const a of accounts) byType[a.type] = (byType[a.type] || 0) + a.balance
  const segments = Object.entries(byType)
    .sort((a, b) => b[1] - a[1])
    .map(([type, value]) => ({ label: ACCOUNT_LABELS[type], value, text: money(value), tone: TYPE_TONE[type] }))
  const idle = accounts.reduce((s, a) => s + (a.uninvested_cash || 0), 0)

  return (
    <Card className="p-5">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">You own</p>
          <p className="tabular mt-1 text-xl font-bold leading-tight text-ink">{money(assets)}</p>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">You owe</p>
          <p className={`tabular mt-1 text-xl font-bold leading-tight ${owed > 0 ? 'text-alert' : 'text-ink'}`}>{money(owed)}</p>
        </div>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-ink-faint">Net</p>
          <p className={`tabular mt-1 text-xl font-bold leading-tight ${assets - owed < 0 ? 'text-alert' : 'text-brand'}`}>
            {money(assets - owed)}
          </p>
        </div>
      </div>
      {segments.length > 0 && (
        <div className="mt-4">
          <StackedBar segments={segments} label={`Balances by account type: ${segments.map((s) => `${s.label} ${s.text}`).join(', ')}`} />
        </div>
      )}
      {idle > 1 && (
        <div className="mt-3 rounded-lg bg-alert-soft px-3 py-2.5 text-sm text-alert">
          <p className="flex items-start gap-2">
            <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
            <span>
              <span className="tabular font-bold">{money(idle)}</span> is inside investment accounts but not invested.
              <span className="text-ink-soft"> Cash in there barely grows until it buys a fund.</span>
            </span>
          </p>
          <Button variant="secondary" size="sm" icon="trending" className="mt-2" onClick={() => openLog({ kind: 'invest' })}>
            I invested it
          </Button>
        </div>
      )}
    </Card>
  )
}

function AccountForm({ onCancel, onSaved }) {
  const [type, setType] = useState('cash')
  const [form, setForm] = useState({
    nickname: '', balance: '', contributions_ytd: '',
    employer_match_rate: '', employer_match_limit_pct: '',
    hdhp_enrolled: false, hsa_coverage: 'self_only',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }))

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createAccount({
        type,
        nickname: form.nickname || ACCOUNT_LABELS[type],
        balance: num(form.balance),
        contributions_ytd: type === 'cash' ? 0 : num(form.contributions_ytd),
        employer_match_rate: type === '401k' ? num(form.employer_match_rate) / 100 : 0,
        employer_match_limit_pct: type === '401k' ? num(form.employer_match_limit_pct) / 100 : 0,
        hdhp_enrolled: type === 'hsa' ? form.hdhp_enrolled : false,
        hsa_coverage: form.hsa_coverage,
      })
      onSaved(`${ACCOUNT_LABELS[type]} added`)
    } catch (err) {
      setError(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card as="form" onSubmit={submit} className="space-y-4 p-5">
      <h2 className="font-bold tracking-tight text-ink">Add an account</h2>

      {/* Pick the kind with a button per type — an icon and a word beat a dropdown
          for five options, and the help line explains the one you chose. */}
      <fieldset>
        <legend className="text-[0.9375rem] font-semibold text-ink">What kind of account is it?</legend>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
          {Object.entries(ACCOUNT_LABELS).map(([v, l]) => (
            <label key={v} className={`flex min-h-16 cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border px-2 py-2 text-center text-sm font-semibold transition-colors ${
              type === v ? 'border-brand-border bg-brand-soft text-brand' : 'border-line-strong text-ink-soft hover:bg-surface-sunken'
            }`}>
              <input type="radio" name="type" value={v} checked={type === v} onChange={() => setType(v)} className="sr-only" />
              <Icon name={TYPE_ICON[v]} className="size-5" />
              {l}
            </label>
          ))}
        </div>
        <p className="mt-2 text-sm text-ink-soft">{TYPE_HELP[type]}</p>
      </fieldset>

      <Field label="Give it a name" hint="Something you'll recognize, like “Fidelity 401(k)”.">
        {(props) => (
          <input {...props} value={form.nickname} onChange={(e) => set('nickname')(e.target.value)}
            placeholder={ACCOUNT_LABELS[type]}
            className="w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 text-base text-ink placeholder:text-ink-faint focus:border-brand" />
        )}
      </Field>

      <Field label="How much is in it right now?" required>
        {(props) => (
          <MoneyInput {...props} value={form.balance} onChange={(e) => set('balance')(e.target.value)} placeholder="0" />
        )}
      </Field>

      {type !== 'cash' && (
        <Field label="How much have you put in this year?" hint="Just your own contributions since January.">
          {(props) => (
            <MoneyInput {...props} value={form.contributions_ytd} onChange={(e) => set('contributions_ytd')(e.target.value)} placeholder="0" />
          )}
        </Field>
      )}

      {type === '401k' && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Employer matches" hint="Often 50%. Enter 0 if unsure.">
            {(props) => (
              <div className="relative">
                <input {...props} type="text" inputMode="decimal" value={form.employer_match_rate}
                  onChange={(e) => set('employer_match_rate')(e.target.value)} placeholder="50"
                  className="tabular w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 pr-8 text-base text-ink focus:border-brand" />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft">%</span>
              </div>
            )}
          </Field>
          <Field label="Up to this share of pay" hint="Often 6%.">
            {(props) => (
              <div className="relative">
                <input {...props} type="text" inputMode="decimal" value={form.employer_match_limit_pct}
                  onChange={(e) => set('employer_match_limit_pct')(e.target.value)} placeholder="6"
                  className="tabular w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 pr-8 text-base text-ink focus:border-brand" />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft">%</span>
              </div>
            )}
          </Field>
        </div>
      )}

      {type === 'hsa' && (
        <>
          <Toggle checked={form.hdhp_enrolled} onChange={set('hdhp_enrolled')}
            label="I'm on a high-deductible health plan"
            hint="Required to put money into an HSA." />
          <Field label="Who does your health plan cover?">
            {(props) => (
              <Select {...props} value={form.hsa_coverage} onChange={(e) => set('hsa_coverage')(e.target.value)}>
                <option value="self_only">Just me</option>
                <option value="family">Me and family</option>
              </Select>
            )}
          </Field>
        </>
      )}

      {error && (
        <p role="alert" className="flex items-start gap-2 text-sm font-medium text-alert">
          <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
          {error.message} Nothing was saved — try again.
        </p>
      )}

      <div className="flex flex-col gap-2 pt-1 sm:flex-row-reverse">
        <Button type="submit" loading={saving} className="sm:flex-1">Save account</Button>
        <Button type="button" variant="ghost" onClick={onCancel} className="sm:flex-1">Cancel</Button>
      </div>
    </Card>
  )
}

function DebtForm({ onCancel, onSaved }) {
  const [form, setForm] = useState({ name: '', balance: '', apr: '', minimum_payment: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }))
  async function submit(e) {
    e.preventDefault()
    setSaving(true); setError(null)
    try {
      await api.createDebt({ name: form.name || 'Loan', balance: num(form.balance), apr: num(form.apr) / 100, minimum_payment: num(form.minimum_payment) })
      onSaved('Debt added')
    } catch (err) { setError(err) } finally { setSaving(false) }
  }
  return (
    <Card as="form" onSubmit={submit} className="space-y-4 p-5">
      <h2 className="font-bold tracking-tight text-ink">Add something you owe</h2>
      <Field label="What is it?" hint="“Credit card”, “Student loan”, “Car”.">
        {(props) => (
          <input {...props} value={form.name} onChange={(e) => set('name')(e.target.value)} placeholder="Credit card"
            className="w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 text-base text-ink placeholder:text-ink-faint focus:border-brand" />
        )}
      </Field>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Balance" required>
          {(props) => <MoneyInput {...props} value={form.balance} onChange={(e) => set('balance')(e.target.value)} placeholder="0" />}
        </Field>
        <Field label="Interest rate" required hint="APR, from your statement.">
          {(props) => (
            <div className="relative">
              <input {...props} type="text" inputMode="decimal" value={form.apr} onChange={(e) => set('apr')(e.target.value)} placeholder="22"
                className="tabular w-full min-h-12 rounded-xl border border-line-strong bg-surface px-3 pr-8 text-base text-ink focus:border-brand" />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft">%</span>
            </div>
          )}
        </Field>
        <Field label="Minimum a month">
          {(props) => <MoneyInput {...props} value={form.minimum_payment} onChange={(e) => set('minimum_payment')(e.target.value)} placeholder="0" />}
        </Field>
      </div>
      {error && (
        <p role="alert" className="flex items-start gap-2 text-sm font-medium text-alert">
          <Icon name="alert" className="mt-0.5 size-4 shrink-0" />{error.message}
        </p>
      )}
      <div className="flex flex-col gap-2 pt-1 sm:flex-row-reverse">
        <Button type="submit" loading={saving} className="sm:flex-1">Save</Button>
        <Button type="button" variant="ghost" onClick={onCancel} className="sm:flex-1">Cancel</Button>
      </div>
    </Card>
  )
}

/** A row is a name, a kind and a number. The rest waits behind a tap. */
function AccountRow({ account, glossary, open, onToggle, onDelete }) {
  const { openLog } = useLog()
  const idle = account.uninvested_cash
  const hasDetail = account.type !== 'cash' || idle > 1
  return (
    <Card as="li" className={open ? 'ring-2 ring-brand-soft' : ''}>
      <button type="button" onClick={onToggle} aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-3 p-4 text-left">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand">
          <Icon name={TYPE_ICON[account.type]} className="size-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-bold text-ink">{account.nickname || ACCOUNT_LABELS[account.type]}</span>
          <span className="block text-sm text-ink-soft">{ACCOUNT_LABELS[account.type]}</span>
        </span>
        <span className="tabular shrink-0 text-lg font-bold text-ink">{money(account.balance)}</span>
        {idle > 1 && <Icon name="alert" className="size-4 shrink-0 text-alert" aria-label="Uninvested cash" />}
        <Icon name="chevronDown" className={`size-5 shrink-0 text-ink-faint transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-line px-4 pb-4">
          {hasDetail && (
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              {account.type !== 'cash' && (
                <div>
                  <dt className="text-ink-faint">Put in this year</dt>
                  <dd className="tabular font-semibold text-ink">{money(account.contributions_ytd)}</dd>
                </div>
              )}
              {account.type === '401k' && account.employer_match_rate > 0 && (
                <div>
                  <dt className="text-ink-faint">Employer match</dt>
                  <dd className="tabular font-semibold text-ink">
                    {percent(account.employer_match_rate)} up to {percent(account.employer_match_limit_pct)}
                  </dd>
                </div>
              )}
              {account.type === 'hsa' && (
                <div>
                  <dt className="text-ink-faint"><Term id="hdhp" glossary={glossary}>HDHP</Term></dt>
                  <dd className="font-semibold text-ink">{account.hdhp_enrolled ? 'Yes' : 'No'}</dd>
                </div>
              )}
            </dl>
          )}
          {idle > 1 && (
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg bg-alert-soft px-3 py-2 text-sm text-alert">
              <Icon name="alert" className="size-4 shrink-0" />
              <span className="flex-1"><span className="tabular font-bold">{money(idle)}</span> here is sitting as cash rather than invested.</span>
              <Button variant="secondary" size="sm" icon="trending" onClick={() => openLog({ kind: 'invest', accountId: account.id, amount: idle })}>
                I invested it
              </Button>
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" icon="plus" onClick={() => openLog({ kind: 'add', accountId: account.id })}>Add money</Button>
            <Button variant="ghost" size="sm" icon="minus" onClick={() => openLog({ kind: 'withdraw', accountId: account.id })}>Take out</Button>
            <Button variant="ghost" size="sm" icon="refresh" onClick={() => openLog({ kind: 'set_balance', accountId: account.id })}>Update balance</Button>
            <Button variant="danger" size="sm" icon="trash" onClick={() => onDelete(account)} className="ml-auto">Remove</Button>
          </div>
        </div>
      )}
    </Card>
  )
}

/** The rate is the whole story for a debt, so it's a chip colored against the line
 *  the plan draws — and the chip says which side it's on in words. */
function DebtRow({ debt, glossary, onDelete }) {
  const { openLog } = useLog()
  const hot = debt.apr > HIGH_APR
  const paid = debt.balance <= 0
  return (
    <Card as="li" className="p-4">
      <div className="flex items-center gap-3">
        <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${paid ? 'bg-brand-soft text-brand' : hot ? 'bg-alert-soft text-alert' : 'bg-surface-sunken text-ink-soft'}`}>
          <Icon name={paid ? 'check' : 'creditCard'} className="size-5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-bold text-ink">{debt.name}</span>
          {paid ? (
            <span className="mt-0.5 inline-flex rounded-full border border-brand-border bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand">Paid off</span>
          ) : (
            <span className={`mt-0.5 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold ${
              hot ? 'border-alert-border bg-alert-soft text-alert' : 'border-line bg-surface-sunken text-ink-soft'
            }`}>
              <span className="tabular">{percent(debt.apr, 1)}</span> <Term id="apr" glossary={glossary}>APR</Term>
              <span aria-hidden="true">·</span> {hot ? 'pay off first' : 'pay on schedule'}
            </span>
          )}
        </span>
        <span className="tabular shrink-0 font-bold text-ink">{money(debt.balance)}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {!paid && (
          <Button variant="secondary" size="sm" icon="check" onClick={() => openLog({ kind: 'pay', debtId: debt.id })}>Log a payment</Button>
        )}
        <Button variant="ghost" size="sm" icon="refresh" onClick={() => openLog({ kind: 'set_balance', debtId: debt.id })}>Update balance</Button>
        <Button variant="danger" size="sm" icon="trash" onClick={() => onDelete(debt)} className="ml-auto">
          <span className="sr-only">Remove {debt.name}</span>
        </Button>
      </div>
    </Card>
  )
}

const VERB = {
  add: { icon: 'plus', text: (e) => <>Added <b>{money(e.amount, { cents: e.amount % 1 !== 0 })}</b> to {e.target_name}</> },
  withdraw: { icon: 'minus', text: (e) => <>Took <b>{money(e.amount, { cents: e.amount % 1 !== 0 })}</b> out of {e.target_name}</> },
  pay: { icon: 'creditCard', text: (e) => <>Paid <b>{money(e.amount, { cents: e.amount % 1 !== 0 })}</b> on {e.target_name}</> },
  invest: { icon: 'trending', text: (e) => <>Invested <b>{money(e.amount, { cents: e.amount % 1 !== 0 })}</b> in {e.target_name}</> },
  new_year: { icon: 'calendar', text: (e) => <><b>{e.target_name}</b> started — this year's contributions reset to $0</> },
  set_balance: { icon: 'refresh', text: (e) => <>Set {e.target_name} to <b>{money(e.amount, { cents: e.amount % 1 !== 0 })}</b></> },
}
const when = (iso) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const days = Math.floor((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 864e5)
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  if (days === 0) return `Today, ${time}`
  if (days === 1) return `Yesterday, ${time}`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: d.getFullYear() === new Date().getFullYear() ? undefined : 'numeric' })
}

/** What you've logged, newest first. Undo is per entry; the server refuses one that
 *  a later entry has built on, and says so. */
function History({ entries, onUndo, undoing }) {
  const { openLog } = useLog()
  if (!entries.length) {
    return (
      <EmptyState icon="list" title="Nothing logged yet"
        action={<Button icon="plus" onClick={() => openLog()}>Log an update</Button>}>
        When you move money — a deposit, a payment, a withdrawal — log it here and the plan updates.
      </EmptyState>
    )
  }
  return (
    <Card as="ul" className="divide-y divide-line">
      {entries.map((e) => {
        const v = VERB[e.kind] || VERB.set_balance
        return (
          <li key={e.id} className="flex items-center gap-3 px-4 py-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-surface-sunken text-ink-soft">
              <Icon name={v.icon} className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="tabular block text-[0.9375rem] text-ink [&_b]:font-bold">{v.text(e)}</span>
              <span className="block text-xs text-ink-faint">{when(e.date)}{e.note ? ` · ${e.note}` : ''}</span>
            </span>
            {e.kind === 'new_year' ? (
              <span className="shrink-0 px-3 text-xs font-semibold text-ink-faint">Automatic</span>
            ) : (
              <Button variant="ghost" size="sm" loading={undoing === e.id} onClick={() => onUndo(e)}>
                Undo<span className="sr-only">: {e.kind} {e.target_name}</span>
              </Button>
            )}
          </li>
        )
      })}
    </Card>
  )
}

export default function AccountsPage({ glossary }) {
  const accounts = useApi(api.accounts, [])
  const debts = useApi(api.debts, [])
  const activity = useApi(api.activity, [])
  const history = useApi(api.history, [])
  const { openLog } = useLog()
  const [tab, setTab] = useState('accounts')
  const [undoing, setUndoing] = useState(null)
  const [adding, setAdding] = useState(null)      // 'account' | 'debt' | null
  const [openId, setOpenId] = useState(null)
  const [toast, setToast] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const dismissToast = useCallback(() => setToast(null), [])

  const refresh = (msg) => { setAdding(null); setToast({ message: msg }); accounts.reload(); debts.reload() }

  async function undo(entry) {
    setUndoing(entry.id)
    try {
      await api.undoActivity(entry.id)
      notifyDataChanged()
      setToast({ message: 'Undone — back to how it was.' })
    } catch (err) {
      setToast({ message: err.message, tone: 'error' })
    } finally {
      setUndoing(null)
    }
  }

  async function confirmDelete() {
    const target = confirming
    setConfirming(null)
    if (target.kind === 'account') await api.deleteAccount(target.item.id)
    else await api.deleteDebt(target.item.id)
    refresh('Removed')
  }

  if (accounts.loading || debts.loading) {
    return <div className="space-y-3"><Skeleton className="h-32 w-full" />{[0, 1].map((i) => <Skeleton key={i} className="h-20 w-full" />)}</div>
  }
  if (accounts.error) return <ErrorState error={accounts.error} onRetry={accounts.reload} />

  const list = accounts.data
  const owed = debts.data || []

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Your money</h1>

      <Overview accounts={list} debts={owed} />

      <Card className="p-5">
        <h2 className="mb-3 font-bold tracking-tight text-ink">Over time</h2>
        <ProgressChart history={history.data} />
      </Card>

      <SegmentedTabs
        label="Accounts and debts"
        value={tab}
        onChange={(t) => { setTab(t); setAdding(null) }}
        tabs={[
          { id: 'accounts', label: 'Accounts', icon: 'wallet', count: list.length },
          { id: 'debts', label: 'You owe', icon: 'creditCard', count: owed.filter((d) => d.balance > 0).length },
          { id: 'history', label: 'History', icon: 'clock' },
        ]}
      />

      {tab === 'accounts' && (
        <>
          {adding === 'account' ? (
            <AccountForm onCancel={() => setAdding(null)} onSaved={refresh} />
          ) : (
            <div className="flex flex-col gap-2 sm:flex-row">
              {list.length > 0 && (
                <Button icon="refresh" onClick={() => openLog()} className="w-full sm:w-auto">Log an update</Button>
              )}
              <Button variant={list.length ? 'secondary' : 'primary'} icon="plus" onClick={() => setAdding('account')} className="w-full sm:w-auto">Add an account</Button>
            </div>
          )}
          {list.length === 0 ? (
            <EmptyState icon="accounts" title="No accounts yet">
              Start with checking or savings — that's where your emergency fund is measured from.
            </EmptyState>
          ) : (
            <ul className="space-y-2">
              {list.map((a) => (
                <AccountRow key={a.id} account={a} glossary={glossary}
                  open={openId === a.id} onToggle={() => setOpenId((v) => (v === a.id ? null : a.id))}
                  onDelete={(item) => setConfirming({ kind: 'account', item })} />
              ))}
            </ul>
          )}
        </>
      )}

      {tab === 'debts' && (
        <>
          {adding === 'debt' ? (
            <DebtForm onCancel={() => setAdding(null)} onSaved={refresh} />
          ) : (
            <Button icon="plus" onClick={() => setAdding('debt')} className="w-full sm:w-auto">Add a debt</Button>
          )}
          {owed.length ? (
            <ul className="space-y-2">
              {owed.map((d) => (
                <DebtRow key={d.id} debt={d} glossary={glossary} onDelete={(item) => setConfirming({ kind: 'debt', item })} />
              ))}
            </ul>
          ) : (
            <EmptyState icon="check" title="No debts recorded">
              A card balance or a loan matters here — expensive debt usually comes before investing.
            </EmptyState>
          )}
          <p className="px-1 text-xs text-ink-faint">
            The plan draws its line at {percent(HIGH_APR, 1)}: above it, pay it off before investing beyond the match.
          </p>
        </>
      )}

      {tab === 'history' && (
        activity.data ? <History entries={activity.data} onUndo={undo} undoing={undoing} /> : <Skeleton className="h-40 w-full" />
      )}

      {confirming && (
        <div className="fixed inset-0 z-60 grid place-items-end bg-black/50 p-4 sm:place-items-center">
          <Card role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-sm p-5">
            <h2 id="confirm-title" className="font-bold text-ink">Remove “{confirming.item.name || confirming.item.nickname}”?</h2>
            <p className="mt-1 text-[0.9375rem] text-ink-soft">Your plan will be recalculated without it.</p>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row-reverse">
              <Button variant="danger" onClick={confirmDelete} className="sm:flex-1">Remove</Button>
              <Button variant="ghost" onClick={() => setConfirming(null)} className="sm:flex-1">Keep it</Button>
            </div>
          </Card>
        </div>
      )}

      <Toast message={toast?.message} tone={toast?.tone} onDismiss={dismissToast} />
    </div>
  )
}
