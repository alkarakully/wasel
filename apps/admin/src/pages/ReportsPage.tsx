import { useState } from 'react'

import { Bars, ErrorNote, PageHeader, Skeleton, Stat, Tabs, TextField } from '../components/ui'
import { query, type Report } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { navigate } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useLoad } from '../lib/useLoad'

const iso = (d: Date) => d.toLocaleDateString('en-CA', { timeZone: 'Asia/Baghdad' })
function daysBack(n: number) {
  const d = new Date()
  d.setDate(d.getDate() - (n - 1))
  return iso(d)
}

export function ReportsPage() {
  const { t, money, num, pct, day } = useI18n()
  const [range, setRange] = useState({ from: daysBack(30), to: iso(new Date()) })
  const preset = [7, 30, 90].find((n) => range.from === daysBack(n) && range.to === iso(new Date()))
  const { data, error, loading, reload } = useLoad<Report>(`reports/${query(range)}`)
  const share = (part: number, whole: number) => (whole ? pct(Math.round((part / whole) * 100)) : '—')

  return (
    <>
      <PageHeader title={t('nav_reports')} />
      <section className="panel toolbar report-range">
        <Tabs
          label={t('nav_reports')}
          value={String(preset ?? '')}
          onChange={(v) => v && setRange({ from: daysBack(Number(v)), to: iso(new Date()) })}
          options={[
            { value: '7', label: t('range_7') },
            { value: '30', label: t('range_30') },
            { value: '90', label: t('range_90') },
          ]}
        />
        <div className="grid-2 compact">
          <TextField
            label={t('from')}
            type="date"
            value={range.from}
            max={range.to}
            onChange={(e) => e.target.value && setRange({ ...range, from: e.target.value })}
          />
          <TextField
            label={t('to')}
            type="date"
            value={range.to}
            min={range.from}
            onChange={(e) => e.target.value && setRange({ ...range, to: e.target.value })}
          />
        </div>
      </section>
      <ErrorNote error={error} onRetry={reload} />
      {loading && !data ? (
        <Skeleton rows={8} />
      ) : (
        data && (
          <div className="overview">
            <section className="tiles">
              <Stat
                tone="hero"
                label={t('sales')}
                value={money(data.totals.sales)}
                sub={`${num(data.totals.orders)} ${t('orders')}`}
              />
              <Stat
                label={t('commission')}
                value={money(data.totals.commission)}
                sub={share(data.totals.commission, data.totals.sales)}
              />
              <Stat
                label={t('service_fees')}
                value={money(data.totals.service_fees)}
                sub={`${t('delivery_fees')}: ${money(data.totals.delivery_fees)}`}
              />
              <Stat
                label={t('ordering_customers')}
                value={num(data.customers)}
                sub={`${t('cancelled')}: ${num(data.totals.cancelled)}`}
              />
            </section>
            <section className="panel chart-panel">
              <header className="panel-head">
                <h2>{t('sales')}</h2>
                <span className="muted">
                  {day(data.from)} – {day(data.to)}
                </span>
              </header>
              <Bars
                label={t('sales')}
                format={money}
                data={data.days.map((d) => ({ key: d.day, value: d.sales, label: day(d.day) }))}
              />
            </section>
            <section className="panel">
              <header className="panel-head">
                <h2>{t('payments')}</h2>
              </header>
              <ul className="status-list">
                {Object.entries(data.payments).map(([kind, p]) => (
                  <li key={kind}>
                    <span>{t(`pay_${kind}` as StringKey)}</span>
                    <span className="muted">{num(p.orders)}</span>
                    <strong>{money(p.sales)}</strong>
                  </li>
                ))}
              </ul>
              <header className="panel-head spaced">
                <h2>{t('cancellations')}</h2>
              </header>
              <ul className="status-list">
                {Object.keys(data.cancelled_by).length === 0 && <li className="muted">{t('none')}</li>}
                {Object.entries(data.cancelled_by).map(([who, n]) => (
                  <li key={who}>
                    <span>{t(`by_${who}` as StringKey)}</span>
                    <strong>{num(n)}</strong>
                  </li>
                ))}
              </ul>
            </section>
            <section className="panel wide-panel">
              <header className="panel-head">
                <h2>{t('by_store')}</h2>
              </header>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('store')}</th>
                      <th className="num">{t('orders')}</th>
                      <th className="num">{t('sales')}</th>
                      <th className="num">{t('commission')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.stores.map((s) => (
                      <tr key={s.id} className="clickable" onClick={() => navigate(`/stores/${s.id}`)}>
                        <td>{s.name}</td>
                        <td className="num">{num(s.orders)}</td>
                        <td className="num">{money(s.sales)}</td>
                        <td className="num">{money(s.commission)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )
      )}
    </>
  )
}
