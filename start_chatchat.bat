@echo off
chcp 65001 >nul
echo ========================================
echo   Chatchat 服务启动脚本
echo ========================================
echo.

REM 检查虚拟环境
if exist ".venv310\Scripts\activate.bat" (
    echo [1/3] 激活虚拟环境...
    call .venv310\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用全局 Python
)

REM 检查 Chatchat 是否安装
echo [2/3] 检查 Chatchat 安装...
python -c "import chatchat" 2>nul
if errorlevel 1 (
    echo [错误] 未安装 Chatchat，请先运行: pip install -e libs/chatchat-server
    pause
    exit /b 1
)

echo [3/3] 启动 Chatchat 服务...
echo.
echo ----------------------------------------
echo 服务地址:
echo   - API Server:  http://127.0.0.1:7861
echo   - API 文档:    http://127.0.0.1:7861/docs
echo   - WebUI:       http://127.0.0.1:8501
echo ----------------------------------------
echo.
echo 按 Ctrl+C 停止服务
echo.

REM 启动服务（API + WebUI）
chatchat start -a

pause
