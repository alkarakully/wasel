# Nawsil logo

**NAWSIL ◆ نوصل**: NAWSIL in blue (`#033990`), a gold divider with a soft diamond, and نوصل in gold (`#E4A739`). Both words are set in IBM Plex Sans Arabic Bold, the apps' own font, so every letter has the same weight; the I is the upright stroke of the same font's L, because Plex's I has serifs. The divider comes from the original WASEL ◆ واصل artwork (`logo-source.jpeg`), redrawn as exact geometry, so the logo stays sharp at any size.

| File | Use |
| :--- | :--- |
| `nawsil-logo.svg` | Blue NAWSIL, gold نوصل, on light backgrounds |
| `nawsil-logo-dark.svg`, `nawsil-logo-on-glaze.svg` | Light NAWSIL, gold نوصل, on dark or lapis backgrounds |
| `nawsil-logo-stacked.svg`, `nawsil-logo-stacked-dark.svg` | نوصل over the divider and NAWSIL, for splash screens and square spaces |
| `nawsil-icon.svg` | App icon: gold نوصل on glazed blue bricks (1024 px, rounded) |
| `nawsil-icon-square.svg`, `nawsil-icon-foreground.svg` | Sources for the iOS icon (square corners) and the Android adaptive foreground |
| `favicon.svg` | Browser tab icon |
| `logo.json` | The same drawing as path data, used by the apps' logo components |

In the apps:
- **Flutter:** `Wordmark` in `apps/nawsil_core/lib/src/widgets/brand.dart`, with paths in `logo_paths.dart`. The launcher icons are in each app's `ios/` and `android/` folders.
- **Store portal and platform admin:** `Logo` in `src/components/Logo.tsx`. Colours come from the CSS variables `--logo-latin`, `--logo-ink` and `--logo-rule`.
- **Django pages:** `backend/accounts/static/nawsil/`.

To rebuild, run the commands at the top of `tools/build_logo.py` (`compose_nawsil.py` sets the lettering), then `python3 brand/tools/sync_apps.py` to copy the new paths into `logo_paths.dart` and the two `Logo.tsx` files, and render the launcher icons again from `nawsil-icon-square.svg` and `nawsil-icon-foreground.svg`.
