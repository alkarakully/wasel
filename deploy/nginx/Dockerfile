# Build context: the repository root (see deploy/docker-compose.prod.yml).

# 1. Build the store portal.
FROM node:24-alpine AS portal
WORKDIR /portal
COPY apps/vendor/package.json apps/vendor/package-lock.json ./
RUN npm ci --ignore-scripts
COPY apps/vendor/ ./
RUN npm run build

# 2. nginx serving the portal and proxying Django.
FROM nginx:1.28-alpine
# Drop the stock site; it would answer requests meant for ours.
RUN apk add --no-cache openssl && rm /etc/nginx/conf.d/default.conf
COPY deploy/nginx/templates/ /etc/nginx/templates/
COPY deploy/nginx/entrypoint/ /docker-entrypoint.d/
COPY --from=portal /portal/dist/ /usr/share/nginx/portal/
