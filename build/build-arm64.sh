#!/bin/bash
set -e

# Платформа: arm64 (Debian Bookworm/RPi)
PLATFORM="linux/arm64"

# Очистка
docker stop $(docker ps --format "{{.Names}}" | grep buildx_buildkit) 2>/dev/null || true
docker buildx rm multiarch 2>/dev/null || true

# Builder (если Docker buildx установлен; если нет — apt install docker-buildx-plugin)
docker buildx create --use --name multiarch --driver docker-container || true
docker buildx inspect --bootstrap multiarch

# Сборка arm64
docker buildx build --platform $PLATFORM \
    -f src/Dockerfile.arm64 \
    -t doc-converter:arm64 \
    --load .

echo "Сборка arm64 завершена."
docker images | grep doc-converter