# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
import os
from pixelle.utils.os_util import get_src_path, get_root_path

os.environ["CHAINLIT_APP_ROOT"] = get_root_path()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from chainlit.config import load_module
from chainlit.server import lifespan as chainlit_lifespan
from chainlit.server import app as chainlit_app

from pixelle.settings import settings
from pixelle.utils.dynamic_util import load_modules
from pixelle.mcp_core import mcp
from pixelle.api.files_api import router as files_router

# 加载Chainlit应用和配置
chainlit_entry_file = get_src_path("web/app.py")

# 导入chainlit配置和模块加载
load_module(chainlit_entry_file)

# 创建MCP的ASGI应用，根据官方文档示例
mcp_asgi_app = mcp.http_app(path='/mcp')


# 组合lifespan
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """组合Chainlit和MCP的lifespan"""
    # 启动MCP lifespan
    async with mcp_asgi_app.lifespan(app):
        # 启动Chainlit lifespan  
        async with chainlit_lifespan(app):
            yield


# 重新创建FastAPI应用，使用组合的lifespan
app = FastAPI(
    title=chainlit_app.title,
    description=chainlit_app.description,
    version=chainlit_app.version,
    lifespan=combined_lifespan,
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 动态加载工具模块
load_modules("tools")

# 注册API路由
app.include_router(files_router, prefix="/files")

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
