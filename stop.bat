@echo off
cd /d "%~dp0"
if exist data\anteumbra.pid (
  set /p PID=<data\anteumbra.pid
  taskkill /PID !PID! /F 2>nul
  del data\anteumbra.pid 2>nul
  echo Anteumbra stopped (PID !PID!).
) else (
  echo No PID file found. Trying port check...
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F 2>nul
    echo Killed process on port 5000 (PID %%a).
  )
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F 2>nul
    echo Killed process on port 8080 (PID %%a).
  )
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8081.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F 2>nul
    echo Killed process on port 8081 (PID %%a).
  )
)
echo Done.
