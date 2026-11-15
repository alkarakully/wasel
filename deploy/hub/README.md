# Deploying from Docker Hub

The server only needs two files, `docker-compose.yml` and `.env`. It pulls two images from Docker Hub:

| Image | What's in it |
| :--- | :--- |
| `<user>/nawsil-backend` | Django API, live sockets, Celery worker and beat |
| `<user>/nawsil-nginx` | Store portal (`/`), platform admin (`/admin/`), TLS and the proxy to Django |

The images contain Nawsil's source code, so make both Docker Hub repositories **private**. Docker Hub's free plan has only one private repository; two need a paid plan.

## 1. Build and push (on your Mac)

```bash
docker login
```

```bash
deploy/hub/build-and-push.sh your-dockerhub-username
```

The script builds for Linux servers (`linux/amd64`) and tags each image with the git commit and `latest`.

## 2. Prepare the Droplet

Use Ubuntu with 4 CPUs and 16 GB. On a smaller Droplet, lower the `PG_*` and `WEB_CONCURRENCY` values in `.env`. Open ports 22, 80 and 443 in the Droplet's firewall, and point your domain's DNS A record at the Droplet's IP.

Install Docker (on the Droplet):

```bash
curl -fsSL https://get.docker.com | sh
```

```bash
mkdir -p /opt/nawsil
```

## 3. Fill in and upload `.env`

`deploy/hub/.env` on your Mac already has fresh secrets. Fill in `DOCKERHUB_USER`, your domain (in `SERVER_NAME`, `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`), and the WhatsApp keys. Then upload both files (on your Mac):

```bash
scp deploy/hub/docker-compose.yml deploy/hub/.env root@YOUR_DROPLET_IP:/opt/nawsil/
```

## 4. Start (on the Droplet, in `/opt/nawsil`)

```bash
docker login
```

```bash
docker compose up -d
```

nginx starts with a temporary self-signed certificate. Get the real one (replace the domain and email):

```bash
docker compose run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot -d your-domain.com --email you@example.com --agree-tos --no-eff-email --force-renewal
```

```bash
docker compose exec nginx nginx -s reload
```

Keep it renewed:

```bash
docker compose --profile certbot up -d certbot
```

Create your platform admin login (it asks for a password), then sign in at `https://your-domain.com/admin/`:

```bash
docker compose exec web python manage.py create_console_admin --email you@your-company.com --name "Your Name"
```

Check:

```bash
curl https://your-domain.com/healthz/
```

```bash
docker compose ps
```

## Updating

Push new images from your Mac with `build-and-push.sh`, then on the Droplet:

```bash
docker compose pull && docker compose up -d
```

Migrations run before the new web container starts. To roll back, set `NAWSIL_TAG` in `.env` to an earlier commit tag and run `docker compose up -d`.

## Backups

```bash
docker compose exec -T db pg_dump -U nawsil -Fc nawsil > nawsil-$(date +%F).dump
```

```bash
docker run --rm -v nawsil_media:/media -v "$PWD":/out alpine tar czf /out/media-$(date +%F).tgz -C /media .
```

Copy the files off the Droplet, or turn on DigitalOcean's Droplet backups as well.
