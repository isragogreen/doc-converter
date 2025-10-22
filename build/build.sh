#!/bin/bash
set -e

# Платформы: amd64 (Windows/Ubuntu), arm64 (Debian Bookworm/RPi)
PLATFORMS="linux/amd64,linux/arm64"

# Сборка multi-arch
docker buildx create --use --name multiarch || true
docker buildx build --platform $PLATFORMS \\
    --build-arg BUILDPLATFORM=linux/amd64 \\
    -t doc-converter:latest \\
    --load .  # --load для локального, --push для registry

echo "Сборка завершена. Размер: $(docker images | grep doc-converter | awk '{print $7}')"
