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

echo Starting Trident...
echo Logs: logs\Trident\
echo.
python app.py
