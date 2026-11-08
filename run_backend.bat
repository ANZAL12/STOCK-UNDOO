@echo off
title STOCK UNDO! Backend Server
cd /d "%~dp0backend"
echo ===================================================
echo  Starting STOCK UNDO! Centralized FastAPI Backend
echo  Tagline: "Check stock before you call the godown!"
echo ===================================================

if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] .venv not found. Using system Python...
)

echo Backend API listening on http://127.0.0.1:8000
echo OpenAPI Docs: http://127.0.0.1:8000/api/docs
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
