import { vi } from 'vitest'

import type { Api, Order, Store } from '../lib/api'

export function order(overrides: Partial<Order> = {}): Order {
  return {
    id: 7,
    vendor: 1,
    vendor_name: 'Tigris Grill',
    captain: null,
    status: 'received',
    payment_type: 'cod',
    delivery_address: 'Karrada, street 62',
    currency: 'IQD',
    total_amount: '16450',
    created_at: new Date(Date.now() - 3 * 60000).toISOString(),
    accepted_at: null,
    estimated_ready_at: null,
    items: [
      {
        id: 1,
        product: 10,
        name: { ar: 'كباب عراقي', ku: 'کەبابی عێراقی', en: 'Iraqi kebab' },
        unit_type: 'item',
        quantity: '2.000',
        line_total: '18000',
        modifiers: [{ modifier: 3, group_name: 'Size', name: { ar: 'كبير', ku: '', en: 'Large' } }],
      },
      {
        id: 2,
        product: 11,
        name: { ar: 'طماطة', ku: '', en: 'Tomatoes' },
        unit_type: 'kg',
        quantity: '1.500',
        line_total: '2250',
        modifiers: [],
      },
    ],
    ...overrides,
  }
}

export const store: Store = {
  id: 1,
  name: 'Tigris Grill',
  is_open: true,
  country: 'IQ',
  currency: 'IQD',
  products: [
    {
      id: 10,
      name_ar: 'كباب',
      name_ku: '',
      name_en: 'Kebab',
      menu_section: 'Grill',
      price: '9000',
      unit_type: 'item',
      is_available: true,
      modifiers: [],
    },
    {
      id: 11,
      name_ar: 'لبن',
      name_ku: '',
      name_en: 'Laban',
      menu_section: 'Drinks',
      price: '1000',
      unit_type: 'item',
      is_available: false,
      modifiers: [],
    },
  ],
}

/** An Api stand-in whose calls are spies. */
export function fakeApi(overrides: Partial<Record<keyof Api, unknown>> = {}) {
  return {
    token: 'abc',
    accept: vi.fn(async (id: number) => order({ id, status: 'preparing' })),
    reject: vi.fn(async (id: number) => order({ id, status: 'cancelled' })),
    ready: vi.fn(async (id: number) => order({ id, status: 'ready' })),
    setAvailable: vi.fn(async (id: number, isAvailable: boolean) => ({ id, is_available: isAvailable })),
    ...overrides,
  } as unknown as Api
}
