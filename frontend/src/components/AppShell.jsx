import { NavLink } from 'react-router-dom'
import Icon from './Icon'
import { useLog } from '../lib/logContext'
import { THEMES, useTheme } from '../lib/theme'
import { api } from '../lib/api'
import { notifyDataChanged, useApi } from '../lib/useApi'

/** Four destinations — under the five-item ceiling for a bottom bar, and each one
 *  keeps both an icon and a text label. Bottom bar on phones (thumb reach), left
 *  sidebar from 1024px up. Same order, same labels, same active treatment. */
/** Five destinations — exactly at the bottom-bar ceiling. Labels are one short word
 *  each so all five stay readable at 320px, and the sidebar uses the same words. */
const NAV = [
  { to: '/', icon: 'plan', label: 'Plan', end: true },
  { to: '/accounts', icon: 'accounts', label: 'Accounts' },
  { to: '/ask', icon: 'ask', label: 'Ask' },
  { to: '/learn', icon: 'learn', label: 'Learn' },
  { to: '/you', icon: 'you', label: 'You' },
]

function NavItem({ item, layout }) {
  const base = 'group flex cursor-pointer items-center gap-3 font-semibold transition-colors duration-200'
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        layout === 'sidebar'
          ? `${base} min-h-11 rounded-xl px-3 py-2.5 text-[0.9375rem] ${
              isActive ? 'bg-brand-soft text-brand' : 'text-ink-soft hover:bg-surface-sunken'
            }`
          : `${base} min-h-14 flex-1 flex-col justify-center gap-1 py-2 text-[0.6875rem] ${
              isActive ? 'text-brand' : 'text-ink-faint'
            }`
      }
    >
      {({ isActive }) => (
        <>
          {/* Active state is weight + a bar + color, never color alone. */}
          {layout === 'bottom' && (
            <span
              className={`h-0.5 w-8 rounded-full transition-colors ${
                isActive ? 'bg-brand' : 'bg-transparent'
              }`}
              aria-hidden="true"
            />
          )}
          <Icon name={item.icon} className={layout === 'sidebar' ? 'size-5' : 'size-6'} />
          <span>{item.label}</span>
        </>
      )}
    </NavLink>
  )
}

/** Three choices as a radio group; the sidebar shows all three, the phone header a
 *  single button that steps through them. */
function ThemePicker() {
  const [theme, setTheme] = useTheme()
  return (
    <fieldset className="px-5">
      <legend className="mb-1.5 text-xs font-bold uppercase tracking-wide text-ink-faint">Appearance</legend>
      <div className="grid grid-cols-3 gap-1 rounded-xl bg-surface-sunken p-1">
        {THEMES.map((t) => (
          <label key={t.id} className={`flex min-h-11 cursor-pointer flex-col items-center justify-center gap-0.5 rounded-lg text-[0.6875rem] font-semibold transition-colors has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-brand ${
            theme === t.id ? 'bg-surface text-ink shadow-sm' : 'text-ink-faint hover:text-ink'
          }`}>
            <input type="radio" name="theme" value={t.id} checked={theme === t.id} onChange={() => setTheme(t.id)} className="sr-only" />
            <Icon name={t.icon} className="size-4" />
            {t.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function ThemeButton() {
  const [theme, setTheme] = useTheme()
  const i = THEMES.findIndex((t) => t.id === theme)
  const next = THEMES[(i + 1) % THEMES.length]
  return (
    <button type="button" onClick={() => setTheme(next.id)}
      aria-label={`Appearance: ${THEMES[i].label}. Switch to ${next.label}.`}
      className="ml-auto grid size-11 cursor-pointer place-items-center rounded-xl text-ink-soft hover:bg-surface-sunken">
      <Icon name={THEMES[i].icon} className="size-5" />
    </button>
  )
}

/** Only on the public demo: say whose numbers these are, and offer a clean slate. */
function DemoBanner() {
  const { data } = useApi(api.health, [])
  if (!data?.demo) return null
  const startOver = async () => { await api.resetProfile(); notifyDataChanged() }
  return (
    <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-line bg-surface-sunken px-4 py-2 text-sm text-ink-soft">
      <Icon name="info" className="size-4 shrink-0 text-ink-faint" />
      <span className="flex-1">
        <span className="font-semibold text-ink">Demo.</span> A sample student's plan — change anything; it stays in this browser and clears after a day.
      </span>
      <button type="button" onClick={startOver} className="min-h-11 cursor-pointer font-semibold text-brand hover:underline">Start over</button>
    </div>
  )
}

export default function AppShell({ children }) {
  const { openLog } = useLog()
  return (
    <div className="min-h-dvh lg:flex">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-brand focus:px-4 focus:py-3 focus:font-semibold focus:text-on-brand"
      >
        Skip to main content
      </a>

      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-line bg-surface lg:flex lg:flex-col">
        <div className="flex items-center gap-2.5 px-5 py-6">
          <span className="grid size-9 place-items-center rounded-xl bg-brand text-on-brand">
            <Icon name="target" className="size-5" />
          </span>
          <span className="text-lg font-bold tracking-tight text-ink">Footing</span>
        </div>
        {/* Keeping the numbers current is the most frequent thing anyone does here,
            so it's a button on every page rather than a form on one of them. */}
        <div className="px-3 pb-3">
          <button type="button" onClick={() => openLog()}
            className="flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-brand px-3 text-[0.9375rem] font-semibold text-on-brand transition-colors duration-200 hover:bg-brand-hover">
            <Icon name="plus" className="size-5" /> Log an update
          </button>
        </div>
        <nav aria-label="Main" className="flex flex-col gap-1 px-3">
          {NAV.map((item) => <NavItem key={item.to} item={item} layout="sidebar" />)}
        </nav>
        <div className="mt-auto pt-6"><ThemePicker /></div>
        <p className="px-5 py-6 text-xs leading-relaxed text-ink-faint">
          Educational information, not financial advice.
        </p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile header */}
        <header className="flex items-center gap-2.5 border-b border-line bg-surface px-4 py-3 lg:hidden">
          <span className="grid size-8 place-items-center rounded-lg bg-brand text-on-brand">
            <Icon name="target" className="size-4" />
          </span>
          <span className="font-bold tracking-tight text-ink">Footing</span>
          <ThemeButton />
        </header>

        {/* pb-40 keeps the last card clear of the fixed bottom bar and the Log button. */}
        <main id="main" className="flex-1 px-4 pb-40 pt-5 sm:px-6 lg:px-10 lg:pb-16 lg:pt-8">
          <div className="mx-auto w-full max-w-3xl"><DemoBanner />{children}</div>
        </main>
      </div>

      {/* Mobile: the bottom bar is already at five, so logging is a floating button
          in thumb reach rather than a sixth tab. Icon and word, not icon alone. */}
      <button type="button" onClick={() => openLog()}
        className="fixed bottom-[calc(4.75rem+env(safe-area-inset-bottom))] right-4 z-30 flex min-h-12 cursor-pointer items-center gap-2 rounded-full bg-brand pl-4 pr-5 font-semibold text-on-brand shadow-lg transition-colors duration-200 hover:bg-brand-hover lg:hidden">
        <Icon name="plus" className="size-5" /> Log
      </button>

      {/* Mobile bottom navigation, held above the iOS home indicator. */}
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        {NAV.map((item) => <NavItem key={item.to} item={item} layout="bottom" />)}
      </nav>
    </div>
  )
}
