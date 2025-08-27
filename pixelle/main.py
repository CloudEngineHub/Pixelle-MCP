# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

# !!! Don't modify the import order, `settings` module must be imported before other modules !!!
from pixelle.settings import settings

from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from chainlit.config import load_module, config as chainlit_config
from chainlit.server import lifespan as chainlit_lifespan
from chainlit.server import app as chainlit_app

from pixelle.utils.dynamic_util import load_modules
from pixelle.utils.os_util import get_src_path
from pixelle.mcp_core import mcp
from pixelle.api.files_api import router as files_router


# Modify chainlit config
chainlit_config.run.host = settings.host
chainlit_config.run.port = settings.port

# Access chainlit entry file path
chainlit_entry_file = get_src_path("web/app.py")
# Load chainlit module
load_module(chainlit_entry_file)

# Create ASGI app of MCP
mcp_app = mcp.http_app(path='/mcp')


# combine multi lifespans
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    # start MCP lifespan
    async with mcp_app.lifespan(app):
        # start chainlit lifespan
        async with chainlit_lifespan(app):
            yield


# Create a fastapi application
app = FastAPI(
    title="Pixelle-MCP",
    description="A fastapi app that contains mcp server and mcp client.",
    lifespan=combined_lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load tools module dynamically
load_modules("tools")

# Register files router
app.include_router(files_router, prefix="/files")

# Mount MCP server to `/pixelle` path
app.mount("/pixelle", mcp_app)

# Transfer all middleware into our app
for middleware in chainlit_app.user_middleware:
    app.add_middleware(middleware.cls, **middleware.kwargs)

# Copy all routes that are in Chainlit's app into our app
for route in chainlit_app.routes:
    app.router.routes.append(route)


def main():
    import uvicorn
    print("🚀 Start server...")
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
