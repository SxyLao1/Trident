@echo off
cd /d "%~dp0"
echo Installing Trident in dev mode...
E:\ProGram\Python\Python3.12\python.exe -m pip install -e . -q
echo.
echo Running core tests...
E:\ProGram\Python\Python3.12\python.exe -m pytest tests\core\ -v --tb=short
pause
