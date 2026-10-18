# Wasel customer app (Flutter)

The customer app: phone login, stores near you, store menus, cart and checkout, and live order tracking on a map. Arabic, Kurdish (Sorani) and English, right-to-left where needed, light and dark.

## Run against the local backend

1. Start the backend and load demo stores (from the repository root):

   ```bash
   docker compose up -d
   ```

   ```bash
   docker compose run --rm web python manage.py seed_demo
   ```

2. Run the app on an iOS simulator, pointing it at the API:

   ```bash
   flutter run --dart-define=API_URL=http://localhost:8000
   ```

   If the backend runs on another port (for example `WASEL_WEB_PORT=8010`), use that port in `API_URL`. An Android emulator reaches your computer at `http://10.0.2.2:8000` instead.

3. Log in with any Iraqi mobile number. In development the code is printed in the backend log:

   ```bash
   docker compose logs web | grep "login code"
   ```

The demo stores are around Karrada, Baghdad. If the phone's location isn't available, the app delivers to Karrada. On a simulator you can set it:

```bash
xcrun simctl location booted set 33.3045,44.4214
```

## Settings

| `--dart-define` | Default | Meaning |
| :--- | :--- | :--- |
| `API_URL` | `http://localhost:8000` | Backend address |
| `MAP_STYLE_LIGHT` | OpenFreeMap Positron | Map style for light mode |
| `MAP_STYLE_DARK` | OpenFreeMap Dark | Map style for dark mode |

## Push notifications

Push is off unless the build gets Firebase settings (from the Firebase console, for this app and platform):

```bash
flutter run --dart-define=API_URL=https://api.example.com --dart-define=FIREBASE_API_KEY=... --dart-define=FIREBASE_PROJECT_ID=... --dart-define=FIREBASE_SENDER_ID=... --dart-define=FIREBASE_APP_ID=...
```

After login the app asks for notification permission and registers the phone with the backend; logging out removes it. iPhone pushes also need the APNs key uploaded to Firebase (see `backend/README.md`) and a real device, since the iOS Simulator can't receive remote pushes.

Tapping an order notification opens that order's tracking screen.

## Layout

| Path | What it holds |
| :--- | :--- |
| `lib/state/` | Session with delivery location, and the cart |
| `lib/screens/` | Home, store, product options, cart, tracking, order history |
| `lib/strings.dart` | Customer text in Arabic, Kurdish and English |
| `../wasel_core` | Shared API client, login screen, live socket, theme and shared text |

## Tests

```bash
flutter test
```

Not built yet: saved addresses and a map pin picker, card payments, ratings, and Kurdish text reviewed by a native speaker.
