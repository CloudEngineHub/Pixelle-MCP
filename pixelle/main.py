# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from pixelle.settings import settings
from pixelle.core import mcp, app
from pixelle.utils.dynamic_util import load_modules

# load modules dynamically
load_modules("tools")
load_modules("api")

mcp_app = mcp.http_app(path='/')
app.mount("/mcp", mcp_app)


def main():
    import uvicorn
    print("🚀 Start server...")
    uvicorn.run(
        "pixelle.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
