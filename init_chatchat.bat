@echo off
chcp 65001 >nul
echo ========================================
echo   Chatchat 数据目录初始化
echo ========================================
echo.

REM 激活虚拟环境
if exist ".venv310\Scripts\activate.bat" (
    echo [1/2] 激活虚拟环境...
    call .venv310\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用全局 Python
)

echo [2/2] 初始化 Chatchat 数据目录...
echo.
chatchat init

echo.
echo ========================================
echo 初始化完成！
echo ========================================
echo.
echo 下一步: 运行 start_chatchat.bat 启动服务
echo.
pause
