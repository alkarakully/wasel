import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { Board } from '../components/Board'
import { Login } from '../components/Login'
import { MenuView } from '../components/MenuView'
import { OrderCard } from '../components/OrderCard'
import { Api, type Lang } from '../lib/api'
import { LangContext } from '../lib/i18n'
import { codeDigits, errorText, money, pickName } from '../lib/strings'
import { fakeApi, order, store } from './fixtures'

const inLang = (ui: ReactNode, lang: Lang = 'en') => render(<LangContext.Provider value={lang}>{ui}</LangContext.Provider>)

describe('strings', () => {
  it('formats dinars and falls back to Arabic names', () => {
    expect(money('en', '16450')).toBe('16,450 IQD')
    expect(money('ar', 1250)).toBe('1,250 د.ع')
    expect(pickName('ku', { ar: 'لبن', ku: '', en: 'Laban' })).toBe('لبن')
    expect(pickName('en', { ar: 'لبن', ku: '', en: 'Laban' })).toBe('Laban')
  })

  it('reads the login code from pasted messages and Arabic digits', () => {
    expect(codeDigits('482913')).toBe('482913')
    expect(codeDigits('Wasel login code for +9647701234567: 482913')).toBe('482913')
    expect(codeDigits('٤٨٢٩١٣')).toBe('482913')
    expect(codeDigits('48 29')).toBe('4829')
  })

  it('maps unknown error codes to a generic message', () => {
    expect(errorText('en', 'invalid_code')).toBe('The code is wrong or has expired.')
    expect(errorText('en', 'something_new')).toBe('Something went wrong. Try again.')
    expect(errorText('en', 'delivery_failed')).toBe("We couldn't send the code right now. Try again shortly.")
    expect(errorText('ar', 'account_disabled')).toBe('هذا الحساب موقوف. تواصل مع فريق واصل.')
  })
})

describe('OrderCard', () => {
  it('shows what to cook, in the chosen language', () => {
    inLang(<OrderCard api={fakeApi()} order={order()} showStore={false} onChanged={vi.fn()} onError={vi.fn()} />, 'ar')
    expect(screen.getByText('كباب عراقي')).toBeInTheDocument()
    expect(screen.getByText('كبير')).toBeInTheDocument()
    expect(screen.getByText('2×')).toBeInTheDocument()
    expect(screen.getByText('1.5 kg')).toBeInTheDocument()
    expect(screen.getByText(/16,450 د.ع/)).toBeInTheDocument()
  })

  it('accepts with the chosen prep time', async () => {
    const api = fakeApi()
    const onChanged = vi.fn()
    inLang(<OrderCard api={api} order={order()} showStore={false} onChanged={onChanged} onError={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: '20 min' }))
    await userEvent.click(screen.getByRole('button', { name: 'Accept' }))
    expect(api.accept).toHaveBeenCalledWith(7, 20)
    expect(onChanged).toHaveBeenCalledWith(expect.objectContaining({ status: 'preparing' }))
  })

  it('rejects with a reason the customer will see', async () => {
    const api = fakeApi()
    inLang(<OrderCard api={api} order={order()} showStore={false} onChanged={vi.fn()} onError={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Reject' }))
    const dialog = screen.getByRole('dialog')
    await userEvent.click(within(dialog).getByLabelText("We're too busy"))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Reject order' }))
    expect(api.reject).toHaveBeenCalledWith(7, "We're too busy")
  })

  it('marks a preparing order ready and shows when it is late', async () => {
    const api = fakeApi()
    const late = new Date(Date.now() - 5 * 60000).toISOString()
    inLang(
      <OrderCard api={api} order={order({ status: 'preparing', estimated_ready_at: late })} showStore={false} onChanged={vi.fn()} onError={vi.fn()} />,
    )
    expect(screen.getByText('5 min late')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Ready' }))
    expect(api.ready).toHaveBeenCalledWith(7)
  })
})

describe('Board', () => {
  it('puts orders in their columns, oldest first', () => {
    const older = order({ id: 1, created_at: new Date(Date.now() - 10 * 60000).toISOString() })
    const newer = order({ id: 2 })
    const cooking = order({ id: 3, status: 'preparing' })
    inLang(<Board api={fakeApi()} orders={[newer, cooking, older]} multiStore={false} onChanged={vi.fn()} onError={vi.fn()} />)

    const fresh = screen.getByRole('region', { name: /New orders/ })
    expect(within(fresh).getAllByRole('article').map((a) => a.getAttribute('aria-label'))).toEqual(['#1', '#2'])
    expect(within(screen.getByRole('region', { name: /Preparing/ })).getAllByRole('article')).toHaveLength(1)
    expect(within(screen.getByRole('region', { name: /Ready for pickup/ })).getByText('Nothing here')).toBeInTheDocument()
  })
})

describe('MenuView', () => {
  it('flips an item out of stock right away and saves it', async () => {
    const api = fakeApi()
    const onChanged = vi.fn()
    inLang(<MenuView api={api} store={store} onChanged={onChanged} onError={vi.fn()} />)
    await userEvent.click(screen.getByRole('switch', { name: 'Kebab' }))
    expect(onChanged).toHaveBeenNthCalledWith(1, { id: 10, is_available: false })
    expect(api.setAvailable).toHaveBeenCalledWith(10, false)
    expect(screen.getByRole('switch', { name: 'Laban' })).not.toBeChecked()
  })

  it('puts the switch back if saving fails', async () => {
    const api = fakeApi({ setAvailable: vi.fn(async () => Promise.reject(new Error('offline'))) })
    const onChanged = vi.fn()
    const onError = vi.fn()
    inLang(<MenuView api={api} store={store} onChanged={onChanged} onError={onError} />)
    await userEvent.click(screen.getByRole('switch', { name: 'Kebab' }))
    expect(onChanged).toHaveBeenLastCalledWith({ id: 10, is_available: true })
    expect(onError).toHaveBeenCalled()
  })
})

/** A fetch stand-in answering the login flow; `routes` adds or overrides answers by URL part. */
function loginFetch(role: string, routes: Record<string, unknown> = {}) {
  const answers: Record<string, unknown> = {
    'otp/request': { phone: '+9647701234567', channel: 'whatsapp', resend_in: 60 },
    'otp/verify': { token: 't', user: { id: 1, phone: '+9647701234567', name: '', role } },
    'store-invites': [],
    'vendors/mine': [],
    'store-applications': { can_apply: true, reason: null, applications: [] },
    ...routes,
  }
  return vi.fn(async (url: string) => {
    const key = Object.keys(answers).find((part) => url.includes(part))
    const body = key ? answers[key] : null
    return new Response(body ? JSON.stringify(body) : null, { status: body ? 200 : 204 })
  })
}

async function signIn(join = false) {
  if (join) {
    await userEvent.click(screen.getByRole('button', { name: 'Join Wasel as a store' }))
    expect(screen.getByRole('heading', { name: 'Join Wasel' })).toBeInTheDocument()
  }
  await userEvent.type(screen.getByLabelText('Phone number'), '07701234567')
  await userEvent.click(screen.getByRole('button', { name: 'Send code' }))
  await userEvent.type(await screen.findByLabelText('Login code'), '482913')
}

describe('Login', () => {
  it('refuses accounts that are not stores, pointing to joining', async () => {
    const fetchMock = loginFetch('customer')
    vi.stubGlobal('fetch', fetchMock)
    const onSignedIn = vi.fn()
    inLang(<Login api={new Api(null)} onSignedIn={onSignedIn} setLang={vi.fn()} />)
    await signIn()

    expect(await screen.findByRole('alert')).toHaveTextContent("This number isn't a store account yet. Choose “Join Wasel as a store”")
    expect(onSignedIn).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenLastCalledWith('/api/auth/logout/', expect.anything())
    vi.unstubAllGlobals()
  })

  it('lets a new number join and fill in its first store', async () => {
    vi.stubGlobal('fetch', loginFetch('customer'))
    const onSignedIn = vi.fn()
    inLang(<Login api={new Api(null)} onSignedIn={onSignedIn} setLang={vi.fn()} />)
    await signIn(true)

    await vi.waitFor(() => expect(onSignedIn).toHaveBeenCalled())
    expect(onSignedIn).toHaveBeenCalledWith('t', expect.objectContaining({ role: 'customer' }), { kind: 'apply' }, true)
    vi.unstubAllGlobals()
  })

  it("won't turn a customer with orders into a store", async () => {
    const fetchMock = loginFetch('customer', {
      'store-applications': { can_apply: false, reason: 'phone_in_use', applications: [] },
    })
    vi.stubGlobal('fetch', fetchMock)
    inLang(<Login api={new Api(null)} onSignedIn={vi.fn()} setLang={vi.fn()} />)
    await signIn(true)
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign your store up with another number.')
    expect(fetchMock).toHaveBeenLastCalledWith('/api/auth/logout/', expect.anything())
    vi.unstubAllGlobals()
  })

  it('shows team invites first, even to a brand-new number', async () => {
    const invite = { id: 4, store: { id: 1, name: 'Tigris Grill', type: 'restaurant' }, role: 'cashier', invited_by: 'Ali', created_at: '' }
    vi.stubGlobal('fetch', loginFetch('customer', { 'store-invites': [invite] }))
    const onSignedIn = vi.fn()
    inLang(<Login api={new Api(null)} onSignedIn={onSignedIn} setLang={vi.fn()} />)
    await signIn()
    await vi.waitFor(() => expect(onSignedIn).toHaveBeenCalled())
    expect(onSignedIn.mock.calls[0][2]).toEqual({ kind: 'invites', invites: [invite] })
    vi.unstubAllGlobals()
  })
})
