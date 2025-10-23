@echo off
REM Platform: amd64 (Windows/Ubuntu 22.04)
SET PLATFORM=linux/amd64
SET LOG_FILE=build.log

REM Set UTF-8 encoding for console output
chcp 65001 >nul

REM Clear previous log file
echo. > %LOG_FILE%

REM Check Docker
echo Checking Docker installation...
echo Checking Docker installation... >> %LOG_FILE%
docker --version >nul 2>&1 || (
    echo ERROR: Docker is not installed or not running. Install Docker Desktop and restart.
    echo ERROR: Docker is not installed or not running. Install Docker Desktop and restart. >> %LOG_FILE%
    exit /b 1
)
echo Docker found.
echo Docker found. >> %LOG_FILE%

REM Cleanup
echo Cleaning up old containers...
echo Cleaning up old containers... >> %LOG_FILE%
docker container prune -f >> %LOG_FILE% 2>&1

REM Build amd64 (ОБЫЧНЫЙ BUILD, БЕЗ BUILDX)
echo Starting amd64 build...
echo Starting amd64 build... >> %LOG_FILE%
docker build --platform %PLATFORM% ^
    -f src/Dockerfile.amd64 ^
    -t doc-converter:amd64 ^
    . >> %LOG_FILE% 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed. Check %LOG_FILE% for details.
    echo ERROR: Build failed. Check %LOG_FILE% for details. >> %LOG_FILE%
    exit /b %ERRORLEVEL%
)
echo amd64 build completed.
echo amd64 build completed. >> %LOG_FILE%

echo Listing Docker images...
echo Listing Docker images... >> %LOG_FILE%
docker images | findstr doc-converter
docker images | findstr doc-converter >> %LOG_FILE% 2>&1

REM Auto cleanup
docker system prune -f >> %LOG_FILE% 2>&1

REM Pause if NO_PAUSE is not set
IF NOT DEFINED NO_PAUSE (
    echo Press any key to continue...
    pause
)