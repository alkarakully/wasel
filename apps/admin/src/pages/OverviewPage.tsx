import { ArrowUpRight, Bell, Storefront } from '@phosphor-icons/react'
import type { ReactNode } from 'react'

import { Bars, ErrorNote, PageHeader, Skeleton, Stat } from '../components/ui'
import type { Overview } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { navigate } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useLoad } from '../lib/useLoad'

export function OverviewPage() {
  const { t, money, num, day } = useI18n()
  const { data, error, reload } = useLoad<Overview>('overview/', 30_000)

  return (
    <>
      <PageHeader eyebrow={t('live_now')} title={t('nav_overview')} />
      <ErrorNote error={error} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={8} />
      ) : (
        <div className="overview">
          <section className="tiles">
            <Stat
              tone="hero"
              label={`${t('sales')} · ${t('today')}`}
              value={money(data.today.sales)}
              sub={`${num(data.today.orders)} ${t('orders')}`}
            />
            <Stat
              label={t('commission')}
              value={money(data.today.commission)}
              sub={`${t('this_month')}: ${money(data.month.commission)}`}
            />
            <Stat
              label={t('delivered')}
              value={num(data.today.delivered)}
              sub={`${t('cancelled')}: ${num(data.today.cancelled)}`}
            />
            <Stat
              label={t('avg_delivery')}
              value={
                data.today.avg_delivery_minutes === null
                  ? '—'
                  : t('minutes_ago', { n: num(data.today.avg_delivery_minutes) })
              }
            />
          </section>

          <section className="live-strip" aria-label={t('live_now')}>
            <LiveChip
              label={t('active_orders')}
              value={num(data.live.active_orders)}
              onClick={() => navigate('/orders')}
            />
            <LiveChip
              label={t('open_alerts')}
              value={num(data.live.open_alerts)}
              alert={data.live.open_alerts > 0}
              icon={<Bell weight="light" size={18} />}
              onClick={() => navigate('/orders?tab=alerts')}
            />
            <LiveChip
              label={t('online_captains')}
              value={num(data.live.online_captains)}
              onClick={() => navigate('/orders?tab=captains')}
            />
            <LiveChip
              label={t('open_stores')}
              value={`${num(data.live.open_stores)} / ${num(data.live.stores)}`}
              onClick={() => navigate('/stores')}
            />
            <LiveChip
              label={t('applications')}
              value={num(data.live.applications)}
              alert={data.live.applications > 0}
              icon={<Storefront weight="light" size={18} />}
              onClick={() => navigate('/stores?status=pending')}
            />
          </section>

          <section className="panel chart-panel">
            <header className="panel-head">
              <h2>{t('last_14_days')}</h2>
              <span className="muted">{t('sales')}</span>
            </header>
            <Bars
              label={t('last_14_days')}
              format={money}
              data={data.days.map((d) => ({ key: d.day, value: d.sales, label: day(d.day) }))}
            />
          </section>

          <section className="panel">
            <header className="panel-head">
              <h2>{t('by_status')}</h2>
            </header>
            <ul className="status-list">
              {Object.entries(data.by_status).map(([status, n]) => (
                <li key={status}>
                  <span className={`dot dot-${status}`} aria-hidden="true" />
                  <span>{t(`st_${status}` as StringKey)}</span>
                  <strong>{num(n)}</strong>
                </li>
              ))}
            </ul>
          </section>

          <section className="panel half">
            <header className="panel-head">
              <h2>{t('top_stores_today')}</h2>
            </header>
            {data.top_stores.length === 0 ? (
              <p className="muted">{t('nothing_here')}</p>
            ) : (
              <ol className="rank-list">
                {data.top_stores.map((s) => (
                  <li key={s.id}>
                    <button type="button" className="rank-row" onClick={() => navigate(`/stores/${s.id}`)}>
                      <span>{s.name}</span>
                      <span className="muted">{num(s.orders)}</span>
                      <strong>{money(s.sales)}</strong>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="panel half">
            <header className="panel-head">
              <h2>{t('this_month')}</h2>
            </header>
            <dl className="facts">
              <div>
                <dt>{t('orders')}</dt>
                <dd>{num(data.month.orders)}</dd>
              </div>
              <div>
                <dt>{t('sales')}</dt>
                <dd>{money(data.month.sales)}</dd>
              </div>
              <div>
                <dt>{t('customers')}</dt>
                <dd>{num(data.live.customers)}</dd>
              </div>
              <div>
                <dt>{t('plus_members')}</dt>
                <dd>{num(data.live.plus_members)}</dd>
              </div>
            </dl>
          </section>
        </div>
      )}
    </>
  )
}

function LiveChip({
  label,
  value,
  alert,
  icon,
  onClick,
}: {
  label: string
  value: string
  alert?: boolean
  icon?: ReactNode
  onClick: () => void
}) {
  return (
    <button type="button" className={`live-chip ${alert ? 'alert' : ''}`} onClick={onClick}>
      <span className="live-chip-top">
        {icon}
        <span>{label}</span>
        <ArrowUpRight weight="light" size={14} className="live-chip-arrow" aria-hidden="true" />
      </span>
      <strong>{value}</strong>
    </button>
  )
}
