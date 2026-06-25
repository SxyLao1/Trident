@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo.
    echo Please run install.bat first to set up Trident.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat 2>nul

echo.
echo   _____     _     _            _
echo  ^|_   _^| __(_) __^| ^| ___ _ __ ^| ^|_
echo    ^| ^|^| '__^| ^|/ _` ^|/ _ \ '_ \^| __^|
echo    ^| ^|^| ^|  ^| ^| (_^| ^|  __/ ^| ^| ^| ^|_
echo    ^|_^|^|_^|  ^|_^|\__,_^|\___^|_^| ^|_^|\__^|
echo.
echo  Trident WebShell Detection System
echo  URL: http://127.0.0.1:8080/admin
echo  Press Ctrl+C to stop
echo.
echo  Logs: logs\Trident\
echo.
python app.py
