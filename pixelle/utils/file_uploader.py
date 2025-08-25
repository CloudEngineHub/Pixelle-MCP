# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""
MCP Base 文件上传器
调用 mcp-base 的 API 进行文件上传
"""

import os
import requests
from pathlib import Path
from typing import Union, Optional, Tuple
from urllib.parse import urlparse
import uuid

from core import logger

MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:9001")

class McpBaseUploader:
    """MCP Base 文件上传器"""
    
    def __init__(self, mcp_base_url: str):
        self.mcp_base_url = mcp_base_url
        self.upload_endpoint = f"{self.mcp_base_url.rstrip('/')}/upload"
    
    def upload(self, data: Union[bytes, str, Path], filename: Optional[str] = None) -> str:
        """
        上传文件到 mcp-base
        
        Args:
            data: 文件数据，可以是 bytes、文件路径或 URL
            filename: 可选的文件名
            
        Returns:
            str: 文件访问URL
        """
        try:
            # 处理不同类型的输入
            file_content, file_name = self._process_input(data, filename)
            
            # 准备上传数据
            files = {
                'file': (file_name, file_content, self._get_content_type(file_name))
            }
            
            # 发送上传请求
            response = requests.post(self.upload_endpoint, files=files, timeout=60)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            file_url = result.get('url')
            
            if not file_url:
                raise Exception("上传响应中未找到文件URL")
            
            logger.info(f"文件上传成功: {file_url}")
            return file_url
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    def _process_input(self, data: Union[bytes, str, Path], filename: Optional[str] = None) -> Tuple[bytes, str]:
        """处理不同类型的输入数据"""
        # 生成UUID作为基础文件名
        base_name = uuid.uuid4().hex
        
        if isinstance(data, bytes):
            # 直接是字节数据
            if filename:
                _, ext = os.path.splitext(filename)
            else:
                ext = ".bin"
            
            file_content = data
            file_name = filename or f"{base_name}{ext}"
        
        elif isinstance(data, (str, Path)):
            data_str = str(data)
            
            # 判断是 URL 还是文件路径
            if data_str.startswith(('http://', 'https://')):
                # 是 URL，下载内容
                response = requests.get(data_str, timeout=30)
                response.raise_for_status()
                file_content = response.content
                
                # 确定文件名
                if filename:
                    file_name = filename
                else:
                    # 从URL路径获取文件名
                    parsed_url = urlparse(data_str)
                    url_filename = os.path.basename(parsed_url.path)
                    if url_filename and '.' in url_filename:
                        file_name = url_filename
                    else:
                        # 尝试从响应头获取扩展名
                        content_type = response.headers.get('Content-Type', '')
                        ext = self._get_ext_from_content_type(content_type)
                        file_name = f"{base_name}{ext}"
            else:
                # 是文件路径
                file_path = Path(data_str)
                if not file_path.exists():
                    raise FileNotFoundError(f"文件不存在: {file_path}")
                
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # 确定文件名
                file_name = filename or file_path.name
        
        else:
            raise ValueError(f"不支持的数据类型: {type(data)}")
        
        return file_content, file_name
    
    def _get_content_type(self, filename: str) -> str:
        """获取文件的MIME类型"""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"
    
    def _get_ext_from_content_type(self, content_type: str) -> str:
        """从Content-Type获取文件扩展名"""
        if not content_type:
            return ".bin"
        
        import mimetypes
        mime_type = content_type.split(';')[0].strip()
        ext = mimetypes.guess_extension(mime_type)
        
        # 优化一些常见的扩展名
        if ext:
            if mime_type == 'image/jpeg' and ext in ['.jpe', '.jpeg']:
                ext = '.jpg'
            elif mime_type == 'image/tiff' and ext == '.tiff':
                ext = '.tif'
            return ext
        else:
            return ".bin"


# 创建默认上传器实例
default_uploader = McpBaseUploader(MCP_BASE_URL)


def upload(data: Union[bytes, str, Path], filename: Optional[str] = None) -> str:
    """
    上传文件的统一接口
    
    Args:
        data: 文件数据，可以是 bytes、文件路径或 URL
        filename: 可选的文件名
        
    Returns:
        str: 文件访问URL
    """
    return default_uploader.upload(data, filename) 