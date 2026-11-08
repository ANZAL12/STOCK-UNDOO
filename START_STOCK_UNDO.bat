@echo off
title STOCK UNDO! Launcher
echo ================================================================
echo   STOCK UNDO! - Centralized TallyPrime Stock Viewer
echo   Tagline: "Check stock before you call the godown!"
echo ================================================================
echo.
echo Starting PC 1 FastAPI Backend Server on port 8000...
start "STOCK UNDO - Backend" cmd /k "cd /d %~dp0 && call run_backend.bat"

timeout /t 2 /nobreak >nul

echo Starting STOCK UNDO Frontend (Vite) on port 5173...
start "STOCK UNDO - Frontend" cmd /k "cd /d %~dp0 && call run_frontend.bat"

timeout /t 2 /nobreak >nul

echo.
echo ================================================================
echo   Application started successfully!
echo   - Web Dashboard:  http://localhost:5173
echo   - Backend API:    http://127.0.0.1:8000
echo   - API Docs:       http://127.0.0.1:8000/api/docs
echo ================================================================
echo.
pause

