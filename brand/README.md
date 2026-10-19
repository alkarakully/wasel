# Wasel logo

The bilingual wordmark: **WASEL ◆ واصل**. Both names are drawn from IBM Plex Sans Arabic (the apps' font) and split by the gold diamond rule used across the apps. WASEL's capitals match the height of the Arabic letters, so the two read as one name.

| File | Use |
| :--- | :--- |
| `wasel-logo.svg` | Lapis on light backgrounds |
| `wasel-logo-dark.svg` | Light واصل with gold WASEL, on dark backgrounds |
| `wasel-logo-on-glaze.svg` | Gold واصل with light WASEL, on the lapis glaze panels (web login) |
| `wasel-logo-stacked.svg`, `wasel-logo-stacked-dark.svg` | واصل over the gold rule and WASEL, for splash screens and square spaces |
| `wasel-icon.svg` | App icon: gold واصل on glazed lapis bricks (1024 px) |
| `favicon.svg` | Browser tab icon |
| `logo.json` | The same drawing as path data, used by the apps' logo components |

In the apps:
- **Flutter:** `Wordmark` in `apps/wasel_core/lib/src/widgets/brand.dart`, with paths in `logo_paths.dart`.
- **Store portal and platform admin:** `Logo` in `src/components/Logo.tsx`. Colours come from the CSS variables `--logo-ink`, `--logo-latin` and `--logo-rule`.
- **Django pages:** `backend/accounts/static/wasel/`.

To change the logo, edit `tools/wordmark.py` and run it (the commands are at the top of the file). Then copy the new paths from `logo.json` into `logo_paths.dart` and the two `Logo.tsx` files.
