import { useCallback, useEffect, useMemo, useState } from 'react'

import { Login } from './components/Login'
import { Portal } from './components/Portal'
import { Api, ApiError, type Lang, type User } from './lib/api'
import { LangContext } from './lib/i18n'
import { isRtl } from './lib/strings'

const LANG_KEY = 'wasel_vendor_lang'

function storedLang(): Lang {
  try {
    const value = localStorage.getItem(LANG_KEY)
    return value === 'ku' || value === 'en' ? value : 'ar'
  } catch {
    return 'ar'
  }
}

export default function App() {
  const api = useMemo(() => new Api(), [])
  const [lang, setLangState] = useState<Lang>(storedLang)
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(Boolean(api.token))

  const setLang = (value: Lang) => {
    setLangState(value)
    try {
      localStorage.setItem(LANG_KEY, value)
    } catch {
      // Not remembered in private mode; still applied now.
    }
  }

  useEffect(() => {
    document.documentElement.lang = lang === 'ku' ? 'ckb' : lang
    document.documentElement.dir = isRtl(lang) ? 'rtl' : 'ltr'
  }, [lang])

  const signOut = useCallback(() => {
    api.setToken(null)
    setUser(null)
  }, [api])

  // Restore a saved session.
  useEffect(() => {
    if (!api.token) return
    api
      .me()
      .then((me) => (me.role === 'vendor' ? setUser(me) : signOut()))
      .catch((error) => {
        if (error instanceof ApiError && error.code === 'unauthorized') signOut()
      })
      .finally(() => setChecking(false))
  }, [api, signOut])

  const signIn = (token: string, me: User) => {
    api.setToken(token)
    setUser(me)
  }

  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // Signed out locally either way.
    }
    signOut()
  }

  return (
    <LangContext.Provider value={lang}>
      {checking ? (
        <div className="splash" aria-hidden="true" />
      ) : user ? (
        <Portal api={api} user={user} onLogout={logout} onUnauthorized={signOut} setLang={setLang} />
      ) : (
        <Login api={api} onSignedIn={signIn} setLang={setLang} />
      )}
    </LangContext.Provider>
  )
}
