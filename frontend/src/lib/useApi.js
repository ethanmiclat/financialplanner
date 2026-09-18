import { useCallback, useEffect, useState } from 'react'

const CHANGED = 'footing:data-changed'

/** Tell every mounted page the saved numbers moved — after logging an update or
 *  undoing one. Pages refetch quietly rather than blanking to a skeleton, so the
 *  number you just changed updates in place. */
export function notifyDataChanged() {
  window.dispatchEvent(new Event(CHANGED))
}

/** One loading/error/reload contract for every page. */
export function useApi(fn, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fn()
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e) => { if (!cancelled) setError(e) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(load, [load])

  // The silent path: keep what's on screen until the fresh copy lands.
  useEffect(() => {
    let cancelled = false
    const refetch = () => { fn().then((d) => { if (!cancelled) setData(d) }).catch(() => {}) }
    window.addEventListener(CHANGED, refetch)
    return () => { cancelled = true; window.removeEventListener(CHANGED, refetch) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, error, loading, reload: load, setData }
}
