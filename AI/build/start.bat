@echo off
chcp 65001 >nul
chcp 65001
setlocal enabledelayedexpansion

REM AI API 服务启动脚本
REM 自动检测环境并启动服务

echo ========================================
echo ?? AI API 服务启动脚本
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ? 错误: 未找到 Python，请先安装 Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 显示 Python 版本
echo ?? 检测到的 Python 版本:
for /f "tokens=*" %%i in ('python --version') do echo    %%i
echo.

REM 检查依赖文件
if not exist "requirements.txt" (
    echo ? 错误: 未找到 requirements.txt 文件
    pause
    exit /b 1
)

if not exist "ai_api_server.py" (
    echo ? 错误: 未找到 ai_api_server.py 文件
    pause
    exit /b 1
)

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo ?? 检测到虚拟环境，正在激活...
    call venv\Scripts\activate.bat
    echo ? 虚拟环境已激活
) else (
    echo ??  未检测到虚拟环境，建议创建虚拟环境:
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo.
    echo ?? 继续使用系统 Python 环境...
)
echo.

REM 检查依赖是否安装
echo ?? 检查依赖包...
python -c "import flask, requests" >nul 2>&1
if errorlevel 1 (
    echo ??  依赖包未完全安装，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ? 依赖安装失败，请手动执行: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo ? 依赖安装完成
) else (
    echo ? 依赖包检查通过
)
echo.

REM 检查配置文件
if not exist "ollama_config.json" (
    echo ??  未找到 ollama_config.json，Ollama 模式可能不可用
) else (
    echo ? 配置文件检查通过
)
echo.

REM 启动选项
echo ?? 启动选项:
echo [1] 默认启动 (localhost:5000, if_else模式)
echo [2] 自定义端口启动
echo [3] Ollama 模式启动
echo [4] 调试模式启动
echo [5] 外网访问启动 (0.0.0.0)
echo [0] 退出
echo.
set /p choice=请选择启动方式 (1-5, 0退出): 

if "%choice%"=="0" (
    echo ?? 再见！
    pause
    exit /b 0
)

if "%choice%"=="1" (
    echo ?? 使用默认配置启动服务...
    python main.py
) else if "%choice%"=="2" (
    set /p port=请输入端口号 (默认5000): 
    if "!port!"=="" set port=5000
    echo ?? 在端口 !port! 启动服务...
    python main.py --port !port!
) else if "%choice%"=="3" (
    echo ?? 使用 Ollama 模式启动服务...
    python main.py --mode ollama
) else if "%choice%"=="4" (
    echo ?? 使用调试模式启动服务...
    python main.py --debug
) else if "%choice%"=="5" (
    echo ?? 启动外网访问模式...
    echo ??  警告: 服务将监听所有网络接口，请确保网络安全
    python main.py --host 0.0.0.0
) else (
    echo ? 无效选择，使用默认配置启动...
    python main.py
)

REM 服务结束后的处理
echo.
echo ?? 服务已停止
echo ?? 如需重新启动，请重新运行此脚本
pause