@echo off
chcp 65001 >nul
title DeskConvert
cd /d "%~dp0"

set "VENV=.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo [*] Setting up DeskConvert...
    python -m venv "%VENV%"
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
    echo.
    echo [*] Setup complete.
)

"%VENV%\Scripts\pythonw.exe" app.py
if errorlevel 1 (
    echo.
    echo [!] DeskConvert could not start. Run the following to see the error:
    echo     "%VENV%\Scripts\python.exe" app.py
    pause
)
