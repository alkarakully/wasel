import { useEffect, useState } from 'react'

import { Api, BOARD_STATUSES, type Order } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { OrderCard } from './OrderCard'

interface Props {
  api: Api
  orders: Order[]
  multiStore: boolean
  onChanged: (order: Order) => void
  onError: (error: unknown) => void
}

/** Three columns: new, preparing, ready. Oldest first so nothing waits too long. */
export function Board({ api, orders, multiStore, onChanged, onError }: Props) {
  const { t } = useI18n()
  // Re-render every 30s so "x min ago" and countdowns stay current.
  const [, setTick] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setTick((n) => n + 1), 30000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="board">
      {BOARD_STATUSES.map((status) => {
        const column = orders
          .filter((o) => o.status === status)
          .sort((a, b) => a.created_at.localeCompare(b.created_at))
        return (
          <section key={status} className={`column column-${status}`} aria-labelledby={`col-${status}`}>
            <h2 id={`col-${status}`}>
              {t(`col_${status}` as 'col_received')}
              <span className="count">{column.length}</span>
            </h2>
            {column.length === 0 ? (
              <p className="empty">{t('emptyColumn')}</p>
            ) : (
              column.map((order) => (
                <OrderCard
                  key={order.id}
                  api={api}
                  order={order}
                  showStore={multiStore}
                  onChanged={onChanged}
                  onError={onError}
                />
              ))
            )}
          </section>
        )
      })}
    </div>
  )
}
