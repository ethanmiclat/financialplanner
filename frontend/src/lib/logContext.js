import { createContext, useContext } from 'react'

/** `openLog(preset?)` from anywhere — the nav button, a plan step, an account row.
 *  A preset is `{ kind, accountId, accountType, debtId, debtName, amount }`, any of
 *  which may be missing; the sheet asks for whatever isn't given. */
export const LogContext = createContext({ openLog: () => {} })
export const useLog = () => useContext(LogContext)

/** The steps that are about moving money. The retirement checks are decisions,
 *  not movements, so they get no log button. */
const MONEY_STEPS = {
  R1_EMERGENCY_FUND: 'add',
  R2_EMPLOYER_MATCH: 'add',
  R3_HIGH_INTEREST_DEBT: 'pay',
  R4_HSA: 'add',
  R5_IRA: 'add',
  R6_REMAINING_401K: 'add',
  R7_TAXABLE: 'add',
  R8_VEHICLE: 'invest',
}

/** A plan action → a filled-in log sheet, or null if logging doesn't fit it. */
export function presetFor(action) {
  const kind = action && action.priority !== 'info' && MONEY_STEPS[action.rule_id]
  if (!kind) return null
  if (kind === 'invest') {
    // Step 8 also flags expensive funds; only the idle-cash items are fixed by investing.
    const idle = action.inputs?.uninvested ?? (action.inputs?.holdings === 0 ? action.inputs.balance : null)
    if (!idle) return null
    return { kind, accountType: action.account_type, amount: idle }
  }
  return {
    kind,
    accountType: action.account_type || undefined,
    debtName: action.inputs?.name,
    amount: action.amount || undefined,
  }
}
