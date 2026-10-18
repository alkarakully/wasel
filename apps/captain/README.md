# Wasel captain app (Flutter)

For delivery captains: log in, go online, take an order, pick it up, share GPS on the way, and finish with the customer's PIN. Arabic, Kurdish (Sorani) and English, light and dark. Shared code (API, login, theme, strings) lives in `../wasel_core`.

## Run against the local backend

1. Start the backend and load demo data, which includes a demo captain (from the repository root):

   ```bash
   docker compose up -d
   ```

   ```bash
   docker compose run --rm web python manage.py seed_demo
   ```

2. Run the app on an iOS simulator:

   ```bash
   flutter run --dart-define=API_URL=http://localhost:8000
   ```

3. Log in as the demo captain, **0750 000 0999**. The code is in the backend log:

   ```bash
   docker compose logs web | grep "login code"
   ```

Only accounts with the captain role can log in; other numbers get "this number isn't registered as a captain". Make captains in the Django admin (Users > role).

To fake driving on a simulator, play a GPS route:

```bash
xcrun simctl location booted start --speed=15 33.3045,44.4214 33.3005,44.4265 33.2992,44.4285
```

## How it works

| Screen | What the captain does |
| :--- | :--- |
| Home | Goes online or offline. Online tells dispatch to send offers, starts GPS sharing, and shows orders open to every captain, updated live. |
| Offer | A new order offered to this captain alone pops up with a sound, vibration and a 30-second countdown: **Take order** or **Skip**. Skipping or letting it run out passes it to the next nearest captain. |
| Delivery | Sees the store, customer and themselves on a map. Taps **Picked up** once the store marks the order ready, then calls the customer, opens directions, collects cash if needed, and enters the PIN to finish. |

GPS goes over the live socket at most every 3 seconds, falling back to REST when the socket is down, and is resent every minute while standing still so dispatch knows the captain is still there. Captains start offline each time the app opens, and can't go offline while carrying an order.

## Tests

```bash
flutter test
```

Not built yet: background location (sharing pauses when the app is closed, so offers stop after about 10 minutes), push notifications for offers, earnings and cash ledger screens, and Kurdish text reviewed by a native speaker.
