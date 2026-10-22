# Wasel Backend (Django REST Framework)

Runs in Docker with PostGIS, since GeoDjango needs GDAL/GEOS/PROJ which are easiest to get from the image.

## Run

From the repository root:

```bash
docker compose up
```

This starts the API server, PostGIS, Redis and a Celery worker. The API is at http://localhost:8000/api/ and the Django admin at http://localhost:8000/django-admin/ (superusers only; set `DJANGO_ADMIN_PATH` to move it). The Wasel team's day-to-day tool is the platform admin in `apps/admin` (see below). If port 8000 (or 5432) is taken, pick others:

```bash
WASEL_WEB_PORT=8010 WASEL_DB_PORT=5433 docker compose up
```

Create an admin user:

```bash
docker compose run --rm web python manage.py createsuperuser
```

## Platform admin

The Wasel team runs the platform from the platform admin, a React app at `/admin/` (source in [`apps/admin`](../apps/admin/README.md)). Staff sign in with a work email, a password and a 6-digit code from an authenticator app (set up on first sign-in), separately from the phone-code login the apps use. Five wrong tries lock the account for 15 minutes; a session lasts 12 hours.

Create the first login (it asks for the password; `--phone` instead gives an existing superuser a login):

```bash
docker compose run --rm web python manage.py create_console_admin --email you@wasel.iq --name "Your Name"
```

Each teammate has one role, and the server enforces it on every request:

| Area | Admin | Operations | Support | Finance | Marketing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Overview | view | view | view | view | view |
| Orders, dispatch and alerts | change | change | change | view | — |
| Stores, applications, menus, store teams | change | change | view | view | view |
| People (block, unblock) | change | change | change | view | — |
| Money (payouts, wallet ledger, wallet adjustments) | change | — | — | change | — |
| Reports | view | view | — | view | view |
| Marketing (offers, banners, Wasel Plus) | change | view | — | — | change |
| Team and audit log | change | — | — | — | — |

Every change made there (store edits and approvals, cancellations with refunds, released captains, blocks, wallet adjustments with their reason, payouts, offers, team changes, sign-ins) is written to the audit log with who, when, what changed and from which IP. The API is `/api/console/` (`backend/console/`); it only accepts the platform admin's session cookie with CSRF, never an app token, and not a Django admin session without the authenticator code.

## Django admin

The Django admin is kept as an emergency tool at `/django-admin/` (set `DJANGO_ADMIN_PATH` to a long random path in production). Only superusers get in, with the account from `createsuperuser` (any phone number works for staff; app accounts need an Iraqi number because they sign in by code). Day-to-day work happens in the platform admin; the old operations page at `/ops/` now sends people there.

## Joining Wasel: store sign-up and approval

Store owners sign themselves up from the store portal (**Join Wasel as a store**): they verify their number with the login code, then send their name and first store (name, restaurant or supermarket, cuisine, address, map spot, delivery distance). That makes the account a store account and the store an application (`Vendor.status` `pending`). Wasel staff approve or reject it in the platform admin › Stores › Applications, and the owner gets a push and sees the result in the portal (with the reason when rejected, and a way to fix and resend). An approved owner adds more branches from **Store settings** in the portal; each goes through the same approval.

Until a store is approved, customers never see it (lists, details, offers, quotes and orders all act as if it doesn't exist), it can't open or take orders, and nobody has a role there, so none of the store endpoints below work for it. Stores staff create in the admin start out approved.

A fresh customer account (no orders, no wallet history) may become a store account; numbers with a customer history, captains and staff can't.

| Endpoint | What it does |
| :--- | :--- |
| `GET /api/store-applications/` | Your stores in every state, whether you may apply now and why not (`application_pending`, `too_many_applications`, `phone_in_use`) |
| `POST /api/store-applications/` | Apply: `{owner_name?, name, type, cuisine, address, latitude, longitude, delivery_radius_km}` |
| `GET /api/ops/applications/?status=` | Staff: applications (pending by default) |
| `POST /api/ops/applications/{id}/approve/` / `reject/` | Staff: `{commission_rate}` / `{reason}` |

## Stores: team, menu, reports and billing

Each store has an owner (`Vendor.owner`) and can have a team (`StoreMember`, role manager or cashier). Owners invite people by phone from the store portal (`StoreInvite`); the person joins only when they accept, the next time they sign in to the portal or the tablet app (a new number just signs in with a code and sees the invite first). Accepting makes the account a store account. The rules live in `vendors/access.py`:

| | Orders, stock, open/closed | Menu, hours | Reports | Billing | Team |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Owner | ✓ | ✓ | ✓ | ✓ | ✓ |
| Manager | ✓ | ✓ | ✓ | | |
| Cashier | ✓ | | | | |

Everyone on the team gets the store's live order updates and new-order pushes.

| Endpoint | What it does |
| :--- | :--- |
| `GET/POST /api/vendors/{id}/team/`, `PATCH/DELETE .../team/{member}/` | List members and open invites, invite (by phone), change role, remove |
| `DELETE /api/vendors/{id}/team/invites/{invite}/` | Cancel an invite |
| `GET /api/store-invites/`, `POST /api/store-invites/{id}/accept/` / `decline/` | The invited person: invites to their number, and their answer |
| `POST /api/vendors/{id}/products/`, `PATCH/DELETE /api/products/{id}/` | Add, edit, remove menu items (ordered items are archived) |
| `PUT /api/vendors/{id}/hours/` | Opening hours: `{"sat": ["10:00", "23:30"], "fri": null, ...}` |
| `GET /api/vendors/{id}/report/?from=&to=` | Sales, earnings, orders, prep time, cancellations, by day and hour, best sellers |
| `GET /api/vendors/{id}/billing/` | This week so far, totals due and paid, statements |
| `GET /api/vendors/{id}/statements/{sid}/` | One week with every order; `?download=csv` for a spreadsheet |

**Billing.** Wasel collects every payment (cash through captains, card and wallet in the app) and pays each store weekly, Saturday to Friday in Baghdad. For each delivered order the store gets the food subtotal minus Wasel's commission and minus discounts from the store's own offers (platform-wide offers are paid by Wasel). A Celery job makes the `Statement`s hourly once a week has ended (it catches up on missed weeks and never makes one twice). Staff see what's due in the platform admin › Money › Payouts and mark statements paid with a transfer reference; owners see it in the portal.

## Tenant isolation

Every store is a tenant. Nobody at one store can see or change another store's orders, customers, menu, hours, team, reports or billing:

- **Every store endpoint checks the store and the role on each request** (`vendors/access.py`). Lookups go through the store in the URL, so an ID from another store returns 404 (a statement, team member or product of store B can't be reached through store A).
- **Order lists and order steps** are limited to the order's customer, its captain and the store's team. The customer's name and phone go only to the order's captain and store team while the order is in progress; the delivery PIN goes only to the customer.
- **Live sockets** join only the channels of the stores the user works at, chosen when the socket connects. Any change to someone's access (removed from a team, added to one, blocked, signed out, store given to another owner) closes their open sockets at once (close code 4409); apps reconnect and get exactly what they're allowed now, or are refused (4401).
- **Pushes** go to the store's current team only.
- **Staff endpoints** (`/api/console/` for the platform admin, and the older `/api/ops/`) need a signed-in staff session; app tokens don't work there. The platform admin also needs the authenticator code.
- **Blocked accounts** lose API and socket access immediately.

`vendors/test_isolation.py` tries every store endpoint from the owner, a manager and a cashier of store A against store B, and checks the sockets; add new store endpoints to it.

In production nginx also keeps the socket's sign-in token out of its access log, and serves the store portal with a strict Content-Security-Policy (only its own scripts, only this server), `X-Frame-Options: DENY` and `nosniff`.

## Test

```bash
docker compose run --rm web python manage.py test
```

## Apps

| App | Models |
| :--- | :--- |
| `accounts` | `User` (phone, optional email and password, role: customer/captain/vendor), `PhoneOTP` (WhatsApp and email codes), `AuthToken` (one per signed-in device), `WalletTransaction` |
| `subscriptions` | `WaselPlusSubscription` |
| `vendors` | `Vendor`, `StoreMember`, `Product`, `ProductModifier`, `Offer` |
| `orders` | `Order`, `OrderItem`, `OrderItemModifier`, `Rating` |
| `ops` | No models: the staff operations page and its API |
| `billing` | `Statement` (weekly store payouts) |

Money fields are whole Iraqi dinars. `Vendor.commission_for(subtotal)` applies the vendor's commission rate, or 0 during its commission-free period.

## Signing in

Customers, captains and store teams sign in with a 6-digit code or a password. There is no SMS. The test page is at http://localhost:8000/login/ (Arabic, Kurdish and English).

**With a code**

1. `POST /api/auth/otp/request/` with `{"phone": "07701234567", "country": "IQ"}` sends a code by WhatsApp. With `{"email": "ali@example.com"}` it sends one by email, but only to an email already confirmed on an account (`no_account_for_email`, 404, otherwise). The response says where it went and by which channel.
2. `POST /api/auth/otp/verify/` with `{"phone" or "email", "code": "123456"}` returns `{"token", "is_new_user", "user"}`. A phone number's first sign-in creates a customer account; every account has a phone number.

**With a password**

People sign up with a code, then the apps offer to set a password. Forgot it? Sign in with a code and set a new one.

- `POST /api/auth/password/login/` with `{"login": phone or email, "password", "country"}` returns the same as a code sign-in. A wrong password and an unknown account give the same `invalid_login`. Five wrong passwords lock password sign-in for 15 minutes (`locked`, 429, with `retry_after`); codes still work.
- `POST /api/auth/password/` (signed in) with `{"password"}` sets or changes it, after Django's password checks (`weak_password`). It signs out the account's other devices.

**Email on the account** (signed in)

- `POST /api/auth/email/` with `{"email"}` sends a code to it; `POST /api/auth/email/verify/` with `{"email", "code"}` adds it. An email belongs to one account (`email_taken`, 409). `DELETE /api/auth/email/` removes it.

**Sessions**

Send `Authorization: Token <token>` on later requests. Each sign-in is its own device: the token lasts until that device logs out (`POST /api/auth/logout/` ends only that device). `GET`/`PATCH /api/auth/me/` reads or updates name and language, and shows `email` and `has_password`.

Rules: codes last 5 minutes, one code per minute and 5 per hour per phone or email, 5 wrong guesses lock a code, and only a hash of the code is stored. Requests are also limited per IP (10 code requests, 30 code checks and 30 password sign-ins per hour).

In development (`DJANGO_DEBUG=1`) codes, WhatsApp and email alike, are written to the server log:

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

To send real email codes, point these at any SMTP provider (Gmail or Google Workspace, Zoho, Mailgun, Brevo, Amazon SES SMTP...):

| Variable | Meaning |
| :--- | :--- |
| `EMAIL_HOST` | SMTP server; email codes stay in the log until it's set |
| `EMAIL_PORT` | Default `587` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP login |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | `1` for STARTTLS (default) / `1` for SSL on port 465 |
| `DEFAULT_FROM_EMAIL` | Sender, e.g. `Wasel <no-reply@example.com>` |

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
| `{"type": "dispatch.offer", "offer": {...}}` | One captain | An order offered to them alone, until `expires_at` (see below). |
| `{"type": "dispatch.offer_closed", "offer_id": 3, "reason": "expired"}` | That captain | The offer ended; close it. |

Updates go through Redis (`REDIS_URL`), so they reach sockets on any server process. They are sent after the change is saved; if Redis is down the change still succeeds and the failure is logged. `runserver` serves both HTTP and WebSockets through Daphne.

## Live captain tracking

Captains send their GPS position every few seconds while working:

* Over their socket: `{"type": "location", "lat": 33.3045, "lng": 44.4214, "heading": 125, "speed": 7.2}` (`heading` in degrees, `speed` in m/s, both optional).
* Or by REST when the app is in the background: `POST /api/captain/location/` with the same fields (204).

Only captains can send positions. Updates less than 2 seconds apart are dropped. The latest position is saved (`CaptainLocation`, one row per captain, useful later for dispatch) and pushed as `captain.location` to the customer and store of each order the captain is on, from claim until delivery. Once an order is delivered or cancelled, its customer stops receiving the captain's position.

Order responses now include `vendor_name`, `vendor_location`, `delivery_location` and, while the order is active, `captain_location`, so a map can start from the last known spot before live updates arrive.

**Tracking page.** `/track/<order_id>/` shows the order on a map for the signed-in customer (it reuses the token saved by `/login/`): store, home and a captain marker that glides between fixes, the status steps, the delivery PIN and when the captain was last seen. It works in Arabic, Kurdish and English, light and dark. Maps come from OpenFreeMap through MapLibre GL, which needs no API key; set `MAP_STYLE_LIGHT` and `MAP_STYLE_DARK` to a licensed provider's style URLs if traffic grows.

## Automatic captain dispatch

When a store accepts an order, dispatch offers it to the **nearest free captain** first (`orders/dispatch.py`, values in `DISPATCH`):

1. Candidates are captains who are online, have a GPS fix from the last 10 minutes within 5 km of the store, aren't carrying another order, and haven't been offered this one yet.
2. The nearest gets `{"type": "dispatch.offer", ...}` on their socket and has **30 seconds**. While the offer runs, nobody else sees the order or can claim it (`offered_to_another`).
3. **Accept** assigns the order to them. **Decline**, a timeout, or going offline moves the offer to the next nearest captain.
4. When no candidate is left, the order joins the open list every captain sees (`order.available`), as before.

| Endpoint | Who | What |
| :--- | :--- | :--- |
| `POST /api/captain/status/` `{"online": true}` | Captain | Start or stop receiving offers. Going offline passes any open offer on. |
| `GET /api/dispatch/offers/current/` | Captain | The offer waiting for them (204 if none), for when the app reconnects. |
| `POST /api/dispatch/offers/{id}/accept/` | That captain | Takes the order; returns it. `offer_gone` (409) if it already ended. |
| `POST /api/dispatch/offers/{id}/decline/` | That captain | Passes it on (204). |

Offers expire on time through a scheduled Celery task, with a sweep every 15 seconds as backup. Every offer is kept as a `DispatchOffer` (admin: Orders) with its distance and outcome.

## Live updates, no pushes

Wasel sends no push notifications (no Firebase). Everything reaches the apps over the live socket while they are open:

| Update | Who sees it |
| :--- | :--- |
| New order offers, with their 30-second window | The offered captain, while online in the app |
| Order status changes | The customer on the tracking screen, the store on its board |
| New orders and cancellations | The store tablet, which stays awake and rings while signed in |
| Store approval or rejection, team invites | The owner or invitee, the next time they open the portal or the store app |

If an app is closed, it catches up from the API when it opens again.

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

Not built yet: Wasel Plus billing and card payments.
