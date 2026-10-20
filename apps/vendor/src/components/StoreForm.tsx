import { PaperPlaneTilt } from '@phosphor-icons/react'
import { lazy, Suspense, useState, type FormEvent } from 'react'

import {
  ApiError,
  CUISINES,
  type ApplicationInput,
  type Cuisine,
  type StoreApplication,
  type StoreType,
} from '../lib/api'
import { useI18n } from '../lib/i18n'
import { STORE_TYPES } from '../lib/storeTypes'
import type { LatLng } from './LocationPicker'

// The map library is big; load it only when the form opens.
const LocationPicker = lazy(() => import('./LocationPicker').then((m) => ({ default: m.LocationPicker })))

interface Props {
  /** First store: also asks the owner's name. Branch: an approved owner adds another store. */
  mode: 'first' | 'branch'
  /** A rejected application to start from. */
  from?: StoreApplication | null
  askName?: boolean
  onSubmit: (input: ApplicationInput) => Promise<unknown>
  onCancel?: () => void
}

/** The store's name, kind, address, map spot and delivery radius, sent to Wasel for approval. */
export function StoreForm({ mode, from, askName = mode === 'first', onSubmit, onCancel }: Props) {
  const { t, error: errorMessage } = useI18n()
  const [ownerName, setOwnerName] = useState('')
  const [name, setName] = useState(from?.name ?? '')
  const [type, setType] = useState<StoreType>(from?.type ?? 'restaurant')
  const [cuisine, setCuisine] = useState<Cuisine | ''>(from?.cuisine ?? '')
  const [address, setAddress] = useState(from?.address ?? '')
  const [spot, setSpot] = useState<LatLng | null>(from ? { lat: from.latitude, lng: from.longitude } : null)
  const [radius, setRadius] = useState(from ? Number(from.delivery_radius_km) : 5)
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!spot) {
      setProblem('location_required')
      return
    }
    setBusy(true)
    setProblem(null)
    try {
      await onSubmit({
        ...(askName ? { owner_name: ownerName.trim() } : {}),
        name: name.trim(),
        type,
        cuisine: type === 'restaurant' ? cuisine : '',
        address: address.trim(),
        latitude: spot.lat,
        longitude: spot.lng,
        delivery_radius_km: String(radius),
      })
    } catch (e) {
      setProblem(e instanceof ApiError ? e.code : 'generic')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="store-form" onSubmit={submit}>
      {askName && (
        <label>
          {t('yourName')}
          <input
            className="text-input"
            autoComplete="name"
            required
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
          />
        </label>
      )}
      <label>
        {t('storeName')}
        <input
          className="text-input"
          required
          maxLength={150}
          placeholder={t('storeNameHint')}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>

      <fieldset className="kind">
        <legend>{t('storeType')}</legend>
        {STORE_TYPES.map(([option, Icon]) => (
          <label key={option} className="kind-option">
            <input type="radio" name="type" checked={type === option} onChange={() => setType(option)} />
            <Icon size={28} weight="light" aria-hidden="true" />
            <span>{t(`type_${option}`)}</span>
          </label>
        ))}
      </fieldset>

      {type === 'restaurant' && (
        <label>
          {t('cuisine')}
          <select className="text-input" value={cuisine} onChange={(e) => setCuisine(e.target.value as Cuisine | '')}>
            <option value="">{t('cuisineNone')}</option>
            {CUISINES.map((c) => (
              <option key={c} value={c}>
                {t(`cuisine_${c}`)}
              </option>
            ))}
          </select>
        </label>
      )}

      <label>
        {t('address')}
        <textarea
          className="text-input"
          required
          rows={2}
          maxLength={300}
          placeholder={t('addressHint')}
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
      </label>

      <div className="field">
        <span className="field-label">{t('storeLocation')}</span>
        <Suspense fallback={<div className="map-frame loading" />}>
          <LocationPicker value={spot} radiusKm={radius} onChange={setSpot} />
        </Suspense>
      </div>

      <label>
        <span className="field-label-row">
          {t('deliveryRadius')}
          <strong>{t('km', { n: radius })}</strong>
        </span>
        <input
          type="range"
          className="range"
          min={1}
          max={20}
          step={0.5}
          value={radius}
          aria-valuetext={t('km', { n: radius })}
          onChange={(e) => setRadius(Number(e.target.value))}
        />
        <span className="help">{t('deliveryRadiusHelp')}</span>
      </label>

      {problem && (
        <p className="error" role="alert">
          {errorMessage(problem)}
        </p>
      )}
      <div className="actions">
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            {t('cancel')}
          </button>
        )}
        <button type="submit" className="primary" disabled={busy}>
          <PaperPlaneTilt size={20} weight="light" aria-hidden="true" />
          {t(mode === 'first' ? 'sendApplication' : 'sendBranch')}
        </button>
      </div>
    </form>
  )
}
