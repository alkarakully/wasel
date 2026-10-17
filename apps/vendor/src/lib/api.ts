// Wasel API types and calls used by the vendor portal.

export type Lang = 'ar' | 'ku' | 'en'
export type Names = { ar: string; ku: string; en: string }

export type OrderStatus = 'received' | 'preparing' | 'ready' | 'out_for_delivery' | 'delivered' | 'cancelled'

export interface OrderItem {
  id: number
  product: number
  name: Names
  unit_type: 'item' | 'kg'
  quantity: string
  line_total: string
  modifiers: { modifier: number; group_name: string; name: Names }[]
}

export interface Order {
  id: number
  vendor: number
  vendor_name: string
  captain: number | null
  status: OrderStatus
  payment_type: 'cod' | 'card' | 'wallet'
  delivery_address: string
  total_amount: string
  items: OrderItem[]
  created_at: string
  accepted_at: string | null
  estimated_ready_at: string | null
}

export interface Modifier {
  id: number
  group_name: string
  name_ar: string
  name_ku: string
  name_en: string
}

export interface Product {
  id: number
  name_ar: string
  name_ku: string
  name_en: string
  menu_section: string
  price: string
  unit_type: 'item' | 'kg'
  is_available: boolean
  modifiers: Modifier[]
}

export interface Store {
  id: number
  name: string
  is_open: boolean
  products: Product[]
}

export interface User {
  id: number
  phone: string
  name: string
  role: 'customer' | 'captain' | 'vendor'
}

/** Board columns: everything the store still has to act on or hand over. */
export const BOARD_STATUSES: OrderStatus[] = ['received', 'preparing', 'ready']

export class ApiError extends Error {
  code: string
  status: number
  retryAfter?: number

  constructor(code: string, status: number, retryAfter?: number) {
    super(code)
    this.code = code
    this.status = status
    this.retryAfter = retryAfter
  }
}

const TOKEN_KEY = 'wasel_vendor_token'

export function loadToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function saveToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Private mode: the session lasts until the tab closes.
  }
}

export class Api {
  token: string | null

  constructor(token: string | null = loadToken()) {
    this.token = token
  }

  /** Switch accounts; remembered across reloads unless `remember` is false. */
  setToken(token: string | null, remember = true) {
    this.token = token
    if (remember) saveToken(token)
  }

  private async send<T>(method: string, path: string, body?: unknown): Promise<T> {
    let response: Response
    try {
      response = await fetch(path, {
        method,
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(this.token ? { Authorization: `Token ${this.token}` } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch {
      throw new ApiError('network', 0)
    }
    const data = response.status === 204 ? null : await response.json().catch(() => null)
    if (!response.ok) {
      let code = response.status === 401 ? 'unauthorized' : 'generic'
      if (data?.error) code = data.error
      else if (data?.phone) code = 'invalid_phone'
      else if (data?.code) code = 'invalid_code'
      else if (data?.reason) code = 'reason_required'
      throw new ApiError(code, response.status, data?.retry_after)
    }
    return data as T
  }

  // Auth
  requestCode = (phone: string, channel: 'whatsapp' | 'sms') =>
    this.send<{ phone: string; channel: string; resend_in: number }>('POST', '/api/auth/otp/request/', { phone, channel })
  verifyCode = (phone: string, code: string) =>
    this.send<{ token: string; user: User }>('POST', '/api/auth/otp/verify/', { phone, code })
  me = () => this.send<User>('GET', '/api/auth/me/')
  logout = () => this.send<null>('POST', '/api/auth/logout/')

  // Stores and menus
  myStores = () => this.send<Store[]>('GET', '/api/vendors/mine/')
  setOpen = (storeId: number, isOpen: boolean) =>
    this.send<{ id: number; is_open: boolean }>('POST', `/api/vendors/${storeId}/open/`, { is_open: isOpen })
  setAvailable = (productId: number, isAvailable: boolean) =>
    this.send<{ id: number; is_available: boolean }>('POST', `/api/products/${productId}/availability/`, {
      is_available: isAvailable,
    })

  // Orders
  openOrders = async () =>
    (await this.send<{ results: Order[] }>('GET', `/api/orders/?status=${BOARD_STATUSES.join(',')}&page_size=100`)).results
  accept = (id: number, prepMinutes: number) =>
    this.send<Order>('POST', `/api/orders/${id}/accept/`, { prep_minutes: prepMinutes })
  reject = (id: number, reason: string) => this.send<Order>('POST', `/api/orders/${id}/reject/`, { reason })
  ready = (id: number) => this.send<Order>('POST', `/api/orders/${id}/ready/`)

  socketUrl() {
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${scheme}://${location.host}/ws/orders/?token=${encodeURIComponent(this.token ?? '')}`
  }
}
