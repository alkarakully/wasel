import { BellRinging, BellSlash, SignOut, Storefront } from '@phosphor-icons/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { OrderAlarm } from '../lib/alarm'
import { Api, ApiError, type Lang, type Store, type User } from '../lib/api'
import { useI18n } from '../lib/i18n'
import { useLiveOrders } from '../lib/useLiveOrders'
import { Board } from './Board'
import { LanguageSwitch } from './LanguageSwitch'
import { MenuView } from './MenuView'

interface Props {
  api: Api
  user: User
  onLogout: () => void
  onUnauthorized: () => void
  setLang: (lang: Lang) => void
}

/** Signed-in store owner: live order board and menu stock. */
export function Portal({ api, user, onLogout, onUnauthorized, setLang }: Props) {
  const { t, error: errorMessage } = useI18n()
  const [tab, setTab] = useState<'orders' | 'menu'>('orders')
  const [stores, setStores] = useState<Store[] | null>(null)
  const [storeId, setStoreId] = useState<number | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const { orders, connected, reload, upsert } = useLiveOrders(api, onUnauthorized)

  const alarm = useMemo(() => new OrderAlarm(), [])
  const [soundReady, setSoundReady] = useState(false)
  // Orders the user silenced with "Stop ringing"; a new order rings again.
  const [silenced, setSilenced] = useState<Set<number>>(new Set())

  useEffect(() => {
    api
      .myStores()
      .then((list) => {
        setStores(list)
        setStoreId((current) => current ?? list[0]?.id ?? null)
      })
      .catch((e) => e instanceof ApiError && e.code === 'unauthorized' && onUnauthorized())
  }, [api, onUnauthorized])

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
          <button type="button" aria-pressed={tab === 'orders'} onClick={() => setTab('orders')}>
            {t('orders')}
            {newOrders.length > 0 && <span className="count">{newOrders.length}</span>}
          </button>
          <button type="button" aria-pressed={tab === 'menu'} onClick={() => setTab('menu')}>
            {t('menu')}
          </button>
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

      <main className="portal-body">
        {stores && stores.length === 0 ? (
          <p className="empty">{t('noStores')}</p>
        ) : tab === 'orders' ? (
          <Board
            api={api}
            orders={orders}
            multiStore={(stores?.length ?? 0) > 1}
            onChanged={upsert}
            onError={showError}
          />
        ) : (
          store && (
            <MenuView
              api={api}
              store={store}
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
          )
        )}
      </main>
    </div>
  )
}
