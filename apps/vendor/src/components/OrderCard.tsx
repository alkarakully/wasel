import { Check, Clock, CreditCard, Hourglass, Money, Moped, Printer, Warning, X } from '@phosphor-icons/react'
import { useState } from 'react'

import { Api, type Order } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { RejectDialog } from './RejectDialog'

const PREP_CHOICES = [10, 15, 20, 30, 45]

interface Props {
  api: Api
  order: Order
  showStore: boolean
  onChanged: (order: Order) => void
  onError: (error: unknown) => void
  /** Print the kitchen ticket and package slip. */
  onPrint?: (order: Order) => void
  /** Print both slips as soon as the order is accepted. */
  autoPrint?: boolean
}

function minutesBetween(from: string, to = Date.now()) {
  return Math.round((to - new Date(from).getTime()) / 60000)
}

export function OrderCard({ api, order, showStore, onChanged, onError, onPrint, autoPrint = false }: Props) {
  const { t, money, name } = useI18n()
  const [busy, setBusy] = useState(false)
  const [prep, setPrep] = useState(15)
  const [rejecting, setRejecting] = useState(false)

  const run = async (step: () => Promise<Order>, then?: (result: Order) => void) => {
    setBusy(true)
    try {
      const result = await step()
      onChanged(result)
      then?.(result)
    } catch (e) {
      onError(e)
    } finally {
      setBusy(false)
    }
  }

  const age = minutesBetween(order.created_at)
  const readyIn = order.estimated_ready_at ? -minutesBetween(order.estimated_ready_at) : null

  return (
    <article className={`card card-${order.status}`} aria-label={`#${order.id}`}>
      <header>
        <strong className="order-id">#{order.id}</strong>
        {showStore && <span className="muted">{order.vendor_name}</span>}
        <span className="muted time">
          <Clock size={16} weight="light" aria-hidden="true" />
          {age < 1 ? t('justNow') : age < 60 ? t('minutesAgo', { n: age }) : t('hoursAgo', { n: Math.floor(age / 60) })}
        </span>
        {onPrint && (
          <button
            type="button"
            className="icon-button print-button"
            title={t('printOrder', { id: order.id })}
            onClick={() => onPrint(order)}
          >
            <Printer size={18} weight="light" aria-hidden="true" />
            <span className="sr-only">{t('printOrder', { id: order.id })}</span>
          </button>
        )}
      </header>

      <ul className="items">
        {order.items.map((item) => (
          <li key={item.id}>
            <span className="qty">
              {item.unit_type === 'kg' ? `${Number(item.quantity)} kg` : `${Number(item.quantity)}×`}
            </span>
            <span>
              {name(item.name)}
              {item.modifiers.length > 0 && (
                <span className="mods">{item.modifiers.map((m) => name(m.name)).join('، ')}</span>
              )}
            </span>
          </li>
        ))}
      </ul>

      <p className="total">
        <span className={`pay ${order.payment_type === 'cod' ? 'pay-cash' : ''}`}>
          {order.payment_type === 'cod' ? (
            <Money size={16} weight="light" aria-hidden="true" />
          ) : (
            <CreditCard size={16} weight="light" aria-hidden="true" />
          )}
          {order.payment_type === 'cod' ? t('cash') : t('paid')}
        </span>
        <span className="amount">{money(order.total_amount, order.currency)}</span>
      </p>

      {order.status === 'received' && (
        <>
          <fieldset className="prep">
            <legend>{t('prepTime')}</legend>
            {PREP_CHOICES.map((minutes) => (
              <button key={minutes} type="button" aria-pressed={prep === minutes} onClick={() => setPrep(minutes)}>
                {minutes} {t('min')}
              </button>
            ))}
          </fieldset>
          <div className="actions">
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() => run(() => api.accept(order.id, prep), autoPrint ? onPrint : undefined)}
            >
              <Check size={20} weight="light" aria-hidden="true" />
              {t('accept')}
            </button>
            <button type="button" className="secondary" disabled={busy} onClick={() => setRejecting(true)}>
              <X size={20} weight="light" aria-hidden="true" />
              {t('reject')}
            </button>
          </div>
        </>
      )}

      {order.status === 'preparing' && (
        <>
          {readyIn !== null && (
            <p className={readyIn < 0 ? 'late' : 'eta'}>
              {readyIn < 0 ? (
                <Warning size={18} weight="light" aria-hidden="true" />
              ) : (
                <Hourglass size={18} weight="light" aria-hidden="true" />
              )}
              {readyIn < 0 ? t('late', { n: -readyIn }) : t('readyIn', { n: readyIn })}
            </p>
          )}
          <div className="actions">
            <button type="button" className="primary" disabled={busy} onClick={() => run(() => api.ready(order.id))}>
              <Check size={20} weight="light" aria-hidden="true" />
              {t('markReady')}
            </button>
          </div>
        </>
      )}

      {order.status === 'ready' && (
        <p className="waiting">
          <Moped size={20} weight="light" aria-hidden="true" />
          {order.captain ? t('captainComing') : t('waitingCaptain')}
        </p>
      )}

      {rejecting && (
        <RejectDialog
          orderId={order.id}
          onCancel={() => setRejecting(false)}
          onConfirm={(reason) => {
            setRejecting(false)
            run(() => api.reject(order.id, reason))
          }}
        />
      )}
    </article>
  )
}
