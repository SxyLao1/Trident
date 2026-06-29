@echo off
cd /d "%~dp0"

:: Kill any existing Anteumbra instances to prevent port conflicts
taskkill /FI "WINDOWTITLE eq Anteumbra" /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1

E:\ProGram\Python\Python3.12\python.exe -c "from anteumbra.domain.entities import FileRecord" >nul 2>&1
if errorlevel 1 (
  echo Installing Anteumbra...
  E:\ProGram\Python\Python3.12\python.exe -m pip install -e . -q
)
echo Anteumbra: http://127.0.0.1:5000/admin
start "Anteumbra" E:\ProGram\Python\Python3.12\python.exe run.py
