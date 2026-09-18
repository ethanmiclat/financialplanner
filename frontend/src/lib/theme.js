import { useState } from 'react'

/** 'system' follows the OS; 'light' and 'dark' pin it. Stored per browser — it's a
 *  viewing preference, not part of the plan. index.html applies it before paint. */
const KEY = 'footing:theme'
const read = () => { try { return localStorage.getItem(KEY) || 'system' } catch { return 'system' } }

function apply(theme) {
  const root = document.documentElement
  if (theme === 'system') delete root.dataset.theme
  else root.dataset.theme = theme
  try {
    if (theme === 'system') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, theme)
  } catch { /* private mode: the choice lasts for this visit */ }
}

export function useTheme() {
  const [theme, setTheme] = useState(read)
  return [theme, (t) => { apply(t); setTheme(t) }]
}

export const THEMES = [
  { id: 'system', label: 'System', icon: 'monitor' },
  { id: 'light', label: 'Light', icon: 'sun' },
  { id: 'dark', label: 'Dark', icon: 'moon' },
]
