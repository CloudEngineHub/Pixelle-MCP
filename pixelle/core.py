# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
from fastapi import FastAPI
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from pixelle.utils.dynamic_util import load_modules

# initialize MCP server
mcp = FastMCP(
    name="pixelle-mcp-server",
    on_duplicate_tools="replace",
)

mcp_app = mcp.http_app(path='/')

app = FastAPI(
    title="Pixelle-MCP",
    description="基础服务，提供文件存储和共用服务能力",
    lifespan=mcp_app.lifespan,
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "status": "running",
        "/docs": "swagger documents",
        "/mcp": "mcp server url"
    }

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
