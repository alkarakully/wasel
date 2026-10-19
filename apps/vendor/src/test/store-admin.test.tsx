import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { BillingView } from '../components/BillingView'
import { MenuView } from '../components/MenuView'
import { ReportsView } from '../components/ReportsView'
import { TeamView } from '../components/TeamView'
import { ApiError, type Billing, type Report } from '../lib/api'
import { LangContext } from '../lib/i18n'
import { fakeApi, store } from './fixtures'

const inEnglish = (ui: ReactNode) => render(<LangContext.Provider value="en">{ui}</LangContext.Provider>)

beforeAll(() => {
  // jsdom has no <dialog> methods.
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.open = true
  }
})
afterEach(cleanup)

describe('Menu editing', () => {
  it('owners and managers add items; cashiers only see stock switches', async () => {
    const api = fakeApi({ addProduct: vi.fn(async () => ({})) })
    const onReload = vi.fn()
    inEnglish(
      <MenuView api={api} store={store} onChanged={vi.fn()} onError={vi.fn()} canEdit onReload={onReload} />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Add item' }))
    await userEvent.type(screen.getByLabelText('Name in Arabic'), 'تكة')
    await userEvent.type(screen.getByLabelText('Name in English'), 'Tikka')
    await userEvent.type(screen.getByLabelText('Price'), '8,000')
    await userEvent.click(screen.getByRole('button', { name: 'Per kg' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(api.addProduct).toHaveBeenCalledWith(1, {
      name_ar: 'تكة',
      name_ku: '',
      name_en: 'Tikka',
      menu_section: '',
      price: '8000',
      unit_type: 'kg',
    })
    expect(onReload).toHaveBeenCalled()
    cleanup()

    inEnglish(<MenuView api={fakeApi()} store={store} onChanged={vi.fn()} onError={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'Add item' })).toBeNull()
    expect(screen.queryByRole('button', { name: /Edit item/ })).toBeNull()
  })
})

describe('Team', () => {
  it('invites a cashier by phone, explaining refusals, and lists the invite until answered', async () => {
    const addMember = vi
      .fn()
      .mockRejectedValueOnce(new ApiError('phone_in_use', 400))
      .mockResolvedValueOnce({ id: 3, phone: '+9647801112233', name: 'Sara', role: 'cashier', created_at: '' })
    const team = vi
      .fn()
      .mockResolvedValueOnce({ owner: { user: 1, phone: '+9647800000999', name: 'Ali', role: 'owner' }, members: [], invites: [] })
      .mockResolvedValue({
        owner: { user: 1, phone: '+9647800000999', name: 'Ali', role: 'owner' },
        members: [],
        invites: [{ id: 3, phone: '+9647801112233', name: 'Sara', role: 'cashier', created_at: '' }],
      })
    const api = fakeApi({ team, addMember, cancelInvite: vi.fn(async () => null) })
    inEnglish(<TeamView api={api} storeId={1} myUserId={1} onError={vi.fn()} />)
    expect(await screen.findByText('Owner · You')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Phone number'), '0780 111 2233')
    await userEvent.type(screen.getByLabelText('Name'), 'Sara')
    await userEvent.click(screen.getByRole('button', { name: 'Send invite' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('already belongs to a customer or captain')

    await userEvent.click(screen.getByRole('button', { name: 'Send invite' }))
    expect(addMember).toHaveBeenLastCalledWith(1, { phone: '0780 111 2233', name: 'Sara', role: 'cashier' })
    expect(await screen.findByRole('status')).toHaveTextContent('Invite sent to')
    expect(await screen.findByText('Invited · Cashier')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Cancel invite Sara' }))
    expect(api.cancelInvite).toHaveBeenCalledWith(1, 3)
  })
})

const report: Report = {
  from: '2026-10-12',
  to: '2026-10-18',
  orders: 12,
  delivered: 10,
  cancelled: 2,
  cancelled_by: { customer: 1, vendor: 1 },
  food_sales: 150000,
  store_discounts: 0,
  commission: 22500,
  payout: 127500,
  average_order: 15000,
  average_prep_minutes: 14,
  days: [
    { date: '2026-10-17', orders: 4, sales: 60000 },
    { date: '2026-10-18', orders: 6, sales: 90000 },
  ],
  hours: Array.from({ length: 24 }, (_, hour) => ({ hour, orders: hour === 20 ? 5 : 0 })),
  top_items: [{ product: 10, name: { ar: 'كباب', ku: '', en: 'Kebab' }, quantity: '14', orders: 9, sales: 126000 }],
}

describe('Reports', () => {
  it('shows earnings, orders and best sellers for the range', async () => {
    const api = fakeApi({ report: vi.fn(async () => report) })
    inEnglish(<ReportsView api={api} storeId={1} onError={vi.fn()} />)
    expect(await screen.findByText('127,500 IQD')).toBeInTheDocument()
    expect(screen.getByText('10 delivered')).toBeInTheDocument()
    expect(screen.getByText('14 min')).toBeInTheDocument()
    expect(screen.getByText('1 by customer · 1 by store')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Kebab' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Last 30 days' }))
    expect(api.report).toHaveBeenCalledTimes(2)
  })
})

describe('Billing', () => {
  it('shows this week, totals and a statement with its orders', async () => {
    const billing: Billing = {
      current_week: {
        period_start: '2026-10-17',
        period_end: '2026-10-23',
        orders_count: 3,
        food_sales: 30000,
        store_discounts: 0,
        commission: 4500,
        payout: 25500,
      },
      due_total: 24650,
      paid_total: 100000,
      commission_rate: '15',
      statements: [
        {
          id: 5,
          store_name: 'Tigris Grill',
          period_start: '2026-10-10',
          period_end: '2026-10-16',
          orders_count: 2,
          food_sales: 30000,
          store_discounts: 1000,
          commission: 4350,
          payout: 24650,
          status: 'due',
          paid_at: null,
          paid_reference: '',
        },
      ],
    }
    const api = fakeApi({
      billing: vi.fn(async () => billing),
      statement: vi.fn(async () => ({
        ...billing.statements[0],
        orders: [
          { order: 7, delivered_at: '', payment_type: 'cod', food_sales: 10000, store_discount: 1000, commission: 1350, payout: 7650 },
        ],
      })),
    })
    inEnglish(<BillingView api={api} storeId={1} onError={vi.fn()} />)
    expect(await screen.findByText('25,500 IQD')).toBeInTheDocument()
    expect(screen.getByText(/minus Wasel’s commission \(15%\)/)).toBeInTheDocument()

    const row = screen.getByRole('row', { name: /2026-10-10/ })
    expect(within(row).getByText('Due')).toBeInTheDocument()
    await userEvent.click(within(row).getByRole('button'))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText('#7')).toBeInTheDocument()
    expect(within(dialog).getByText('7,650 IQD')).toBeInTheDocument()
  })
})
