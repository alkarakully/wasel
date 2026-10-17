# wasel_core

Code shared by the Wasel Flutter apps (`apps/customer`, `apps/captain`). It isn't published; apps depend on it by path:

```yaml
wasel_core:
  path: ../wasel_core
```

| File | What it holds |
| :--- | :--- |
| `lib/src/api/` | REST client (customer and captain endpoints) and data models |
| `lib/src/live_updates.dart` | The live order socket, with reconnect and ping |
| `lib/src/session.dart` | `BaseSession`: token, user and language; apps extend it |
| `lib/src/login_screen.dart` | Phone and WhatsApp/SMS code login; `acceptUser` lets an app refuse some accounts |
| `lib/src/strings.dart` | Shared text in Arabic, Kurdish and English; apps add theirs with `S.addStrings` |
| `lib/src/theme.dart` | Brand colours (Babylon lapis and gold) and the Material theme |

The API address comes from `--dart-define=API_URL=...` (default `http://localhost:8000`).

```bash
flutter test
```
