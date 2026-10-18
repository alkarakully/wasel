import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OrderCard } from '../components/OrderCard'
import { PrintSlips } from '../components/PrintSlips'
import { LangContext } from '../lib/i18n'
import { fakeApi, order } from './fixtures'

const inEnglish = (ui: ReactNode) => render(<LangContext.Provider value="en">{ui}</LangContext.Provider>)

afterEach(cleanup)

describe('Printing', () => {
  it('prints from the card, and right after accepting when asked to', async () => {
    const onPrint = vi.fn()
    const api = fakeApi()
    inEnglish(
      <OrderCard api={api} order={order()} showStore={false} onChanged={vi.fn()} onError={vi.fn()} onPrint={onPrint} autoPrint />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Print order #7' }))
    expect(onPrint).toHaveBeenLastCalledWith(expect.objectContaining({ id: 7, status: 'received' }))

    await userEvent.click(screen.getByRole('button', { name: 'Accept' }))
    expect(onPrint).toHaveBeenLastCalledWith(expect.objectContaining({ id: 7, status: 'preparing' }))
  })

  it("doesn't print on accept unless the setting is on", async () => {
    const onPrint = vi.fn()
    inEnglish(
      <OrderCard api={fakeApi()} order={order()} showStore={false} onChanged={vi.fn()} onError={vi.fn()} onPrint={onPrint} />,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Accept' }))
    expect(onPrint).not.toHaveBeenCalled()
  })

  it('makes a kitchen ticket and a package slip, without the delivery PIN', () => {
    const printed = order({
      payment_type: 'cod',
      total_amount: '20250',
      customer_contact: { name: 'Zainab', phone: '+9647701234567' },
      estimated_ready_at: '2026-10-18T13:20:00+03:00',
    })
    inEnglish(<PrintSlips order={{ ...printed, delivery_pin: '4821' } as typeof printed} storeName="Tigris Grill" />)
    const root = document.getElementById('print-root')!
    const [kitchen, bag] = Array.from(root.querySelectorAll('section'))

    expect(kitchen).toHaveTextContent('Kitchen')
    expect(kitchen).toHaveTextContent('#7')
    expect(kitchen).toHaveTextContent('2×Iraqi kebabLarge')
    expect(kitchen).toHaveTextContent('1.5 kgTomatoes')
    expect(kitchen).toHaveTextContent('Ready by')

    expect(bag).toHaveTextContent('Package')
    expect(bag).toHaveTextContent('Customer: Zainab')
    expect(bag).toHaveTextContent('Cash: captain collects 20,250 IQD')
    expect(root).not.toHaveTextContent('4821')
    expect(root).not.toHaveTextContent('+9647701234567')
  })
})
