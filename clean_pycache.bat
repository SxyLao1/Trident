@echo off
chcp 65001 >nul
setlocal

if "%~1"=="" (
    set "TARGET=%CD%"
    echo [INFO] Using current directory: %TARGET%
) else (
    set "TARGET=%~f1"
    echo [INFO] Target directory: %TARGET%
)

if not exist "%TARGET%" (
    echo [ERROR] Directory not found: %TARGET%
    pause
    exit /b 1
)

echo.
echo [1/3] Removing __pycache__ directories ...
for /r "%TARGET%" %%D in (__pycache__) do (
    if exist "%%D\" (
        echo   - rm dir: %%D
        rmdir /s /q "%%D"
    )
)

echo [2/3] Removing *.pyc / *.pyo files ...
for /r "%TARGET%" %%F in (*.pyc) do (
    echo   - rm file: %%F
    del /f /q "%%F"
)
for /r "%TARGET%" %%F in (*.pyo) do (
    echo   - rm file: %%F
    del /f /q "%%F"
)

echo [3/3] Removing *.pyd compiled extensions ...
for /r "%TARGET%" %%F in (*.pyd) do (
    echo   - rm file: %%F
    del /f /q "%%F"
)

echo.
echo Done.
pause
