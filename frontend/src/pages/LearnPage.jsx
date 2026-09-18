import { Link, useParams } from 'react-router-dom'
import Icon from '../components/Icon'
import { Annotated } from '../components/Term'
import { Card, Disclosure, ErrorState, ScrollX, Skeleton } from '../components/ui'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const TOPIC_ICON = { '401k': 'briefcase', ira: 'piggy', hsa: 'heart', taxable: 'trending', index_funds: 'layers' }

export function LearnIndex({ glossary }) {
  const { data, error, loading, reload } = useApi(api.contentList, [])

  if (loading) return <div className="space-y-3">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-28 w-full" />)}</div>
  if (error) return <ErrorState error={error} onRetry={reload} />

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">Learn</h1>
        <Link to="/ask" className="text-sm font-semibold text-brand">Or just ask</Link>
      </div>

      <ul className="grid gap-3 sm:grid-cols-2">
        {data.map((entry) => (
          <li key={entry.key}>
            <Link
              to={`/learn/${entry.key}`}
              className="flex h-full flex-col rounded-[--radius-card] border border-line bg-surface p-4 transition-colors duration-200 hover:border-brand-border hover:bg-brand-soft"
            >
              <span className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand">
                  <Icon name={TOPIC_ICON[entry.key] || 'book'} className="size-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-bold tracking-tight text-ink">{entry.name}</span>
                  <span className="block truncate text-sm text-ink-soft">{entry.tagline}</span>
                </span>
                <Icon name="chevronRight" className="size-5 shrink-0 text-ink-faint" />
              </span>
              <span className="mt-3 border-t border-line pt-3 text-sm font-medium leading-relaxed text-brand">
                <Annotated text={entry.layer1} glossary={glossary} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function LearnDetail({ glossary }) {
  const { key } = useParams()
  const { data, error, loading, reload } = useApi(() => api.content(key), [key])

  if (loading) return <Skeleton className="h-96 w-full" />
  if (error) return <ErrorState error={error} onRetry={reload} />

  return (
    <article className="space-y-4">
      <Link to="/learn" className="inline-flex min-h-11 items-center gap-1 text-[0.9375rem] font-semibold text-brand">
        <Icon name="chevronLeft" className="size-4" /> All topics
      </Link>

      <header>
        <h1 className="text-2xl font-bold tracking-tight text-ink">{data.name}</h1>
      </header>

      {/* Layer 1 */}
      <Card tone="brand" className="p-5">
        <h2 className="text-xs font-bold uppercase tracking-wide text-brand">
          What this means for you
        </h2>
        <p className="mt-2 text-lg font-semibold leading-snug text-ink">
          <Annotated text={data.layer1.decision} glossary={glossary} />
        </p>
      </Card>

      {/* Layer 2 */}
      <Card className="p-5">
        <h2 className="font-bold tracking-tight text-ink">How it actually works</h2>
        <p className="mt-2 text-[1.0625rem] leading-relaxed text-ink">
          <Annotated text={data.layer2.why} glossary={glossary} />
        </p>
      </Card>

      {/* Layer 3 */}
      <Card className="p-5">
        <Disclosure label="All the detail — limits and edge cases">
          <ul className="mt-3 space-y-3">
            {data.layer3.details.map((d, i) => (
              <li key={i} className="flex gap-2.5 text-[0.9375rem] leading-relaxed text-ink-soft">
                <Icon name="chevronRight" className="mt-1 size-4 shrink-0 text-brand" />
                <span><Annotated text={d} glossary={glossary} /></span>
              </li>
            ))}
          </ul>

          {data.layer3.numbers && (
            <ScrollX label="Key numbers" className="mt-5">
              <h3 className="pb-2 text-sm font-bold text-ink">The numbers</h3>
              <table className="w-full text-left text-sm">
                <tbody>
                  {Object.entries(data.layer3.numbers)
                    .filter(([, v]) => v !== null && typeof v !== 'object')
                    .map(([k, v]) => (
                      <tr key={k} className="border-b border-line last:border-0">
                        <th scope="row" className="py-2 pr-4 font-medium capitalize text-ink-soft">
                          {k.replace(/_/g, ' ')}
                        </th>
                        <td className="tabular py-2 text-right font-semibold text-ink whitespace-nowrap">
                          {typeof v === 'number' && v > 100 ? `$${v.toLocaleString()}` : String(v)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </ScrollX>
          )}
        </Disclosure>
      </Card>

      <p className="px-1 text-xs leading-relaxed text-ink-faint">{data.disclaimer}</p>
    </article>
  )
}
