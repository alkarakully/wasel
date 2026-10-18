import { BellRinging, BellSlash, Printer, SignOut, Storefront } from '@phosphor-icons/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { OrderAlarm } from '../lib/alarm'
import { Api, ApiError, type Lang, type Order, type Store, type StoreRole, type User } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { useLiveOrders } from '../lib/useLiveOrders'
import { BillingView } from './BillingView'
import { Board } from './Board'
import { HoursEditor } from './HoursEditor'
import { LanguageSwitch } from './LanguageSwitch'
import { MenuView } from './MenuView'
import { PrintSlips } from './PrintSlips'
import { ReportsView } from './ReportsView'
import { TeamView } from './TeamView'

interface Props {
  api: Api
  user: User
  onLogout: () => void
  onUnauthorized: () => void
  setLang: (lang: Lang) => void
}

type Tab = 'orders' | 'menu' | 'reports' | 'billing' | 'team'

/** Which sections each role sees (the server checks the same rules). */
const TABS: Record<StoreRole, Tab[]> = {
  owner: ['orders', 'menu', 'reports', 'billing', 'team'],
  manager: ['orders', 'menu', 'reports'],
  cashier: ['orders', 'menu'],
}

/** Signed-in store team: live order board, menu, and for owners and managers reports, billing and the team. */
export function Portal({ api, user, onLogout, onUnauthorized, setLang }: Props) {
  const { t, error: errorMessage } = useI18n()
  const [tab, setTab] = useState<Tab>('orders')
  const [stores, setStores] = useState<Store[] | null>(null)
  const [storeId, setStoreId] = useState<number | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const { orders, loaded, connected, reload, upsert } = useLiveOrders(api, onUnauthorized)

  // Printing: render the slips for one order, open the print dialog, then clear them.
  const [printing, setPrinting] = useState<Order | null>(null)
  const [autoPrint, setAutoPrint] = useState(() => readFlag(AUTO_PRINT_KEY))
  useEffect(() => {
    if (!printing) return
    const done = () => setPrinting(null)
    window.addEventListener('afterprint', done)
    // Let the slips render before the dialog opens.
    const timer = setTimeout(() => window.print(), 60)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('afterprint', done)
    }
  }, [printing])
  const toggleAutoPrint = () => {
    setAutoPrint((on) => {
      writeFlag(AUTO_PRINT_KEY, !on)
      return !on
    })
  }

  const alarm = useMemo(() => new OrderAlarm(), [])
  const [soundReady, setSoundReady] = useState(false)
  // Orders the user silenced with "Stop ringing"; a new order rings again.
  const [silenced, setSilenced] = useState<Set<number>>(new Set())

  const loadStores = useCallback(() => {
    api
      .myStores()
      .then((list) => {
        setStores(list)
        setStoreId((current) => current ?? list[0]?.id ?? null)
      })
      .catch((e) => e instanceof ApiError && e.code === 'unauthorized' && onUnauthorized())
  }, [api, onUnauthorized])
  useEffect(loadStores, [loadStores])

  const newOrders = orders.filter((o) => o.status === 'received')
  const ringing = newOrders.some((o) => !silenced.has(o.id))

  useEffect(() => {
    if (ringing && soundReady) alarm.start()
    else alarm.stop()
  }, [ringing, soundReady, alarm])
  useEffect(() => () => alarm.stop(), [alarm])

  // Show the count of new orders in the browser tab, so it's visible from across the kitchen.
  const baseTitle = useRef(document.title)
  useEffect(() => {
    document.title = newOrders.length ? `(${newOrders.length}) ${t('col_received')} | واصل` : `${t('orders')} | واصل`
    const original = baseTitle.current
    return () => {
      document.title = original
    }
  }, [newOrders.length, t])

  const enableSound = async () => setSoundReady(await alarm.unlock())

  const showError = useCallback(
    (e: unknown) => {
      const code = e instanceof ApiError ? e.code : 'generic'
      setNotice(errorMessage(code))
      if (code === 'invalid_transition') reload()
    },
    [errorMessage, reload],
  )

  const store = stores?.find((s) => s.id === storeId) ?? null
  const role: StoreRole = store?.my_role ?? 'owner'
  const tabs = TABS[role]
  // Switching to a store where this section isn't allowed falls back to orders.
  const section: Tab = tabs.includes(tab) ? tab : 'orders'

  const toggleOpen = async () => {
    if (!store) return
    try {
      const result = await api.setOpen(store.id, !store.is_open)
      setStores((list) => list?.map((s) => (s.id === result.id ? { ...s, is_open: result.is_open } : s)) ?? null)
    } catch (e) {
      showError(e)
    }
  }

  return (
    <div className="portal">
      <header className="topbar">
        <div className="topbar-start">
          <span className="brand-mark glaze" aria-hidden="true">
            و
          </span>
          {stores && stores.length > 1 ? (
            <select aria-label="Store" value={storeId ?? ''} onChange={(e) => setStoreId(Number(e.target.value))}>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          ) : (
            <strong className="store-name">{store?.name}</strong>
          )}
          {store && (
            <button
              type="button"
              className={`pill ${store.is_open ? 'pill-on' : 'pill-off'}`}
              aria-pressed={store.is_open}
              onClick={toggleOpen}
            >
              {store.is_open ? (
                <span className="dot" aria-hidden="true" />
              ) : (
                <Storefront size={18} weight="light" aria-hidden="true" />
              )}
              {store.is_open ? t('storeOpen') : t('storeClosed')}
            </button>
          )}
        </div>
        <nav className="tabs" aria-label="Sections">
          {tabs.map((name) => (
            <button key={name} type="button" aria-pressed={section === name} onClick={() => setTab(name)}>
              {t(name)}
              {name === 'orders' && newOrders.length > 0 && (
                <span key={newOrders.length} className="count pop">
                  {newOrders.length}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="topbar-end">
          {soundReady ? (
            <span className="sound-state" title={t('soundOn')}>
              <BellRinging size={22} weight="light" aria-hidden="true" />
              <span className="sr-only">{t('soundOn')}</span>
            </span>
          ) : (
            <button type="button" className="pill pill-warn" onClick={enableSound}>
              <BellSlash size={18} weight="light" aria-hidden="true" />
              {t('soundOff')}
            </button>
          )}
          <LanguageSwitch setLang={setLang} />
          <button type="button" className="icon-button" onClick={onLogout} title={`${t('logout')} (${user.phone})`}>
            <SignOut size={20} weight="light" aria-hidden="true" />
            <span className="sr-only">{t('logout')}</span>
          </button>
        </div>
      </header>

      <div className="banners">
        {!soundReady && newOrders.length > 0 && (
          <button type="button" className="banner banner-warn" onClick={enableSound}>
            {t('soundBlocked')}
          </button>
        )}
        {ringing && soundReady && (
          <button
            type="button"
            className="banner banner-alert glaze"
            onClick={() => setSilenced(new Set(newOrders.map((o) => o.id)))}
          >
            <BellSlash size={22} weight="light" aria-hidden="true" />
            {t('mute')}
          </button>
        )}
        {!connected && <p className="banner banner-warn">{t('offline')}</p>}
        {notice && (
          <p className="banner banner-error" role="alert" onClick={() => setNotice(null)}>
            {notice}
          </p>
        )}
      </div>

      {/* Keyed by tab so switching sections fades the new one in. */}
      <main className="portal-body view" key={`${section}-${store?.id}`}>
        {stores && stores.length === 0 ? (
          <p className="empty">{t('noStores')}</p>
        ) : section === 'reports' && store ? (
          <ReportsView api={api} storeId={store.id} onError={showError} />
        ) : section === 'billing' && store ? (
          <BillingView api={api} storeId={store.id} onError={showError} />
        ) : section === 'team' && store ? (
          <TeamView api={api} storeId={store.id} myUserId={user.id} onError={showError} />
        ) : section === 'orders' ? (
          <>
            <div className="board-tools">
              <button
                type="button"
                className={`pill ${autoPrint ? 'pill-on' : 'pill-off'}`}
                aria-pressed={autoPrint}
                onClick={toggleAutoPrint}
              >
                <Printer size={18} weight="light" aria-hidden="true" />
                {t('printOnAccept')}
              </button>
            </div>
            <Board
              api={api}
              orders={orders}
              loading={!loaded}
              multiStore={(stores?.length ?? 0) > 1}
              onChanged={upsert}
              onError={showError}
              onPrint={setPrinting}
              autoPrint={autoPrint}
            />
          </>
        ) : (
          store && (
            <div className="menu-page">
              {role !== 'cashier' && (
                <HoursEditor
                  api={api}
                  store={store}
                  onSaved={(hours) =>
                    setStores(
                      (list) => list?.map((s) => (s.id === store.id ? { ...s, opening_hours: hours } : s)) ?? null,
                    )
                  }
                  onError={showError}
                />
              )}
              <MenuView
                api={api}
                store={store}
                canEdit={role !== 'cashier'}
                onReload={loadStores}
                onChanged={(product) =>
                  setStores(
                    (list) =>
                      list?.map((s) =>
                        s.id === store.id
                          ? {
                              ...s,
                              products: s.products.map((p) => (p.id === product.id ? { ...p, ...product } : p)),
                            }
                          : s,
                      ) ?? null,
                  )
                }
                onError={showError}
              />
            </div>
          )
        )}
      </main>
      {printing && <PrintSlips order={printing} storeName={printing.vendor_name} />}
    </div>
  )
}

const AUTO_PRINT_KEY = 'wasel_print_on_accept'

function readFlag(key: string) {
  try {
    return localStorage.getItem(key) === '1'
  } catch {
    return false
  }
}

function writeFlag(key: string, on: boolean) {
  try {
    localStorage.setItem(key, on ? '1' : '0')
  } catch {
    // Private mode: the setting lasts until the tab closes.
  }
}
