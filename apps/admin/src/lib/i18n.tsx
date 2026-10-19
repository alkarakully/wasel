import { createContext, useContext } from 'react'

import type { Lang } from './api'
import { region } from './countries'
import { dateTime, day, money, number, translate, type StringKey } from './strings'

export const LangContext = createContext<Lang>('ar')

/** The operating country the admin is looking at: its numbers, currency and clock. */
export const CountryContext = createContext<{ country: string; setCountry: (code: string) => void }>({
  country: 'IQ',
  setCountry: () => {},
})

export const useCountry = () => {
  const value = useContext(CountryContext)
  return { ...value, region: region(value.country) }
}

export function useI18n() {
  const lang = useContext(LangContext)
  const here = region(useContext(CountryContext).country)
  return {
    lang,
    t: (key: StringKey, vars?: Record<string, string | number>) => translate(lang, key, vars),
    /** For keys built from API values, e.g. `st_${status}`. Unknown keys show the raw value. */
    tk: (key: string, vars?: Record<string, string | number>) => translate(lang, key as StringKey, vars),
    /** In the given currency, or the selected country's when left out. */
    money: (amount: number | string, currency: string = here.currency) => money(lang, amount, currency),
    num: (value: number) => number(lang, value),
    pct: (value: number) => `${number(lang, value)}${lang === 'ar' ? '٪' : '%'}`,
    /** On the given time zone's clock, or the selected country's. */
    when: (iso: string | null, withTime = true, timeZone: string = here.timeZone) =>
      dateTime(lang, iso, withTime, timeZone),
    day: (iso: string) => day(lang, iso),
  }
}
