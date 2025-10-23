@echo off
REM Platform: amd64 (Windows/Ubuntu 20.04)
SET PLATFORM=linux/amd64
SET LOG_FILE=build.log

REM Set UTF-8 encoding for console output
chcp 65001 >nul

REM Clear previous log file
echo. > %LOG_FILE%

REM Check Docker and Build
echo Checking Docker installation...
echo Checking Docker installation... >> %LOG_FILE%
docker --version >nul 2>&1 || (
    echo ERROR: Docker is not installed or not running. Install Docker Desktop and restart.
    echo ERROR: Docker is not installed or not running. Install Docker Desktop and restart. >> %LOG_FILE%
    exit /b 1
)
echo Docker found.
echo Docker found. >> %LOG_FILE%

echo Checking Docker Build...
echo Checking Docker Build... >> %LOG_FILE%
docker build version >nul 2>&1 || (
    echo ERROR: Docker Build is not installed. Install the build plugin.
    echo ERROR: Docker Build is not installed. Install the build plugin. >> %LOG_FILE%
    exit /b 1
)
echo Build found.
echo Build found. >> %LOG_FILE%

REM Cleanup
echo Cleaning up old containers and builder...
echo Cleaning up old containers and builder... >> %LOG_FILE%
for /f "tokens=*" %%i in ('docker ps -a -q --filter "name=build_buildkit"') do (
    echo Stopping container %%i...
    echo Stopping container %%i... >> %LOG_FILE%
    docker stop %%i >> %LOG_FILE% 2>&1
    echo Removing container %%i...
    echo Removing container %%i... >> %LOG_FILE%
    docker rm %%i >> %LOG_FILE% 2>&1
)
echo Removing old multiarch builder...
echo Removing old multiarch builder... >> %LOG_FILE%
docker build rm multiarch >> %LOG_FILE% 2>&1
echo Cleanup completed.
echo Cleanup completed. >> %LOG_FILE%

REM Create builder
echo Creating Build builder...
echo Creating Build builder... >> %LOG_FILE%
docker build create --use --name multiarch --driver docker-container >> %LOG_FILE% 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create Build builder. Check %LOG_FILE% for details.
    echo ERROR: Failed to create Build builder. Check %LOG_FILE% for details. >> %LOG_FILE%
    exit /b %ERRORLEVEL%
)
echo Build builder created.
echo Build builder created. >> %LOG_FILE%

echo Bootstrapping builder...
echo Bootstrapping builder... >> %LOG_FILE%
docker build inspect --bootstrap multiarch >> %LOG_FILE% 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to bootstrap builder. Check %LOG_FILE% for details.
    echo ERROR: Failed to bootstrap builder. Check %LOG_FILE% for details. >> %LOG_FILE%
    exit /b %ERRORLEVEL%
)
echo Builder bootstrapped.
echo Builder bootstrapped. >> %LOG_FILE%

REM Build amd64
echo Starting amd64 build...
echo Starting amd64 build... >> %LOG_FILE%
docker build build --no-cache --platform %PLATFORM% ^
    -f src/Dockerfile.amd64 ^
    -t doc-converter:amd64 ^
    --load . >> %LOG_FILE% 2>&1
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

REM Pause if NO_PAUSE is not set
IF NOT DEFINED NO_PAUSE (
    echo Press any key to continue...
    pause
)