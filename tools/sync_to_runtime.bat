@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  sync_to_runtime.bat
REM  将源码改动同步到测试运行实例，方便立即查看修改效果
REM
REM  用法: 修改源码后双击运行，或在终端执行
REM ============================================================

set "SRC=F:\Home\Github\Trident\Trident_v1.0\Trident_1.8"
set "DST=F:\Home\Recently\Trident_1.7.9"

echo.
echo ========================================
echo   Trident 源码 → 运行时 同步
echo ========================================
echo.
echo   源: %SRC%
echo   目标: %DST%
echo.

if not exist "%SRC%" (
    echo [ERROR] 源码目录不存在
    goto :end
)
if not exist "%DST%" (
    echo [ERROR] 运行时目录不存在
    goto :end
)

echo [INFO] 正在同步...

REM /E  = 递归复制子目录（含空目录）
REM /XO = 只复制更新的文件（跳过目标端更新的文件，保护运行时配置）
REM /XD = 排除这些目录
REM /XF = 排除这些文件
robocopy "%SRC%" "%DST%" /E /XO /NJH /NJS /NP /NDL ^
    /XD .git __pycache__ venv data .claude ^
    /XF .env .env.example config.toml .gitignore

if errorlevel 8 (
    echo [WARN] 部分文件复制失败，请检查权限
) else (
    echo [OK] 同步完成
)

echo.
echo 改动已同步到测试环境，刷新浏览器查看效果。
echo.

:end
pause >nul
