import { createContext, useContext } from 'react'

import type { Lang } from './api'
import { errorText, money, pickName, translate, type StringKey } from './strings'
import type { Names } from './api'

export const LangContext = createContext<Lang>('ar')

/** Text helpers bound to the current language. */
export function useI18n() {
  const lang = useContext(LangContext)
  return {
    lang,
    t: (key: StringKey, vars?: Record<string, string | number>) => translate(lang, key, vars),
    error: (code: string) => errorText(lang, code),
    money: (amount: string | number) => money(lang, amount),
    name: (names: Names) => pickName(lang, names),
  }
}
