import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { Shell, SECTIONS } from './components/Shell'
import { SignIn } from './components/SignIn'
import { ToastHost } from './components/ui'
import { api, whenSignedOut, type Lang, type Me } from './lib/api'
import { CountryContext, LangContext } from './lib/i18n'
import { REGIONS } from './lib/countries'
import { navigate, useRoute } from './lib/router'
import { AuditPage } from './pages/AuditPage'
import { MarketingPage } from './pages/MarketingPage'
import { MoneyPage } from './pages/MoneyPage'
import { OrdersPage } from './pages/OrdersPage'
import { OverviewPage } from './pages/OverviewPage'
import { PeoplePage } from './pages/PeoplePage'
import { ReportsPage } from './pages/ReportsPage'
import { StaffPage } from './pages/StaffPage'
import { StoresPage } from './pages/StoresPage'

function savedLang(): Lang {
  try {
    return localStorage.getItem('wasel-admin-lang') === 'en' ? 'en' : 'ar'
  } catch {
    return 'ar'
  }
}

function savedCountry() {
  try {
    const code = localStorage.getItem('wasel-admin-country') ?? 'IQ'
    return REGIONS.some((r) => r.country === code) ? code : 'IQ'
  } catch {
    return 'IQ'
  }
}

export default function App() {
  const [lang, setLangState] = useState<Lang>(savedLang)
  const [country, setCountryState] = useState(savedCountry)
  const setCountry = useCallback((code: string) => {
    setCountryState(code)
    try {
      localStorage.setItem('wasel-admin-country', code)
    } catch {
      /* private mode */
    }
  }, [])
  const [me, setMe] = useState<Me | null | undefined>(undefined)
  const route = useRoute()

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    try {
      localStorage.setItem('wasel-admin-lang', next)
    } catch {
      /* private mode */
    }
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    document.title = lang === 'ar' ? 'واصل | إدارة المنصة' : 'Wasel | Platform admin'
  }, [lang])

  useEffect(() => {
    whenSignedOut(() => setMe(null))
    api<{ user: Me | null }>('auth/session/')
      .then((r) => setMe(r.user))
      .catch(() => setMe(null))
  }, [])

  async function signOut() {
    await api('auth/logout/', { method: 'POST' }).catch(() => undefined)
    setMe(null)
    navigate('/', true)
  }

  let body
  if (me === undefined) body = <div className="splash glaze" aria-busy="true" />
  else if (me === null) body = <SignIn onSignedIn={setMe} setLang={setLang} />
  else {
    const section = SECTIONS.find((s) => s.path === route.section)
    const allowed = section && me.areas[section.area]
    const can = (area: keyof Me['areas']) => me.areas[area] === 'write'
    const pages: Record<string, () => ReactNode> = {
      '': () => <OverviewPage />,
      orders: () => <OrdersPage id={route.id} canWrite={can('orders')} />,
      stores: () => <StoresPage id={route.id} canWrite={can('stores')} />,
      people: () => <PeoplePage id={route.id} canWrite={can('people')} canMoney={can('money')} />,
      money: () => <MoneyPage canWrite={can('money')} />,
      reports: () => <ReportsPage />,
      marketing: () => <MarketingPage canWrite={can('marketing')} />,
      team: () => <StaffPage me={me} />,
      audit: () => <AuditPage />,
    }
    body = (
      <Shell me={me} section={allowed ? route.section : ''} setLang={setLang} onSignOut={signOut}>
        {allowed ? pages[route.section]() : <OverviewPage />}
      </Shell>
    )
  }

  return (
    <LangContext.Provider value={lang}>
      <CountryContext.Provider value={{ country, setCountry }}>
        <ToastHost>{body}</ToastHost>
      </CountryContext.Provider>
    </LangContext.Provider>
  )
}
