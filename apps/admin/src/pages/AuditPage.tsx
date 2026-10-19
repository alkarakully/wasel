import { ClipboardText } from '@phosphor-icons/react'
import { useState } from 'react'

import { Empty, ErrorNote, PageHeader, Pager, SearchBox, Skeleton } from '../components/ui'
import { query, type AuditRow, type Page } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { useLoad } from '../lib/useLoad'

export function AuditPage() {
  const { t, when } = useI18n()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<number | null>(null)
  const { data, error, loading, reload } = useLoad<Page<AuditRow>>(`audit/${query({ q, page })}`)

  return (
    <>
      <PageHeader title={t('nav_audit')} />
      <section className="panel table-panel">
        <div className="toolbar">
          <SearchBox value={q} onChange={(v) => (setQ(v), setPage(1))} placeholder={t('search_audit')} />
        </div>
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton />
        ) : data && data.results.length === 0 ? (
          <Empty icon={<ClipboardText weight="light" />}>{q ? t('no_results') : t('nothing_here')}</Empty>
        ) : (
          data && (
            <ol className="audit-list">
              {data.results.map((e) => {
                const changes = Object.entries(e.changes ?? {})
                return (
                  <li key={e.id}>
                    <button
                      type="button"
                      className="audit-row"
                      aria-expanded={open === e.id}
                      disabled={!changes.length}
                      onClick={() => setOpen(open === e.id ? null : e.id)}
                    >
                      <time className="muted">{when(e.created_at)}</time>
                      <code className="audit-action" dir="ltr">
                        {e.action}
                      </code>
                      <span className="audit-summary" dir="auto">
                        {e.summary}
                      </span>
                      <bdi dir="ltr" className="muted">
                        {e.actor}
                      </bdi>
                    </button>
                    {open === e.id && (
                      <dl className="audit-changes" dir="ltr">
                        {changes.map(([field, value]) => (
                          <div key={field}>
                            <dt>{field}</dt>
                            <dd>
                              {Array.isArray(value) && value.length === 2
                                ? `${String(value[0])} → ${String(value[1])}`
                                : JSON.stringify(value)}
                            </dd>
                          </div>
                        ))}
                        {e.ip && (
                          <div>
                            <dt>ip</dt>
                            <dd>{e.ip}</dd>
                          </div>
                        )}
                      </dl>
                    )}
                  </li>
                )
              })}
            </ol>
          )
        )}
        {data && <Pager page={page} count={data.count} onPage={setPage} />}
      </section>
    </>
  )
}
