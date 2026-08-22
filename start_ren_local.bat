@echo off
title REN-AI — Local Wi-Fi Mobile Server
cd /d "%~dp0"

echo ============================================================
echo   🪐 REN-AI LOCAL SERVER INITIALIZING
echo ============================================================
echo.

:: Activate Python Virtual Environment if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Start REN Server on Local Network
python server.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] REN-AI Server encountered an unexpected error.
    pause
)
