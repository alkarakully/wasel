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
import { errorText, money, pickName } from '../lib/strings'
import { fakeApi, order, store } from './fixtures'

const inLang = (ui: ReactNode, lang: Lang = 'en') => render(<LangContext.Provider value={lang}>{ui}</LangContext.Provider>)

describe('strings', () => {
  it('formats dinars and falls back to Arabic names', () => {
    expect(money('en', '16450')).toBe('16,450 IQD')
    expect(money('ar', 1250)).toBe('1,250 د.ع')
    expect(pickName('ku', { ar: 'لبن', ku: '', en: 'Laban' })).toBe('لبن')
    expect(pickName('en', { ar: 'لبن', ku: '', en: 'Laban' })).toBe('Laban')
  })

  it('maps unknown error codes to a generic message', () => {
    expect(errorText('en', 'invalid_code')).toBe('The code is wrong or has expired.')
    expect(errorText('en', 'something_new')).toBe('Something went wrong. Try again.')
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

describe('Login', () => {
  it('refuses accounts that are not stores', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      const body = url.includes('request')
        ? { phone: '+9647701234567', channel: 'whatsapp', resend_in: 60 }
        : url.includes('verify')
          ? { token: 't', user: { id: 1, phone: '+9647701234567', name: '', role: 'customer' } }
          : null
      return new Response(body ? JSON.stringify(body) : null, { status: body ? 200 : 204 })
    })
    vi.stubGlobal('fetch', fetchMock)
    const onSignedIn = vi.fn()
    inLang(<Login api={new Api(null)} onSignedIn={onSignedIn} setLang={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Phone number'), '07701234567')
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }))
    await userEvent.type(await screen.findByLabelText('Login code'), '482913')

    expect(await screen.findByRole('alert')).toHaveTextContent("This number isn't a store account.")
    expect(onSignedIn).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenLastCalledWith('/api/auth/logout/', expect.anything())
    vi.unstubAllGlobals()
  })
})
