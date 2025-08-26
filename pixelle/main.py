# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
import os
from pixelle.utils.os_util import get_src_path, get_root_path

os.environ["CHAINLIT_APP_ROOT"] = get_root_path()

from pixelle.settings import settings
from pixelle.utils.dynamic_util import load_modules

# load modules dynamically
load_modules("tools")
load_modules("api")

# 加载Chainlit应用和配置
chainlit_entry_file = get_src_path("web/app.py")

# 导入chainlit配置和模块加载
from chainlit.config import load_module
load_module(chainlit_entry_file)

# 获取我们的MCP对象和FastAPI应用
from pixelle.core import mcp, app as fastapi_app

# 根据FastMCP官方文档，正确处理lifespan
from contextlib import asynccontextmanager
from fastapi import FastAPI

# 创建MCP的ASGI应用，根据官方文档示例
mcp_asgi_app = mcp.http_app(path='/mcp')

# 获取Chainlit的lifespan
from chainlit.server import lifespan as chainlit_lifespan

# 组合lifespan
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """组合Chainlit和MCP的lifespan"""
    # 启动MCP lifespan
    async with mcp_asgi_app.lifespan(app):
        # 启动Chainlit lifespan  
        async with chainlit_lifespan(app):
            yield

# 获取Chainlit的主应用并重新配置lifespan
from chainlit.server import app as chainlit_app

# 重新创建FastAPI应用，使用组合的lifespan
app = FastAPI(
    title=chainlit_app.title,
    description=chainlit_app.description, 
    version=chainlit_app.version,
    lifespan=combined_lifespan
)

# 先挂载我们的API路由（优先级更高）
app.mount("/api", fastapi_app)

# 挂载MCP服务到/pixelle路径
app.mount("/pixelle", mcp_asgi_app)

# 复制Chainlit的所有中间件
for middleware in chainlit_app.user_middleware:
    app.add_middleware(middleware.cls, **middleware.kwargs)

# 最后复制Chainlit的所有路由（这样不会覆盖我们的挂载）
for route in chainlit_app.routes:
    app.router.routes.append(route)


def main():
    import uvicorn
    print("🚀 Start server...")
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
