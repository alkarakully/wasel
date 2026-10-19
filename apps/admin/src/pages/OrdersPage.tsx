import { Bell, CheckCircle, Motorcycle, Prohibit, UserMinus } from '@phosphor-icons/react'
import { useState } from 'react'

import { Phone, StatusBadge, Who } from '../components/bits'
import { ReasonDialog } from '../components/ReasonDialog'
import {
  Badge,
  Button,
  Drawer,
  Empty,
  ErrorNote,
  PageHeader,
  Pager,
  SearchBox,
  SelectField,
  Skeleton,
  Tabs,
  useToast,
} from '../components/ui'
import {
  api,
  query,
  type Alert,
  type CaptainPin,
  type OrderDetail,
  type OrderRow,
  type OrderStatus,
  type Page,
} from '../lib/api'
import { useCountry, useI18n } from '../lib/i18n'
import { navigate, useRoute } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useAction, useLoad } from '../lib/useLoad'

type Tab = 'live' | 'all' | 'alerts' | 'captains'
const STATUSES: OrderStatus[] = ['received', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled']

export function OrdersPage({ id, canWrite }: { id: string; canWrite: boolean }) {
  const { t } = useI18n()
  const { search } = useRoute()
  const tab = (
    ['live', 'all', 'alerts', 'captains'].includes(search.get('tab') ?? '') ? search.get('tab') : 'live'
  ) as Tab
  const setTab = (next: Tab) => navigate(`/orders${next === 'live' ? '' : `?tab=${next}`}`)
  const { country } = useCountry()
  const alerts = useLoad<Alert[]>(`alerts/?country=${country}`, 20_000)

  return (
    <>
      <PageHeader title={t('nav_orders')} />
      <Tabs
        label={t('nav_orders')}
        value={tab}
        onChange={setTab}
        options={[
          { value: 'live', label: t('live') },
          { value: 'all', label: t('all_orders') },
          { value: 'alerts', label: t('alerts'), count: alerts.data?.length },
          { value: 'captains', label: t('captains') },
        ]}
      />
      {tab === 'alerts' ? (
        <AlertsList alerts={alerts} canWrite={canWrite} />
      ) : tab === 'captains' ? (
        <CaptainsList />
      ) : (
        <OrdersTable scope={tab} />
      )}
      {id && (
        <OrderDrawer
          id={Number(id)}
          canWrite={canWrite}
          onChanged={alerts.reload}
          onClose={() => navigate(`/orders${tab === 'live' ? '' : `?tab=${tab}`}`)}
        />
      )}
    </>
  )
}

function OrdersTable({ scope }: { scope: 'live' | 'all' }) {
  const { t, money, num, when } = useI18n()
  const { country } = useCountry()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const { data, error, loading, reload } = useLoad<Page<OrderRow>>(
    `orders/${query({ scope, q, status: scope === 'all' ? status : '', page, country })}`,
    scope === 'live' ? 15_000 : undefined,
  )
  const open = (orderId: number) => navigate(`/orders/${orderId}${scope === 'all' ? '?tab=all' : ''}`)

  return (
    <section className="panel table-panel">
      <div className="toolbar">
        <SearchBox value={q} onChange={(v) => (setQ(v), setPage(1))} placeholder={t('search_orders')} />
        {scope === 'all' && (
          <SelectField
            label={t('status')}
            value={status}
            onChange={(e) => (setStatus(e.target.value), setPage(1))}
            options={[
              { value: '', label: t('all') },
              ...STATUSES.map((s) => ({ value: s, label: t(`st_${s}` as StringKey) })),
            ]}
          />
        )}
      </div>
      <ErrorNote error={error} onRetry={reload} />
      {loading && !data ? (
        <Skeleton />
      ) : data && data.results.length === 0 ? (
        <Empty icon={<Motorcycle weight="light" />}>{q || status ? t('no_results') : t('nothing_here')}</Empty>
      ) : (
        data && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>{t('status')}</th>
                  <th>{t('store')}</th>
                  <th>{t('customer')}</th>
                  <th>{t('captain')}</th>
                  <th className="num">{t('total')}</th>
                  <th>{scope === 'live' ? '' : t('date')}</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((o) => (
                  <tr key={o.id} className="clickable" onClick={() => open(o.id)}>
                    <td>
                      <button type="button" className="row-link" onClick={(e) => (e.stopPropagation(), open(o.id))}>
                        #{o.id}
                      </button>
                    </td>
                    <td>
                      <span className="cell-stack">
                        <StatusBadge status={o.status} />
                        {(o.alerts as string[]).map((a) => (
                          <Badge key={a} tone="warn">
                            {t(`alert_${a}` as StringKey)}
                          </Badge>
                        ))}
                      </span>
                    </td>
                    <td>{o.store.name}</td>
                    <td>
                      <Who name={o.customer.name} phone={o.customer.phone} />
                    </td>
                    <td>
                      {o.captain ? (
                        <Who name={o.captain.name} phone={o.captain.phone} />
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="num">
                      {money(o.total, o.currency)}
                      <span className="sub">{t(`pay_${o.payment_type}` as StringKey)}</span>
                    </td>
                    <td className={scope === 'live' && o.minutes >= 30 ? 'late' : 'muted'}>
                      {scope === 'live' ? t('minutes_ago', { n: num(o.minutes) }) : when(o.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
    </section>
  )
}

function AlertsList({ alerts, canWrite }: { alerts: ReturnType<typeof useLoad<Alert[]>>; canWrite: boolean }) {
  const { t, num } = useI18n()
  const toast = useToast()
  const { run, busy } = useAction()
  const { data, error, reload } = alerts
  async function resolve(alert: Alert) {
    const ok = await run(() => api(`alerts/${alert.id}/resolve/`, { method: 'POST' }))
    if (ok !== undefined) {
      toast(t('saved'))
      void reload()
    }
  }
  return (
    <section className="panel">
      <ErrorNote error={error} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={4} />
      ) : data.length === 0 ? (
        <Empty icon={<CheckCircle weight="light" />}>{t('nothing_here')}</Empty>
      ) : (
        <ul className="alert-list">
          {data.map((a) => (
            <li key={a.id} className="alert-row">
              <Bell weight="light" size={22} className="alert-icon" aria-hidden="true" />
              <button type="button" className="alert-main" onClick={() => navigate(`/orders/${a.order}?tab=alerts`)}>
                <strong>{t(`alert_${a.reason}` as StringKey)}</strong>
                <span className="muted">
                  #{a.order} · {a.store} · {t('minutes_ago', { n: num(a.minutes) })}
                </span>
              </button>
              <StatusBadge status={a.status} />
              {canWrite && (
                <Button busy={busy} onClick={() => resolve(a)}>
                  {t('resolve')}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function CaptainsList() {
  const { t, num } = useI18n()
  const { country } = useCountry()
  const { data, error, reload } = useLoad<{ captains: CaptainPin[] }>(`map/?country=${country}`, 20_000)
  const ago = (s: number) =>
    s < 90
      ? `${num(s)}s`
      : s < 5400
        ? t('minutes_ago', { n: num(Math.round(s / 60)) })
        : `${num(Math.round(s / 3600))}h`
  return (
    <section className="panel">
      <ErrorNote error={error} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={4} />
      ) : data.captains.length === 0 ? (
        <Empty icon={<Motorcycle weight="light" />}>{t('nothing_here')}</Empty>
      ) : (
        <ul className="captain-grid">
          {data.captains.map((c) => (
            <li key={c.id} className={`captain-card ${c.online ? 'online' : ''}`}>
              <span className="presence" aria-hidden="true" />
              <div>
                <strong>{c.name || '—'}</strong>
                <Phone value={c.phone} />
              </div>
              <div className="captain-meta">
                <Badge tone={c.online ? 'good' : 'neutral'}>{c.online ? t('online') : t('offline')}</Badge>
                {c.order ? (
                  <button type="button" className="link" onClick={() => navigate(`/orders/${c.order}?tab=captains`)}>
                    {t('carrying', { n: c.order })}
                  </button>
                ) : (
                  c.online && <span className="muted">{t('free')}</span>
                )}
                <span className="muted small">{t('seen_ago', { t: ago(c.seconds_ago) })}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function OrderDrawer({
  id,
  canWrite,
  onClose,
  onChanged,
}: {
  id: number
  canWrite: boolean
  onClose: () => void
  onChanged: () => void
}) {
  const { t, money, num, when } = useI18n()
  const toast = useToast()
  const { data, error, reload, setData } = useLoad<OrderDetail>(`orders/${id}/`)
  const action = useAction()
  const [dialog, setDialog] = useState<'cancel' | 'release' | null>(null)

  async function act(path: string, body?: unknown) {
    const result = await action.run(() =>
      api<OrderDetail & { offered?: boolean }>(`orders/${id}/${path}/`, { method: 'POST', body }),
    )
    if (!result) return
    setData(result)
    setDialog(null)
    onChanged()
    toast(path === 'dispatch' ? (result.offered ? t('offered') : t('nobody_free')) : t('saved'))
  }

  const by = (who: string) => t(`by_${who}` as StringKey)

  return (
    <Drawer
      title={t('order_n', { n: id })}
      onClose={onClose}
      footer={
        canWrite &&
        data &&
        (data.can_cancel || data.can_release || data.can_dispatch) && (
          <>
            {data.can_dispatch && (
              <Button
                tone="primary"
                icon={<Motorcycle weight="light" size={18} />}
                busy={action.busy}
                onClick={() => act('dispatch')}
              >
                {t('send_to_dispatch')}
              </Button>
            )}
            {data.can_release && (
              <Button
                icon={<UserMinus weight="light" size={18} />}
                onClick={() => (action.clear(), setDialog('release'))}
              >
                {t('release_captain')}
              </Button>
            )}
            {data.can_cancel && (
              <Button
                tone="danger"
                icon={<Prohibit weight="light" size={18} />}
                onClick={() => (action.clear(), setDialog('cancel'))}
              >
                {t('cancel_order')}
              </Button>
            )}
          </>
        )
      }
    >
      <ErrorNote error={error} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={8} />
      ) : (
        <div className="stack">
          <div className="cell-stack">
            <StatusBadge status={data.status} />
            <Badge
              tone={data.payment_status === 'paid' ? 'good' : data.payment_status === 'refunded' ? 'gold' : 'neutral'}
            >
              {t(`pay_${data.payment_type}` as StringKey)} · {t(`pay_${data.payment_status}` as StringKey)}
            </Badge>
            {data.cancelled_by && <Badge tone="bad">{t('cancelled_by', { who: by(data.cancelled_by) })}</Badge>}
          </div>
          {data.cancel_reason && <p className="quote">{data.cancel_reason}</p>}

          <dl className="facts two">
            <div>
              <dt>{t('store')}</dt>
              <dd>
                <button type="button" className="link" onClick={() => navigate(`/stores/${data.store.id}`)}>
                  {data.store.name}
                </button>
              </dd>
            </div>
            <div>
              <dt>{t('customer')}</dt>
              <dd>
                <button type="button" className="link" onClick={() => navigate(`/people/${data.customer.id}`)}>
                  <Who name={data.customer.name} phone={data.customer.phone} />
                </button>
              </dd>
            </div>
            <div>
              <dt>{t('captain')}</dt>
              <dd>{data.captain ? <Who name={data.captain.name} phone={data.captain.phone} /> : '—'}</dd>
            </div>
            <div>
              <dt>{t('address')}</dt>
              <dd>{data.delivery_address}</dd>
            </div>
          </dl>

          <section>
            <h3>{t('items')}</h3>
            <ul className="items">
              {data.items.map((item, i) => (
                <li key={i}>
                  <span className="qty">{num(Number(item.quantity))}×</span>
                  <span>
                    {item.name}
                    {item.options.length > 0 && <span className="sub">{item.options.join('، ')}</span>}
                  </span>
                  <span className="num">{money(item.price, data.currency)}</span>
                </li>
              ))}
            </ul>
            <dl className="totals">
              <div>
                <dt>{t('subtotal')}</dt>
                <dd>{money(data.subtotal, data.currency)}</dd>
              </div>
              <div>
                <dt>{t('delivery_fee')}</dt>
                <dd>{money(data.delivery_fee, data.currency)}</dd>
              </div>
              <div>
                <dt>{t('service_fee')}</dt>
                <dd>{money(data.service_fee, data.currency)}</dd>
              </div>
              {Number(data.tip) > 0 && (
                <div>
                  <dt>{t('tip')}</dt>
                  <dd>{money(data.tip, data.currency)}</dd>
                </div>
              )}
              {Number(data.discount) > 0 && (
                <div>
                  <dt>{t('discount')}</dt>
                  <dd>−{money(data.discount, data.currency)}</dd>
                </div>
              )}
              <div className="grand">
                <dt>{t('total')}</dt>
                <dd>{money(data.total, data.currency)}</dd>
              </div>
              <div className="muted">
                <dt>{t('commission')}</dt>
                <dd>{money(data.commission, data.currency)}</dd>
              </div>
            </dl>
          </section>

          <section>
            <h3>{t('timeline')}</h3>
            <ol className="timeline">
              {data.timeline.map((step) => (
                <li key={step.step} className={`tl-${step.step}`}>
                  <span>{t(`tl_${step.step}` as StringKey)}</span>
                  <time className="muted">{when(step.at, true, data.time_zone)}</time>
                </li>
              ))}
            </ol>
          </section>

          {data.alerts.length > 0 && (
            <section>
              <h3>{t('alerts')}</h3>
              <ul className="plain">
                {data.alerts.map((a) => (
                  <li key={a.id}>
                    <Badge tone={a.resolved_at ? 'neutral' : 'warn'}>{t(`alert_${a.reason}` as StringKey)}</Badge>{' '}
                    <span className="muted">{when(a.created_at, true, data.time_zone)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.offers.length > 0 && (
            <section>
              <h3>{t('dispatch_offers')}</h3>
              <ul className="plain">
                {data.offers.map((o, i) => (
                  <li key={i}>
                    <Who name={o.captain.name} phone={o.captain.phone} /> · {num(Math.round(o.distance_m / 100) / 10)}{' '}
                    km · <span className="muted">{t(`offer_st_${o.status}` as StringKey)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
      {dialog === 'cancel' && (
        <ReasonDialog
          title={t('cancel_order')}
          lead={t('cancel_order_lead')}
          confirm={t('cancel_order')}
          danger
          busy={action.busy}
          error={action.error}
          onClose={() => setDialog(null)}
          onSubmit={(reason) => act('cancel', { reason })}
        />
      )}
      {dialog === 'release' && (
        <ReasonDialog
          title={t('release_captain')}
          lead={t('release_lead')}
          confirm={t('release_captain')}
          busy={action.busy}
          error={action.error}
          onClose={() => setDialog(null)}
          onSubmit={(reason) => act('release', { reason })}
        />
      )}
    </Drawer>
  )
}
