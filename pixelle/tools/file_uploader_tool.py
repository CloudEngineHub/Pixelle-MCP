# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import aiohttp
import os
from pydantic import Field
from pixelle.logger import logger
from pixelle.mcp_core import mcp
from pixelle.settings import settings


async def _file_request(method, path, **kwargs):
    async with aiohttp.ClientSession() as session:
        url = f"http://localhost:{settings.server_port}{path}"
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    # Check if the content type is JSON
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        json_response = await response.json()
                        return {"url": json_response.get("url"), "isError": False}
                    else:
                        # For file downloads, return the content directly
                        return await response.read()
                else:
                    error_text = await response.text()
                    logger.error(f"API request failed with status {response.status}: {error_text}")
                    return {"url": None, "isError": True}
        except aiohttp.ClientError as e:
            logger.error(f"AIOHTTP client error: {e}")
            return {"url": None, "isError": True}

@mcp.tool()
async def upload_file(
    file_path: str = Field(description="The path to the file to upload.")
):
    """
    Upload File
    
    Args:
        file_path (str): The path to the file to upload.
        
    Returns:
        url: The URL of the uploaded file.
        isError: Whether the upload was successful.
    """
    if not os.path.exists(file_path):
        return {"error": "File not found at the specified path."}
    
    data = aiohttp.FormData()
    data.add_field('file',
                   open(file_path, 'rb'),
                   filename=os.path.basename(file_path))

    return await _file_request("post", "/files/upload", data=data)
