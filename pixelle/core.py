# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
from fastapi import FastAPI
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from pixelle import settings
from pixelle.filter import HealthCheckFilter
from pixelle.yml_env_loader import load_yml_and_set_env
import logging

# load config.yml and inject environment variables
load_yml_and_set_env("server")

app = FastAPI(
    title="Pixelle-MCP",
    description="基础服务，提供文件存储和共用服务能力"
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "status": "running",
        "/docs": "swagger documents",
        "/mcp": "mcp server url"
    }


# 应用过滤器到访问日志记录器
access_logger = logging.getLogger("uvicorn.access")
access_logger.addFilter(HealthCheckFilter())

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# initialize MCP server
mcp = FastMCP(
    name="pixelle-mcp-server",
    on_duplicate_tools="replace",
)

# log config
logger_level = logging.INFO
logging.basicConfig(
    level=logger_level,
    format='%(asctime)s- %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)

logger = logging.getLogger("PMS")
logger.setLevel(logger_level)
