// Wasel load test (k6). Everyone at once, like a busy evening:
//   customers  browse, search, open a store, quote, sometimes order (ramping up to PEAK)
//   trackers   customers with the app open on an order: live socket + a reload every 30 s
//   captains   online, GPS every 3 s over the socket, decline the offers they get
//   stores     tablets: live socket, reload the board every 10 s, accept and mark ready
// Users, tokens and menus come from `manage.py seed_loadtest` (/loadtest/data.json).
import http from 'k6/http'
import ws from 'k6/ws'
import { check, sleep } from 'k6'
import { Counter, Trend } from 'k6/metrics'
import { SharedArray } from 'k6/data'

const BASE = __ENV.BASE || 'http://localhost:8090'
const WS = BASE.replace(/^http/, 'ws')
const PEAK = Number(__ENV.PEAK || 1000)
const MINUTES = Number(__ENV.MINUTES || 2)

// Each list is shared between all virtual users; reading an entry copies only that entry.
const file = () => JSON.parse(open('/loadtest/data.json'))
const customers = new SharedArray('customers', () => file().customers)
const captains = new SharedArray('captains', () => file().captains)
const stores = new SharedArray('stores', () => file().stores)
const CENTRE = new SharedArray('centre', () => [file().centre])[0]
const ordersPlaced = new Counter('orders_placed')
const offersSeen = new Counter('dispatch_offers')
const socketMessages = new Counter('socket_messages')
const orderTime = new Trend('place_order_ms', true)

// Behind nginx in production, which says the request came over HTTPS.
const headers = (token) => ({
  headers: {
    Authorization: `Token ${token}`,
    'Content-Type': 'application/json',
    'X-Forwarded-Proto': 'https',
  },
})

const minutes = (m) => `${Math.max(1, Math.round(m * 60))}s`

export const options = {
  discardResponseBodies: false,
  scenarios: {
    customers: {
      executor: 'ramping-vus',
      exec: 'customer',
      startVUs: 0,
      stages: [
        { duration: minutes(MINUTES), target: Math.round(PEAK * 0.25) },
        { duration: minutes(MINUTES), target: Math.round(PEAK * 0.5) },
        { duration: minutes(MINUTES), target: Math.round(PEAK * 0.75) },
        { duration: minutes(MINUTES), target: PEAK },
        { duration: minutes(MINUTES), target: PEAK },
        { duration: '20s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
    trackers: {
      executor: 'constant-vus',
      exec: 'tracker',
      vus: Number(__ENV.TRACKERS || 300),
      duration: minutes(MINUTES * 5),
    },
    captains: {
      executor: 'constant-vus',
      exec: 'captain',
      vus: Math.min(Number(__ENV.CAPTAINS || 300), captains.length),
      duration: minutes(MINUTES * 5),
    },
    stores: {
      executor: 'constant-vus',
      exec: 'store',
      vus: Math.min(Number(__ENV.STORES || 150), stores.length),
      duration: minutes(MINUTES * 5),
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{kind:browse}': ['p(95)<800'],
    'http_req_duration{kind:order}': ['p(95)<1500'],
  },
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)]
}

function nearby() {
  const { lat, lng } = CENTRE
  return { lat: lat + (Math.random() - 0.5) * 0.08, lng: lng + (Math.random() - 0.5) * 0.08 }
}

function get(path, token, kind) {
  return http.get(`${BASE}${path}`, Object.assign(headers(token), { tags: { kind, name: path.split('?')[0].replace(/\d+/g, '{id}') } }))
}

function post(path, token, body, kind) {
  return http.post(
    `${BASE}${path}`,
    JSON.stringify(body || {}),
    Object.assign(headers(token), { tags: { kind, name: path.replace(/\d+/g, '{id}') } }),
  )
}

// One customer session: home, maybe a search, a store, maybe an order.
export function customer() {
  const me = customers[(__VU * 7 + __ITER) % customers.length]
  const at = nearby()
  const home = get(`/api/vendors/?lat=${at.lat}&lng=${at.lng}`, me.token, 'browse')
  check(home, { 'home 200': (r) => r.status === 200 })
  get('/api/offers/?banner=1', me.token, 'browse')
  get(`/api/vendors/?lat=${at.lat}&lng=${at.lng}&offers=1`, me.token, 'browse')
  sleep(2 + Math.random() * 4)

  if (Math.random() < 0.3) {
    get(`/api/vendors/?lat=${at.lat}&lng=${at.lng}&q=${encodeURIComponent(pick(['كباب', 'برغر', 'pizza', 'صيدلية']))}`, me.token, 'browse')
    sleep(1 + Math.random() * 3)
  }

  const store = pick(stores)
  const page = get(`/api/vendors/${store.id}/`, me.token, 'browse')
  check(page, { 'store 200': (r) => r.status === 200 })
  sleep(3 + Math.random() * 6)

  if (Math.random() < 0.35) {
    const cart = {
      vendor: store.id,
      items: [{ product: pick(store.products), quantity: 1 + Math.floor(Math.random() * 3) }],
      delivery_latitude: CENTRE.lat + (Math.random() - 0.5) * 0.02,
      delivery_longitude: CENTRE.lng + (Math.random() - 0.5) * 0.02,
    }
    const quote = post('/api/orders/quote/', me.token, cart, 'order')
    check(quote, { 'quote 200': (r) => r.status === 200 })
    sleep(2 + Math.random() * 4)
    if (Math.random() < 0.5) {
      const placed = post(
        '/api/orders/',
        me.token,
        Object.assign(cart, { delivery_address: 'Karrada, street 52', payment_type: 'cod' }),
        'order',
      )
      orderTime.add(placed.timings.duration)
      if (check(placed, { 'order 201': (r) => r.status === 201 })) ordersPlaced.add(1)
    }
  }
  sleep(5 + Math.random() * 10)
}

// A customer with the app open on their orders: live socket, reload every 30 s.
export function tracker() {
  const me = customers[(customers.length - 1 - __VU) % customers.length]
  ws.connect(`${WS}/ws/orders/?token=${me.token}`, {}, (socket) => {
    socket.on('open', () => get('/api/orders/', me.token, 'browse'))
    socket.on('message', () => socketMessages.add(1))
    socket.setInterval(() => get('/api/orders/', me.token, 'browse'), 30000 + Math.random() * 5000)
    socket.setTimeout(() => socket.close(), 60000 * MINUTES * 5)
  })
}

// A captain on shift: online, GPS every 3 s, taking 7 in 10 offers (declining the
// rest), then picking the order up once it's ready. A delivery needs the customer's
// PIN, which only their app sees, so a captain stays on their first order.
export function captain() {
  const me = captains[(__VU - 1) % captains.length]
  post('/api/captain/status/', me.token, { online: true }, 'captain')
  let { lat, lng } = nearby()
  let carrying = null
  ws.connect(`${WS}/ws/orders/?token=${me.token}`, {}, (socket) => {
    socket.on('message', (raw) => {
      socketMessages.add(1)
      const message = JSON.parse(raw)
      if (message.type === 'dispatch.offer' && carrying === null) {
        offersSeen.add(1)
        if (Math.random() < 0.7) {
          const taken = post(`/api/dispatch/offers/${message.offer.id}/accept/`, me.token, {}, 'captain')
          if (taken.status === 200) carrying = taken.json('id')
        } else {
          post(`/api/dispatch/offers/${message.offer.id}/decline/`, me.token, {}, 'captain')
        }
      }
    })
    socket.setInterval(() => {
      lat += (Math.random() - 0.5) * 0.0004
      lng += (Math.random() - 0.5) * 0.0004
      socket.send(JSON.stringify({ type: 'location', lat, lng, heading: 90, speed: 8 }))
    }, 3000)
    socket.setInterval(() => {
      if (carrying === null) return
      const order = get(`/api/orders/${carrying}/`, me.token, 'captain')
      if (order.status === 200 && order.json('status') === 'ready') {
        post(`/api/orders/${carrying}/pickup/`, me.token, {}, 'captain')
      }
    }, 10000)
    socket.setTimeout(() => socket.close(), 60000 * MINUTES * 5)
  })
}

// A store tablet: live socket, board reload every 10 s, accepting and readying orders.
export function store() {
  const me = stores[(__VU - 1) % stores.length]
  const work = () => {
    const board = get('/api/orders/?status=received,preparing,ready&page_size=100', me.token, 'store')
    if (board.status !== 200) return
    for (const order of board.json('results') || []) {
      if (order.status === 'received') post(`/api/orders/${order.id}/accept/`, me.token, { prep_minutes: 15 }, 'store')
      else if (order.status === 'preparing' && Math.random() < 0.3) post(`/api/orders/${order.id}/ready/`, me.token, {}, 'store')
    }
  }
  ws.connect(`${WS}/ws/orders/?token=${me.token}`, {}, (socket) => {
    socket.on('open', work)
    socket.on('message', () => socketMessages.add(1))
    socket.setInterval(work, 10000 + Math.random() * 2000)
    socket.setTimeout(() => socket.close(), 60000 * MINUTES * 5)
  })
}
