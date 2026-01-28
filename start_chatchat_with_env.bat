@echo off
chcp 65001 >nul
echo ========================================
echo   Chatchat 服务启动脚本 (带环境变量)
echo ========================================
echo.

REM 设置环境变量
echo [1/3] 设置环境变量...
set OPENAI_API_KEY=EMPTY
set OPENAI_API_BASE=http://127.0.0.1:9997/v1
echo   ✓ 设置 OPENAI_API_KEY=EMPTY
echo   ✓ 设置 OPENAI_API_BASE=http://127.0.0.1:9997/v1

REM 激活虚拟环境
if exist ".venv310\Scripts\activate.bat" (
    echo [2/3] 激活虚拟环境...
    call .venv310\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用全局 Python
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