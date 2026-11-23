@echo off
chcp 65001 >nul
title DeskConvert
cd /d "%~dp0"

set "VENV=.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo [*] Setting up DeskConvert...
    python -m venv "%VENV%"
    if errorlevel 1 goto setup_failed
)

if not exist "%VENV%\deskconvert-requirements.txt" goto install
fc /b requirements.txt "%VENV%\deskconvert-requirements.txt" >nul 2>nul
if errorlevel 1 goto install
goto launch

:install
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed
copy /y requirements.txt "%VENV%\deskconvert-requirements.txt" >nul
if errorlevel 1 goto setup_failed

:launch
"%VENV%\Scripts\pythonw.exe" app.py
if errorlevel 1 (
    echo.
    echo [!] DeskConvert could not start. Run the following to see the error:
    echo     "%VENV%\Scripts\python.exe" app.py
    pause
)
exit /b

:setup_failed
echo.
echo [!] Could not set up DeskConvert. Check Python and your internet connection.
pause
exit /b 1
