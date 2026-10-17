# Wasel vendor portal (React)

For store owners on a computer or a kitchen tablet: a live order board with a loud new-order alarm, accept (with prep time), reject (with a reason), mark ready, and switches for item stock and the store's open/closed state. Arabic, Kurdish (Sorani) and English, right-to-left where needed, light and dark.

Built with Vite, React 19 and TypeScript. Icons from Phosphor.

## Run against the local backend

1. Start the backend and load demo stores (from the repository root):

   ```bash
   docker compose up -d
   ```

   ```bash
   docker compose run --rm web python manage.py seed_demo
   ```

2. Install and start the portal:

   ```bash
   npm install
   ```

   ```bash
   npm run dev
   ```

   Open http://localhost:5173. Vite forwards `/api` and the live socket `/ws` to the backend at `http://localhost:8000`; if it runs elsewhere, start with `API_TARGET=http://localhost:8010 npm run dev`.

3. Log in as the demo store owner, **0780 000 0999**. The code is in the backend log:

   ```bash
   docker compose logs web | grep "login code"
   ```

Only store-owner accounts (role `vendor`) can log in.

## How it works

| Part | What it does |
| :--- | :--- |
| Order board | New, Preparing and Ready columns, oldest first, updated live over the order socket. Reconnects and reloads by itself after a drop. |
| New-order alarm | A repeating loud chime (made with Web Audio, no sound files) while any new order is waiting, plus a pulsing card and the count in the browser tab. Browsers need one click to allow sound, so the portal asks for it. **Stop ringing** silences the current orders; the next new order rings again. |
| Accept | Pick 10 to 45 minutes of prep time; the customer sees the ready estimate and late orders turn red. |
| Reject | Pick a common reason or type one; the customer sees it and wallet payments are refunded. |
| Menu | Switch items in or out of stock instantly; out-of-stock items can't be ordered. |
| Open / closed | Closed stores can't receive orders. |

## Production

`npm run build` writes static files to `dist/`. Serve them from the same domain as the API and forward `/api` and `/ws` to Django (Daphne), so the portal needs no CORS setup.

## Tests

```bash
npm test
```

Not built yet: order history and daily totals, editing menus and prices, opening hours, and Kurdish text reviewed by a native speaker.
