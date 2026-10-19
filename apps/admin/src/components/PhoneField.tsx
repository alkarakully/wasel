import { CaretDown, MagnifyingGlass } from '@phosphor-icons/react'
import { useEffect, useId, useMemo, useRef, useState } from 'react'

import { COUNTRIES, country as countryInfo, flag, SHORT_LIST } from '../lib/countries'
import { useI18n } from '../lib/i18n'

/** A phone number with its country: Iraq by default, then the Gulf, then every country. */
export function PhoneField({
  label,
  phone,
  country,
  onPhone,
  onCountry,
  errors,
  required,
}: {
  label: string
  phone: string
  country: string
  onPhone: (value: string) => void
  onCountry: (code: string) => void
  errors?: string[]
  required?: boolean
}) {
  const { t, lang } = useI18n()
  const id = useId()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const box = useRef<HTMLDivElement>(null)
  const selected = countryInfo(country) ?? COUNTRIES[0]
  const name = (c: (typeof COUNTRIES)[number]) => (lang === 'ar' ? c.ar : c.en)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !box.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  const matches = useMemo(() => {
    const term = q.trim().toLowerCase().replace(/^\+/, '')
    if (!term) return null
    return COUNTRIES.filter((c) => c.en.toLowerCase().includes(term) || c.ar.includes(term) || c.dial.startsWith(term))
  }, [q])

  const pick = (code: string) => {
    onCountry(code)
    setOpen(false)
    setQ('')
  }
  const option = (c: (typeof COUNTRIES)[number]) => (
    <li key={c.code}>
      <button type="button" role="option" aria-selected={c.code === country} onClick={() => pick(c.code)}>
        <span aria-hidden="true">{flag(c.code)}</span>
        <span className="cp-name">{name(c)}</span>
        <bdi dir="ltr" className="cp-dial">
          +{c.dial}
        </bdi>
      </button>
    </li>
  )

  return (
    <div className={`field ${errors?.length ? 'has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      <div className="phone-field" ref={box} dir="ltr">
        <button
          type="button"
          className="cp-button"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={`${t('phone_country')}: ${name(selected)}`}
          onClick={() => setOpen(!open)}
        >
          <span aria-hidden="true">{flag(selected.code)}</span>+{selected.dial}
          <CaretDown weight="light" size={12} aria-hidden="true" />
        </button>
        <input
          id={id}
          type="tel"
          inputMode="tel"
          autoComplete="tel-national"
          required={required}
          value={phone}
          aria-invalid={!!errors?.length}
          placeholder={country === 'IQ' ? '07xx xxx xxxx' : ''}
          onChange={(e) => onPhone(e.target.value)}
        />
        {open && (
          <div className="cp-panel" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
            <label className="search">
              <MagnifyingGlass weight="light" size={16} aria-hidden="true" />
              <input
                autoFocus
                type="search"
                value={q}
                placeholder={t('search_countries')}
                aria-label={t('search_countries')}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
            <ul role="listbox" aria-label={t('phone_country')}>
              {matches ? (
                matches.map(option)
              ) : (
                <>
                  {SHORT_LIST.map((code) => option(countryInfo(code)!))}
                  <li className="cp-divider" role="presentation">
                    {t('all_countries')}
                  </li>
                  {COUNTRIES.filter((c) => !SHORT_LIST.includes(c.code)).map(option)}
                </>
              )}
            </ul>
          </div>
        )}
      </div>
      {errors?.length ? <p className="field-error">{errors.join(' ')}</p> : null}
    </div>
  )
}
