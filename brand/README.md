# Wasel logo

**WASEL ◆ واصل**: WASEL in blue (`#033990`), a gold divider with a soft diamond, and واصل in gold (`#E4A739`) with slanted stem tops. The artwork is `logo-source.jpeg`, traced into vector paths. The divider is redrawn as exact geometry, so the logo stays sharp at any size.

| File | Use |
| :--- | :--- |
| `wasel-logo.svg` | Blue WASEL, gold واصل, on light backgrounds |
| `wasel-logo-dark.svg`, `wasel-logo-on-glaze.svg` | Light WASEL, gold واصل, on dark or lapis backgrounds |
| `wasel-logo-stacked.svg`, `wasel-logo-stacked-dark.svg` | واصل over the divider and WASEL, for splash screens and square spaces |
| `wasel-icon.svg` | App icon: gold واصل on glazed blue bricks (1024 px, rounded) |
| `wasel-icon-square.svg`, `wasel-icon-foreground.svg` | Sources for the iOS icon (square corners) and the Android adaptive foreground |
| `favicon.svg` | Browser tab icon |
| `logo.json` | The same drawing as path data, used by the apps' logo components |

In the apps:
- **Flutter:** `Wordmark` in `apps/wasel_core/lib/src/widgets/brand.dart`, with paths in `logo_paths.dart`. The launcher icons are in each app's `ios/` and `android/` folders.
- **Store portal and platform admin:** `Logo` in `src/components/Logo.tsx`. Colours come from the CSS variables `--logo-latin`, `--logo-ink` and `--logo-rule`.
- **Django pages:** `backend/accounts/static/wasel/`.

To rebuild after changing the artwork, replace `logo-source.jpeg` and run the commands at the top of `tools/build_logo.py`. Then copy the new paths from `logo.json` into `logo_paths.dart` and the two `Logo.tsx` files, and render the icons again.
