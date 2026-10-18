# Deploying Wasel

One Linux server running Docker serves everything from one domain:

| Path | Served by |
| :--- | :--- |
| `/` | Store portal (React, built into the nginx image) |
| `/api/`, `/admin/`, `/ops/`, `/login/`, `/track/`, `/healthz/` | Django (Daphne) |
| `/ws/` | Live order socket (Daphne, kept open up to an hour between pings) |
| `/static/` | Django static files, straight from nginx |

The mobile apps talk to the same domain: build them with `--dart-define=API_URL=https://your-domain`.

```
             ┌──────────── nginx :80/:443 (TLS, portal, static) ────────────┐
 internet ──►│  /api /admin /ops /login /track /ws ──► web (Daphne :8000)   │
             └──────────────────────────────────────────────────────────────┘
   web, worker (Celery), beat (Celery schedule) ──► db (PostGIS), redis
   migrate: runs once per deploy (migrations + static files)
```

## What you need

- A Linux server with Docker and the Compose plugin, ports 80 and 443 open.
- A domain whose DNS points at the server.
- For login codes in production: a WhatsApp Business (Meta Cloud API) number with an approved authentication template. No SMS provider is connected yet, so WhatsApp is required.
- For push notifications: a Firebase project (see `backend/README.md`, "Turning on real pushes").

## First deploy

1. Copy the repository to the server and create the settings file:

   ```bash
   cp deploy/.env.example deploy/.env
   ```

   Fill in `SERVER_NAME`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and generate the secrets:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   Use one value for `DJANGO_SECRET_KEY` and another for `POSTGRES_PASSWORD`. Put the Firebase service account JSON in `deploy/secrets/` if you use push.

2. Build and start (from the repository root):

   ```bash
   docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml up -d --build
   ```

   The `migrate` service applies migrations and collects static files, then `web`, `worker`, `beat` and `nginx` start. nginx begins with a temporary self-signed certificate.

3. Get the real certificate from Let's Encrypt (replace the domain and email):

   ```bash
   docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot -d wasel.example.com --email you@example.com --agree-tos --no-eff-email --force-renewal
   ```

   ```bash
   docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec nginx nginx -s reload
   ```

4. Keep it renewed: start the certbot service, which renews twice a day (nginx reloads certificates every 6 hours):

   ```bash
   docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml --profile certbot up -d certbot
   ```

5. Create the first admin account, then add stores and captains in `/admin/`:

   ```bash
   docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

## Updating

```bash
git pull
```

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml up -d --build
```

`migrate` runs again before the new `web` starts. Open sockets reconnect on their own.

## Checks

```bash
curl https://wasel.example.com/healthz/
```

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml ps
```

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml logs -f web worker
```

`python manage.py check --deploy` reports two optional HSTS settings (include subdomains, preload). They're off on purpose: turning them on commits every subdomain of your domain to HTTPS for months, so enable them only once you're sure.

## Backups

The database lives in the `wasel-prod_pgdata` volume. Back it up daily, for example:

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.prod.yml exec -T db pg_dump -U wasel -Fc wasel > wasel-$(date +%F).dump
```

Copy the dumps off the server.

## Settings reference

All settings live in `deploy/.env` (see `.env.example`):

| Setting | Meaning |
| :--- | :--- |
| `SERVER_NAME` | The domain nginx answers for and gets a certificate for |
| `DJANGO_SECRET_KEY` | Long random secret; changing it signs everyone out of the admin |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names Django accepts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` origins allowed to post forms (admin) |
| `DJANGO_HSTS_SECONDS` | How long browsers must use HTTPS (default 30 days) |
| `DJANGO_LOG_LEVEL` | `WARNING` by default; `INFO` for more detail |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database name and credentials |
| `WHATSAPP_*` | WhatsApp login codes (see `backend/README.md`) |
| `FCM_CREDENTIALS_FILE`, `FCM_PROJECT_ID` | Push notifications |
| `MAP_STYLE_LIGHT`, `MAP_STYLE_DARK` | Map styles for the tracking page (optional) |
| `HTTP_PORT`, `HTTPS_PORT` | Host ports for nginx (80/443) |

## Scaling later

- Run more `web` or `worker` replicas (`--scale web=3`); live updates reach every replica through Redis. Keep exactly one `beat`.
- Move Postgres and Redis to managed services by changing the URLs in the compose file.
- Put a CDN in front of `/assets/` and `/static/`; both are safe to cache.
