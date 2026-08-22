@echo off
title REN-AI Minecraft AGI Agent
cls
echo ================================================================
echo   🎮 STARTING REN-AI MINECRAFT SURVIVAL AGENT
echo   Reinforcement Learning ^| Curiosity Engine ^| Chat Control
echo ================================================================
echo.

python start_minecraft_ren.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Minecraft Agent exited with error code %ERRORLEVEL%.
    pause
)
