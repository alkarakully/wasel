import { PencilSimple, Plus, SealPercent, StopCircle, X } from '@phosphor-icons/react'
import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from 'react'

import { Api, type OfferInput, type OfferType, type StoreOffer } from '../lib/api'
import { regionForCurrency } from '../lib/countries'
import { useI18n } from '../lib/i18n'
import { amountInput } from '../lib/strings'

interface Props {
  api: Api
  storeId: number
  currency: string
  onError: (error: unknown) => void
}

const TYPES: OfferType[] = ['percent', 'fixed', 'free_delivery']
const ORDER: Record<StoreOffer['state'], number> = {
  running: 0,
  scheduled: 1,
  ended: 2,
}

/** "2026-10-20T15:30" for a datetime-local input, in the browser's clock. */
function localInput(date: Date): string {
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return shifted.toISOString().slice(0, 16)
}

/** The store's own discounts: percent or amount off, or free delivery, for a set time. */
export function OffersView({ api, storeId, currency, onError }: Props) {
  const { t, lang, money } = useI18n()
  const [offers, setOffers] = useState<StoreOffer[] | null>(null)
  const [editing, setEditing] = useState<StoreOffer | 'new' | null>(null)

  const load = useCallback(() => {
    api.offers(storeId).then(setOffers, onError)
  }, [api, storeId, onError])
  useEffect(load, [load])

  const when = (iso: string) =>
    new Intl.DateTimeFormat(lang === 'en' ? 'en-GB' : `${lang}-IQ`, {
      day: 'numeric',
      month: 'short',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(iso))

  const summary = (offer: StoreOffer) => {
    const deal =
      offer.type === 'percent'
        ? t('offerPercent', { value: offer.value })
        : offer.type === 'fixed'
          ? t('offerFixed', { value: money(offer.value, offer.currency) })
          : t('offerFree')
    return Number(offer.min_order) > 0
      ? `${deal} · ${t('offerMin', { value: money(offer.min_order, offer.currency) })}`
      : deal
  }

  const end = async (offer: StoreOffer) => {
    if (!window.confirm(t('endOfferConfirm', { name: offer.title }))) return
    try {
      await api.endOffer(storeId, offer.id)
      load()
    } catch (e) {
      onError(e)
    }
  }

  const saved = () => {
    setEditing(null)
    load()
  }

  const sorted = [...(offers ?? [])].sort((a, b) => ORDER[a.state] - ORDER[b.state])

  return (
    <div className="offers">
      <p className="muted offers-help">{t('offersHelp')}</p>
      <div className="menu-tools">
        {editing === 'new' ? (
          <OfferForm
            api={api}
            storeId={storeId}
            currency={currency}
            onSaved={saved}
            onCancel={() => setEditing(null)}
          />
        ) : (
          <button type="button" className="primary" onClick={() => setEditing('new')}>
            <Plus size={20} weight="light" aria-hidden="true" />
            {t('newOffer')}
          </button>
        )}
      </div>
      {offers && offers.length === 0 && editing !== 'new' && (
        <p className="empty">
          <SealPercent size={40} weight="light" aria-hidden="true" />
          {t('noOffers')}
        </p>
      )}
      {sorted.length > 0 && (
        <ul className="offer-list">
          {sorted.map((offer, index) =>
            editing !== 'new' && editing?.id === offer.id ? (
              <li key={offer.id} className="editing">
                <OfferForm
                  api={api}
                  storeId={storeId}
                  currency={currency}
                  offer={offer}
                  onSaved={saved}
                  onCancel={() => setEditing(null)}
                />
              </li>
            ) : (
              <li
                key={offer.id}
                className={`offer-row ${offer.state}`}
                style={{ '--i': Math.min(index, 10) } as CSSProperties}
              >
                <span className="offer-badge" aria-hidden="true">
                  <SealPercent size={24} weight="light" />
                </span>
                <span className="offer-text">
                  <span className="product-name">{offer.title}</span>
                  <span className="offer-deal">{summary(offer)}</span>
                  <span className="muted small">
                    {when(offer.starts_at)} – {when(offer.ends_at)}
                    {offer.orders ? ` · ${t('offerUsed', { n: offer.orders })}` : ''}
                    {offer.is_banner ? ` · ${t('onHomeBanner')}` : ''}
                  </span>
                </span>
                <span className={`chip state-${offer.state}`}>{t(`state_${offer.state}`)}</span>
                {offer.state !== 'ended' && (
                  <span className="row-actions">
                    <button
                      type="button"
                      className="icon-button"
                      title={t('editOffer')}
                      onClick={() => setEditing(offer)}
                    >
                      <PencilSimple size={18} weight="light" aria-hidden="true" />
                      <span className="sr-only">
                        {t('editOffer')} {offer.title}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="icon-button danger-icon"
                      title={t('endOffer')}
                      onClick={() => end(offer)}
                    >
                      <StopCircle size={18} weight="light" aria-hidden="true" />
                      <span className="sr-only">
                        {t('endOffer')} {offer.title}
                      </span>
                    </button>
                  </span>
                )}
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  )
}

interface FormProps {
  api: Api
  storeId: number
  currency: string
  offer?: StoreOffer
  onSaved: () => void
  onCancel: () => void
}

function OfferForm({ api, storeId, currency, offer, onSaved, onCancel }: FormProps) {
  const { t, error } = useI18n()
  const decimals = regionForCurrency(currency).decimals
  const [values, setValues] = useState<OfferInput>(() => {
    if (offer) {
      return {
        title: offer.title,
        type: offer.type,
        value: offer.type === 'free_delivery' ? '' : offer.value,
        min_order: offer.min_order,
        starts_at: localInput(new Date(offer.starts_at)),
        ends_at: localInput(new Date(offer.ends_at)),
      }
    }
    const now = new Date()
    return {
      title: '',
      type: 'percent',
      value: '',
      min_order: '0',
      starts_at: localInput(now),
      ends_at: localInput(new Date(now.getTime() + 7 * 86_400_000)),
    }
  })
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const set = (key: keyof OfferInput) => (value: string) => setValues((v) => ({ ...v, [key]: value }))

  const value = Number(values.value)
  const valueOk = values.type === 'free_delivery' || (values.type === 'percent' ? value > 0 && value <= 100 : value > 0)
  const datesOk = values.starts_at !== '' && values.ends_at !== '' && values.ends_at > values.starts_at
  const valid = values.title.trim() !== '' && valueOk && datesOk

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!valid) return
    setBusy(true)
    setProblem(null)
    const body: OfferInput = {
      ...values,
      value: values.type === 'free_delivery' ? '0' : values.value,
      min_order: values.min_order || '0',
      starts_at: new Date(values.starts_at).toISOString(),
      ends_at: new Date(values.ends_at).toISOString(),
    }
    try {
      if (offer) await api.updateOffer(storeId, offer.id, body)
      else await api.addOffer(storeId, body)
      onSaved()
    } catch {
      setProblem(error('generic'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="item-form" onSubmit={submit}>
      <div className="form-head">
        <strong>{offer ? t('editOffer') : t('newOffer')}</strong>
        <button type="button" className="icon-button" onClick={onCancel} title={t('cancel')}>
          <X size={18} weight="light" aria-hidden="true" />
          <span className="sr-only">{t('cancel')}</span>
        </button>
      </div>
      <div className="form-grid">
        <label className="wide">
          {t('offerTitle')}
          <input
            className="text-input"
            required
            maxLength={150}
            placeholder={t('offerTitleHint')}
            value={values.title}
            onChange={(e) => set('title')(e.target.value)}
          />
        </label>
        <fieldset className="unit wide">
          <legend>{t('offerType')}</legend>
          <div className="segmented">
            {TYPES.map((type) => (
              <button key={type} type="button" aria-pressed={values.type === type} onClick={() => set('type')(type)}>
                {t(`type_${type}`)}
              </button>
            ))}
          </div>
        </fieldset>
        {values.type !== 'free_delivery' && (
          <label>
            {values.type === 'percent' ? t('percentOff') : `${t('amountOff')} · ${currency}`}
            <input
              className="text-input"
              dir="ltr"
              inputMode={values.type === 'fixed' && decimals ? 'decimal' : 'numeric'}
              required
              value={values.value}
              onChange={(e) => set('value')(amountInput(e.target.value, values.type === 'percent' ? 0 : decimals))}
            />
          </label>
        )}
        <label>
          {t('minOrder')} · {currency}
          <input
            className="text-input"
            dir="ltr"
            inputMode={decimals ? 'decimal' : 'numeric'}
            placeholder={t('minOrderHint')}
            value={values.min_order}
            onChange={(e) => set('min_order')(amountInput(e.target.value, decimals))}
          />
        </label>
        <label>
          {t('startsAt')}
          <input
            className="text-input"
            type="datetime-local"
            dir="ltr"
            required
            value={values.starts_at}
            onChange={(e) => set('starts_at')(e.target.value)}
          />
        </label>
        <label>
          {t('endsAt')}
          <input
            className="text-input"
            type="datetime-local"
            dir="ltr"
            required
            value={values.ends_at}
            onChange={(e) => set('ends_at')(e.target.value)}
          />
        </label>
      </div>
      {!datesOk && values.starts_at && values.ends_at && (
        <p className="error small" role="alert">
          {t('offerEndsBeforeStart')}
        </p>
      )}
      {problem && (
        <p className="error" role="alert">
          {problem}
        </p>
      )}
      <div className="actions">
        <button type="submit" className="primary" disabled={!valid || busy}>
          {t('save')}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          {t('cancel')}
        </button>
      </div>
    </form>
  )
}
