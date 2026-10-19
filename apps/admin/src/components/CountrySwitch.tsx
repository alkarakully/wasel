import { CaretDown } from '@phosphor-icons/react'

import { country as countryInfo, flag, REGIONS } from '../lib/countries'
import { useCountry, useI18n } from '../lib/i18n'

/** Which operating country the numbers, money and clocks are for. */
export function CountrySwitch() {
  const { t, lang } = useI18n()
  const { country, setCountry } = useCountry()
  return (
    <label className="country-switch">
      <span className="sr-only">{t('country')}</span>
      <span className="country-flag" aria-hidden="true">
        {flag(country)}
      </span>
      <select value={country} onChange={(e) => setCountry(e.target.value)}>
        {REGIONS.map((r) => {
          const c = countryInfo(r.country)!
          return (
            <option key={r.country} value={r.country}>
              {(lang === 'ar' ? c.ar : c.en) + ' · ' + r.currency}
            </option>
          )
        })}
      </select>
      <CaretDown weight="light" size={14} aria-hidden="true" />
    </label>
  )
}
