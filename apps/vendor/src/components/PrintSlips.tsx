import { createPortal } from 'react-dom'

import type { Order } from '../lib/api'
import { useI18n } from '../lib/i18n'

interface Props {
  order: Order
  storeName: string
}

function clock(iso: string | null | undefined) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

function quantity(item: Order['items'][number]) {
  const n = Number(item.quantity)
  return item.unit_type === 'kg' ? `${n} kg` : `${n}×`
}

/**
 * Two 80 mm slips for one order: a kitchen ticket with what to cook, and a
 * package slip to clip to the bag. Only shown when printing (see styles.css).
 * The delivery PIN is never printed: it's the customer's proof of delivery.
 */
export function PrintSlips({ order, storeName }: Props) {
  const { t, money, name } = useI18n()
  const count = order.items.reduce((sum, item) => sum + (item.unit_type === 'kg' ? 1 : Number(item.quantity)), 0)
  const items = order.items.map((item) => (
    <li key={item.id}>
      <span className="slip-qty">{quantity(item)}</span>
      <span>
        {name(item.name)}
        {item.modifiers.length > 0 && (
          <span className="slip-mods">{item.modifiers.map((m) => name(m.name)).join('، ')}</span>
        )}
      </span>
    </li>
  ))

  return createPortal(
    <div id="print-root" aria-hidden="true">
      <section className="slip">
        <header>
          <span className="slip-brand">واصل</span>
          <span className="slip-kind">{t('kitchenTicket')}</span>
        </header>
        <p className="slip-store">{storeName}</p>
        <p className="slip-number">#{order.id}</p>
        <dl className="slip-times">
          <dt>{t('placed')}</dt>
          <dd>{clock(order.created_at)}</dd>
          {order.estimated_ready_at && (
            <>
              <dt>{t('readyBy')}</dt>
              <dd>{clock(order.estimated_ready_at)}</dd>
            </>
          )}
        </dl>
        <ul className="slip-items slip-large">{items}</ul>
        <p className="slip-foot">{t('itemsCount', { n: count })}</p>
      </section>

      <section className="slip">
        <header>
          <span className="slip-brand">واصل</span>
          <span className="slip-kind">{t('packageSlip')}</span>
        </header>
        <p className="slip-number">#{order.id}</p>
        {order.customer_contact?.name && (
          <p className="slip-customer">
            {t('customer')}: <strong>{order.customer_contact.name}</strong>
          </p>
        )}
        <ul className="slip-items slip-check">{items}</ul>
        <p className="slip-pay">
          {order.payment_type === 'cod' ? t('collectCash', { amount: money(order.total_amount) }) : t('paidInApp')}
        </p>
        <p className="slip-foot">{t('checkItems')}</p>
        <p className="slip-thanks">{t('thanks', { store: storeName })}</p>
      </section>
    </div>,
    document.body,
  )
}
