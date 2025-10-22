@echo off
REM Установка кодировки для поддержки кириллицы (UTF-8)
chcp 65001 >nul

REM Платформа: amd64 (Windows/Ubuntu 20.04)
SET PLATFORM=linux/amd64
SET LOG_FILE=build.log

REM Проверка Docker и Buildx
docker --version >nul 2>&1 || (
    echo ОШИБКА: Docker не установлен или не запущен. Установите Docker Desktop и перезапустите. >> %LOG_FILE%
    echo ОШИБКА: Docker не установлен или не запущен. Установите Docker Desktop и перезапустите.
    exit /b 1
)
docker buildx version >nul 2>&1 || (
    echo ОШИБКА: Docker Buildx не установлен. Установите plugin buildx. >> %LOG_FILE%
    echo ОШИБКА: Docker Buildx не установлен. Установите plugin buildx.
    exit /b 1
)

REM Очистка
echo Очистка старых контейнеров и builder... >> %LOG_FILE%
for /f "tokens=*" %%i in ('docker ps -a -q --filter "name=buildx_buildkit"') do (
    echo Останавливаю контейнер %%i >> %LOG_FILE%
    docker stop %%i >> %LOG_FILE% 2>&1
    docker rm %%i >> %LOG_FILE% 2>&1
)
docker buildx rm multiarch >> %LOG_FILE% 2>&1

REM Создание builder
echo Создание Buildx builder... >> %LOG_FILE%
docker buildx create --use --name multiarch --driver docker-container >> %LOG_FILE% 2>&1
docker buildx inspect --bootstrap multiarch >> %LOG_FILE% 2>&1

REM Сборка amd64
echo Запуск сборки amd64... >> %LOG_FILE%
docker buildx build --platform %PLATFORM% ^
    -f src/Dockerfile.amd64 ^
    -t doc-converter:amd64 ^
    --load . >> %LOG_FILE% 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Сборка не удалась. Проверьте %LOG_FILE% для деталей. >> %LOG_FILE%
    echo ОШИБКА: Сборка не удалась. Проверьте %LOG_FILE% для деталей.
    exit /b %ERRORLEVEL%
)

echo Сборка amd64 завершена. >> %LOG_FILE%
echo Сборка amd64 завершена.
docker images | findstr doc-converter

REM Пауза, если NO_PAUSE не установлена
IF NOT DEFINED NO_PAUSE (
    pause
)