@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo.
    echo Trident has not been installed yet, or the installation was interrupted.
    echo.
    echo Please run the installer first:
    echo   install.bat
    echo.
    echo The installer will:
    echo   1. Create a Python virtual environment
    echo   2. Install all dependencies
    echo   3. Configure your website path and password
    echo.
    pause
    exit /b 1
)

echo Starting Trident in background...
echo.

rem Use Python launcher to avoid all batch quoting/escaping issues
venv\Scripts\python.exe scripts\background_launcher.py

if exist trident.pid (
    for /f %%a in (trident.pid) do (
        echo.
        echo Trident is running in background.
        echo   PID:        %%a
        echo   PID file:   trident.pid
        echo   Log file:   logs\trident_background.log
        echo   Admin URL:  http://127.0.0.1:8080/admin
        echo.
        echo To stop, run: stop.bat
    )
) else (
    echo.
    echo [WARN] Trident may not have started correctly.
    echo   Try running start.bat to see the error message.
    echo   Or check logs\trident_background.log for details.
)
