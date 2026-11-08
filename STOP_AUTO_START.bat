@echo off
title Stop Auto-Start for STOCK UNDO! Server
cd /d "%~dp0"

echo ==========================================================
echo  STOCK UNDO! - Stop & Remove Auto-Start Service
echo ==========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Elevating to Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_auto_start.ps1"

echo.
pause

