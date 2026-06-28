@echo off
cd /d "%~dp0"
E:\ProGram\Python\Python3.12\python.exe -c "from anteumbra.domain.entities import FileRecord" >nul 2>&1
if errorlevel 1 (
  echo Installing Anteumbra...
  E:\ProGram\Python\Python3.12\python.exe -m pip install -e . -q
)
echo Anteumbra: http://127.0.0.1:8080/admin
start "Anteumbra" E:\ProGram\Python\Python3.12\python.exe run.py
