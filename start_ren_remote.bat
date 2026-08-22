@echo off
title REN-AI — Global Remote Mobile Access
cd /d "%~dp0"

echo ============================================================
echo   🪐 REN-AI GLOBAL REMOTE SERVER INITIALIZING
echo ============================================================
echo.

:: Activate Python Virtual Environment if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Start REN Server with Cloudflare Global HTTPS Tunnel
python server.py --public

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] REN-AI Server encountered an unexpected error.
    pause
)
