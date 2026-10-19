import { createContext, useContext } from 'react'

import type { Lang } from './api'
import { dateTime, day, money, number, translate, type StringKey } from './strings'

export const LangContext = createContext<Lang>('ar')

export function useI18n() {
  const lang = useContext(LangContext)
  return {
    lang,
    t: (key: StringKey, vars?: Record<string, string | number>) => translate(lang, key, vars),
    /** For keys built from API values, e.g. `st_${status}`. Unknown keys show the raw value. */
    tk: (key: string, vars?: Record<string, string | number>) => translate(lang, key as StringKey, vars),
    money: (amount: number) => money(lang, amount),
    num: (value: number) => number(lang, value),
    pct: (value: number) => `${number(lang, value)}${lang === 'ar' ? '٪' : '%'}`,
    when: (iso: string | null, withTime = true) => dateTime(lang, iso, withTime),
    day: (iso: string) => day(lang, iso),
  }
}
