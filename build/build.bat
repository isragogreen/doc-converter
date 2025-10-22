@echo off
REM Платформы: amd64, arm64
set PLATFORMS=linux/amd64,linux/arm64

REM Создать buildx builder если нет
docker buildx create --use --name multiarch || exit /b 0

REM Сборка
docker buildx build --platform %PLATFORMS% ^
    --build-arg BUILDPLATFORM=linux/amd64 ^
    -t doc-converter:latest ^
    --load .

echo Сборка завершена.
docker images | findstr doc-converter
pause
