import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import type { Me } from '../lib/api'

type Handler = (body: unknown, init: RequestInit) => [number, unknown]
let routes: Record<string, Handler>
let calls: { method: string; path: string; body: unknown }[]

function json(status: number, body: unknown) {
  return Promise.resolve(
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

beforeEach(() => {
  calls = []
  localStorage.setItem('wasel-admin-lang', 'en')
  localStorage.removeItem('wasel-admin-country')
  window.history.replaceState(null, '', import.meta.env.BASE_URL)
  vi.stubGlobal('fetch', (url: string, init: RequestInit = {}) => {
    const path = url.replace('/api/console/', '')
    const method = init.method ?? 'GET'
    const body = init.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ method, path, body })
    const handler = routes[`${method} ${path.split('?')[0]}`]
    if (!handler) return json(404, { detail: 'Not found.' })
    const [status, data] = handler(body, init)
    return json(status, data)
  })
})

afterEach(() => vi.unstubAllGlobals())

const admin: Me = {
  id: 1,
  email: 'admin@wasel.iq',
  name: 'Admin',
  role: 'admin',
  areas: {
    overview: 'read',
    orders: 'write',
    stores: 'write',
    people: 'write',
    money: 'write',
    marketing: 'write',
    reports: 'read',
    staff: 'write',
    audit: 'read',
  },
}

const overview = {
  today: {
    orders: 3,
    delivered: 1,
    cancelled: 0,
    sales: 30000,
    commission: 4500,
    service_fees: 0,
    delivery_fees: 0,
    discounts: 0,
    avg_delivery_minutes: 28,
  },
  month: {
    orders: 9,
    delivered: 6,
    cancelled: 1,
    sales: 90000,
    commission: 13500,
    service_fees: 0,
    delivery_fees: 0,
    discounts: 0,
    avg_delivery_minutes: 30,
  },
  live: {
    active_orders: 2,
    open_alerts: 1,
    online_captains: 1,
    open_stores: 4,
    stores: 6,
    applications: 2,
    customers: 40,
    plus_members: 3,
  },
  by_status: { received: 1, preparing: 1, ready: 0, out_for_delivery: 0 },
  days: [{ day: '2026-10-18', orders: 3, sales: 30000 }],
  top_stores: [],
}

describe('sign in', () => {
  it('asks for the password, then sets up the authenticator, then opens the overview', async () => {
    routes = {
      'GET auth/session/': () => [200, { user: null }],
      'POST auth/login/': (b) =>
        (b as { password: string }).password === 'right-password'
          ? [
              200,
              {
                next: 'setup',
                secret: 'JBSWY3DPEHPK3PXP',
                uri: 'otpauth://totp/Wasel:admin%40wasel.iq?secret=JBSWY3DPEHPK3PXP',
              },
            ]
          : [400, { error: 'invalid_login', detail: 'Wrong email or password.' }],
      'POST auth/verify/': (b) =>
        (b as { code: string }).code === '123456'
          ? [200, { user: admin }]
          : [400, { error: 'invalid_code', detail: 'That code isn’t right.' }],
      'GET overview/': () => [200, overview],
      'GET alerts/': () => [200, []],
    }
    const user = userEvent.setup()
    render(<App />)
    await user.type(await screen.findByLabelText('Work email'), 'admin@wasel.iq')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: /Continue/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong email or password.')

    await user.clear(screen.getByLabelText('Password'))
    await user.type(screen.getByLabelText('Password'), 'right-password')
    await user.click(screen.getByRole('button', { name: /Continue/ }))
    expect(await screen.findByRole('heading', { name: 'Set up your authenticator' })).toBeInTheDocument()
    expect(screen.getByText('JBSW Y3DP EHPK 3PXP')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Authenticator code'), '123456')
    await user.click(screen.getByRole('button', { name: 'Verify' }))
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByText('30,000 IQD')).toBeInTheDocument()
  })
})

describe('roles', () => {
  it('shows only the areas the role can use', async () => {
    const finance: Me = {
      ...admin,
      role: 'finance',
      areas: { overview: 'read', orders: 'read', people: 'read', money: 'write', reports: 'read' },
    }
    routes = { 'GET auth/session/': () => [200, { user: finance }], 'GET overview/': () => [200, overview] }
    render(<App />)
    const nav = await screen.findByRole('navigation', { name: '' }).catch(() => screen.findByRole('complementary'))
    await waitFor(() => expect(within(nav).getByText('Money')).toBeInTheDocument())
    expect(within(nav).queryByText('Team')).not.toBeInTheDocument()
    expect(within(nav).queryByText('Marketing')).not.toBeInTheDocument()
    // Orders are view only for finance.
    expect(within(nav).getByText('Orders').closest('a')).toHaveTextContent('View only')
  })
})

describe('orders', () => {
  it('cancelling an order needs a reason', async () => {
    window.history.replaceState(null, '', `${import.meta.env.BASE_URL}orders/7`)
    const order = {
      id: 7,
      status: 'preparing',
      store: { id: 2, name: 'Tigris Grill', phone: '+9647800000993' },
      customer: { id: 5, name: 'Zainab', phone: '+9647700000991' },
      captain: null,
      total: 10000,
      payment_type: 'wallet',
      payment_status: 'paid',
      created_at: '2026-10-18T10:00:00Z',
      minutes: 12,
      delivery_address: 'Karrada',
      subtotal: 8000,
      delivery_fee: 1500,
      service_fee: 500,
      tip: 0,
      discount: 0,
      commission: 1200,
      estimated_ready_at: null,
      cancelled_by: '',
      cancel_reason: '',
      timeline: [{ step: 'received', at: '2026-10-18T10:00:00Z' }],
      items: [],
      alerts: [],
      offers: [],
      can_cancel: true,
      can_release: false,
      can_dispatch: true,
    }
    routes = {
      'GET auth/session/': () => [200, { user: admin }],
      'GET alerts/': () => [200, []],
      'GET orders/': () => [200, { count: 0, next: null, previous: null, results: [] }],
      'GET orders/7/': () => [200, order],
      'POST orders/7/cancel/': () => [
        200,
        {
          ...order,
          status: 'cancelled',
          payment_status: 'refunded',
          cancelled_by: 'support',
          cancel_reason: 'Store closed',
          can_cancel: false,
          can_dispatch: false,
        },
      ],
    }
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Cancel order' }))
    const dialog = screen.getByRole('dialog', { name: 'Cancel order' })
    const confirm = within(dialog).getByRole('button', { name: 'Cancel order' })
    expect(confirm).toBeDisabled()
    await user.type(within(dialog).getByLabelText('Reason'), 'Store closed')
    await user.click(confirm)
    await waitFor(() =>
      expect(calls.find((c) => c.path === 'orders/7/cancel/')?.body).toEqual({ reason: 'Store closed' }),
    )
    expect(await screen.findByText('Cancelled by Wasel support')).toBeInTheDocument()
  })
})

describe('other countries', () => {
  it('formats each currency with its own decimals', async () => {
    const { money } = await import('../lib/strings')
    expect(money('en', '3.15', 'KWD')).toBe('3.150 KWD')
    expect(money('en', '12.5', 'SAR')).toBe('12.50 SAR')
    expect(money('en', '18000', 'IQD')).toBe('18,000 IQD')
    expect(money('ar', '3.15', 'KWD')).toContain('د.ك')
  })

  it('the country switch reloads the overview for that country', async () => {
    routes = {
      'GET auth/session/': () => [200, { user: admin }],
      'GET overview/': () => [200, overview],
    }
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('heading', { name: 'Overview' })
    expect(calls.some((c) => c.path === 'overview/?country=IQ')).toBe(true)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Country' }), 'KW')
    await waitFor(() => expect(calls.some((c) => c.path === 'overview/?country=KW')).toBe(true))
  })

  it('adds a store team member with a Saudi number', async () => {
    window.history.replaceState(null, '', `${import.meta.env.BASE_URL}stores/4`)
    const store = {
      id: 4,
      name: 'Riyadh Grill',
      type: 'restaurant',
      cuisine: '',
      is_open: true,
      status: 'approved',
      country: 'SA',
      currency: 'SAR',
      owner: { id: 9, name: 'Owner', phone: '+966501112233' },
      commission_rate: '15',
      created_at: '2026-10-18T10:00:00Z',
      address: '',
      latitude: 24.7,
      longitude: 46.6,
      delivery_radius_km: '5',
      commission_free_until: null,
      opening_hours: {},
      time_zone: 'Asia/Riyadh',
      rejection_reason: '',
      reviewed_at: null,
    }
    routes = {
      'GET auth/session/': () => [200, { user: admin }],
      'GET stores/': () => [200, { counts: { approved: 1, pending: 0, rejected: 0 }, results: [] }],
      'GET stores/4/': () => [200, store],
      'GET stores/4/team/': () => [200, { owner: store.owner, members: [], invites: [] }],
      'POST stores/4/team/': () => [201, { id: 1 }],
    }
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('tab', { name: 'Team' }))
    // Role queries are slow with the long country lists, so find the picker by its label.
    await user.click(await screen.findByLabelText(/Phone country: Iraq/))
    const list = screen.getByRole('listbox', { name: 'Phone country' })
    // Iraq first, then the Gulf.
    expect(
      within(list)
        .getAllByRole('option')
        .slice(0, 3)
        .map((o) => o.textContent),
    ).toEqual(['🇮🇶Iraq+964', '🇸🇦Saudi Arabia+966', '🇦🇪United Arab Emirates+971'])
    await user.click(within(list).getByRole('option', { name: /Saudi Arabia/ }))
    await user.type(screen.getByLabelText('Phone'), '050 123 4567')
    await user.click(screen.getByRole('button', { name: 'Add to team' }))
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        phone: '050 123 4567',
        country: 'SA',
        role: 'cashier',
      }),
    )
    expect(screen.getByText('+966 501112233')).toBeInTheDocument()
  })
})
