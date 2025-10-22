#!/bin/bash
set -e

# Платформа: amd64 (Ubuntu 20.04)
PLATFORM="linux/amd64"

# Очистка
docker stop $(docker ps --format "{{.Names}}" | grep buildx_buildkit) 2>/dev/null || true
docker buildx rm multiarch 2>/dev/null || true

# Builder
docker buildx create --use --name multiarch --driver docker-container
docker buildx inspect --bootstrap multiarch

# Сборка amd64
docker buildx build --platform $PLATFORM \
    -f src/Dockerfile.amd64 \
    -t doc-converter:amd64 \
    --load .

echo "Сборка amd64 завершена."
docker images | grep doc-converter
