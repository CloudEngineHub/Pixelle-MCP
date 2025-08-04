# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import aiohttp
import os
from pydantic import Field
from core import mcp, logger
import json

BASE_URL = os.environ.get("mcp_base_url", "http://localhost:9001")

async def _request(method, path, **kwargs):
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}{path}"
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    # Check if the content type is JSON
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        return await response.json()
                    else:
                        # For file downloads, return the content directly
                        return await response.read()
                else:
                    error_text = await response.text()
                    logger.error(f"API request failed with status {response.status}: {error_text}")
                    return {"error": f"API Error: {response.status}", "details": error_text}
        except aiohttp.ClientError as e:
            logger.error(f"AIOHTTP client error: {e}")
            return {"error": "Client Connection Error", "details": str(e)}

@mcp.tool()
async def root__get():
    """
    Root - 根路径
    """
    return await _request("get", "/")

@mcp.tool()
async def health_check_health_get():
    """
    Health Check - 健康检查
    """
    return await _request("get", "/health")

@mcp.tool()
async def upload_file_upload_post(
    file_path: str = Field(description="The path to the file to upload.")
):
    """
    Upload File - 上传文件
    
    Args:
        file_path (str): The path to the file to upload.
        
    Returns:
        FileInfo: 文件信息
    """
    if not os.path.exists(file_path):
        return {"error": "File not found at the specified path."}
    
    data = aiohttp.FormData()
    data.add_field('file',
                   open(file_path, 'rb'),
                   filename=os.path.basename(file_path))

    return await _request("post", "/upload", data=data)


@mcp.tool()
async def get_file_files__file_id__get(
    file_id: str = Field(description="文件ID")
):
    """
    Get File - 获取文件
    
    Args:
        file_id: 文件ID
        
    Returns:
        文件内容
    """
    return await _request("get", f"/files/{file_id}")

@mcp.tool()
async def get_file_info_files__file_id__info_get(
    file_id: str = Field(description="文件ID")
):
    """
    Get File Info - 获取文件信息
    
    Args:
        file_id: 文件ID
    
    Returns:
        FileInfo: 文件信息
    """
    return await _request("get", f"/files/{file_id}/info")

@mcp.tool()
async def check_file_exists_files__file_id__exists_get(
    file_id: str = Field(description="文件ID")
):
    """
    Check File Exists - 检查文件是否存在
    
    Args:
        file_id: 文件ID
    
    Returns:
        存在性检查结果
    """
    return await _request("get", f"/files/{file_id}/exists")
