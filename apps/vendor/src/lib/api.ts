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
  subtotal?: string
  /** Shown to the store's team while the order is in progress. */
  customer_contact?: { name: string; phone: string } | null
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

/** Who the signed-in user is at a store; decides which sections they see. */
export type StoreRole = 'owner' | 'manager' | 'cashier'

export const DAYS = ['sat', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri'] as const
export type Day = (typeof DAYS)[number]
/** One opening per day as [open, close] ("10:00", "23:30"), or null when closed. */
export type OpeningHours = Partial<Record<Day, [string, string] | null>>

export interface Store {
  id: number
  name: string
  is_open: boolean
  products: Product[]
  my_role?: StoreRole
  commission_rate?: string
  opening_hours?: OpeningHours
}

export interface ProductInput {
  name_ar: string
  name_ku: string
  name_en: string
  menu_section: string
  price: string
  unit_type: 'item' | 'kg'
}

export interface TeamMember {
  id: number
  user: number
  phone: string
  name: string
  role: 'manager' | 'cashier'
}

export interface Team {
  owner: { user: number; phone: string; name: string; role: 'owner' }
  members: TeamMember[]
}

export interface Report {
  from: string
  to: string
  orders: number
  delivered: number
  cancelled: number
  cancelled_by: Record<string, number>
  food_sales: number
  store_discounts: number
  commission: number
  payout: number
  average_order: number
  average_prep_minutes: number | null
  days: { date: string; orders: number; sales: number }[]
  hours: { hour: number; orders: number }[]
  top_items: { product: number; name: Names; quantity: string; orders: number; sales: number }[]
}

export interface WeekFigures {
  orders_count: number
  food_sales: number
  store_discounts: number
  commission: number
  payout: number
}

export interface Statement extends WeekFigures {
  id: number
  store_name: string
  period_start: string
  period_end: string
  status: 'due' | 'paid'
  paid_at: string | null
  paid_reference: string
}

export interface StatementLine {
  order: number
  delivered_at: string
  payment_type: 'cod' | 'card' | 'wallet'
  food_sales: number
  store_discount: number
  commission: number
  payout: number
}

export interface Billing {
  current_week: WeekFigures & { period_start: string; period_end: string }
  due_total: number
  paid_total: number
  commission_rate: string
  statements: Statement[]
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
    this.send<{ phone: string; channel: string; resend_in: number }>('POST', '/api/auth/otp/request/', {
      phone,
      channel,
    })
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

  // Store team, menu, hours (owner and managers)
  team = (storeId: number) => this.send<Team>('GET', `/api/vendors/${storeId}/team/`)
  addMember = (storeId: number, member: { phone: string; name: string; role: 'manager' | 'cashier' }) =>
    this.send<TeamMember>('POST', `/api/vendors/${storeId}/team/`, member)
  setMemberRole = (storeId: number, memberId: number, role: 'manager' | 'cashier') =>
    this.send<TeamMember>('PATCH', `/api/vendors/${storeId}/team/${memberId}/`, { role })
  removeMember = (storeId: number, memberId: number) =>
    this.send<null>('DELETE', `/api/vendors/${storeId}/team/${memberId}/`)
  addProduct = (storeId: number, product: ProductInput) =>
    this.send<Product>('POST', `/api/vendors/${storeId}/products/`, product)
  updateProduct = (productId: number, product: Partial<ProductInput>) =>
    this.send<Product>('PATCH', `/api/products/${productId}/`, product)
  removeProduct = (productId: number) => this.send<null>('DELETE', `/api/products/${productId}/`)
  setHours = (storeId: number, hours: OpeningHours) =>
    this.send<{ id: number; opening_hours: OpeningHours }>('PUT', `/api/vendors/${storeId}/hours/`, hours)

  // Reports and billing
  report = (storeId: number, from: string, to: string) =>
    this.send<Report>('GET', `/api/vendors/${storeId}/report/?from=${from}&to=${to}`)
  billing = (storeId: number) => this.send<Billing>('GET', `/api/vendors/${storeId}/billing/`)
  statement = (storeId: number, statementId: number) =>
    this.send<Statement & { orders: StatementLine[] }>('GET', `/api/vendors/${storeId}/statements/${statementId}/`)

  /** Downloads a statement as a spreadsheet (CSV); the token rides in the header, not the URL. */
  async downloadStatement(storeId: number, statement: Statement) {
    const response = await fetch(`/api/vendors/${storeId}/statements/${statement.id}/?download=csv`, {
      headers: this.token ? { Authorization: `Token ${this.token}` } : {},
    })
    if (!response.ok) throw new ApiError('generic', response.status)
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = `wasel-${statement.period_start}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  // Orders
  openOrders = async () =>
    (await this.send<{ results: Order[] }>('GET', `/api/orders/?status=${BOARD_STATUSES.join(',')}&page_size=100`))
      .results
  accept = (id: number, prepMinutes: number) =>
    this.send<Order>('POST', `/api/orders/${id}/accept/`, { prep_minutes: prepMinutes })
  reject = (id: number, reason: string) => this.send<Order>('POST', `/api/orders/${id}/reject/`, { reason })
  ready = (id: number) => this.send<Order>('POST', `/api/orders/${id}/ready/`)

  socketUrl() {
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${scheme}://${location.host}/ws/orders/?token=${encodeURIComponent(this.token ?? '')}`
  }
}
