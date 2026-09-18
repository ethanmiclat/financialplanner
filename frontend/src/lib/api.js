/** Thin wrapper over the Flask API. Every call goes through here so error shape,
 *  loading state and the base path stay in one place. */

// Empty in dev and when Flask serves the build; the API's origin when the frontend
// is hosted on its own (GitHub Pages → PythonAnywhere). Set at build time.
const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

// Who this browser is to a demo server, which keeps one sandboxed plan per visitor.
// A header rather than a cookie, because a cross-site cookie is dropped by Safari.
// Made here, before the first call, so the page's opening burst shares one sandbox.
function visitorId() {
  const fresh = () => crypto.randomUUID().replaceAll('-', '')
  try {
    let id = localStorage.getItem('footing:visitor')
    if (!/^[0-9a-f]{32}$/.test(id || '')) {
      id = fresh()
      localStorage.setItem('footing:visitor', id)
    }
    return id
  } catch {
    return (visitorId.memo ??= fresh())
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}/api${path}`, {
    headers: { 'Content-Type': 'application/json', 'X-Footing-Visitor': visitorId() },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(data?.error || `Something went wrong (${res.status})`)
  }
  return data
}

export const api = {
  health: () => request('/health'),
  actions: () => request('/actions?order=priority'),
  plan: () => request('/plan'),
  /** `whatIf` values are tried on a copy of the profile server-side — never saved. */
  projection: (scenario, whatIf = {}) => {
    const params = new URLSearchParams()
    if (scenario) params.set('scenario', scenario)
    for (const [k, v] of Object.entries(whatIf)) params.set(k, v ?? '')
    const qs = params.toString()
    return request(`/projection${qs ? `?${qs}` : ''}`)
  },
  putAssumptions: (body) => request('/assumptions', { method: 'PUT', body }),
  schedule: (months) => request(`/schedule${months ? `?months=${months}` : ''}`),
  /** The plan run backwards: what reaching a number costs per year, month and
   *  paycheck. Read-only — an estimate never changes the saved plan. */
  target: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null),
    ).toString()
    return request(`/target${qs ? `?${qs}` : ''}`)
  },
  waterfall: () => request('/waterfall'),
  profile: () => request('/profile'),
  patchProfile: (body) => request('/profile', { method: 'PATCH', body }),
  putGoal: (body) => request('/goal', { method: 'PUT', body }),
  resetProfile: () => request('/profile/reset', { method: 'POST' }),
  accounts: () => request('/accounts'),
  createAccount: (body) => request('/accounts', { method: 'POST', body }),
  updateAccount: (id, body) => request(`/accounts/${id}`, { method: 'PUT', body }),
  deleteAccount: (id) => request(`/accounts/${id}`, { method: 'DELETE' }),
  debts: () => request('/debts'),
  createDebt: (body) => request('/debts', { method: 'POST', body }),
  deleteDebt: (id) => request(`/debts/${id}`, { method: 'DELETE' }),
  /** "I put $200 in savings" — applied as a movement and logged. The response says
   *  which plan steps it finished (`effect.handled`). */
  activity: () => request('/activity'),
  history: () => request('/history'),
  /** Roth or traditional: the federal rate on your next dollar now and in retirement. */
  tax: () => request('/tax'),
  logActivity: (body) => request('/activity', { method: 'POST', body }),
  undoActivity: (id) => request(`/activity/${id}`, { method: 'DELETE' }),
  contentList: () => request('/content'),
  content: (key) => request(`/content/${key}`),
  glossary: () => request('/glossary'),
  questions: () => request('/questions'),
  question: (id) => request(`/questions/${id}`),
  /** The free-text bot. `context` is whatever the previous answer returned, so a
   *  follow-up like "what about traditional?" can resolve — the server keeps no
   *  state; the transcript here does. */
  ask: (question, context) => request('/ask', { method: 'POST', body: { question, context } }),
  knowledge: () => request('/knowledge'),
  knowledgeEntry: (key) => request(`/knowledge/${key}`),
  /** A bot answer's "save this to my plan" names an existing endpoint and body;
   *  this just calls it. No new write path. */
  call: (method, path, body) => request(path.replace(/^\/api/, ''), { method, body }),
}
