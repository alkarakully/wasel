import { CalendarCheck, Money, Receipt } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import { Who } from '../components/bits'
import {
  Badge,
  Button,
  Empty,
  ErrorNote,
  Modal,
  PageHeader,
  Pager,
  SearchBox,
  Skeleton,
  Stat,
  Tabs,
  TextField,
  useToast,
} from '../components/ui'
import { api, query, type Page, type Statement, type WalletRow } from '../lib/api'
import { useCountry, useI18n } from '../lib/i18n'
import { navigate, useRoute } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useAction, useLoad } from '../lib/useLoad'

export function MoneyPage({ canWrite }: { canWrite: boolean }) {
  const { t } = useI18n()
  const { search } = useRoute()
  const tab = search.get('tab') === 'wallet' ? 'wallet' : 'payouts'
  return (
    <>
      <PageHeader title={t('nav_money')} />
      <Tabs
        label={t('nav_money')}
        value={tab}
        onChange={(v) => navigate(`/money${v === 'payouts' ? '' : '?tab=wallet'}`)}
        options={[
          { value: 'payouts', label: t('payouts') },
          { value: 'wallet', label: t('wallet_ledger') },
        ]}
      />
      {tab === 'payouts' ? <Payouts canWrite={canWrite} /> : <Ledger />}
    </>
  )
}

function Payouts({ canWrite }: { canWrite: boolean }) {
  const { t, money, num, day } = useI18n()
  const toast = useToast()
  const [status, setStatus] = useState<'due' | 'paid'>('due')
  const [page, setPage] = useState(1)
  const { country } = useCountry()
  const { data, error, loading, reload } = useLoad<Page<Statement> & { due_total: string; due_count: number }>(
    `payouts/${query({ status, page, country })}`,
  )
  const [paying, setPaying] = useState<Statement | null>(null)
  const close = useAction()

  async function closeWeeks() {
    const result = await close.run(() => api<{ made: number }>('payouts/close/', { method: 'POST' }))
    if (result) {
      toast(t('weeks_closed', { n: num(result.made) }))
      void reload()
    }
  }

  return (
    <>
      {data && (
        <section className="tiles two">
          <Stat
            tone="hero"
            label={t('due_total')}
            value={money(data.due_total)}
            sub={`${num(data.due_count)} ${t('week')}`}
          />
          {canWrite && (
            <div className="stat action-tile">
              <Button icon={<CalendarCheck weight="light" size={18} />} busy={close.busy} onClick={closeWeeks}>
                {t('close_weeks')}
              </Button>
              <ErrorNote error={close.error} />
            </div>
          )}
        </section>
      )}
      <section className="panel table-panel">
        <div className="toolbar">
          <Tabs
            label={t('payouts')}
            value={status}
            onChange={(s) => (setStatus(s), setPage(1))}
            options={[
              { value: 'due', label: t('due') },
              { value: 'paid', label: t('paid') },
            ]}
          />
        </div>
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton />
        ) : data && data.results.length === 0 ? (
          <Empty icon={<Money weight="light" />}>{t('nothing_here')}</Empty>
        ) : (
          data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('store')}</th>
                    <th>{t('week')}</th>
                    <th className="num">{t('orders')}</th>
                    <th className="num">{t('food_sales')}</th>
                    <th className="num">{t('commission')}</th>
                    <th className="num">{t('payout')}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <button type="button" className="row-link" onClick={() => navigate(`/stores/${s.store}`)}>
                          {s.store_name}
                        </button>
                      </td>
                      <td className="muted">
                        {day(s.period_start)} – {day(s.period_end)}
                      </td>
                      <td className="num">{num(s.orders_count)}</td>
                      <td className="num">
                        {money(s.food_sales, s.currency)}
                        {Number(s.store_discounts) > 0 && (
                          <span className="sub">−{money(s.store_discounts, s.currency)}</span>
                        )}
                      </td>
                      <td className="num">{money(s.commission, s.currency)}</td>
                      <td className="num strong">{money(s.payout, s.currency)}</td>
                      <td>
                        {s.status === 'paid' ? (
                          <Badge tone="good">{s.paid_reference || t('paid')}</Badge>
                        ) : (
                          canWrite && (
                            <Button tone="primary" onClick={() => setPaying(s)}>
                              {t('mark_paid')}
                            </Button>
                          )
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
      {paying && (
        <PayDialog
          statement={paying}
          onClose={() => setPaying(null)}
          onDone={() => {
            setPaying(null)
            toast(t('saved'))
            void reload()
          }}
        />
      )}
    </>
  )
}

function PayDialog({ statement, onClose, onDone }: { statement: Statement; onClose: () => void; onDone: () => void }) {
  const { t, money } = useI18n()
  const { busy, error, run } = useAction()
  const [reference, setReference] = useState('')
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (await run(() => api(`payouts/${statement.id}/paid/`, { method: 'POST', body: { reference } }))) onDone()
  }
  return (
    <Modal
      title={`${t('mark_paid')} · ${statement.store_name}`}
      lead={money(statement.payout, statement.currency)}
      onClose={onClose}
    >
      <form className="stack" onSubmit={submit}>
        <TextField
          label={t('reference')}
          dir="ltr"
          autoFocus
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
        <ErrorNote error={error} />
        <div className="row-end">
          <Button onClick={onClose}>{t('cancel')}</Button>
          <Button tone="primary" type="submit" busy={busy}>
            {t('mark_paid')}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

const TX = ['top_up', 'payment', 'refund', 'cashback', 'adjustment'] as const

function Ledger() {
  const { t, money, when } = useI18n()
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { country } = useCountry()
  const { data, error, loading, reload } = useLoad<Page<WalletRow> & { totals: Record<string, string> }>(
    `wallet/${query({ type, q, page, country })}`,
  )
  return (
    <>
      {data && (
        <section className="tiles five">
          {TX.map((k) => (
            <Stat key={k} label={t(`tx_${k}` as StringKey)} value={money(data.totals[k] ?? 0)} />
          ))}
        </section>
      )}
      <section className="panel table-panel">
        <div className="toolbar">
          <SearchBox value={q} onChange={(v) => (setQ(v), setPage(1))} placeholder={t('search_people')} />
          <Tabs
            label={t('type')}
            value={type}
            onChange={(v) => (setType(v), setPage(1))}
            options={[
              { value: '', label: t('all') },
              ...TX.map((k) => ({ value: k, label: t(`tx_${k}` as StringKey) })),
            ]}
          />
        </div>
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton />
        ) : data && data.results.length === 0 ? (
          <Empty icon={<Receipt weight="light" />}>{t('nothing_here')}</Empty>
        ) : (
          data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('customer')}</th>
                    <th>{t('type')}</th>
                    <th>{t('orders')}</th>
                    <th>{t('date')}</th>
                    <th className="num">{t('amount')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((w) => (
                    <tr key={w.id} className="clickable" onClick={() => navigate(`/people/${w.user.id}`)}>
                      <td>
                        <Who name={w.user.name} phone={w.user.phone} />
                      </td>
                      <td>{t(`tx_${w.type}` as StringKey)}</td>
                      <td>{w.order ? `#${w.order}` : '—'}</td>
                      <td className="muted">{when(w.created_at)}</td>
                      <td className={`num ${Number(w.amount) < 0 ? 'neg' : 'pos'}`}>{money(w.amount, w.currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
        {data && <Pager page={page} count={data.count} onPage={setPage} />}
      </section>
    </>
  )
}
