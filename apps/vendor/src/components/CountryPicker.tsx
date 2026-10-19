import { CaretDown, MagnifyingGlass } from '@phosphor-icons/react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { COUNTRIES, country as countryInfo, flag, SHORT_LIST, type Country } from '../lib/countries'
import { useI18n } from '../lib/i18n'
import { isRtl } from '../lib/strings'

const KEY = 'wasel-portal-phone-country'

/** The phone country last picked on this device (Iraq at first). */
export function savedPhoneCountry() {
  try {
    const code = localStorage.getItem(KEY)
    return code && countryInfo(code) ? code : 'IQ'
  } catch {
    return 'IQ'
  }
}

/**
 * The country code in front of a phone number: flag and +code, opening a
 * searchable list with Iraq first, then the Gulf, then every country.
 */
export function CountryPicker({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  const { t, lang } = useI18n()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const box = useRef<HTMLDivElement>(null)
  const selected = countryInfo(value) ?? COUNTRIES[0]
  // Kurdish readers get the Arabic names.
  const name = (c: Country) => (lang === 'en' ? c.en : c.ar)

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
    onChange(code)
    try {
      localStorage.setItem(KEY, code)
    } catch {
      /* private mode */
    }
    setOpen(false)
    setQ('')
  }

  const option = (c: Country) => (
    <li key={c.code}>
      <button type="button" role="option" aria-selected={c.code === value} onClick={() => pick(c.code)}>
        <span aria-hidden="true">{flag(c.code)}</span>
        <span className="cp-name">{name(c)}</span>
        <bdi dir="ltr" className="cp-dial">
          +{c.dial}
        </bdi>
      </button>
    </li>
  )

  return (
    <div className="cp" ref={box}>
      <button
        type="button"
        className="cp-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${t('phoneCountry')}: ${name(selected)}`}
        onClick={() => setOpen(!open)}
      >
        <span aria-hidden="true">{flag(selected.code)}</span>+{selected.dial}
        <CaretDown size={12} weight="light" aria-hidden="true" />
      </button>
      {open && (
        <div className="cp-panel" dir={isRtl(lang) ? 'rtl' : 'ltr'}>
          <label className="cp-search">
            <MagnifyingGlass size={16} weight="light" aria-hidden="true" />
            <input
              autoFocus
              type="search"
              value={q}
              placeholder={t('searchCountries')}
              aria-label={t('searchCountries')}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
          <ul role="listbox" aria-label={t('phoneCountry')}>
            {matches ? (
              matches.map(option)
            ) : (
              <>
                {SHORT_LIST.map((code) => option(countryInfo(code)!))}
                <li className="cp-divider" role="presentation">
                  {t('allCountries')}
                </li>
                {COUNTRIES.filter((c) => !SHORT_LIST.includes(c.code)).map(option)}
              </>
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
