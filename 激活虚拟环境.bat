@echo off
chcp 65001 >nul
echo ========================================
echo   激活虚拟环境
echo ========================================
echo.

REM 激活虚拟环境
call .venv310\Scripts\activate.bat

REM 检查是否激活成功
if errorlevel 1 (
    echo [错误] 虚拟环境激活失败
    pause
    exit /b 1
)

echo.
echo [成功] 虚拟环境已激活
echo.
echo 当前 Python 路径:
where python
echo.
echo 提示: 现在可以运行 chatchat 相关命令了
echo.
pause
