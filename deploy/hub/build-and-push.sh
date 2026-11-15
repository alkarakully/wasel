#!/bin/sh
# Build Nawsil's two images for Linux servers (amd64) and push them to Docker Hub.
#   deploy/hub/build-and-push.sh <dockerhub-username> [tag]
# Run `docker login` first. Pushes <tag> (default: the git commit) and latest.
set -eu

user=${1:?usage: deploy/hub/build-and-push.sh <dockerhub-username> [tag]}
tag=${2:-$(git rev-parse --short HEAD)}
root=$(cd "$(dirname "$0")/../.." && pwd)
platform=${PLATFORM:-linux/amd64}

echo "Backend: $user/nawsil-backend:$tag"
docker buildx build --platform "$platform" --push \
  -t "$user/nawsil-backend:$tag" -t "$user/nawsil-backend:latest" \
  "$root/backend"

echo "nginx (store portal + platform admin): $user/nawsil-nginx:$tag"
docker buildx build --platform "$platform" --push \
  -f "$root/deploy/nginx/Dockerfile" \
  -t "$user/nawsil-nginx:$tag" -t "$user/nawsil-nginx:latest" \
  "$root"

echo "Pushed $user/nawsil-backend:$tag and $user/nawsil-nginx:$tag (also tagged latest)."
