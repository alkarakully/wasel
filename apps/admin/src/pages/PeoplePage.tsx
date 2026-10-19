import { LockKey, LockKeyOpen, UsersThree, Wallet } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import { Phone, StatusBadge } from '../components/bits'
import { ReasonDialog } from '../components/ReasonDialog'
import {
  Badge,
  Button,
  Drawer,
  Empty,
  ErrorNote,
  Field,
  Modal,
  PageHeader,
  Pager,
  SearchBox,
  Skeleton,
  Tabs,
  TextField,
  useToast,
} from '../components/ui'
import { api, query, type Page, type UserDetail, type UserRow } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { navigate, useRoute } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useAction, useLoad } from '../lib/useLoad'

type Role = UserRow['role']

export function PeoplePage({ id, canWrite, canMoney }: { id: string; canWrite: boolean; canMoney: boolean }) {
  const { t, money, num, when } = useI18n()
  const { search } = useRoute()
  const role = (
    ['customer', 'captain', 'vendor'].includes(search.get('role') ?? '') ? search.get('role') : 'customer'
  ) as Role
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data, error, loading, reload } = useLoad<Page<UserRow> & { counts: Record<Role, number> }>(
    `users/${query({ role, q, page })}`,
  )
  const suffix = role === 'customer' ? '' : `?role=${role}`

  return (
    <>
      <PageHeader title={t('nav_people')} />
      <Tabs
        label={t('nav_people')}
        value={role}
        onChange={(r) => (setPage(1), navigate(`/people${r === 'customer' ? '' : `?role=${r}`}`))}
        options={(['customer', 'captain', 'vendor'] as const).map((r) => ({
          value: r,
          label: t(`role_${r}` as StringKey),
          count: data?.counts[r],
        }))}
      />
      <section className="panel table-panel">
        <div className="toolbar">
          <SearchBox value={q} onChange={(v) => (setQ(v), setPage(1))} placeholder={t('search_people')} />
        </div>
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton />
        ) : data && data.results.length === 0 ? (
          <Empty icon={<UsersThree weight="light" />}>{q ? t('no_results') : t('nothing_here')}</Empty>
        ) : (
          data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('name')}</th>
                    <th>{t('phone')}</th>
                    <th className="num">{t('orders_count')}</th>
                    <th className="num">{t('wallet')}</th>
                    <th>{t('joined')}</th>
                    <th>{t('status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((u) => (
                    <tr key={u.id} className="clickable" onClick={() => navigate(`/people/${u.id}${suffix}`)}>
                      <td>
                        <button
                          type="button"
                          className="row-link"
                          onClick={(e) => (e.stopPropagation(), navigate(`/people/${u.id}${suffix}`))}
                        >
                          {u.name || '—'}
                        </button>
                      </td>
                      <td>
                        <Phone value={u.phone} />
                      </td>
                      <td className="num">{num(u.orders ?? 0)}</td>
                      <td className="num">{money(u.wallet_balance)}</td>
                      <td className="muted">{when(u.joined, false)}</td>
                      <td>
                        {u.is_active ? (
                          <Badge tone="good">{t('active')}</Badge>
                        ) : (
                          <Badge tone="bad">{t('blocked')}</Badge>
                        )}
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
      {id && (
        <PersonDrawer
          id={Number(id)}
          canWrite={canWrite}
          canMoney={canMoney}
          onChanged={reload}
          onClose={() => navigate(`/people${suffix}`)}
        />
      )}
    </>
  )
}

function PersonDrawer({
  id,
  canWrite,
  canMoney,
  onClose,
  onChanged,
}: {
  id: number
  canWrite: boolean
  canMoney: boolean
  onClose: () => void
  onChanged: () => void
}) {
  const { t, money, num, when } = useI18n()
  const toast = useToast()
  const { data, error, reload, setData } = useLoad<UserDetail>(`users/${id}/`)
  const action = useAction()
  const [dialog, setDialog] = useState<'block' | 'wallet' | null>(null)

  async function setActive(isActive: boolean, reason = '') {
    const row = await action.run(() =>
      api<UserRow>(`users/${id}/active/`, { method: 'POST', body: { is_active: isActive, reason } }),
    )
    if (row && data) {
      setData({ ...data, is_active: row.is_active })
      setDialog(null)
      onChanged()
      toast(t('saved'))
    }
  }

  return (
    <Drawer
      title={data ? data.name || data.phone : '…'}
      onClose={onClose}
      footer={
        data &&
        (canWrite || canMoney) && (
          <>
            {canMoney && (
              <Button icon={<Wallet weight="light" size={18} />} onClick={() => (action.clear(), setDialog('wallet'))}>
                {t('adjust_wallet')}
              </Button>
            )}
            {canWrite &&
              (data.is_active ? (
                <Button
                  tone="danger"
                  icon={<LockKey weight="light" size={18} />}
                  onClick={() => (action.clear(), setDialog('block'))}
                >
                  {t('block')}
                </Button>
              ) : (
                <Button
                  icon={<LockKeyOpen weight="light" size={18} />}
                  busy={action.busy}
                  onClick={() => setActive(true)}
                >
                  {t('unblock')}
                </Button>
              ))}
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
            <Badge tone="lapis">{t(`role_${data.role}` as StringKey)}</Badge>
            {data.is_active ? <Badge tone="good">{t('active')}</Badge> : <Badge tone="bad">{t('blocked')}</Badge>}
            {data.plus && <Badge tone="gold">{`${t('plus')} · ${t(`plus_${data.plus.status}` as StringKey)}`}</Badge>}
          </div>
          <dl className="facts two">
            <div>
              <dt>{t('phone')}</dt>
              <dd>
                <Phone value={data.phone} />
              </dd>
            </div>
            <div>
              <dt>{t('balance')}</dt>
              <dd>{money(data.wallet_balance)}</dd>
            </div>
            <div>
              <dt>{data.role === 'captain' ? t('deliveries') : t('orders_count')}</dt>
              <dd>{num(data.role === 'captain' ? data.deliveries : data.orders_count)}</dd>
            </div>
            <div>
              <dt>{t('spend')}</dt>
              <dd>{money(data.delivered_spend)}</dd>
            </div>
            <div>
              <dt>{t('joined')}</dt>
              <dd>{when(data.joined, false)}</dd>
            </div>
            <div>
              <dt>{t('last_login')}</dt>
              <dd>{when(data.last_login)}</dd>
            </div>
          </dl>
          {data.stores.length > 0 && (
            <section>
              <h3>{t('stores')}</h3>
              <ul className="plain">
                {data.stores.map((s) => (
                  <li key={`${s.id}-${s.role}`}>
                    <button type="button" className="link" onClick={() => navigate(`/stores/${s.id}`)}>
                      {s.name}
                    </button>{' '}
                    <Badge>{s.role === 'owner' ? t('owner') : t(s.role as StringKey)}</Badge>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section>
            <h3>{t('recent_orders')}</h3>
            {data.recent_orders.length === 0 ? (
              <p className="muted">{t('nothing_here')}</p>
            ) : (
              <ul className="mini-rows">
                {data.recent_orders.map((o) => (
                  <li key={o.id}>
                    <button type="button" className="link" onClick={() => navigate(`/orders/${o.id}?tab=all`)}>
                      #{o.id}
                    </button>
                    <span>{o.store}</span>
                    <StatusBadge status={o.status} />
                    <span className="num">{money(o.total)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          {data.wallet.length > 0 && (
            <section>
              <h3>{t('wallet')}</h3>
              <ul className="mini-rows">
                {data.wallet.map((w) => (
                  <li key={w.id}>
                    <span>{t(`tx_${w.type}` as StringKey)}</span>
                    <span className="muted">{when(w.created_at)}</span>
                    <span className={`num ${w.amount < 0 ? 'neg' : 'pos'}`}>{money(w.amount)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
      {dialog === 'block' && (
        <ReasonDialog
          title={t('block')}
          lead={t('block_lead')}
          confirm={t('block')}
          danger
          busy={action.busy}
          error={action.error}
          onClose={() => setDialog(null)}
          onSubmit={(reason) => setActive(false, reason)}
        />
      )}
      {dialog === 'wallet' && data && (
        <WalletDialog
          userId={id}
          onClose={() => setDialog(null)}
          onDone={(balance) => {
            setDialog(null)
            toast(t('saved'))
            void reload()
            setData({ ...data, wallet_balance: balance })
          }}
        />
      )}
    </Drawer>
  )
}

function WalletDialog({
  userId,
  onClose,
  onDone,
}: {
  userId: number
  onClose: () => void
  onDone: (balance: number) => void
}) {
  const { t } = useI18n()
  const { busy, error, run } = useAction()
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  async function submit(e: FormEvent) {
    e.preventDefault()
    const result = await run(() =>
      api<{ wallet_balance: number }>(`users/${userId}/wallet/`, {
        method: 'POST',
        body: { amount: Number(amount), reason },
      }),
    )
    if (result) onDone(result.wallet_balance)
  }
  return (
    <Modal title={t('adjust_wallet')} lead={t('adjust_lead')} onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <TextField
          label={t('amount')}
          dir="ltr"
          inputMode="numeric"
          pattern="-?[0-9]+"
          required
          autoFocus
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          errors={error?.fields.amount}
        />
        <Field label={t('reason')} hint={t('reason_hint')} errors={error?.fields.reason}>
          {(fid, describedBy) => (
            <textarea
              id={fid}
              aria-describedby={describedBy}
              rows={2}
              maxLength={255}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          )}
        </Field>
        {!error?.fields.amount && !error?.fields.reason && <ErrorNote error={error} />}
        <div className="row-end">
          <Button onClick={onClose}>{t('cancel')}</Button>
          <Button tone="primary" type="submit" busy={busy}>
            {t('confirm')}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
