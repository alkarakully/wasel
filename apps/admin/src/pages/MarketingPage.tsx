import { Crown, Megaphone, Plus } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import { Who } from '../components/bits'
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
  Stat,
  Tabs,
  TextField,
  Toggle,
  useToast,
} from '../components/ui'
import { api, query, type Offer, type Page, type PlusRow } from '../lib/api'
import { regionForCurrency } from '../lib/countries'
import { useCountry, useI18n } from '../lib/i18n'
import { navigate, useRoute } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useAction, useLoad } from '../lib/useLoad'

export function MarketingPage({ canWrite }: { canWrite: boolean }) {
  const { t } = useI18n()
  const { search } = useRoute()
  const tab = search.get('tab') === 'plus' ? 'plus' : 'offers'
  return (
    <>
      <PageHeader title={t('nav_marketing')} />
      <Tabs
        label={t('nav_marketing')}
        value={tab}
        onChange={(v) => navigate(`/marketing${v === 'offers' ? '' : '?tab=plus'}`)}
        options={[
          { value: 'offers', label: t('offers') },
          { value: 'plus', label: t('plus') },
        ]}
      />
      {tab === 'offers' ? <Offers canWrite={canWrite} /> : <PlusMembers />}
    </>
  )
}

const STATE_TONE = { running: 'good', scheduled: 'gold', ended: 'neutral' } as const

function Offers({ canWrite }: { canWrite: boolean }) {
  const { t, money, num, pct, when } = useI18n()
  const [state, setState] = useState<'running' | 'scheduled' | 'ended' | ''>('running')
  const [page, setPage] = useState(1)
  const { country } = useCountry()
  const { data, error, loading, reload } = useLoad<Page<Offer>>(`offers/${query({ state, page, country })}`)
  const [editing, setEditing] = useState<Offer | 'new' | null>(null)

  const describe = (o: Offer) =>
    o.type === 'percent'
      ? pct(Number(o.value))
      : o.type === 'fixed'
        ? money(o.value, o.currency)
        : t(`offer_${o.type}` as StringKey)

  return (
    <section className="panel table-panel">
      <div className="toolbar">
        <Tabs
          label={t('offers')}
          value={state}
          onChange={(s) => (setState(s), setPage(1))}
          options={[
            { value: 'running', label: t('running') },
            { value: 'scheduled', label: t('scheduled') },
            { value: 'ended', label: t('ended') },
            { value: '', label: t('all') },
          ]}
        />
        {canWrite && (
          <Button tone="primary" icon={<Plus weight="light" size={18} />} onClick={() => setEditing('new')}>
            {t('new_offer')}
          </Button>
        )}
      </div>
      <ErrorNote error={error} onRetry={reload} />
      {loading && !data ? (
        <Skeleton />
      ) : data && data.results.length === 0 ? (
        <Empty icon={<Megaphone weight="light" />}>{t('nothing_here')}</Empty>
      ) : (
        data && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('title')}</th>
                  <th>{t('store')}</th>
                  <th>{t('value')}</th>
                  <th>{t('starts')}</th>
                  <th>{t('ends')}</th>
                  <th className="num">{t('orders')}</th>
                  <th>{t('status')}</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((o) => (
                  <tr key={o.id} className={canWrite ? 'clickable' : ''} onClick={() => canWrite && setEditing(o)}>
                    <td>
                      {o.title}
                      {o.is_banner && <span className="sub">{t('banner')}</span>}
                    </td>
                    <td>{o.store?.name ?? <Badge tone="lapis">{t('platform_wide')}</Badge>}</td>
                    <td>
                      {describe(o)}
                      {Number(o.min_order) > 0 && <span className="sub">≥ {money(o.min_order, o.currency)}</span>}
                    </td>
                    <td className="muted">{when(o.starts_at)}</td>
                    <td className="muted">{when(o.ends_at)}</td>
                    <td className="num">{num(o.orders ?? 0)}</td>
                    <td>
                      <Badge tone={STATE_TONE[o.state]}>{t(o.state)}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
      {editing && (
        <OfferDrawer
          offer={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => (setEditing(null), void reload())}
        />
      )}
    </section>
  )
}

/** datetime-local wants "YYYY-MM-DDTHH:MM" in local time. */
function localInput(iso: string) {
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

function OfferDrawer({ offer, onClose, onSaved }: { offer: Offer | null; onClose: () => void; onSaved: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const here = useCountry().region
  const stores = useLoad<{ id: number; name: string }[]>(`stores/choices/?country=${offer?.country ?? here.country}`)
  const currency = offer?.currency ?? here.currency
  const decimals = regionForCurrency(currency).decimals
  const save = useAction()
  const remove = useAction()
  const now = new Date()
  const [form, setForm] = useState({
    title: offer?.title ?? '',
    vendor: offer?.store ? String(offer.store.id) : '',
    type: offer?.type ?? 'percent',
    value: offer?.value ?? '',
    min_order: String(offer?.min_order ?? 0),
    starts_at: localInput(offer?.starts_at ?? now.toISOString()),
    ends_at: localInput(offer?.ends_at ?? new Date(now.getTime() + 7 * 86_400_000).toISOString()),
    is_banner: offer?.is_banner ?? false,
  })
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))
  const errors = save.error?.fields ?? {}

  async function submit(e: FormEvent) {
    e.preventDefault()
    const body = {
      ...form,
      vendor: form.vendor ? Number(form.vendor) : null,
      // A platform-wide offer runs in the selected country, in its currency.
      country: offer?.country ?? here.country,
      value: form.type === 'free_delivery' ? '0' : form.value,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
    }
    const ok = await save.run(() =>
      api(offer ? `offers/${offer.id}/` : 'offers/', { method: offer ? 'PATCH' : 'POST', body }),
    )
    if (ok) {
      toast(t('saved'))
      onSaved()
    }
  }
  async function end() {
    if (!offer) return
    const ok = await remove.run(() => api(`offers/${offer.id}/`, { method: 'DELETE' }).then(() => true))
    if (ok) {
      toast(t('saved'))
      onSaved()
    }
  }

  return (
    <Drawer
      title={offer ? offer.title : t('new_offer')}
      onClose={onClose}
      footer={
        offer &&
        offer.state !== 'ended' && (
          <Button tone="danger" busy={remove.busy} onClick={end}>
            {offer.orders ? t('end_now') : t('delete')}
          </Button>
        )
      }
    >
      <form className="stack" onSubmit={submit}>
        <TextField
          label={t('title')}
          required
          maxLength={150}
          value={form.title}
          onChange={set('title')}
          errors={errors.title}
        />
        <SelectField
          label={t('store')}
          value={form.vendor}
          onChange={set('vendor')}
          options={[
            { value: '', label: t('platform_wide') },
            ...(stores.data ?? []).map((s) => ({ value: String(s.id), label: s.name })),
          ]}
        />
        <div className="grid-2">
          <SelectField
            label={t('type')}
            value={form.type}
            onChange={set('type')}
            options={(['percent', 'fixed', 'free_delivery', 'bundle'] as const).map((v) => ({
              value: v,
              label: t(`offer_${v}` as StringKey),
            }))}
          />
          {form.type !== 'free_delivery' && (
            <TextField
              label={form.type === 'fixed' ? `${t('value')} · ${currency}` : `${t('value')} %`}
              dir="ltr"
              inputMode="decimal"
              required
              value={form.value}
              onChange={set('value')}
              errors={errors.value}
            />
          )}
        </div>
        <TextField
          label={`${t('min_order')} · ${currency}`}
          dir="ltr"
          inputMode={decimals ? 'decimal' : 'numeric'}
          value={form.min_order}
          onChange={set('min_order')}
          errors={errors.min_order}
        />
        <div className="grid-2">
          <TextField
            label={t('starts')}
            type="datetime-local"
            required
            value={form.starts_at}
            onChange={set('starts_at')}
            errors={errors.starts_at}
          />
          <TextField
            label={t('ends')}
            type="datetime-local"
            required
            value={form.ends_at}
            onChange={set('ends_at')}
            errors={errors.ends_at}
          />
        </div>
        <Toggle
          label={t('banner')}
          checked={form.is_banner}
          onChange={(v) => setForm((f) => ({ ...f, is_banner: v }))}
        />
        {Object.keys(errors).length === 0 && <ErrorNote error={save.error ?? remove.error} />}
        {errors.non_field_errors && <p className="field-error">{errors.non_field_errors.join(' ')}</p>}
        <Button tone="primary" type="submit" busy={save.busy}>
          {t('save')}
        </Button>
      </form>
    </Drawer>
  )
}

function PlusMembers() {
  const { t, num, when } = useI18n()
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data, error, loading, reload } = useLoad<Page<PlusRow> & { counts: Record<string, number> }>(
    `plus/${query({ status, q, page })}`,
  )
  return (
    <>
      {data && (
        <section className="tiles three">
          <Stat tone="hero" label={t('plus_active')} value={num(data.counts.active ?? 0)} />
          <Stat label={t('plus_trial')} value={num(data.counts.trial ?? 0)} />
          <Stat label={t('plus_expired')} value={num(data.counts.expired ?? 0)} />
        </section>
      )}
      <section className="panel table-panel">
        <div className="toolbar">
          <SearchBox value={q} onChange={(v) => (setQ(v), setPage(1))} placeholder={t('search_people')} />
          <Tabs
            label={t('plus')}
            value={status}
            onChange={(v) => (setStatus(v), setPage(1))}
            options={[
              { value: '', label: t('all') },
              { value: 'active', label: t('plus_active') },
              { value: 'trial', label: t('plus_trial') },
              { value: 'expired', label: t('plus_expired') },
            ]}
          />
        </div>
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton />
        ) : data && data.results.length === 0 ? (
          <Empty icon={<Crown weight="light" />}>{t('nothing_here')}</Empty>
        ) : (
          data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('customer')}</th>
                    <th>{t('status')}</th>
                    <th>{t('trial_ends')}</th>
                    <th>{t('renews')}</th>
                    <th>{t('joined')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((s) => (
                    <tr key={s.id} className="clickable" onClick={() => navigate(`/people/${s.user.id}`)}>
                      <td>
                        <Who name={s.user.name} phone={s.user.phone} />
                      </td>
                      <td>
                        <Badge tone={s.status === 'active' ? 'good' : s.status === 'trial' ? 'gold' : 'neutral'}>
                          {t(`plus_${s.status}` as StringKey)}
                        </Badge>
                      </td>
                      <td className="muted">{when(s.trial_end, false)}</td>
                      <td className="muted">{when(s.renews_at, false)}</td>
                      <td className="muted">{when(s.created_at, false)}</td>
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
