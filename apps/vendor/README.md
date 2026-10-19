# Wasel vendor portal (React)

Each store's own admin, on a computer or a kitchen tablet: a live order board with a loud new-order alarm, the menu and opening hours, reports, weekly billing statements and the store team. Owners, managers and cashiers each see what their role allows. Arabic, Kurdish (Sorani) and English, right-to-left where needed, light and dark.

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

Store accounts (role `vendor`) log in. New store owners choose **Join Wasel as a store** on the login page: they verify their number, fill in their first store (with its spot on a map and delivery distance) and see **Waiting for approval** until Wasel staff approve it in `/ops/`. Someone invited to a store's team sees the invite when they sign in, and joins by accepting.

## How it works

| Part | What it does |
| :--- | :--- |
| Order board | New, Preparing and Ready columns, oldest first, updated live over the order socket. Reconnects and reloads by itself after a drop. |
| New-order alarm | A repeating loud chime (made with Web Audio, no sound files) while any new order is waiting, plus a pulsing card and the count in the browser tab. Browsers need one click to allow sound, so the portal asks for it. **Stop ringing** silences the current orders; the next new order rings again. |
| Accept | Pick 10 to 45 minutes of prep time; the customer sees the ready estimate and late orders turn red. |
| Reject | Pick a common reason or type one; the customer sees it and wallet payments are refunded. |
| Menu | Switch items in or out of stock instantly; out-of-stock items can't be ordered. |
| Open / closed | Closed stores can't receive orders. |
| Menu editing | Owners and managers add items (names in Arabic, Kurdish and English, section, price, per item or per kg), edit them and remove them. Items that were ever ordered are archived rather than deleted, so old orders keep them. |
| Opening hours | One opening per weekday or closed; a closing time before the opening means after midnight. |
| Reports | For the last 7 or 30 days, this month, or any dates: earnings after commission, food sales, orders, average order, average prep time, cancellations, sales by day, busiest hours and best sellers. |
| Billing | Wasel collects every payment and pays the store weekly (Saturday to Friday). The owner sees this week so far, what's due and what's been paid, and each week's statement with every order, downloadable as a spreadsheet. |
| Team | The owner invites managers and cashiers by phone and sees invites waiting for an answer (and can cancel them). People join when they accept at their next sign-in, here or in the tablet app. |
| Store settings | The owner's stores and branches with their approval state (and the reason when one wasn't approved), and **Add a branch**, which goes to Wasel for approval like the first store. |
| Printing | Every order card has a print button, and **Print when accepting** prints automatically on accept. It prints two 80 mm slips, for kitchen receipt printers (any printer works): a kitchen ticket with the order number, times and items in large type, and a package slip to clip to the bag with a tick box per item, the customer's name and cash to collect. The delivery PIN and the customer's phone are never printed. For printing without the dialog, run Chrome in kiosk printing mode (`--kiosk-printing`). |

Who sees what:

| | Orders, stock, open/closed | Menu, hours | Reports | Billing | Team |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Owner | ✓ | ✓ | ✓ | ✓ | ✓ (and store settings) |
| Manager | ✓ | ✓ | ✓ | | |
| Cashier | ✓ | | | | |

The server enforces the same rules, so hiding a tab is never the only protection.

## Production

`npm run build` writes static files to `dist/`. Serve them from the same domain as the API and forward `/api` and `/ws` to Django (Daphne), so the portal needs no CORS setup.

## Tests

```bash
npm test
```

Not built yet: order history and daily totals, editing menus and prices, opening hours, and Kurdish text reviewed by a native speaker.
