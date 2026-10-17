# Wasel Backend (Django REST Framework)

Runs in Docker with PostGIS, since GeoDjango needs GDAL/GEOS/PROJ which are easiest to get from the image.

## Run

From the repository root:

```bash
docker compose up
```

This starts the API server, PostGIS, Redis and a Celery worker. The API is at http://localhost:8000/api/ and the admin at http://localhost:8000/admin/. If port 8000 (or 5432) is taken, pick others:

```bash
WASEL_WEB_PORT=8010 WASEL_DB_PORT=5433 docker compose up
```

Create an admin user:

```bash
docker compose run --rm web python manage.py createsuperuser
```

## Test

```bash
docker compose run --rm web python manage.py test
```

## Apps

| App | Models |
| :--- | :--- |
| `accounts` | `User` (phone login, role: customer/captain/vendor), `PhoneOTP`, `WalletTransaction` |
| `subscriptions` | `WaselPlusSubscription` |
| `vendors` | `Vendor`, `Product`, `ProductModifier`, `Offer` |
| `orders` | `Order`, `OrderItem`, `OrderItemModifier`, `Rating` |

Money fields are whole Iraqi dinars. `Vendor.commission_for(subtotal)` applies the vendor's commission rate, or 0 during its commission-free period.

## Phone login

Customers, captains and vendors log in with their phone number and a 6-digit code. The test page is at http://localhost:8000/login/ (Arabic, Kurdish and English).

1. `POST /api/auth/otp/request/` with `{"phone": "07701234567", "channel": "whatsapp"}` sends a code. `channel` is `whatsapp` (default) or `sms`; if WhatsApp fails the code goes by SMS, and the response says which was used.
2. `POST /api/auth/otp/verify/` with `{"phone": "...", "code": "123456"}` returns `{"token", "is_new_user", "user"}`. A first login creates a customer account.
3. Send `Authorization: Token <token>` on later requests. `GET`/`PATCH /api/auth/me/` reads or updates name and language; `POST /api/auth/logout/` deletes the token.

Rules: codes last 5 minutes, one code per minute and 5 per hour per number, 5 wrong guesses lock a code, and only a hash of the code is stored. Requests are also limited per IP (10 code requests and 30 checks per hour).

In development (`DJANGO_DEBUG=1`) codes are written to the server log:

```bash
docker compose logs web | grep "login code"
```

To send real WhatsApp codes, create an authentication template with a copy-code button in WhatsApp Manager and set:

| Variable | Meaning |
| :--- | :--- |
| `WHATSAPP_TOKEN` | Cloud API access token |
| `WHATSAPP_PHONE_NUMBER_ID` | Sender phone number ID |
| `WHATSAPP_TEMPLATE` | Template name (default `wasel_login_code`) |
| `WHATSAPP_TEMPLATE_LANGUAGE` | Template language (default `ar`) |

No SMS provider is connected yet. With `DJANGO_DEBUG` off, SMS sending fails until one is added in `accounts/otp.py`.

## API (so far)

| Endpoint | Notes |
| :--- | :--- |
| `GET /api/vendors/` | `?lat=&lng=` shows only vendors that deliver there, nearest first; `?type=`, `?cuisine=`. Open vendors come first. |
| `GET /api/vendors/{id}/` | Vendor with full menu and modifiers. |
| `GET /api/offers/` | Offers running now; `?banner=1` for home banners. |
| `GET /api/orders/` | Login required. Orders where you are the customer, captain or vendor owner. The delivery PIN is shown to the customer only. |
| `POST /api/orders/quote/` | Login required. Prices a cart without placing it (see below). |
| `POST /api/orders/` | Login required. Places the order at exactly the quoted price. |
| `POST /api/orders/{id}/<step>/` | Moves an order through its statuses (see below). |
| `GET /api/orders/available/` | Captains only. Accepted orders no captain has taken yet, oldest first. |

## Placing orders

Both endpoints take the same cart. Placing an order also needs `delivery_address` and optionally `payment_type` (`cod` default, `card`, `wallet`):

```json
{
  "vendor": 1,
  "items": [
    {"product": 3, "quantity": 2, "modifiers": [7, 9]},
    {"product": 5, "quantity": "1.5"}
  ],
  "delivery_latitude": 33.3496,
  "delivery_longitude": 44.4009,
  "offer": null,
  "tip": 1000
}
```

How the price is built (`orders/pricing.py`, values in `ORDER_PRICING` in settings):

* **Subtotal:** each line is (product price + chosen options) × quantity. Per-kg items accept decimals; other items need whole numbers. Every required option group must be chosen.
* **Delivery fee:** 1,500 IQD for the first 2 km, then 250 IQD per started km, rounded up to 250 IQD. The store must be open and the address inside its delivery radius.
* **Service fee:** 500 IQD.
* **Wasel Plus:** members get free delivery from a 15,000 IQD subtotal and a 250 IQD service fee.
* **Offers:** the best running offer for that store or the whole platform is applied automatically. Sending `offer` uses that one instead, or fails with `offer_not_applicable`.
* **Total:** subtotal + delivery fee + service fee + tip - discount.
* **Commission:** the store's rate on the subtotal, or on the discounted subtotal when the store funds the offer. Platform offers don't reduce it, and it is 0 during the commission-free period. It is saved on the order but not shown to customers.

Wallet orders are paid at once from the customer's balance; cash and card orders stay `pending` (no card gateway yet). Errors come back as `{"error": "<code>", "detail": "..."}` with codes such as `vendor_closed`, `out_of_delivery_area`, `product_unavailable`, `missing_required_option`, `offer_not_applicable` and `insufficient_wallet_balance`.

## Order status flow

```
received --accept--> preparing --ready--> ready --pickup--> out_for_delivery --deliver (PIN)--> delivered
   |                     ^                  ^
   |-- cancel (customer) +-- claim (captain, once, while preparing or ready)
   +-- reject (store)
```

| Step | Who | Body | Rule |
| :--- | :--- | :--- | :--- |
| `accept` | Store owner | `{"prep_minutes": 15}` (5-120) | Only from `received`. Sets the estimated ready time. |
| `reject` | Store owner | `{"reason": "..."}` | Only from `received`. |
| `ready` | Store owner | | Only from `preparing`. |
| `cancel` | Customer | `{"reason": "..."}` (optional) | Only before the store accepts. |
| `claim` | Any captain | | While `preparing` or `ready` and no captain yet. First captain wins; others get `already_claimed`. |
| `pickup` | The order's captain | | Only from `ready`. |
| `deliver` | The order's captain | `{"pin": "1234"}` | The customer reads the 4-digit PIN at the door. 5 wrong PINs lock the order until support steps in. |

Every step returns the updated order, or `{"error", "detail"}`: `not_allowed` (403), `invalid_transition` or `already_claimed` (409), `wrong_pin` (400), `pin_locked` (423). Users who aren't part of an order get 404. Each step records its time (`accepted_at`, `ready_at`, `picked_up_at`, `delivered_at`, `cancelled_at`).

Cancelled or rejected wallet orders are refunded to the wallet straight away. Cash orders are marked paid when delivered.

## Live order updates (WebSockets)

Apps keep one socket open per signed-in user, using the same API token as REST:

```
ws://localhost:8000/ws/orders/?token=<token>
```

On connect the server sends `{"type": "connected", "user_id": 12}`. A missing or wrong token is accepted and then closed with code `4401`, so the app can tell it apart from a network drop. Send `{"type": "ping"}` to keep a mobile connection alive; the server answers `{"type": "pong"}`.

| Message | Who gets it | When |
| :--- | :--- | :--- |
| `{"type": "order.updated", "order": {...}}` | The customer, the store owner and the order's captain | The order is placed or changes status. `order` is the same as `GET /api/orders/{id}/`; only the customer's copy includes `delivery_pin`. |
| `{"type": "order.available", "order": {...}}` | All captains | A store accepts an order that has no captain yet. |
| `{"type": "order.unavailable", "order_id": 12}` | All captains | That order was claimed or cancelled; remove it from the list. |
| `{"type": "order.stuck", "alert": {...}}` | Staff users | An order has sat in one step too long (see below). |
| `{"type": "wasel_plus.trial_ended"}` | That customer | Their free Wasel Plus trial has ended; offer the paid plan. |
| `{"type": "captain.location", "order_id": 12, "location": {...}}` | The customer and the store | The order's captain moved (see below). |

Updates go through Redis (`REDIS_URL`), so they reach sockets on any server process. They are sent after the change is saved; if Redis is down the change still succeeds and the failure is logged. `runserver` serves both HTTP and WebSockets through Daphne.

## Live captain tracking

Captains send their GPS position every few seconds while working:

* Over their socket: `{"type": "location", "lat": 33.3045, "lng": 44.4214, "heading": 125, "speed": 7.2}` (`heading` in degrees, `speed` in m/s, both optional).
* Or by REST when the app is in the background: `POST /api/captain/location/` with the same fields (204).

Only captains can send positions. Updates less than 2 seconds apart are dropped. The latest position is saved (`CaptainLocation`, one row per captain, useful later for dispatch) and pushed as `captain.location` to the customer and store of each order the captain is on, from claim until delivery. Once an order is delivered or cancelled, its customer stops receiving the captain's position.

Order responses now include `vendor_name`, `vendor_location`, `delivery_location` and, while the order is active, `captain_location`, so a map can start from the last known spot before live updates arrive.

**Tracking page.** `/track/<order_id>/` shows the order on a map for the signed-in customer (it reuses the token saved by `/login/`): store, home and a captain marker that glides between fixes, the status steps, the delivery PIN and when the captain was last seen. It works in Arabic, Kurdish and English, light and dark. Maps come from OpenFreeMap through MapLibre GL, which needs no API key; set `MAP_STYLE_LIGHT` and `MAP_STYLE_DARK` to a licensed provider's style URLs if traffic grows.

## Background jobs (Celery)

The `worker` service runs Celery with its beat schedule (`celery -A wasel worker -B`). In production, run beat as its own single process (`celery -A wasel beat`) next to one or more workers.

**Stuck-order alerts** (every minute). An order is flagged when it sits too long in one step (minutes in `STUCK_ORDER_MINUTES`):

| Reason | Flagged when |
| :--- | :--- |
| `not_accepted` | The store hasn't accepted 5 minutes after the order was placed |
| `not_ready` | Still preparing 15 minutes past the store's estimated ready time |
| `no_captain` | No captain has taken it 10 minutes after the store accepted |
| `not_picked_up` | Ready with a captain but not picked up after 15 minutes |
| `delivery_late` | Out for delivery for more than 60 minutes |

Each alert is saved as a `StuckOrderAlert` (admin: Orders > Stuck order alerts) and pushed to staff sockets. There is only one open alert per order and reason, and it is resolved automatically once the order moves on.

**Wasel Plus trials.** A customer's first login starts a free 14-day trial (`WASEL_PLUS_TRIAL_DAYS`). Every 15 minutes, finished trials are marked expired and the customer's app gets `wasel_plus.trial_ended`. Pricing already stops the benefits at the trial's end date, so the check never lets anyone keep free delivery.

Not built yet: Wasel Plus billing, push notifications for when the app is closed, automatic captain dispatch, an SMS provider and card payments.
