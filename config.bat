@echo off
set "CONFIG_FILE=config.ini"

:: If config.ini already exists, skip to launch
if exist "%CONFIG_FILE%" goto :launch

echo ========================================
echo   GEOGRAPHY FLIGHT TOOL: INITIAL SETUP
echo ========================================
echo.
echo 1. I am the TEACHER (Host)
echo 2. I am a STUDENT (Guest)
echo.
set /p CHOICE="Choose (1 or 2): "

if "%CHOICE%"=="1" (
    echo [SETTINGS]> "%CONFIG_FILE%"
    echo IS_HOST = True>> "%CONFIG_FILE%"
    echo HOST_IP = 127.0.0.1>> "%CONFIG_FILE%"
    echo PORT = 80>> "%CONFIG_FILE%"
    echo Teacher mode configured.
) else (
    set /p USER_IP="Enter the Teacher's IP (e.g. 70.71.224.191): "
    echo [SETTINGS]> "%CONFIG_FILE%"
    echo IS_HOST = False>> "%CONFIG_FILE%"
    echo HOST_IP = %USER_IP%>> "%CONFIG_FILE%"
    echo PORT = 80>> "%CONFIG_FILE%"
    echo Student mode configured for %USER_IP%.
)

:launch
echo.
echo Launching Flight Sync...
start NS2.exe
exit