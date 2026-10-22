import { useCallback, useEffect, useMemo, useState } from 'react'

import { Login } from './components/Login'
import { ApplyStep, InvitesStep, WaitingStep } from './components/Onboarding'
import { Portal } from './components/Portal'
import { Api, ApiError, type Lang, type User } from './lib/api'
import { LangContext } from './lib/i18n'
import { nextStep, type Step } from './lib/onboarding'
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
  const [step, setStep] = useState<Step | null>(null)
  // Came through "Join Wasel as a store": a fresh customer number may still apply.
  const [joining, setJoining] = useState(false)
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
    setStep(null)
    setJoining(false)
  }, [api])

  /** Re-reads the account (applying or accepting an invite makes it a store account) and the next step. */
  const advance = useCallback(async () => {
    try {
      const me = await api.me()
      const next = await nextStep(api, me, joining)
      if (next.kind === 'refused') return signOut()
      // Only store accounts are remembered across reloads.
      if (me.role === 'vendor') api.setToken(api.token)
      setUser(me)
      setStep(next)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'unauthorized') signOut()
    }
  }, [api, joining, signOut])

  // Restore a saved session.
  useEffect(() => {
    if (!api.token) return
    advance().finally(() => setChecking(false))
    // Only on start; later changes go through advance() directly.
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const signIn = (token: string, me: User, first: Step, isJoining: boolean) => {
    api.setToken(token, me.role === 'vendor')
    setUser(me)
    setStep(first)
    setJoining(isJoining)
  }

  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // Signed out locally either way.
    }
    signOut()
  }

  const stepProps = user && { api, user, setLang, onLogout: logout, onDone: advance }

  return (
    <LangContext.Provider value={lang}>
      {checking ? (
        <div className="splash" aria-hidden="true" />
      ) : user && step ? (
        step.kind === 'portal' ? (
          <Portal
            api={api}
            user={user}
            onUserChanged={setUser}
            onLogout={logout}
            onUnauthorized={signOut}
            setLang={setLang}
          />
        ) : step.kind === 'invites' ? (
          <InvitesStep key="invites" {...stepProps!} invites={step.invites} />
        ) : step.kind === 'waiting' ? (
          <WaitingStep {...stepProps!} applications={step.applications} canApply={step.canApply} />
        ) : (
          <ApplyStep {...stepProps!} />
        )
      ) : (
        <Login api={api} onSignedIn={signIn} setLang={setLang} />
      )}
    </LangContext.Provider>
  )
}
