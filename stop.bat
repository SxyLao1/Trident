@echo off
chcp 65001 >nul
echo Stopping Trident...

rem Strategy 1: PID file
if exist trident.pid (
    for /f %%a in (trident.pid) do (
        echo Terminating PID %%a...
        taskkill /PID %%a /F /T >nul 2>&1
        if errorlevel 1 (
            echo PID %%a not found or already stopped.
        ) else (
            echo Trident [PID %%a] stopped.
        )
    )
    del trident.pid 2>nul
    goto :done
)

rem Strategy 2: Fallback - search for python processes running app.py
echo No PID file found. Searching for Trident processes...
for /f "tokens=2" %%a in ('tasklist ^| findstr python.exe') do (
    echo Found python.exe PID %%a, attempting to stop...
    taskkill /PID %%a /F /T >nul 2>&1
)
echo Done.

:done
