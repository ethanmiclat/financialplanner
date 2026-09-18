export const money = (n, { cents = false } = {}) =>
  n == null
    ? '—'
    : n.toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: cents ? 2 : 0,
        maximumFractionDigits: cents ? 2 : 0,
      })

export const percent = (n, digits = 0) =>
  n == null ? '—' : `${(n * 100).toFixed(digits)}%`

/** Turn an engine `inputs` key into something a person can read.
 *  The engine names things precisely; this layer names them plainly. */
const LABELS = {
  cash_on_hand: 'Cash you have now',
  monthly_expenses: 'Your monthly expenses',
  months_covered: 'Months that cash covers',
  floor_months: 'Minimum months recommended',
  target_months: 'Your target in months',
  floor_amount: 'Minimum recommended',
  target_amount: 'Your target',
  income: 'Your income',
  match_rate: 'Your employer matches',
  match_limit_pct: 'Up to this much of your pay',
  deferral_needed_for_full_match: 'You need to contribute',
  max_match_dollars: 'Most your employer will add',
  contributions_ytd: 'Contributed so far this year',
  employer_match_received_ytd: 'Match received so far',
  unclaimed_match: 'Match still unclaimed',
  balance: 'Balance',
  apr: 'Interest rate',
  cutoff_apr: 'High-interest cutoff',
  annual_interest_cost: 'Interest this costs per year',
  coverage: 'Your coverage type',
  annual_limit: 'Most you can put in this year',
  catch_up_included: 'Extra allowed for your age',
  remaining_room: 'Room left this year',
  combined_limit: 'Limit across all your IRAs',
  elective_deferral_limit: 'Your 401(k) limit this year',
  base_limit: 'Standard limit',
  catch_up_amount: 'Extra allowed for your age',
  catch_up_must_be_roth: 'Catch-up must be Roth',
  prior_year_wages_from_employer: 'Last year’s wages from this employer',
  remaining_tax_advantaged_room: 'Tax-advantaged room left',
  invested: 'Actually invested',
  uninvested: 'Still sitting in cash',
  symbol: 'Fund',
  expense_ratio: 'Yearly fee',
  value: 'Amount held',
  annual_cost: 'What that fee costs you a year',
  filing_status: 'Tax filing status',
  year: 'Tax year',
  holdings: 'Funds recorded',
  retirement_age: 'Retirement age you picked',
  years_to_retirement: 'Years until then',
  plan_to_age: 'Money planned to last to age',
  retirement_spending_annual: 'Yearly spending in retirement',
  social_security_annual: 'Social Security per year',
  social_security_provided: 'Social Security estimate given',
  social_security_claim_age: 'Claiming Social Security at',
  projected_at_retirement: 'Your plan reaches (today’s money)',
  needed_at_retirement: 'Needed to last (today’s money)',
  funded_ratio: 'How far that gets you',
  gap: 'Shortfall (today’s money)',
  extra_savings_per_year: 'Extra saving needed per year',
  money_lasts_to_age: 'Money runs out around age',
  earliest_retirement_age: 'Earliest age this plan supports',
  sustainable_monthly_spending: 'Monthly spending that lasts',
  applies: 'Applies to you',
  penalty_free_age: 'Penalty-free withdrawals from age',
  bridge_years: 'Years to bridge',
  spending_to_cover: 'Spending to cover (today’s money)',
  taxable_by_retirement: 'Taxable account by then',
  cash_beyond_emergency_fund: 'Cash beyond your emergency fund',
  rule_of_55_applies: 'Rule of 55 applies',
  rule_of_55_age: 'Rule of 55 age',
  reachable_401k_by_retirement: '401(k) reachable under the Rule of 55',
  reachable_total: 'Reachable before 59½',
  annual_to_close_gap: 'Yearly saving to close it',
  medicare_age: 'Medicare starts at',
  years_without_medicare: 'Years before Medicare',
  rmd_age: 'Required withdrawals start at',
  birth_year: 'Birth year (approx.)',
  name: 'Debt',
  minimum_payment: 'Minimum payment',
}

/** What a missing value means depends on the question — "not provided" is wrong for
 *  "when does the money run out?" when the answer is "it doesn't". */
const NULL_TEXT = {
  money_lasts_to_age: 'Lasts the whole plan',
  earliest_retirement_age: 'Not before 80',
  extra_savings_per_year: 'None needed',
  annual_to_close_gap: 'No working years left',
  sustainable_monthly_spending: 'Not provided',
}

const MONEY_KEYS = new Set([
  'cash_on_hand', 'monthly_expenses', 'floor_amount', 'target_amount', 'income',
  'deferral_needed_for_full_match', 'max_match_dollars', 'contributions_ytd',
  'employer_match_received_ytd', 'unclaimed_match', 'balance',
  'annual_interest_cost', 'annual_limit', 'catch_up_included', 'remaining_room',
  'combined_limit', 'elective_deferral_limit', 'base_limit', 'catch_up_amount',
  'prior_year_wages_from_employer', 'remaining_tax_advantaged_room', 'invested',
  'uninvested', 'value', 'annual_cost',
  'retirement_spending_annual', 'social_security_annual', 'projected_at_retirement',
  'needed_at_retirement', 'gap', 'extra_savings_per_year', 'sustainable_monthly_spending',
  'spending_to_cover', 'taxable_by_retirement', 'cash_beyond_emergency_fund',
  'reachable_401k_by_retirement', 'reachable_total', 'annual_to_close_gap',
  'minimum_payment',
])
const PERCENT_KEYS = new Set([
  'match_rate', 'match_limit_pct', 'apr', 'cutoff_apr', 'expense_ratio', 'funded_ratio',
])

export const labelFor = (key) =>
  LABELS[key] || key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

export function formatInput(key, value) {
  if (value == null) return NULL_TEXT[key] ?? 'Not provided'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return null // nested; rendered separately
  if (MONEY_KEYS.has(key)) return money(value)
  if (PERCENT_KEYS.has(key)) {
    return percent(value, key === 'expense_ratio' ? 2 : key === 'funded_ratio' ? 0 : 1)
  }
  if (key === 'penalty_free_age') return value === 59.5 ? '59½' : String(value)
  if (key === 'filing_status') return String(value).replace(/_/g, ' ')
  return String(value)
}

/** One icon per account kind, shared by the accounts page and the log sheet. */
export const ACCOUNT_ICONS = { '401k': 'briefcase', ira: 'piggy', hsa: 'heart', taxable: 'trending', cash: 'wallet' }

export const ACCOUNT_LABELS = {
  '401k': '401(k)',
  ira: 'IRA',
  hsa: 'HSA',
  taxable: 'Taxable brokerage',
  cash: 'Cash / savings',
}
