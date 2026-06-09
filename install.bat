@echo off
chcp 65001 >nul
rem Trident Installer Entry Point (Windows)
rem Design: This script ONLY detects Python, then delegates ALL logic to scripts\install.py
rem Benefit: Version upgrades never require changing this file -- only scripts\install.py

echo.
echo   _____     _     _            _
echo  ^|_   _^| __(_) __^| ^| ___ _ __ ^| ^|_
echo    ^| ^|^| '__^| ^|/ _` ^|/ _ \ '_ \^| __^|
echo    ^| ^|^| ^|  ^| ^| (_^| ^|  __/ ^| ^| ^| ^|_
echo    ^|_^|^|_^|  ^|_^|\__,_^|\___^|_^| ^|_^|\__^|
echo.

rem Detect Python 3.8+
set "PYTHON_CMD="

for /f "tokens=*" %%a in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul') do (
    if not defined PYTHON_CMD (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    for /f "tokens=*" %%a in ('py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul') do (
        if not defined PYTHON_CMD (
            set "PYTHON_CMD=py"
        )
    )
)

if not defined PYTHON_CMD (
    for /f "tokens=*" %%a in ('python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul') do (
        if not defined PYTHON_CMD (
            set "PYTHON_CMD=python3"
        )
    )
)

if not defined PYTHON_CMD (
    echo.
    echo  [ERROR] Python 3.8+ is required but not found.
    echo.
    echo  Tried: python, py, python3
    echo.
    echo  Please install Python 3.8 or higher:
    echo    https://www.python.org/downloads/
    echo.
    echo  Make sure Python is added to PATH.
    echo  Verify with: python --version
    pause
    exit /b 1
)

rem Verify version >= 3.8
for /f "tokens=1,2 delims=." %%a in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if %PY_MAJOR% LSS 3 (
    echo [ERROR] Python version too old. Need 3.8+.
    pause
    exit /b 1
)
if %PY_MAJOR%==3 if %PY_MINOR% LSS 8 (
    echo [ERROR] Python version too old. Need 3.8+.
    pause
    exit /b 1
)

rem Delegate to Python installer (Single Source of Truth for all install logic)
cd /d "%~dp0"

echo  [OK] Python found, delegating to scripts\install.py...
echo.

%PYTHON_CMD% scripts\install.py
