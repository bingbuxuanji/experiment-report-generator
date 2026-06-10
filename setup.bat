@echo off
cd /d "%~dp0"
title Report Generator Setup

echo.
echo [Setup] Experiment Report Generator
echo [Setup] Checking Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [Error] Python not found. Please install Python 3 first.
        echo         https://www.python.org/downloads/
        echo         Check "Add Python to PATH" during install.
        pause
        exit /b 1
    )
    set PY=python3
) else (
    set PY=python
)

%PY% setup.py
pause
