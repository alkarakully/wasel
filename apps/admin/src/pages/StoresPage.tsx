import { CheckCircle, ForkKnife, Plus, Storefront, Trash, UserPlus, XCircle } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'

import { Phone, Who } from '../components/bits'
import { PhoneField } from '../components/PhoneField'
import { ReasonDialog } from '../components/ReasonDialog'
import {
  Badge,
  Button,
  Drawer,
  Empty,
  ErrorNote,
  PageHeader,
  SearchBox,
  SelectField,
  Skeleton,
  Tabs,
  TextField,
  Toggle,
  useToast,
} from '../components/ui'
import { api, type Product, type StoreDetail, type StoreRow, type StoreStatus, type Team } from '../lib/api'
import { query } from '../lib/api'
import { country as countryInfo, region as regionOf, regionForCurrency, REGIONS } from '../lib/countries'
import { useCountry, useI18n } from '../lib/i18n'
import { navigate, useRoute } from '../lib/router'
import type { StringKey } from '../lib/strings'
import { useAction, useLoad } from '../lib/useLoad'

const CUISINES = ['popular', 'eastern', 'western', 'fast_food', 'sweets', 'drinks']

export function StoresPage({ id, canWrite }: { id: string; canWrite: boolean }) {
  const { t, money, num, pct } = useI18n()
  const { search } = useRoute()
  const status = (
    ['approved', 'pending', 'rejected'].includes(search.get('status') ?? '') ? search.get('status') : 'approved'
  ) as StoreStatus
  const [q, setQ] = useState('')
  const { country } = useCountry()
  const { data, error, loading, reload } = useLoad<{ counts: Record<StoreStatus, number>; results: StoreRow[] }>(
    `stores/${query({ status, q, country })}`,
  )
  const back = `/stores${status === 'approved' ? '' : `?status=${status}`}`

  return (
    <>
      <PageHeader
        title={t('nav_stores')}
        actions={
          canWrite && (
            <Button
              tone="primary"
              icon={<Plus weight="light" size={18} />}
              onClick={() => navigate(`/stores/new${status === 'approved' ? '' : `?status=${status}`}`)}
            >
              {t('new_store')}
            </Button>
          )
        }
      />
      <Tabs
        label={t('nav_stores')}
        value={status}
        onChange={(s) => navigate(`/stores${s === 'approved' ? '' : `?status=${s}`}`)}
        options={(['approved', 'pending', 'rejected'] as const).map((s) => ({
          value: s,
          label: t(`st_${s}` as StringKey),
          count: data?.counts[s],
        }))}
      />
      <section className="panel table-panel">
        <div className="toolbar">
          <SearchBox value={q} onChange={setQ} placeholder={t('search_stores')} />
        </div>
        <ErrorNote error={error} onRetry={reload} />
        {loading && !data ? (
          <Skeleton />
        ) : data && data.results.length === 0 ? (
          <Empty icon={<Storefront weight="light" />}>{q ? t('no_results') : t('nothing_here')}</Empty>
        ) : (
          data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{t('store')}</th>
                    <th>{t('owner')}</th>
                    <th>{t('type')}</th>
                    <th className="num">{t('commission_rate')}</th>
                    {status === 'approved' && <th className="num">{t('today_orders')}</th>}
                    <th>{status === 'approved' ? t('status') : t('created')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((s) => (
                    <tr
                      key={s.id}
                      className="clickable"
                      onClick={() => navigate(`/stores/${s.id}${status === 'approved' ? '' : `?status=${status}`}`)}
                    >
                      <td>
                        <button
                          type="button"
                          className="row-link"
                          onClick={(e) => (
                            e.stopPropagation(),
                            navigate(`/stores/${s.id}${status === 'approved' ? '' : `?status=${status}`}`)
                          )}
                        >
                          {s.name}
                        </button>
                      </td>
                      <td>
                        <Who name={s.owner.name} phone={s.owner.phone} />
                      </td>
                      <td>
                        {t(`type_${s.type}` as StringKey)}
                        {s.cuisine && <span className="sub">{t(`cu_${s.cuisine}` as StringKey)}</span>}
                      </td>
                      <td className="num">{pct(Number(s.commission_rate))}</td>
                      {status === 'approved' && (
                        <td className="num">
                          {num(s.orders_today ?? 0)}
                          <span className="sub">{money(s.sales_today ?? 0, s.currency)}</span>
                        </td>
                      )}
                      <td>
                        {status === 'approved' ? (
                          <Badge tone={s.is_open ? 'good' : 'neutral'}>{s.is_open ? t('open') : t('closed')}</Badge>
                        ) : (
                          <CreatedAt iso={s.created_at} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </section>
      {id === 'new' ? (
        <NewStoreDrawer
          onClose={() => navigate(back)}
          onCreated={(s) => (void reload(), navigate(`/stores/${s.id}`))}
        />
      ) : (
        id && <StoreDrawer id={Number(id)} canWrite={canWrite} onClose={() => navigate(back)} onChanged={reload} />
      )}
    </>
  )
}

function CreatedAt({ iso }: { iso: string }) {
  const { when } = useI18n()
  return <span className="muted">{when(iso, false)}</span>
}

// --- New store -----------------------------------------------------------------

function NewStoreDrawer({ onClose, onCreated }: { onClose: () => void; onCreated: (s: StoreDetail) => void }) {
  const { t, lang } = useI18n()
  const toast = useToast()
  const { busy, error, run } = useAction()
  const here = useCountry().region
  const [form, setForm] = useState({
    name: '',
    type: 'restaurant',
    cuisine: '',
    address: '',
    country: here.country,
    latitude: String(here.center.lat),
    longitude: String(here.center.lng),
    owner_phone: '',
    owner_country: here.country,
    owner_name: '',
    commission_rate: '15',
  })
  // A new country moves the map spot to its capital, unless one was typed.
  const setCountry = (code: string) =>
    setForm((f) => {
      const old = regionOf(f.country).center
      const moved = f.latitude === String(old.lat) && f.longitude === String(old.lng)
      const c = regionOf(code).center
      return {
        ...f,
        country: code,
        owner_country: f.owner_phone ? f.owner_country : code,
        ...(moved ? { latitude: String(c.lat), longitude: String(c.lng) } : {}),
      }
    })
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))
  const fieldErrors = error?.fields ?? {}

  async function submit(e: FormEvent) {
    e.preventDefault()
    const store = await run(() =>
      api<StoreDetail>('stores/', {
        method: 'POST',
        body: { ...form, latitude: Number(form.latitude), longitude: Number(form.longitude) },
      }),
    )
    if (store) {
      toast(t('saved'))
      onCreated(store)
    }
  }

  return (
    <Drawer title={t('new_store')} onClose={onClose}>
      <form className="stack" onSubmit={submit} id="new-store">
        <TextField
          label={t('store_name')}
          required
          value={form.name}
          onChange={set('name')}
          errors={fieldErrors.name}
        />
        <div className="grid-2">
          <SelectField
            label={t('type')}
            value={form.type}
            onChange={set('type')}
            options={['restaurant', 'supermarket'].map((v) => ({ value: v, label: t(`type_${v}` as StringKey) }))}
          />
          <SelectField
            label={t('cuisine')}
            value={form.cuisine}
            onChange={set('cuisine')}
            options={[
              { value: '', label: '—' },
              ...CUISINES.map((v) => ({ value: v, label: t(`cu_${v}` as StringKey) })),
            ]}
          />
        </div>
        <SelectField
          label={t('store_country')}
          value={form.country}
          onChange={(e) => setCountry(e.target.value)}
          errors={fieldErrors.country}
          options={REGIONS.map((r) => ({
            value: r.country,
            label: `${countryInfo(r.country)![lang === 'ar' ? 'ar' : 'en']} · ${r.currency}`,
          }))}
        />
        <TextField label={t('address')} value={form.address} onChange={set('address')} errors={fieldErrors.address} />
        <div className="grid-2">
          <TextField
            label={t('latitude')}
            inputMode="decimal"
            dir="ltr"
            required
            value={form.latitude}
            onChange={set('latitude')}
            errors={fieldErrors.latitude}
          />
          <TextField
            label={t('longitude')}
            inputMode="decimal"
            dir="ltr"
            required
            value={form.longitude}
            onChange={set('longitude')}
            errors={fieldErrors.longitude}
          />
        </div>
        <div className="grid-2">
          <PhoneField
            label={t('owner_phone')}
            required
            phone={form.owner_phone}
            country={form.owner_country}
            onPhone={(v) => setForm((f) => ({ ...f, owner_phone: v }))}
            onCountry={(c) => setForm((f) => ({ ...f, owner_country: c }))}
            errors={fieldErrors.owner_phone}
          />
          <TextField label={t('owner_name')} value={form.owner_name} onChange={set('owner_name')} />
        </div>
        <TextField
          label={t('commission_rate')}
          inputMode="decimal"
          dir="ltr"
          value={form.commission_rate}
          onChange={set('commission_rate')}
          errors={fieldErrors.commission_rate}
        />
        {Object.keys(fieldErrors).length === 0 && <ErrorNote error={error} />}
        <Button tone="primary" type="submit" busy={busy}>
          {t('save')}
        </Button>
      </form>
    </Drawer>
  )
}

// --- One store ----------------------------------------------------------------

type StoreTab = 'details' | 'menu' | 'team'

function StoreDrawer({
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
  const { t } = useI18n()
  const toast = useToast()
  const { data, error, reload, setData } = useLoad<StoreDetail>(`stores/${id}/`)
  const [tab, setTab] = useState<StoreTab>('details')
  const review = useAction()
  const [rejecting, setRejecting] = useState(false)

  async function decide(decision: 'approve' | 'reject', reason = '') {
    const store = await review.run(() =>
      api<StoreDetail>(`stores/${id}/review/`, { method: 'POST', body: { decision, reason } }),
    )
    if (store) {
      setData(store)
      setRejecting(false)
      onChanged()
      toast(t('saved'))
    }
  }

  return (
    <Drawer
      wide
      title={data?.name ?? '…'}
      onClose={onClose}
      footer={
        canWrite &&
        data &&
        data.status !== 'approved' && (
          <>
            <Button
              tone="primary"
              icon={<CheckCircle weight="light" size={18} />}
              busy={review.busy}
              onClick={() => decide('approve')}
            >
              {t('approve')}
            </Button>
            {data.status === 'pending' && (
              <Button
                tone="danger"
                icon={<XCircle weight="light" size={18} />}
                onClick={() => (review.clear(), setRejecting(true))}
              >
                {t('reject')}
              </Button>
            )}
          </>
        )
      }
    >
      <ErrorNote error={error ?? (rejecting ? null : review.error)} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={8} />
      ) : (
        <>
          <div className="cell-stack">
            <Badge tone={data.status === 'approved' ? 'good' : data.status === 'pending' ? 'gold' : 'bad'}>
              {t(`st_${data.status}` as StringKey)}
            </Badge>
            {data.status === 'approved' && (
              <Badge tone={data.is_open ? 'good' : 'neutral'}>{data.is_open ? t('open') : t('closed')}</Badge>
            )}
          </div>
          {data.rejection_reason && <p className="quote">{t('rejected_because', { r: data.rejection_reason })}</p>}
          <Tabs
            label={data.name}
            value={tab}
            onChange={setTab}
            options={[
              { value: 'details', label: t('details') },
              { value: 'menu', label: t('menu') },
              { value: 'team', label: t('team') },
            ]}
          />
          {tab === 'details' && (
            <StoreDetails key={data.id} store={data} canWrite={canWrite} onSaved={(s) => (setData(s), onChanged())} />
          )}
          {tab === 'menu' && <StoreMenu storeId={id} canWrite={canWrite} currency={data.currency} />}
          {tab === 'team' && <StoreTeam storeId={id} canWrite={canWrite} />}
        </>
      )}
      {rejecting && (
        <ReasonDialog
          title={t('reject')}
          confirm={t('reject')}
          hint={t('reject_reason_hint')}
          danger
          busy={review.busy}
          error={review.error}
          onClose={() => setRejecting(false)}
          onSubmit={(reason) => decide('reject', reason)}
        />
      )}
    </Drawer>
  )
}

function StoreDetails({
  store,
  canWrite,
  onSaved,
}: {
  store: StoreDetail
  canWrite: boolean
  onSaved: (s: StoreDetail) => void
}) {
  const { t } = useI18n()
  const toast = useToast()
  const { busy, error, run } = useAction()
  const initial = {
    name: store.name,
    type: store.type,
    cuisine: store.cuisine,
    address: store.address,
    latitude: String(store.latitude),
    longitude: String(store.longitude),
    delivery_radius_km: store.delivery_radius_km,
    commission_rate: store.commission_rate,
    commission_free_until: store.commission_free_until?.slice(0, 10) ?? '',
    // Iraqi numbers the local way; others keep their + code, which the server reads whatever country is picked.
    owner_phone: store.owner.phone.startsWith('+964') ? `0${store.owner.phone.slice(4)}` : store.owner.phone,
    owner_country: 'IQ',
    is_open: store.is_open,
  }
  const [form, setForm] = useState(initial)
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))
  const errors = error?.fields ?? {}
  const dirty = JSON.stringify(form) !== JSON.stringify(initial)

  async function submit(e: FormEvent) {
    e.preventDefault()
    const body: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(form)) {
      if (value === initial[key as keyof typeof initial]) continue
      if (key === 'latitude' || key === 'longitude') {
        body.latitude = Number(form.latitude)
        body.longitude = Number(form.longitude)
      } else if (key === 'commission_free_until') body[key] = value ? `${value}T00:00:00` : null
      else body[key] = value
    }
    if (body.owner_phone) body.owner_country = form.owner_country
    const saved = await run(() => api<StoreDetail>(`stores/${store.id}/`, { method: 'PATCH', body }))
    if (saved) {
      toast(t('saved'))
      onSaved(saved)
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <fieldset disabled={!canWrite} className="stack">
        {store.status === 'approved' && (
          <Toggle
            label={t('accepting_orders')}
            checked={form.is_open}
            onChange={(v) => setForm((f) => ({ ...f, is_open: v }))}
          />
        )}
        <TextField label={t('store_name')} value={form.name} onChange={set('name')} errors={errors.name} />
        <div className="grid-2">
          <SelectField
            label={t('type')}
            value={form.type}
            onChange={set('type')}
            options={['restaurant', 'supermarket'].map((v) => ({ value: v, label: t(`type_${v}` as StringKey) }))}
          />
          <SelectField
            label={t('cuisine')}
            value={form.cuisine}
            onChange={set('cuisine')}
            options={[
              { value: '', label: '—' },
              ...CUISINES.map((v) => ({ value: v, label: t(`cu_${v}` as StringKey) })),
            ]}
          />
        </div>
        <TextField label={t('address')} value={form.address} onChange={set('address')} errors={errors.address} />
        <div className="grid-3">
          <TextField
            label={t('latitude')}
            dir="ltr"
            inputMode="decimal"
            value={form.latitude}
            onChange={set('latitude')}
            errors={errors.latitude}
          />
          <TextField
            label={t('longitude')}
            dir="ltr"
            inputMode="decimal"
            value={form.longitude}
            onChange={set('longitude')}
            errors={errors.longitude}
          />
          <TextField
            label={t('radius')}
            dir="ltr"
            inputMode="decimal"
            value={form.delivery_radius_km}
            onChange={set('delivery_radius_km')}
            errors={errors.delivery_radius_km}
          />
        </div>
        <div className="grid-2">
          <TextField
            label={t('commission_rate')}
            dir="ltr"
            inputMode="decimal"
            value={form.commission_rate}
            onChange={set('commission_rate')}
            errors={errors.commission_rate}
          />
          <TextField
            label={t('commission_free_until')}
            type="date"
            value={form.commission_free_until}
            onChange={set('commission_free_until')}
            errors={errors.commission_free_until}
          />
        </div>
        <PhoneField
          label={t('owner_phone')}
          phone={form.owner_phone}
          country={form.owner_country}
          onPhone={(v) => setForm((f) => ({ ...f, owner_phone: v }))}
          onCountry={(c) => setForm((f) => ({ ...f, owner_country: c }))}
          errors={errors.owner_phone}
        />
      </fieldset>
      {Object.keys(errors).length === 0 && <ErrorNote error={error} />}
      {canWrite && (
        <div className="row-end">
          <Button tone="primary" type="submit" busy={busy} disabled={!dirty}>
            {t('save')}
          </Button>
        </div>
      )}
    </form>
  )
}

function StoreMenu({ storeId, canWrite, currency }: { storeId: number; canWrite: boolean; currency: string }) {
  const { t, money } = useI18n()
  const decimals = regionForCurrency(currency).decimals
  const { data, error, reload, setData } = useLoad<Product[]>(`stores/${storeId}/menu/`)
  const action = useAction()
  const [draft, setDraft] = useState({ name_ar: '', name_en: '', menu_section: '', price: '' })

  async function add(e: FormEvent) {
    e.preventDefault()
    const product = await action.run(() => api<Product>(`stores/${storeId}/menu/`, { method: 'POST', body: draft }))
    if (product && data) {
      setData([...data, product])
      setDraft({ name_ar: '', name_en: '', menu_section: draft.menu_section, price: '' })
    }
  }
  async function toggle(p: Product) {
    const updated = await action.run(() =>
      api<Product>(`products/${p.id}/`, { method: 'PATCH', body: { is_available: !p.is_available } }),
    )
    if (updated && data) setData(data.map((x) => (x.id === p.id ? updated : x)))
  }
  async function remove(p: Product) {
    const ok = await action.run(() => api(`products/${p.id}/`, { method: 'DELETE' }).then(() => true))
    if (ok && data) setData(data.filter((x) => x.id !== p.id))
  }

  const sections = data ? [...new Set(data.map((p) => p.menu_section || '—'))] : []
  return (
    <div className="stack">
      <ErrorNote error={error ?? action.error} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={5} />
      ) : data.length === 0 ? (
        <Empty icon={<ForkKnife weight="light" />}>{t('nothing_here')}</Empty>
      ) : (
        sections.map((section) => (
          <section key={section}>
            <h3>{section}</h3>
            <ul className="menu-list">
              {data
                .filter((p) => (p.menu_section || '—') === section)
                .map((p) => (
                  <li key={p.id} className={p.is_available ? '' : 'unavailable'}>
                    <span>
                      {p.name_ar}
                      {p.name_en && <span className="sub">{p.name_en}</span>}
                    </span>
                    <span className="num">
                      {money(p.price, currency)}
                      {p.unit_type === 'kg' && <span className="sub">{t('per_kg')}</span>}
                    </span>
                    <Toggle
                      label={p.is_available ? t('available') : t('out_of_stock')}
                      checked={p.is_available}
                      disabled={!canWrite || action.busy}
                      onChange={() => toggle(p)}
                    />
                    {canWrite && (
                      <button
                        type="button"
                        className="icon-btn"
                        aria-label={`${t('remove')} ${p.name_ar}`}
                        onClick={() => remove(p)}
                      >
                        <Trash weight="light" size={18} />
                      </button>
                    )}
                  </li>
                ))}
            </ul>
          </section>
        ))
      )}
      {canWrite && data && (
        <form className="inline-form" onSubmit={add}>
          <h3>{t('add_item')}</h3>
          <div className="grid-2">
            <TextField
              label={t('item_name_ar')}
              required
              value={draft.name_ar}
              onChange={(e) => setDraft({ ...draft, name_ar: e.target.value })}
              errors={action.error?.fields.name_ar}
            />
            <TextField
              label={t('item_name_en')}
              value={draft.name_en}
              onChange={(e) => setDraft({ ...draft, name_en: e.target.value })}
            />
            <TextField
              label={t('section')}
              value={draft.menu_section}
              onChange={(e) => setDraft({ ...draft, menu_section: e.target.value })}
            />
            <TextField
              label={`${t('price')} · ${currency}`}
              dir="ltr"
              inputMode={decimals ? 'decimal' : 'numeric'}
              pattern={decimals ? `[0-9]+([.][0-9]{1,${decimals}})?` : '[0-9]+'}
              required
              value={draft.price}
              onChange={(e) => setDraft({ ...draft, price: e.target.value })}
              errors={action.error?.fields.price}
            />
          </div>
          <div className="row-end">
            <Button tone="primary" type="submit" busy={action.busy} icon={<Plus weight="light" size={18} />}>
              {t('add_item')}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}

function StoreTeam({ storeId, canWrite }: { storeId: number; canWrite: boolean }) {
  const { t } = useI18n()
  const { data, error, reload } = useLoad<Team>(`stores/${storeId}/team/`)
  const action = useAction()
  const [phone, setPhone] = useState('')
  const [phoneCountry, setPhoneCountry] = useState(useCountry().country)
  const [role, setRole] = useState('cashier')

  async function add(e: FormEvent) {
    e.preventDefault()
    const ok = await action.run(() =>
      api(`stores/${storeId}/team/`, { method: 'POST', body: { phone, country: phoneCountry, role } }),
    )
    if (ok) {
      setPhone('')
      void reload()
    }
  }
  async function change(memberId: number, nextRole: string) {
    if (
      await action.run(() => api(`stores/${storeId}/team/${memberId}/`, { method: 'PATCH', body: { role: nextRole } }))
    )
      void reload()
  }
  async function remove(memberId: number) {
    if (
      (await action.run(() => api(`stores/${storeId}/team/${memberId}/`, { method: 'DELETE' }).then(() => true))) !==
      undefined
    )
      void reload()
  }

  return (
    <div className="stack">
      <ErrorNote error={error ?? (action.error?.fields.phone ? null : action.error)} onRetry={reload} />
      {!data ? (
        !error && <Skeleton rows={3} />
      ) : (
        <ul className="team-list">
          <li>
            <Who name={data.owner.name} phone={data.owner.phone} />
            <Badge tone="lapis">{t('owner')}</Badge>
          </li>
          {data.members.map((m) => (
            <li key={m.id}>
              <Who name={m.name} phone={m.phone} />
              {canWrite ? (
                <select aria-label={t('role')} value={m.role} onChange={(e) => change(m.id, e.target.value)}>
                  <option value="manager">{t('manager')}</option>
                  <option value="cashier">{t('cashier')}</option>
                </select>
              ) : (
                <Badge>{t(m.role)}</Badge>
              )}
              {canWrite && (
                <button type="button" className="icon-btn" aria-label={t('remove')} onClick={() => remove(m.id)}>
                  <Trash weight="light" size={18} />
                </button>
              )}
            </li>
          ))}
          {data.invites.map((i) => (
            <li key={`i${i.id}`} className="muted">
              <Phone value={i.phone} />
              <Badge tone="gold">{t('invited')}</Badge>
            </li>
          ))}
        </ul>
      )}
      {canWrite && (
        <form className="inline-form" onSubmit={add}>
          <h3>{t('add_member')}</h3>
          <div className="grid-2">
            <PhoneField
              label={t('phone')}
              required
              phone={phone}
              country={phoneCountry}
              onPhone={setPhone}
              onCountry={setPhoneCountry}
              errors={action.error?.fields.phone}
            />
            <SelectField
              label={t('role')}
              value={role}
              onChange={(e) => setRole(e.target.value)}
              options={[
                { value: 'manager', label: t('manager') },
                { value: 'cashier', label: t('cashier') },
              ]}
            />
          </div>
          <div className="row-end">
            <Button tone="primary" type="submit" busy={action.busy} icon={<UserPlus weight="light" size={18} />}>
              {t('add_member')}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
