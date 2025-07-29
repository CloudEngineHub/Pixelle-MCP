@echo off
chcp 65001 >nul 2>&1

echo 启动 Pixelle MCP 服务...

echo 启动 mcp-base...
start "mcp-base" cmd /k "cd mcp-base && uv sync && uv run main.py"

echo 等待 mcp-base 启动...
timeout /t 3 /nobreak >nul

echo 启动 mcp-server...
start "mcp-server" cmd /k "cd mcp-server && uv sync && uv run main.py"

echo 启动 mcp-client...
start "mcp-client" cmd /k "cd mcp-client && uv sync && uv run main.py"

echo.
echo 所有服务已启动！
echo 🔧 Base Service: http://localhost:9001/dos
echo 🗄️ Server: http://localhost:9002/sse
echo 🌐 Client: http://localhost:9003 
