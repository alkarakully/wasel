#!/bin/sh
# Build Wasel's two images for Linux servers (amd64) and push them to Docker Hub.
#   deploy/hub/build-and-push.sh <dockerhub-username> [tag]
# Run `docker login` first. Pushes <tag> (default: the git commit) and latest.
set -eu

user=${1:?usage: deploy/hub/build-and-push.sh <dockerhub-username> [tag]}
tag=${2:-$(git rev-parse --short HEAD)}
root=$(cd "$(dirname "$0")/../.." && pwd)
platform=${PLATFORM:-linux/amd64}

echo "Backend: $user/wasel-backend:$tag"
docker buildx build --platform "$platform" --push \
  -t "$user/wasel-backend:$tag" -t "$user/wasel-backend:latest" \
  "$root/backend"

echo "nginx (store portal + platform admin): $user/wasel-nginx:$tag"
docker buildx build --platform "$platform" --push \
  -f "$root/deploy/nginx/Dockerfile" \
  -t "$user/wasel-nginx:$tag" -t "$user/wasel-nginx:latest" \
  "$root"

echo "Pushed $user/wasel-backend:$tag and $user/wasel-nginx:$tag (also tagged latest)."
