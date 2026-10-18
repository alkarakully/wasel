# Wasel store app (Flutter, tablets)

The order board for restaurants and shops, made for an iPad or Android tablet on the counter. Log in as the store owner, hear new orders ring, accept with a prep time or reject with a reason, mark orders ready, open or close the store, and switch menu items in or out of stock. Arabic, Kurdish (Sorani) and English, light and dark. It does what the web [store portal](../vendor/README.md) does, plus a ring that works with the screen locked and a screen that stays awake. Shared code (API, login, theme, strings) lives in `../wasel_core`.

## Run against the local backend

1. Start the backend and load demo data, which includes a demo store owner (from the repository root):

   ```bash
   WASEL_WEB_PORT=8010 docker compose up -d
   ```

   ```bash
   docker compose run --rm web python manage.py seed_demo
   ```

2. Boot an iPad simulator and run the app on it:

   ```bash
   xcrun simctl boot "iPad (A16)" && open -a Simulator
   ```

   ```bash
   flutter run -d "iPad (A16)" --dart-define=API_URL=http://localhost:8010
   ```

3. Log in as the demo store owner, **0780 000 0999**. The code is in the backend log:

   ```bash
   docker compose logs web | grep "login code" | tail -1
   ```

Only store owners (role Vendor) can log in. Add owners and their stores in the Django admin (see `backend/README.md`).

## How it works

| Part | What the store does |
| :--- | :--- |
| Board | New, preparing and ready orders, oldest first. Landscape tablets (or any screen 900 points wide) show all three columns; portrait shows one column with tabs. Each card lists items and options, cash or paid, the total, and the next step. |
| New order | Rings the same four-note chime as the web portal, even with the silent switch on, until someone accepts, rejects or taps the banner to stop ringing. The card glows and the gold count pops. |
| Accept | Pick a prep time (10 to 45 minutes) and accept; the customer is told when it'll be ready and dispatch offers it to the nearest captain. |
| Reject | Pick a common reason or type one; the customer sees it. |
| Ready | Marks it ready for the captain, then shows whether a captain is on the way. |
| Menu | Every item with an in-stock switch. Out-of-stock items can't be ordered. |

Orders arrive over the live socket. If the connection drops, a banner says so and the board reloads as soon as it's back. The screen stays awake while signed in.

## Push notifications

Push is off unless the build gets Firebase settings (from the Firebase console, for this app and platform):

```bash
flutter run --dart-define=API_URL=https://api.example.com --dart-define=FIREBASE_API_KEY=... --dart-define=FIREBASE_PROJECT_ID=... --dart-define=FIREBASE_SENDER_ID=... --dart-define=FIREBASE_APP_ID=...
```

After login the tablet registers as a "store" device. The owner then gets an urgent push for every new order ("New order #12") and when a customer cancels, even with the app closed.

## Tests

```bash
flutter test
```
