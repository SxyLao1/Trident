@echo off
cd /d "%~dp0..\.."
echo Anteumbra WAF Proxy v1.0
echo   Listening: http://127.0.0.1:8081
echo   Dashboard: http://127.0.0.1:8081
echo   Backend:   127.0.0.1:80
echo.
E:\ProGram\Python\Python3.12\python.exe tools\waf_proxy\waf_proxy.py 8081 80
pause
