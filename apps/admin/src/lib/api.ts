/** The platform admin API (/api/console/), signed in with a session cookie. */

export type Lang = 'ar' | 'en'
export type Access = 'read' | 'write'
export type Area = 'overview' | 'stores' | 'orders' | 'people' | 'money' | 'marketing' | 'reports' | 'staff' | 'audit'
export type Role = 'admin' | 'operations' | 'support' | 'finance' | 'marketing'

export interface Me {
  id: number
  email: string
  name: string
  role: Role
  areas: Partial<Record<Area, Access>>
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export class ApiError extends Error {
  status: number
  code: string
  fields: Record<string, string[]>

  constructor(status: number, body: unknown) {
    const data = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>
    const detail = typeof data.detail === 'string' ? data.detail : ''
    super(detail || `HTTP ${status}`)
    this.status = status
    this.code = typeof data.error === 'string' ? data.error : status === 403 ? 'forbidden' : 'unknown'
    this.fields = {}
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) this.fields[key] = value.map(String)
      else if (key === 'detail' && value && typeof value === 'object') {
        for (const [k, v] of Object.entries(value)) this.fields[k] = Array.isArray(v) ? v.map(String) : [String(v)]
      }
    }
  }
}

const BASE = '/api/console/'

function csrfToken() {
  return document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ?? ''
}

/** Called when the session ends (signed out elsewhere, expired); the app shows sign-in. */
let onSignedOut: () => void = () => {}
export function whenSignedOut(callback: () => void) {
  onSignedOut = callback
}

export async function api<T = unknown>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (method !== 'GET') {
    headers['X-CSRFToken'] = csrfToken()
    headers['Content-Type'] = 'application/json'
  }
  const response = await fetch(BASE + path, {
    method,
    headers,
    credentials: 'same-origin',
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new ApiError(response.status, body)
    if (response.status === 403 && !path.startsWith('auth/') && /sign in/i.test(error.message)) onSignedOut()
    throw error
  }
  return body as T
}

export function query(params: Record<string, string | number | undefined | null>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

// --- Shapes ----------------------------------------------------------------

/** Money from the API: a string with exactly its currency's decimals ("18000", "12.50", "0.750"). */
export type Money = string

export interface Person {
  id: number
  name: string
  phone: string
}

export type OrderStatus = 'received' | 'preparing' | 'ready' | 'out_for_delivery' | 'delivered' | 'cancelled'

export interface OrderRow {
  id: number
  status: OrderStatus
  store: { id: number; name: string; phone?: string }
  customer: Person
  captain: Person | null
  total: Money
  currency: string
  payment_type: 'cod' | 'card' | 'wallet'
  payment_status: 'pending' | 'paid' | 'refunded'
  created_at: string
  minutes: number
  alerts: string[] | { id: number; reason: string; created_at: string; resolved_at: string | null }[]
}

export interface OrderDetail extends Omit<OrderRow, 'alerts'> {
  delivery_address: string
  subtotal: Money
  delivery_fee: Money
  service_fee: Money
  tip: Money
  discount: Money
  commission: Money
  estimated_ready_at: string | null
  time_zone: string
  cancelled_by: string
  cancel_reason: string
  timeline: { step: string; at: string }[]
  items: { name: string; name_en: string; quantity: string; price: Money; options: string[] }[]
  alerts: { id: number; reason: string; created_at: string; resolved_at: string | null }[]
  offers: { captain: Person; status: string; distance_m: number; created_at: string }[]
  can_cancel: boolean
  can_release: boolean
  can_dispatch: boolean
}

export type StoreStatus = 'pending' | 'approved' | 'rejected'

export interface StoreRow {
  id: number
  name: string
  type: string
  cuisine: string
  is_open: boolean
  status: StoreStatus
  country: string
  currency: string
  owner: Person
  commission_rate: string
  created_at: string
  orders_today?: number
  sales_today?: number
}

export interface StoreDetail extends StoreRow {
  address: string
  latitude: number
  longitude: number
  delivery_radius_km: string
  commission_free_until: string | null
  opening_hours: Record<string, [string, string] | null>
  time_zone: string
  rejection_reason: string
  reviewed_at: string | null
}

export interface Product {
  id: number
  name_ar: string
  name_ku: string
  name_en: string
  menu_section: string
  price: Money
  currency: string
  unit_type: string
  is_available: boolean
}

export interface Team {
  owner: Person
  members: { id: number; user: number; phone: string; name: string; role: 'manager' | 'cashier' }[]
  invites: { id: number; phone: string; name: string; role: string; created_at: string }[]
}

export interface UserRow {
  id: number
  phone: string
  name: string
  role: 'customer' | 'captain' | 'vendor'
  is_active: boolean
  country: string
  wallet_currency: string
  wallet_balance: Money
  orders: number | null
  joined: string
}

export interface UserDetail extends UserRow {
  language: string
  last_login: string | null
  orders_count: number
  delivered_spend: Money
  deliveries: number
  stores: { id: number; name: string; role: string; status: string }[]
  plus: { status: string; renews_at: string | null; trial_end: string | null } | null
  recent_orders: {
    id: number
    status: OrderStatus
    store: string
    currency: string
    total: Money
    created_at: string
  }[]
  wallet: { id: number; type: string; currency: string; amount: Money; order: number | null; created_at: string }[]
}

export interface StaffRow {
  id: number
  user: number
  email: string
  name: string
  role: Role
  is_active: boolean
  two_factor: boolean
  locked: boolean
  last_login: string | null
  created_at: string
}

export interface AuditRow {
  id: number
  actor: string
  action: string
  target_type: string
  target_id: string
  summary: string
  changes: Record<string, unknown>
  ip: string | null
  created_at: string
}

export interface Statement {
  id: number
  store: number
  store_name: string
  period_start: string
  period_end: string
  orders_count: number
  currency: string
  food_sales: Money
  store_discounts: Money
  commission: Money
  payout: Money
  status: 'due' | 'paid'
  paid_at: string | null
  paid_reference: string
}

export interface WalletRow {
  id: number
  user: Person
  type: string
  currency: string
  amount: Money
  order: number | null
  created_at: string
}

export interface Offer {
  id: number
  store: { id: number; name: string } | null
  country: string
  currency: string
  title: string
  type: 'percent' | 'fixed' | 'free_delivery' | 'bundle'
  value: string
  min_order: Money
  starts_at: string
  ends_at: string
  is_banner: boolean
  state: 'scheduled' | 'running' | 'ended'
  orders: number | null
}

export interface PlusRow {
  id: number
  user: Person
  status: 'trial' | 'active' | 'expired'
  trial_end: string | null
  renews_at: string | null
  created_at: string
}

export interface Figures {
  orders: number
  delivered: number
  cancelled: number
  sales: Money
  commission: Money
  service_fees: Money
  delivery_fees: Money
  discounts: Money
  avg_delivery_minutes: number | null
}

export interface Overview {
  country: string
  currency: string
  time_zone: string
  today: Figures
  month: Figures
  live: {
    active_orders: number
    open_alerts: number
    online_captains: number
    open_stores: number
    stores: number
    applications: number
    customers: number
    plus_members: number
  }
  by_status: Record<string, number>
  days: { day: string; orders: number; sales: Money }[]
  top_stores: { id: number; name: string; orders: number; sales: Money }[]
}

export interface Report {
  from: string
  to: string
  country: string
  currency: string
  time_zone: string
  totals: Figures
  customers: number
  days: { day: string; orders: number; sales: Money; commission: Money }[]
  stores: { id: number; name: string; orders: number; sales: Money; commission: Money }[]
  payments: Record<string, { orders: number; sales: Money }>
  cancelled_by: Record<string, number>
}

export interface Alert {
  id: number
  order: number
  store: string
  status: OrderStatus
  reason: string
  minutes: number
}

export interface CaptainPin {
  id: number
  name: string
  phone: string
  online: boolean
  lat: number | null
  lng: number | null
  seconds_ago: number
  order: number | null
}
