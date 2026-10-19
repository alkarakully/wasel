import { ChartBar, Clock, Fire, ForkKnife, Receipt, XCircle } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'

import { Api, type Report } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  api: Api
  storeId: number
  onError: (error: unknown) => void
}

type Preset = 'last7' | 'last30' | 'thisMonth' | 'custom'

/** Calendar day in local time as YYYY-MM-DD. */
export function isoDay(date: Date) {
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}

function rangeFor(preset: Exclude<Preset, 'custom'>, today = new Date()): [string, string] {
  const end = isoDay(today)
  if (preset === 'thisMonth') return [`${end.slice(0, 8)}01`, end]
  const start = new Date(today)
  start.setDate(start.getDate() - (preset === 'last7' ? 6 : 29))
  return [isoDay(start), end]
}

/** A store's numbers for a date range: earnings, orders, sales by day, busy hours, best sellers. */
export function ReportsView({ api, storeId, onError }: Props) {
  const { t, money: format, name } = useI18n()
  const [preset, setPreset] = useState<Preset>('last7')
  const [[from, to], setRange] = useState(() => rangeFor('last7'))
  const [report, setReport] = useState<Report | null>(null)
  // Amounts are in the store's own currency.
  const money = (amount: string | number) => format(amount, report?.currency)

  useEffect(() => {
    let current = true
    api.report(storeId, from, to).then((r) => current && setReport(r), onError)
    return () => {
      current = false
    }
  }, [api, storeId, from, to, onError])

  const pick = (next: Exclude<Preset, 'custom'>) => {
    setPreset(next)
    setRange(rangeFor(next))
  }

  const cancelledBy = report
    ? Object.entries(report.cancelled_by)
        .map(([who, n]) => `${n} ${t(`by_${who}` as 'by_customer')}`)
        .join(' · ')
    : ''

  return (
    <div className="reports">
      <div className="range-bar">
        <div className="segmented" role="group" aria-label={t('reports')}>
          {(['last7', 'last30', 'thisMonth'] as const).map((option) => (
            <button key={option} type="button" aria-pressed={preset === option} onClick={() => pick(option)}>
              {t(option)}
            </button>
          ))}
        </div>
        <label className="date">
          {t('from')}
          <input
            type="date"
            value={from}
            max={to}
            onChange={(e) => {
              setPreset('custom')
              setRange([e.target.value, to])
            }}
          />
        </label>
        <label className="date">
          {t('to')}
          <input
            type="date"
            value={to}
            min={from}
            onChange={(e) => {
              setPreset('custom')
              setRange([from, e.target.value])
            }}
          />
        </label>
      </div>

      {!report ? (
        <div className="bento loading" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton-card">
              <span className="bone short" />
              <span className="bone tall" />
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="bento">
            <article className="tile hero glaze">
              <p className="eyebrow">{t('yourEarnings')}</p>
              <p className="big">{money(report.payout)}</p>
              <span className="gold-rule" />
              <p className="sub">
                {t('sales')} {money(report.food_sales)} · {t('commissionLabel')} {money(report.commission)}
                {Number(report.store_discounts) > 0 && ` · ${t('storeDiscounts')} ${money(report.store_discounts)}`}
              </p>
            </article>
            <article className="tile">
              <p className="label">
                <Receipt size={20} weight="light" aria-hidden="true" />
                {t('ordersLabel')}
              </p>
              <p className="num">{report.orders.toLocaleString('en-US')}</p>
              <p className="hint">{t('deliveredOf', { n: report.delivered })}</p>
            </article>
            <article className="tile">
              <p className="label">
                <ForkKnife size={20} weight="light" aria-hidden="true" />
                {t('avgOrder')}
              </p>
              <p className="num">{money(report.average_order)}</p>
            </article>
            <article className="tile">
              <p className="label">
                <Clock size={20} weight="light" aria-hidden="true" />
                {t('avgPrep')}
              </p>
              <p className="num">
                {report.average_prep_minutes == null ? '—' : t('minutes', { n: report.average_prep_minutes })}
              </p>
            </article>
            <article className={`tile ${report.cancelled ? 'warn' : ''}`}>
              <p className="label">
                <XCircle size={20} weight="light" aria-hidden="true" />
                {t('cancellations')}
              </p>
              <p className="num">{report.cancelled}</p>
              {cancelledBy && <p className="hint">{cancelledBy}</p>}
            </article>
          </div>

          <div className="report-split">
            <section className="plate-card">
              <h2>
                <ChartBar size={20} weight="light" aria-hidden="true" />
                {t('salesByDay')}
              </h2>
              <DayChart days={report.days} money={money} />
            </section>
            <section className="plate-card">
              <h2>
                <Fire size={20} weight="light" aria-hidden="true" />
                {t('busyHours')}
              </h2>
              <HourStrip hours={report.hours} />
            </section>
          </div>

          <section className="plate-card">
            <h2>{t('topItems')}</h2>
            {report.top_items.length === 0 ? (
              <p className="muted">{t('noData')}</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>{t('menu')}</th>
                    <th>{t('qty')}</th>
                    <th>{t('ordersLabel')}</th>
                    <th>{t('sales')}</th>
                  </tr>
                </thead>
                <tbody>
                  {report.top_items.map((item, i) => {
                    const top = Number(report.top_items[0].sales)
                    const share = top ? Number(item.sales) / top : 0
                    return (
                      <tr key={item.product}>
                        <td className="rank">{i + 1}</td>
                        <td>
                          {name(item.name)}
                          <span
                            className="share"
                            style={{ width: `${Math.max(4, share * 100)}%` }}
                            aria-hidden="true"
                          />
                        </td>
                        <td className="num">{item.quantity}</td>
                        <td className="num">{item.orders}</td>
                        <td className="num">{money(item.sales)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  )
}

/** Bars for each day's food sales; time runs left to right in every language. */
function DayChart({ days, money }: { days: Report['days']; money: (n: string | number) => string }) {
  const max = Math.max(1, ...days.map((d) => Number(d.sales)))
  const step = days.length > 14 ? Math.ceil(days.length / 10) : 1
  return (
    <div
      className="day-chart"
      dir="ltr"
      role="img"
      aria-label={days.map((d) => `${d.date}: ${money(d.sales)}`).join(', ')}
    >
      {days.map((day, i) => (
        <div key={day.date} className="bar-col" title={`${day.date} · ${money(day.sales)} · ${day.orders}`}>
          <div
            className="bar"
            style={{ height: `${(Number(day.sales) / max) * 100}%`, animationDelay: `${i * 25}ms` }}
          />
          <span className="bar-label">{i % step === 0 ? day.date.slice(8) : ''}</span>
        </div>
      ))}
    </div>
  )
}

/** 24 cells, darker where more orders came in. */
function HourStrip({ hours }: { hours: Report['hours'] }) {
  const max = Math.max(1, ...hours.map((h) => h.orders))
  return (
    <div className="hour-strip" dir="ltr">
      {hours.map((h) => (
        <div
          key={h.hour}
          className="hour"
          title={`${String(h.hour).padStart(2, '0')}:00 · ${h.orders}`}
          style={{ opacity: h.orders ? 0.2 + 0.8 * (h.orders / max) : 0.08 }}
        />
      ))}
      <div className="hour-labels">
        {[0, 6, 12, 18, 23].map((h) => (
          <span key={h} style={{ insetInlineStart: `${(h / 23) * 100}%` }}>
            {String(h).padStart(2, '0')}
          </span>
        ))}
      </div>
    </div>
  )
}
