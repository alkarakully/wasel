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
| `accounts` | `User` (phone login, role: customer/captain/vendor), `WalletTransaction` |
| `subscriptions` | `WaselPlusSubscription` |
| `vendors` | `Vendor`, `Product`, `ProductModifier`, `Offer` |
| `orders` | `Order`, `OrderItem`, `OrderItemModifier`, `Rating` |

Money fields are whole Iraqi dinars. `Vendor.commission_for(subtotal)` applies the vendor's commission rate, or 0 during its commission-free period.

## API (so far)

| Endpoint | Notes |
| :--- | :--- |
| `GET /api/vendors/` | `?lat=&lng=` shows only vendors that deliver there, nearest first; `?type=`, `?cuisine=`. Open vendors come first. |
| `GET /api/vendors/{id}/` | Vendor with full menu and modifiers. |
| `GET /api/offers/` | Offers running now; `?banner=1` for home banners. |
| `GET /api/orders/` | Login required. Orders where you are the customer, captain or vendor owner. |

Not built yet: WhatsApp/SMS login, placing orders, payments, WebSockets (Django Channels) and background jobs (Celery).
