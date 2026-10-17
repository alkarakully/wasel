# Wasel Backend (Django REST Framework)

Runs in Docker with PostGIS, since GeoDjango needs GDAL/GEOS/PROJ which are easiest to get from the image.

## Run

From the repository root:

```bash
docker compose up
```

The API is at http://localhost:8000/api/ and the admin at http://localhost:8000/admin/. If port 8000 (or 5432) is taken, pick others:

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
| `GET /api/orders/` | Login required. Orders where you are the customer, captain or vendor owner. |

Not built yet: an SMS provider, placing orders, payments, WebSockets (Django Channels) and background jobs (Celery).
