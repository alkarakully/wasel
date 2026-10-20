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
  /** Every amount on the order is in this currency (the store's, when it was placed). */
  currency: string
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
  description_ar: string
  description_ku: string
  description_en: string
  menu_section: string
  /** Path on this server ("/media/products/12-ab.jpg"), or null without a photo. */
  image: string | null
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
  /** Where the store trades: its currency, clock and fees. */
  country: string
  currency: string
  products: Product[]
  my_role?: StoreRole
  commission_rate?: string
  opening_hours?: OpeningHours
}

export interface ProductInput {
  name_ar: string
  name_ku: string
  name_en: string
  description_ar: string
  description_ku: string
  description_en: string
  menu_section: string
  price: string
  unit_type: 'item' | 'kg'
}

export type OfferType = 'percent' | 'fixed' | 'free_delivery'

/** A store's own offer. Checkout applies the best running one the cart qualifies for. */
export interface StoreOffer {
  id: number
  title: string
  type: OfferType
  /** Percent off for "percent", an amount in `currency` for "fixed", "0" for free delivery. */
  value: string
  min_order: string
  currency: string
  starts_at: string
  ends_at: string
  /** Shown on the customer app's home banner (Wasel staff decide). */
  is_banner: boolean
  state: 'running' | 'scheduled' | 'ended'
  orders: number | null
}

export interface OfferInput {
  title: string
  type: OfferType
  value: string
  min_order: string
  starts_at: string
  ends_at: string
}

export interface TeamMember {
  id: number
  user: number
  phone: string
  name: string
  role: 'manager' | 'cashier'
}

/** Someone the owner invited; they join when they accept at their next sign-in. */
export interface TeamInvite {
  id: number
  phone: string
  name: string
  role: 'manager' | 'cashier'
  created_at: string
}

export interface Team {
  owner: { user: number; phone: string; name: string; role: 'owner' }
  members: TeamMember[]
  invites: TeamInvite[]
}

/** An invite to join a store's team, as the invited person sees it. */
export interface Invite {
  id: number
  store: { id: number; name: string; type: StoreType }
  role: 'manager' | 'cashier'
  invited_by: string
  created_at: string
}

export type StoreType = 'restaurant' | 'supermarket' | 'cafe' | 'pharmacy' | 'convenience' | 'flowers'
export const CUISINES = ['popular', 'eastern', 'western', 'fast_food', 'sweets', 'drinks'] as const
export type Cuisine = (typeof CUISINES)[number]
export type ApplicationStatus = 'pending' | 'approved' | 'rejected'

/** One of the owner's stores in any state: waiting for Wasel, approved or rejected. */
export interface StoreApplication {
  id: number
  name: string
  type: StoreType
  cuisine: Cuisine | ''
  address: string
  latitude: number
  longitude: number
  delivery_radius_km: string
  status: ApplicationStatus
  rejection_reason: string
  created_at: string
  reviewed_at: string | null
}

export interface Applications {
  can_apply: boolean
  /** Why not: phone_in_use, application_pending or too_many_applications. */
  reason: string | null
  applications: StoreApplication[]
}

export interface ApplicationInput {
  owner_name?: string
  name: string
  type: StoreType
  cuisine: Cuisine | ''
  address: string
  latitude: number
  longitude: number
  delivery_radius_km: string
}

/** Money from the API: a string with exactly its currency's decimals ("18000", "12.50", "0.750"). */
export type Money = string

export interface Report {
  from: string
  to: string
  currency: string
  orders: number
  delivered: number
  cancelled: number
  cancelled_by: Record<string, number>
  food_sales: Money
  store_discounts: Money
  commission: Money
  payout: Money
  average_order: Money
  average_prep_minutes: number | null
  days: { date: string; orders: number; sales: Money }[]
  hours: { hour: number; orders: number }[]
  top_items: { product: number; name: Names; quantity: string; orders: number; sales: Money }[]
}

export interface WeekFigures {
  orders_count: number
  food_sales: Money
  store_discounts: Money
  commission: Money
  payout: Money
}

export interface Statement extends WeekFigures {
  id: number
  currency: string
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
  food_sales: Money
  store_discount: Money
  commission: Money
  payout: Money
}

export interface Billing {
  currency: string
  current_week: WeekFigures & { period_start: string; period_end: string }
  due_total: Money
  paid_total: Money
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
          // The browser sets the multipart boundary for uploads itself.
          ...(body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
          ...(this.token ? { Authorization: `Token ${this.token}` } : {}),
        },
        body: body === undefined || body instanceof FormData ? body : JSON.stringify(body),
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
  /** `country` says how to read a local number (Iraq by default); numbers with a + code say it themselves. */
  requestCode = (phone: string, channel: 'whatsapp' | 'sms', country = 'IQ') =>
    this.send<{ phone: string; channel: string; resend_in: number }>('POST', '/api/auth/otp/request/', {
      phone,
      channel,
      country,
    })
  verifyCode = (phone: string, code: string, country = 'IQ') =>
    this.send<{ token: string; user: User }>('POST', '/api/auth/otp/verify/', { phone, code, country })
  me = () => this.send<User>('GET', '/api/auth/me/')
  logout = () => this.send<null>('POST', '/api/auth/logout/')

  // Joining Wasel: store applications and team invites
  applications = () => this.send<Applications>('GET', '/api/store-applications/')
  apply = (input: ApplicationInput) => this.send<StoreApplication>('POST', '/api/store-applications/', input)
  myInvites = () => this.send<Invite[]>('GET', '/api/store-invites/')
  answerInvite = (inviteId: number, answer: 'accept' | 'decline') =>
    this.send<{ id: number; status: string }>('POST', `/api/store-invites/${inviteId}/${answer}/`)

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
  /** Invites someone by phone; they join when they accept. */
  addMember = (
    storeId: number,
    member: { phone: string; name: string; role: 'manager' | 'cashier'; country?: string },
  ) => this.send<TeamInvite>('POST', `/api/vendors/${storeId}/team/`, member)
  cancelInvite = (storeId: number, inviteId: number) =>
    this.send<null>('DELETE', `/api/vendors/${storeId}/team/invites/${inviteId}/`)
  setMemberRole = (storeId: number, memberId: number, role: 'manager' | 'cashier') =>
    this.send<TeamMember>('PATCH', `/api/vendors/${storeId}/team/${memberId}/`, { role })
  removeMember = (storeId: number, memberId: number) =>
    this.send<null>('DELETE', `/api/vendors/${storeId}/team/${memberId}/`)
  addProduct = (storeId: number, product: ProductInput) =>
    this.send<Product>('POST', `/api/vendors/${storeId}/products/`, product)
  updateProduct = (productId: number, product: Partial<ProductInput>) =>
    this.send<Product>('PATCH', `/api/products/${productId}/`, product)
  removeProduct = (productId: number) => this.send<null>('DELETE', `/api/products/${productId}/`)
  setProductImage = (productId: number, image: Blob) => {
    const form = new FormData()
    form.append('image', image, 'photo.jpg')
    return this.send<Product>('POST', `/api/products/${productId}/image/`, form)
  }
  removeProductImage = (productId: number) => this.send<Product>('DELETE', `/api/products/${productId}/image/`)

  // Offers
  offers = (storeId: number) => this.send<StoreOffer[]>('GET', `/api/vendors/${storeId}/offers/`)
  addOffer = (storeId: number, offer: OfferInput) =>
    this.send<StoreOffer>('POST', `/api/vendors/${storeId}/offers/`, offer)
  updateOffer = (storeId: number, offerId: number, offer: Partial<OfferInput>) =>
    this.send<StoreOffer>('PATCH', `/api/vendors/${storeId}/offers/${offerId}/`, offer)
  /** Deletes an offer nobody used; one already on orders ends now instead. */
  endOffer = (storeId: number, offerId: number) =>
    this.send<null>('DELETE', `/api/vendors/${storeId}/offers/${offerId}/`)
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
