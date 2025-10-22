@echo off
REM Платформа: amd64 (Windows/Ubuntu 20.04)
set PLATFORM=linux/amd64

REM Очистка
for /f "tokens=1" %%i in ('docker ps --format "{{.Names}}" ^| findstr buildx_buildkit') do (
    echo Stopping container %%i
    docker stop %%i >nul 2>&1
)
docker buildx rm multiarch >nul 2>&1

REM Builder
docker buildx create --use --name multiarch --driver docker-container
docker buildx inspect --bootstrap multiarch

REM Сборка amd64
docker buildx build --platform %PLATFORM% ^
    -f src/Dockerfile.amd64 ^
    -t doc-converter:amd64 ^
    --load .

echo Сборка amd64 завершена.
docker images | findstr doc-converter
pause
"@ | Out-File -FilePath "build\build-amd64.bat" -Encoding ascii

# build-arm64.bat (cross-build arm64 на Windows, для RPi)
Remove-Item "build\build-arm64.bat" -Force
@"
@echo off
REM Платформа: arm64 (Debian Bookworm/RPi)
set PLATFORM=linux/arm64

REM Очистка
for /f "tokens=1" %%i in ('docker ps --format "{{.Names}}" ^| findstr buildx_buildkit') do (
    echo Stopping container %%i
    docker stop %%i >nul 2>&1
)
docker buildx rm multiarch >nul 2>&1

REM Builder
docker buildx create --use --name multiarch --driver docker-container
docker buildx inspect --bootstrap multiarch

REM Сборка arm64
docker buildx build --platform %PLATFORM% ^
    -f src/Dockerfile.arm64 ^
    -t doc-converter:arm64 ^
    --load .

echo Сборка arm64 завершена.
docker images | findstr doc-converter
pause
"@ | Out-File -FilePath "build\build-arm64.bat" -Encoding ascii

# build-arm64.sh (native для RPi/Linux)
Remove-Item "build\build-arm64.sh" -Force
@'
#!/bin/bash
set -e

PLATFORM="linux/arm64"

# Очистка
docker stop $(docker ps --format "{{.Names}}" | grep buildx_buildkit) 2>/dev/null || true
docker buildx rm multiarch 2>/dev/null || true

# Builder
docker buildx create --use --name multiarch --driver docker-container
docker buildx inspect --bootstrap multiarch

# Сборка arm64
docker buildx build --platform $PLATFORM \
    -f src/Dockerfile.arm64 \
    -t doc-converter:arm64 \
    --load .

echo "Сборка arm64 завершена."
docker images | grep doc-converter