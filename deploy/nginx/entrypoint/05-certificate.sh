#!/bin/sh
# nginx won't start without a certificate, but Let's Encrypt needs nginx running
# to prove the domain. Start with a short-lived self-signed one; certbot
# replaces it (see deploy/README.md).
set -eu
live="/etc/letsencrypt/live/${SERVER_NAME}"
if [ ! -f "$live/fullchain.pem" ]; then
  echo "No certificate for ${SERVER_NAME} yet: creating a temporary self-signed one."
  mkdir -p "$live"
  openssl req -x509 -nodes -newkey rsa:2048 -days 7 \
    -subj "/CN=${SERVER_NAME}" \
    -keyout "$live/privkey.pem" -out "$live/fullchain.pem" 2>/dev/null
fi
