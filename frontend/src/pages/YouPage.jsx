import { useEffect, useState } from 'react'
import Icon from '../components/Icon'
import TaxCompare from '../components/TaxCompare'
import Term from '../components/Term'
import {
  Button, Card, ErrorState, Field, MoneyInput, PercentInput, SegmentedTabs, Select, Skeleton, TextInput, Toast,
} from '../components/ui'
import { api } from '../lib/api'
import { money } from '../lib/format'
import { notifyDataChanged, useApi } from '../lib/useApi'

const FILING = {
  single: 'Single',
  married_filing_jointly: 'Married, filing jointly',
  married_filing_separately: 'Married, filing separately',
  head_of_household: 'Head of household',
}

const toNum = (v) => {
  const n = parseFloat(String(v).replace(/[^0-9.-]/g, ''))
  return Number.isFinite(n) ? n : null
}

/** 0.07 -> "7" for the form; divided back by 100 on save. */
const toPct = (rate) => String(Math.round(rate * 10000) / 100)

const PAYCHECKS_PER_YEAR = { weekly: 52, biweekly: 26, semimonthly: 24, monthly: 12 }

const SAVINGS_LABELS = {
  monthly: 'How much each month?',
  per_paycheck: 'How much per paycheck?',
  percent_of_pay: 'What share of each paycheck?',
  yearly: 'How much each year?',
}

/** Whatever unit they chose, shown back as a yearly figure — the one the rest of the
 *  plan is built on, so the two can't feel like different numbers. */
function savingsHint(form) {
  if (form.savings_amount === '') {
    return 'Optional. Fill this in and we’ll schedule exactly where each dollar goes.'
  }
  const n = toNum(form.savings_amount) ?? 0
  const annual = form.savings_basis === 'yearly' ? n
    : form.savings_basis === 'monthly' ? n * 12
      : form.savings_basis === 'per_paycheck' ? n * (PAYCHECKS_PER_YEAR[form.pay_frequency] ?? 26)
        : (n / 100) * (toNum(form.income) ?? 0)
  return `That’s ${money(annual)} a year — ${money(annual / 12)} a month.`
}

/** Mirrors the backend's validation, so most mistakes are caught on blur. */
const RATE_RANGES = {
  return_rate: [-5, 15],
  retirement_return_rate: [-5, 15],
  inflation: [0, 10],
  contribution_growth: [0, 15],
}

const SECTIONS = [
  { id: 'basics', label: 'Basics', icon: 'you', fields: ['age', 'income', 'filing_status'] },
  { id: 'saving', label: 'Saving', icon: 'piggy', fields: ['monthly_expenses', 'emergency_fund_months', 'savings_basis', 'savings_amount'] },
  { id: 'pay', label: 'Pay', icon: 'wallet', fields: ['pay_frequency', 'take_home_per_paycheck'] },
  { id: 'retire', label: 'Retiring', icon: 'flag', fields: ['retirement_age', 'plan_to_age', 'retirement_monthly_spending', 'social_security_monthly', 'social_security_claim_age', 'expects_lower_bracket_in_retirement'] },
  { id: 'assume', label: 'Assumes', icon: 'sliders', fields: ['return_rate', 'retirement_return_rate', 'inflation', 'contribution_growth'] },
]

export default function YouPage({ glossary }) {
  const { data, error, loading, reload } = useApi(api.profile, [])
  const [section, setSection] = useState('basics')
  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const { data: taxData } = useApi(api.tax, [])
  const [saveError, setSaveError] = useState(null)

  useEffect(() => {
    if (!data) return
    setForm({
      age: String(data.age),
      income: String(data.income),
      filing_status: data.filing_status,
      state: data.state || '',
      savings_basis: data.savings_basis,
      savings_amount: data.savings_amount == null
        ? ''
        : String(data.savings_basis === 'percent_of_pay'
          ? Math.round(data.savings_amount * 10000) / 100
          : data.savings_amount),
      pay_frequency: data.pay_frequency,
      take_home_per_paycheck: data.take_home_per_paycheck == null ? '' : String(data.take_home_per_paycheck),
      expects_lower_bracket_in_retirement: data.expects_lower_bracket_in_retirement,
      monthly_expenses: String(data.goal.monthly_expenses),
      emergency_fund_months: String(data.goal.emergency_fund_months),
      retirement_age: String(data.goal.retirement_age ?? 67),
      plan_to_age: String(data.goal.plan_to_age),
      retirement_monthly_spending: data.goal.retirement_monthly_spending == null ? '' : String(data.goal.retirement_monthly_spending),
      social_security_monthly: data.goal.social_security_monthly == null ? '' : String(data.goal.social_security_monthly),
      social_security_claim_age: String(data.goal.social_security_claim_age),
      return_rate: toPct(data.assumptions.return_rate),
      retirement_return_rate: toPct(data.assumptions.retirement_return_rate),
      inflation: toPct(data.assumptions.inflation),
      contribution_growth: toPct(data.assumptions.contribution_growth),
    })
  }, [data])

  if (loading || !form) return <div className="space-y-3"><Skeleton className="h-96 w-full" /></div>
  if (error) return <ErrorState error={error} onRetry={reload} />

  const set = (k) => (v) => {
    setForm((f) => ({ ...f, [k]: v }))
    setErrors((e) => ({ ...e, [k]: undefined }))
  }

  /** Validate on blur, not on every keystroke — errors that appear while you're
   *  still typing read as being told off mid-sentence. */
  const validate = (k) => () => {
    const v = form[k]
    let msg
    if (k === 'age') {
      const n = toNum(v)
      if (n == null || n < 16 || n > 110) msg = 'Enter an age between 16 and 110.'
    }
    if (k === 'income' || k === 'monthly_expenses') {
      const n = toNum(v)
      if (n == null || n < 0) msg = 'Enter an amount of 0 or more.'
    }
    if (k === 'retirement_age') {
      const n = toNum(v)
      if (n == null || !Number.isInteger(n) || n < 18 || n > 90) msg = 'Enter a whole-number age between 18 and 90.'
    }
    if (k === 'plan_to_age') {
      const n = toNum(v)
      const floor = Math.max(toNum(form.retirement_age) ?? 67, toNum(form.age) ?? 0)
      if (n == null || !Number.isInteger(n) || n <= floor || n > 120) msg = `Enter an age above ${floor}, up to 120.`
    }
    if (k === 'take_home_per_paycheck' && v !== '') {
      const n = toNum(v)
      if (n == null || n < 0) msg = 'Enter an amount of 0 or more, or leave it blank.'
    }
    if (k === 'savings_amount' && v !== '') {
      const n = toNum(v)
      const isPct = form.savings_basis === 'percent_of_pay'
      if (n == null || n < 0) msg = 'Enter an amount of 0 or more, or leave it blank.'
      else if (isPct && n > 100) msg = 'Enter a share between 0% and 100%.'
    }
    if ((k === 'retirement_monthly_spending' || k === 'social_security_monthly') && v !== '') {
      const n = toNum(v)
      if (n == null || n < 0) msg = 'Enter an amount of 0 or more, or leave it blank.'
    }
    if (RATE_RANGES[k]) {
      const n = toNum(v)
      const [lo, hi] = RATE_RANGES[k]
      if (n == null || n < lo || n > hi) msg = `Enter a rate between ${lo}% and ${hi}%.`
    }
    setErrors((e) => ({ ...e, [k]: msg }))
  }

  const hasErrors = Object.values(errors).some(Boolean)

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setSaveError(null)
    try {
      await api.patchProfile({
        age: toNum(form.age) ?? data.age,
        income: toNum(form.income) ?? data.income,
        filing_status: form.filing_status,
        state: form.state,
        // The basis and the raw figure are what's stored; the backend derives the
        // yearly number from them, so a percent-of-pay plan follows a pay rise.
        savings_basis: form.savings_basis,
        savings_amount: form.savings_amount === ''
          ? null
          : form.savings_basis === 'percent_of_pay'
            ? (toNum(form.savings_amount) ?? 0) / 100
            : toNum(form.savings_amount),
        ...(form.savings_amount === '' ? { annual_savings_capacity: null } : {}),
        pay_frequency: form.pay_frequency,
        take_home_per_paycheck: form.take_home_per_paycheck === '' ? null : toNum(form.take_home_per_paycheck),
        expects_lower_bracket_in_retirement: form.expects_lower_bracket_in_retirement,
      })
      await api.putGoal({
        monthly_expenses: toNum(form.monthly_expenses) ?? 0,
        emergency_fund_months: toNum(form.emergency_fund_months) ?? 6,
        retirement_target: data.goal.retirement_target,
        retirement_age: toNum(form.retirement_age) ?? data.goal.retirement_age,
        plan_to_age: toNum(form.plan_to_age) ?? data.goal.plan_to_age,
        retirement_monthly_spending: form.retirement_monthly_spending === '' ? null : toNum(form.retirement_monthly_spending),
        social_security_monthly: form.social_security_monthly === '' ? null : toNum(form.social_security_monthly),
        social_security_claim_age: toNum(form.social_security_claim_age) ?? 67,
      })
      await api.putAssumptions(Object.fromEntries(
        Object.keys(RATE_RANGES).map((k) => [k, (toNum(form[k]) ?? data.assumptions[k] * 100) / 100]),
      ))
      setToast('Saved — your plan has been updated')
      notifyDataChanged()
      reload()
    } catch (err) {
      setSaveError(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">About you</h1>

      {/* One section at a time. A tab with a count has a field to fix inside it. */}
      <SegmentedTabs
        label="Profile sections"
        value={section}
        onChange={setSection}
        tabs={SECTIONS.map((sec) => ({
          id: sec.id, label: sec.label, icon: sec.icon,
          count: sec.fields.filter((f) => errors[f]).length || undefined,
        }))}
      />

      {section === 'basics' && (
      <Card className="space-y-5 p-5">
        <h2 className="font-bold tracking-tight text-ink">The basics</h2>

        <Field label="How old are you?" required error={errors.age}
          hint="Contribution limits go up at 50, and again between 60 and 63.">
          {(props) => (
            <TextInput {...props} type="text" inputMode="numeric" value={form.age}
              onChange={(e) => set('age')(e.target.value)} onBlur={validate('age')} className="tabular" />
          )}
        </Field>

        <Field label="What do you earn a year, before tax?" required error={errors.income}
          hint="Used to work out your employer match and whether income limits apply to you.">
          {(props) => (
            <MoneyInput {...props} value={form.income}
              onChange={(e) => set('income')(e.target.value)} onBlur={validate('income')} />
          )}
        </Field>

        <Field label="How do you file your taxes?"
          hint="Changes the income cut-offs for a Roth IRA.">
          {(props) => (
            <Select {...props} value={form.filing_status}
              onChange={(e) => set('filing_status')(e.target.value)}>
              {Object.entries(FILING).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          )}
        </Field>
      </Card>
      )}

      {section === 'saving' && (
      <Card className="space-y-5 p-5">
        <div>
          <h2 className="font-bold tracking-tight text-ink">Your spending and saving</h2>
          <p className="mt-1 text-sm text-ink-soft">
            This is what sizes your <Term id="emergency_fund" glossary={glossary}>emergency fund</Term> —
            step one of the plan.
          </p>
        </div>

        <Field label="What do you spend in a typical month?" required error={errors.monthly_expenses}
          hint="Rent, food, bills, transport — the things you'd still pay if you lost your income. A rough number is fine.">
          {(props) => (
            <MoneyInput {...props} value={form.monthly_expenses}
              onChange={(e) => set('monthly_expenses')(e.target.value)}
              onBlur={validate('monthly_expenses')} />
          )}
        </Field>

        <Field label="How many months of cushion do you want?"
          hint="Three is the usual minimum. Six if your income is irregular or you'd be hard to re-employ.">
          {(props) => (
            <Select {...props} value={form.emergency_fund_months}
              onChange={(e) => set('emergency_fund_months')(e.target.value)}>
              {[3, 4, 5, 6, 9, 12].map((m) => (
                <option key={m} value={m}>{m} months</option>
              ))}
            </Select>
          )}
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="How do you want to think about saving?"
            hint="All four mean the same thing to your plan. Pick the one you’d actually act on.">
            {(props) => (
              <Select {...props} value={form.savings_basis}
                onChange={(e) => set('savings_basis')(e.target.value)}>
                <option value="monthly">A set amount each month</option>
                <option value="per_paycheck">A set amount per paycheck</option>
                <option value="percent_of_pay">A share of my pay</option>
                <option value="yearly">A set amount each year</option>
              </Select>
            )}
          </Field>

          <Field label={SAVINGS_LABELS[form.savings_basis]} error={errors.savings_amount}
            hint={savingsHint(form)}>
            {(props) => (
              form.savings_basis === 'percent_of_pay'
                ? <PercentInput {...props} value={form.savings_amount}
                    onChange={(e) => set('savings_amount')(e.target.value)}
                    onBlur={validate('savings_amount')} placeholder="10" />
                : <MoneyInput {...props} value={form.savings_amount}
                    onChange={(e) => set('savings_amount')(e.target.value)}
                    onBlur={validate('savings_amount')} placeholder="Leave blank to skip" />
            )}
          </Field>
        </div>
      </Card>
      )}

      {section === 'pay' && (
      <Card className="space-y-5 p-5">
        <div>
          <h2 className="font-bold tracking-tight text-ink">How you’re paid</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-soft">
            This turns your plan into a payday schedule — what to move, and what’s left
            to spend until the next one.
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="How often are you paid?">
            {(props) => (
              <Select {...props} value={form.pay_frequency}
                onChange={(e) => set('pay_frequency')(e.target.value)}>
                <option value="weekly">Every week</option>
                <option value="biweekly">Every two weeks</option>
                <option value="semimonthly">Twice a month</option>
                <option value="monthly">Once a month</option>
              </Select>
            )}
          </Field>

          <Field label="Take-home pay per paycheck" error={errors.take_home_per_paycheck}
            hint="What actually lands in your account, after tax and deductions.">
            {(props) => (
              <MoneyInput {...props} value={form.take_home_per_paycheck}
                onChange={(e) => set('take_home_per_paycheck')(e.target.value)}
                onBlur={validate('take_home_per_paycheck')} placeholder="Optional" />
            )}
          </Field>
        </div>
      </Card>
      )}

      {section === 'retire' && (
      <Card className="space-y-5 p-5">
        <div>
          <h2 className="font-bold tracking-tight text-ink">Your retirement</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-soft">
            Any age works — 50, 67, 75. The plan reshapes itself around it: which accounts
            you can reach in time, how long the money has to last, and whether it adds up.
          </p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="When do you want to retire?" required error={errors.retirement_age}
            hint="The age you’d stop working full-time.">
            {(props) => (
              <TextInput {...props} type="text" inputMode="numeric" value={form.retirement_age}
                onChange={(e) => set('retirement_age')(e.target.value)}
                onBlur={validate('retirement_age')} className="tabular" />
            )}
          </Field>

          <Field label="Plan for the money to last until" required error={errors.plan_to_age}
            hint="95 is a cautious default — running out early is the risk that matters.">
            {(props) => (
              <TextInput {...props} type="text" inputMode="numeric" value={form.plan_to_age}
                onChange={(e) => set('plan_to_age')(e.target.value)}
                onBlur={validate('plan_to_age')} className="tabular" />
            )}
          </Field>
        </div>

        <Field label="What will you spend a month once you retire?" error={errors.retirement_monthly_spending}
          hint={`In today’s money. Leave blank to use what you spend now (${money(toNum(form.monthly_expenses) ?? 0)}).`}>
          {(props) => (
            <MoneyInput {...props} value={form.retirement_monthly_spending}
              onChange={(e) => set('retirement_monthly_spending')(e.target.value)}
              onBlur={validate('retirement_monthly_spending')} placeholder="Same as now" />
          )}
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Social Security estimate, per month" error={errors.social_security_monthly}
            hint="Your benefit at full retirement age, from ssa.gov/myaccount. Leave blank and we’ll count none.">
            {(props) => (
              <MoneyInput {...props} value={form.social_security_monthly}
                onChange={(e) => set('social_security_monthly')(e.target.value)}
                onBlur={validate('social_security_monthly')} placeholder="Don’t know" />
            )}
          </Field>

          <Field label="Claim Social Security at"
            hint="Each year before 67 shrinks the check for life; each year after, up to 70, adds 8%.">
            {(props) => (
              <Select {...props} value={form.social_security_claim_age}
                onChange={(e) => set('social_security_claim_age')(e.target.value)}>
                {[62, 63, 64, 65, 66, 67, 68, 69, 70].map((a) => (
                  <option key={a} value={a}>
                    {a}{a === 62 ? ' — earliest' : a === 67 ? ' — full benefit' : a === 70 ? ' — largest check' : ''}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>
      </Card>
      )}

      {section === 'assume' && (
      <Card className="space-y-5 p-5">
        <div>
          <h2 className="font-bold tracking-tight text-ink">Planning assumptions</h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-soft">
            Nobody knows these numbers. The defaults are middle-of-the-road guesses — change
            any of them to see how much your plan depends on it.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          {[
            ['return_rate', 'Yearly return while you’re saving', 'Before inflation. About 7% is the long-run average for a mostly-stock mix.'],
            ['retirement_return_rate', 'Yearly return once you’ve retired', 'Usually lower — retirees tend to hold more bonds.'],
            ['inflation', 'Inflation', 'The long-run US average is roughly 2.5–3%.'],
            ['contribution_growth', 'Raise what you save each year by', '0% keeps it flat. Many people add 1–3% a year as their pay rises.'],
          ].map(([k, label, hint]) => (
            <Field key={k} label={label} hint={hint} error={errors[k]}>
              {(props) => (
                <PercentInput {...props} value={form[k]}
                  onChange={(e) => set(k)(e.target.value)} onBlur={validate(k)} />
              )}
            </Field>
          ))}
        </div>
      </Card>
      )}

      {section === 'retire' && (
      <Card className="space-y-4 p-5">
        <div>
          <h2 className="font-bold tracking-tight text-ink">
            <Term id="roth" glossary={glossary}>Roth</Term> or <Term id="traditional" glossary={glossary}>traditional</Term>?
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-soft">
            It comes down to when your tax rate is lower — now, or when you take the money out. Estimated from your saved numbers.
          </p>
        </div>

        <TaxCompare data={taxData} glossary={glossary} />

        <fieldset>
          <legend className="text-[0.9375rem] font-semibold text-ink">
            Which should the plan go by?
          </legend>
          <div className="mt-2 space-y-1">
            {[
              [null, 'The estimate', 'Recommended. Follows your numbers as they change.'],
              [true, 'I expect a lower rate in retirement', 'Points toward traditional, whatever the estimate says.'],
              [false, 'I expect the same or a higher rate', 'Points toward Roth, whatever the estimate says.'],
            ].map(([value, label, hint]) => (
              <label key={String(value)} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-xl px-2 py-2 hover:bg-surface-sunken">
                <input
                  type="radio"
                  name="bracket"
                  checked={form.expects_lower_bracket_in_retirement === value}
                  onChange={() => set('expects_lower_bracket_in_retirement')(value)}
                  className="mt-1 size-5 shrink-0 cursor-pointer accent-brand"
                />
                <span>
                  <span className="block text-[0.9375rem] font-medium text-ink">{label}</span>
                  <span className="block text-sm text-ink-soft">{hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      </Card>
      )}

      {saveError && (
        <Card tone="alert" className="p-4">
          <p role="alert" className="flex items-start gap-2 text-sm font-medium text-alert">
            <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
            {saveError.message} Check the fields above and try again.
          </p>
        </Card>
      )}

      {/* Sticky on mobile so the save button is always in thumb reach on a long form. */}
      <div className="sticky bottom-20 z-20 -mx-4 border-t border-line bg-surface/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6 lg:static lg:mx-0 lg:border-0 lg:bg-transparent lg:px-0 lg:backdrop-blur-none">
        <Button type="submit" loading={saving} disabled={hasErrors} className="w-full lg:w-auto">
          Save and update my plan
        </Button>
        {hasErrors && (
          <p className="mt-2 text-sm font-medium text-alert">
            Fix the fields marked on the tabs above first.
          </p>
        )}
      </div>

      <Toast message={toast} onDismiss={() => setToast(null)} />
    </form>
  )
}
