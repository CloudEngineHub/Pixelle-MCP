@echo off
setlocal enabledelayedexpansion

REM 设置控制台编码为 UTF-8
chcp 65001 >nul 2>&1

REM Script directory
set "SCRIPT_DIR=%~dp0"
set "PID_FILE=%SCRIPT_DIR%.pids"
set "LOG_DIR=%SCRIPT_DIR%logs"

REM 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 颜色输出函数
:print_info
echo [INFO] %~1
goto :eof

:print_success
echo [SUCCESS] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_header
echo ========================================
echo %~1
echo ========================================
goto :eof

REM 安全退出函数 - 确保始终暂停
:safe_exit
set "exit_code=%~1"
if "%exit_code%"=="" set "exit_code=0"
echo.
if %exit_code% neq 0 (
    call :print_error "脚本执行失败，退出码: %exit_code%"
) else (
    call :print_success "脚本执行完成"
)
echo 按任意键退出...
pause >nul
exit /b %exit_code%

REM 环境检查函数
:check_environment
call :print_header "Pixelle MCP 环境检查"

set "env_ok=1"

REM 检查 Python
call :print_info "检查 Python 安装..."
python --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python 未安装或不在 PATH 中"
    echo    解决方案：
    echo    1. 下载安装 Python: https://python.org
    echo    2. 确保安装时勾选 "Add Python to PATH"
    echo    3. 重启命令提示符后重试
    set "env_ok=0"
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do (
        call :print_success "Python 已安装: %%v"
    )
)

REM 检查 uv
call :print_info "检查 uv 包管理器..."
uv --version >nul 2>&1
if errorlevel 1 (
    call :print_error "uv 未安装"
    echo    解决方案：
    echo    方法1 ^(推荐^): PowerShell 管理员模式运行：
    echo        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo    方法2: 访问 https://github.com/astral-sh/uv 手动安装
    echo    方法3: 使用 pip install uv
    set "env_ok=0"
) else (
    for /f "tokens=*" %%v in ('uv --version 2^>^&1') do (
        call :print_success "uv 已安装: %%v"
    )
)

REM 检查项目目录结构
call :print_info "检查项目目录结构..."
set "required_dirs=mcp-base mcp-server mcp-client"
for %%d in (%required_dirs%) do (
    if exist "%%d\" (
        call :print_success "目录 %%d 存在"
        if exist "%%d\main.py" (
            call :print_success "  main.py 存在"
        ) else (
            call :print_error "  main.py 不存在于 %%d"
            set "env_ok=0"
        )
        if exist "%%d\pyproject.toml" (
            call :print_success "  pyproject.toml 存在"
        ) else (
            call :print_warning "  pyproject.toml 不存在于 %%d"
        )
    ) else (
        call :print_error "目录 %%d 不存在"
        echo    请确保在正确的项目根目录运行此脚本
        set "env_ok=0"
    )
)

REM 检查端口占用
call :print_info "检查端口占用情况..."
set "ports=9001 9002 9003"
for %%p in (%ports%) do (
    netstat -an | find ":%%p " | find "LISTENING" >nul
    if not errorlevel 1 (
        call :print_warning "端口 %%p 被占用"
        for /f "tokens=5" %%a in ('netstat -ano ^| find ":%%p " ^| find "LISTENING"') do (
            call :print_warning "  占用进程 PID: %%a"
        )
        call :print_info "  将尝试自动释放端口"
    ) else (
        call :print_success "端口 %%p 可用"
    )
)

if %env_ok% equ 0 (
    echo.
    call :print_error "环境检查失败，请根据上述提示解决问题后重试"
    call :safe_exit 1
)

call :print_success "环境检查通过！"
echo.
goto :eof

REM 停止现有服务
:stop_services
call :print_info "停止现有服务..."
if exist "%PID_FILE%" (
    set "stopped_count=0"
    for /f "tokens=*" %%i in (%PID_FILE%) do (
        if not "%%i"=="" (
            taskkill /PID %%i /F >nul 2>&1
            if !errorlevel! equ 0 (
                call :print_info "停止进程 %%i"
                set /a stopped_count+=1
            ) else (
                call :print_warning "进程 %%i 可能已经停止"
            )
        )
    )
    del "%PID_FILE%" >nul 2>&1
    if !stopped_count! gtr 0 (
        call :print_success "已停止 !stopped_count! 个服务"
    )
) else (
    call :print_info "没有发现运行中的服务"
)
goto :eof

REM 检查并释放端口
:check_port
set "port=%~1"
netstat -an | find ":%port% " | find "LISTENING" >nul
if not errorlevel 1 (
    call :print_warning "端口 %port% 被占用，尝试释放..."
    for /f "tokens=5" %%a in ('netstat -ano ^| find ":%port% " ^| find "LISTENING"') do (
        taskkill /PID %%a /F >nul 2>&1
        if !errorlevel! equ 0 (
            call :print_success "已释放端口 %port% ^(PID: %%a^)"
        ) else (
            call :print_warning "无法释放端口 %port%，可能需要管理员权限"
        )
    )
    REM 等待端口释放
    timeout /t 2 /nobreak >nul
)
goto :eof

REM 启动单个服务
:start_service
set "service_name=%~1"
set "service_dir=%~2"
set "port=%~3"

call :print_info "启动 %service_name%..."

REM 进入服务目录
if not exist "%SCRIPT_DIR%%service_dir%" (
    call :print_error "服务目录不存在: %SCRIPT_DIR%%service_dir%"
    goto :eof
)

cd /d "%SCRIPT_DIR%%service_dir%"

REM 检查 main.py
if not exist "main.py" (
    call :print_error "main.py 不存在于 %service_dir%"
    cd /d "%SCRIPT_DIR%"
    goto :eof
)

REM 同步依赖
call :print_info "同步 %service_name% 依赖..."
uv sync
if errorlevel 1 (
    call :print_error "依赖同步失败: %service_name%"
    echo    可能的解决方案：
    echo    1. 检查网络连接
    echo    2. 删除 .venv 目录后重试
    echo    3. 检查 pyproject.toml 文件
    cd /d "%SCRIPT_DIR%"
    goto :eof
)

REM 检查并释放端口
call :check_port "%port%"

REM 启动服务
call :print_info "启动 %service_name% 服务 ^(端口: %port%^)..."
start /b "Pixelle MCP - %service_name%" uv run main.py
timeout /t 3 /nobreak >nul

REM 查找进程 PID
set "found_pid="
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%uv run main.py%%' and commandline like '%%%service_dir%%%'" get processid /value 2^>nul ^| find "ProcessId" 2^>nul') do (
    set "found_pid=%%a"
    echo %%a >> "%SCRIPT_DIR%.pids"
    call :print_success "%service_name% 启动成功 ^(PID: %%a^)"
    goto :service_check_port
)

REM 如果 PID 检测失败，检查端口是否在监听
:service_check_port
timeout /t 2 /nobreak >nul
netstat -an | find ":%port% " | find "LISTENING" >nul
if not errorlevel 1 (
    if "%found_pid%"=="" (
        call :print_warning "%service_name% 已启动但 PID 检测失败"
    )
    call :print_success "%service_name% 正在监听端口 %port%"
) else (
    call :print_error "%service_name% 启动失败 - 端口 %port% 未监听"
    echo    请检查 %service_dir%/main.py 是否有错误
)

cd /d "%SCRIPT_DIR%"
goto :eof

REM 启动所有服务
:start_services
call :print_header "启动 Pixelle MCP 服务"

REM 清空 PID 文件
echo. > "%PID_FILE%" 2>nul

REM 启动基础服务
call :start_service "mcp-base" "mcp-base" "9001"

REM 启动服务器
call :start_service "mcp-server" "mcp-server" "9002"

REM 启动客户端
call :start_service "mcp-client" "mcp-client" "9003"

echo.
call :print_success "所有服务启动完成！"
echo.
echo 🔧 Base Service: http://localhost:9001
echo 🗄️ Server: http://localhost:9002
echo 🌐 Client: http://localhost:9003
echo.
call :print_info "服务正在运行中..."
echo 按任意键停止所有服务...
goto :eof

REM 检查服务状态
:show_status
call :print_header "检查服务状态"

if not exist "%PID_FILE%" (
    call :print_info "没有运行中的服务"
    goto :eof
)

set "running_count=0"
set "services=mcp-base:9001 mcp-server:9002 mcp-client:9003"

for %%s in (%services%) do (
    for /f "tokens=1,2 delims=:" %%a in ("%%s") do (
        set "service_name=%%a"
        set "port=%%b"
        netstat -an | find ":!port! " | find "LISTENING" >nul
        if not errorlevel 1 (
            call :print_success "!service_name! 运行中 ^(端口: !port!^)"
            set /a running_count+=1
        ) else (
            call :print_error "!service_name! 未运行"
        )
    )
)

echo.
echo 运行中的服务: !running_count!/3
goto :eof

REM 显示帮助信息
:show_help
call :print_header "Pixelle MCP 启动脚本帮助"
echo 用法: %~nx0 [命令]
echo.
echo 命令:
echo   start            启动所有服务 ^(前台模式^)
echo   stop             停止所有服务
echo   restart          重启所有服务
echo   status           检查服务状态
echo   help             显示帮助信息
echo.
echo 示例:
echo   %~nx0            # 默认启动服务
echo   %~nx0 start      # 启动服务
echo   %~nx0 restart    # 重启所有服务
echo.
goto :eof

REM 主逻辑
:main
set "command=%~1"

REM 显示欢迎信息
call :print_header "Pixelle MCP 启动脚本"

REM 默认命令为 start
if "%command%"=="" set "command=start"

REM 处理命令
if "%command%"=="start" (
    call :check_environment
    call :stop_services
    call :start_services
    pause >nul
    call :stop_services
    call :safe_exit 0
) else if "%command%"=="stop" (
    call :stop_services
    call :safe_exit 0
) else if "%command%"=="restart" (
    call :check_environment
    call :stop_services
    call :start_services
    call :safe_exit 0
) else if "%command%"=="status" (
    call :show_status
    call :safe_exit 0
) else if "%command%"=="help" (
    call :show_help
    call :safe_exit 0
) else (
    call :print_error "未知命令: %command%"
    echo.
    call :show_help
    call :safe_exit 1
)

goto :eof

REM 运行主函数，使用错误处理
call :main %*
if errorlevel 1 (
    call :print_error "脚本执行过程中发生错误"
    call :safe_exit 1
) 