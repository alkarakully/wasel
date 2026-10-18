import { Bank, DownloadSimple, Eye, Info } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'

import { Api, type Billing, type Statement, type StatementLine } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  api: Api
  storeId: number
  onError: (error: unknown) => void
}

/**
 * What Wasel pays the store: this week so far, weekly statements (Saturday to
 * Friday) with every order, and payout history. Owners only.
 */
export function BillingView({ api, storeId, onError }: Props) {
  const { t, money } = useI18n()
  const [billing, setBilling] = useState<Billing | null>(null)
  const [open, setOpen] = useState<Statement | null>(null)

  useEffect(() => {
    api.billing(storeId).then(setBilling, onError)
  }, [api, storeId, onError])

  if (!billing) {
    return (
      <div className="bento loading" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton-card">
            <span className="bone short" />
            <span className="bone tall" />
          </div>
        ))}
      </div>
    )
  }

  const week = billing.current_week
  return (
    <div className="billing">
      <div className="bento billing-top">
        <article className="tile hero glaze">
          <p className="eyebrow">{t('thisWeek')}</p>
          <p className="big">{money(week.payout)}</p>
          <span className="gold-rule" />
          <p className="sub">
            {t('weekRange', { from: week.period_start, to: week.period_end })} ·{' '}
            {t('deliveredOf', { n: week.orders_count })}
          </p>
          <dl className="breakdown">
            <dt>{t('foodSales')}</dt>
            <dd>{money(week.food_sales)}</dd>
            {week.store_discounts > 0 && (
              <>
                <dt>{t('storeDiscounts')}</dt>
                <dd>−{money(week.store_discounts)}</dd>
              </>
            )}
            <dt>{t('commissionLabel')}</dt>
            <dd>−{money(week.commission)}</dd>
          </dl>
        </article>
        <article className="tile">
          <p className="label">
            <Bank size={20} weight="light" aria-hidden="true" />
            {t('dueTotal')}
          </p>
          <p className="num">{money(billing.due_total)}</p>
        </article>
        <article className="tile">
          <p className="label">
            <Bank size={20} weight="light" aria-hidden="true" />
            {t('paidTotal')}
          </p>
          <p className="num">{money(billing.paid_total)}</p>
        </article>
      </div>

      <p className="note">
        <Info size={20} weight="light" aria-hidden="true" />
        {t('billingHow', { rate: billing.commission_rate })}
      </p>

      <section className="plate-card">
        <h2>{t('statements')}</h2>
        {billing.statements.length === 0 ? (
          <p className="muted">{t('noStatements')}</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>{t('week')}</th>
                <th>{t('ordersLabel')}</th>
                <th>{t('foodSales')}</th>
                <th>{t('commissionLabel')}</th>
                <th>{t('payout')}</th>
                <th>{t('status')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {billing.statements.map((s) => (
                <tr key={s.id}>
                  <td dir="ltr" className="num">
                    {s.period_start} → {s.period_end}
                  </td>
                  <td className="num">{s.orders_count}</td>
                  <td className="num">{money(s.food_sales)}</td>
                  <td className="num">{money(s.commission)}</td>
                  <td className="num">
                    <strong>{money(s.payout)}</strong>
                  </td>
                  <td>
                    <span className={`chip ${s.status}`}>{s.status === 'paid' ? t('paidStatus') : t('due')}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="icon-button"
                      title={t('statementTitle', { from: s.period_start, to: s.period_end })}
                      onClick={() => setOpen(s)}
                    >
                      <Eye size={18} weight="light" aria-hidden="true" />
                      <span className="sr-only">{t('statementTitle', { from: s.period_start, to: s.period_end })}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {open && (
        <StatementDialog api={api} storeId={storeId} statement={open} onClose={() => setOpen(null)} onError={onError} />
      )}
    </div>
  )
}

interface DialogProps {
  api: Api
  storeId: number
  statement: Statement
  onClose: () => void
  onError: (error: unknown) => void
}

function StatementDialog({ api, storeId, statement, onClose, onError }: DialogProps) {
  const { t, money } = useI18n()
  const dialog = useRef<HTMLDialogElement>(null)
  const [lines, setLines] = useState<StatementLine[] | null>(null)

  useEffect(() => {
    dialog.current?.showModal()
    api.statement(storeId, statement.id).then((s) => setLines(s.orders), onError)
  }, [api, storeId, statement.id, onError])

  const payment = (type: StatementLine['payment_type']) =>
    type === 'cod' ? t('cash') : type === 'card' ? t('card') : t('wallet')

  return (
    <dialog ref={dialog} className="dialog statement" onCancel={onClose} aria-labelledby="statement-title">
      <h2 id="statement-title">{t('statementTitle', { from: statement.period_start, to: statement.period_end })}</h2>
      <p className="muted">
        {statement.status === 'paid' && statement.paid_at
          ? `${t('paidOn', { date: statement.paid_at.slice(0, 10) })}${statement.paid_reference ? ` · ${statement.paid_reference}` : ''}`
          : t('due')}
      </p>
      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th>{t('order')}</th>
              <th>{t('payment')}</th>
              <th>{t('foodSales')}</th>
              <th>{t('commissionLabel')}</th>
              <th>{t('payout')}</th>
            </tr>
          </thead>
          <tbody>
            {lines?.map((line) => (
              <tr key={line.order}>
                <td className="num">#{line.order}</td>
                <td>{payment(line.payment_type)}</td>
                <td className="num">{money(line.food_sales)}</td>
                <td className="num">−{money(line.commission + line.store_discount)}</td>
                <td className="num">{money(line.payout)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2}>{t('total')}</td>
              <td className="num">{money(statement.food_sales)}</td>
              <td className="num">−{money(statement.commission + statement.store_discounts)}</td>
              <td className="num">
                <strong>{money(statement.payout)}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <div className="actions">
        <button
          type="button"
          className="primary"
          onClick={() => api.downloadStatement(storeId, statement).catch(onError)}
        >
          <DownloadSimple size={20} weight="light" aria-hidden="true" />
          {t('download')}
        </button>
        <button type="button" className="secondary" onClick={onClose}>
          {t('close')}
        </button>
      </div>
    </dialog>
  )
}
