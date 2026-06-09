@echo off
chcp 65001 >nul
echo This will remove Trident virtual environment and runtime data.
echo Your config.toml and logs will be preserved.
echo.
set /p confirm="Are you sure? [y/N]: "
if /I "%confirm%"=="y" (
    rmdir /S /Q venv 2>nul
    rmdir /S /Q data 2>nul
    rmdir /S /Q __pycache__ 2>nul
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /S /Q "%%d" 2>nul
    del /S /Q *.pyc 2>nul
    del trident.pid 2>nul
    echo.
    echo Uninstall complete.
    echo Preserved: config.toml, logs\
) else (
    echo Cancelled.
)
pause
