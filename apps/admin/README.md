# Wasel platform admin (React)

Where the Wasel team runs the platform: live orders and dispatch, stuck-order alerts, captains, stores and their applications, menus and store teams, customers and captains, payouts and wallets, reports, offers and Wasel Plus, the team's own logins and the audit log. Arabic and English, light and dark, right-to-left first. It's served at `/admin/` and talks to `/api/console/` on the same domain with a session cookie. The stores have their own portal ([`apps/vendor`](../vendor/README.md)).

## Run against the local backend

1. Start the backend (from the repository root) and create your login; it asks for a password:

   ```bash
   WASEL_WEB_PORT=8010 docker compose up -d
   ```

   ```bash
   docker compose run --rm web python manage.py create_console_admin --email you@wasel.iq --name "Your Name"
   ```

2. Start the app, then open http://localhost:5174/admin/:

   ```bash
   API_TARGET=http://localhost:8010 npm run dev
   ```

3. Sign in with the email and password. The first time, scan the QR code with an authenticator app (Google Authenticator, Microsoft Authenticator, 1Password) and type the code it shows; after that it asks for the code each time.

## Sections

| Section | What the team sees and does |
| :--- | :--- |
| Overview | Today's and this month's sales, commission, deliveries and average delivery time; what's live (orders in progress, open alerts, captains online, stores open, applications waiting); the last 14 days; top stores. |
| Orders | Live orders oldest first, every order with search and status filter, open alerts, and captains with what they carry. An order shows its items, money, timeline, alerts and dispatch offers, with **Find a captain**, **Release captain** and **Cancel order** (wallet payments go back to the wallet). |
| Stores | Live stores, applications and rejected ones. Create a store for an owner by phone, edit its details, commission and location, approve or reject applications, edit the menu and the store's team. |
| People | Customers, captains and store accounts with orders, wallet and stores; block or unblock, and adjust a wallet with a reason. |
| Money | Weekly store payouts (mark paid with a transfer reference, close finished weeks) and the wallet ledger. |
| Reports | Sales, commission, fees, customers, cancellations, payment methods and stores for any range up to a year. |
| Marketing | Offers and banners (platform-wide or for one store) and Wasel Plus members. |
| Team | Teammates and their roles; add someone, change a role, turn a login off, reset an authenticator or set a new password. |
| Audit log | Every change, who made it, when and from where. |

Sections a role can't use aren't shown, and the ones it can only view are marked; the server checks every request anyway.

## Tests and build

```bash
npm test
```

```bash
npm run build
```

In production the nginx image builds this app and serves it at `/admin/` (see `deploy/README.md`).
