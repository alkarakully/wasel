import { Check, X } from '@phosphor-icons/react'
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
}

function minutesBetween(from: string, to = Date.now()) {
  return Math.round((to - new Date(from).getTime()) / 60000)
}

export function OrderCard({ api, order, showStore, onChanged, onError }: Props) {
  const { t, money, name } = useI18n()
  const [busy, setBusy] = useState(false)
  const [prep, setPrep] = useState(15)
  const [rejecting, setRejecting] = useState(false)

  const run = async (step: () => Promise<Order>) => {
    setBusy(true)
    try {
      onChanged(await step())
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
        <span className="muted time">{age < 1 ? t('justNow') : t('minutesAgo', { n: age })}</span>
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
        {order.payment_type === 'cod' ? t('cash') : t('paid')} · {money(order.total_amount)}
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
            <button type="button" className="primary" disabled={busy} onClick={() => run(() => api.accept(order.id, prep))}>
              <Check size={20} weight="bold" aria-hidden="true" />
              {t('accept')}
            </button>
            <button type="button" className="secondary" disabled={busy} onClick={() => setRejecting(true)}>
              <X size={20} weight="bold" aria-hidden="true" />
              {t('reject')}
            </button>
          </div>
        </>
      )}

      {order.status === 'preparing' && (
        <>
          {readyIn !== null && (
            <p className={readyIn < 0 ? 'late' : 'muted'}>
              {readyIn < 0 ? t('late', { n: -readyIn }) : t('readyIn', { n: readyIn })}
            </p>
          )}
          <div className="actions">
            <button type="button" className="primary" disabled={busy} onClick={() => run(() => api.ready(order.id))}>
              <Check size={20} weight="bold" aria-hidden="true" />
              {t('markReady')}
            </button>
          </div>
        </>
      )}

      {order.status === 'ready' && <p className="muted">{order.captain ? t('captainComing') : t('waitingCaptain')}</p>}

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
