@echo off
title Setup Auto-Start for STOCK UNDO! Server
cd /d "%~dp0"

echo ==========================================================
echo  STOCK UNDO! - Setup Persistent Auto-Start on Power-On
echo  Tagline: "Check stock before you call the godown!"
echo ==========================================================
echo.
echo Requesting Administrator privileges...
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Elevating to Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo Running Auto-Start Configuration...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_auto_start.ps1"

echo.
pause

