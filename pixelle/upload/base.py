# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""
存储抽象基类
定义存储后端的统一接口
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from dataclasses import dataclass


@dataclass
class FileInfo:
    """文件信息"""
    file_id: str
    filename: str
    content_type: str
    size: int
    url: str


class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    async def upload(
        self, 
        file_data: BinaryIO, 
        filename: str, 
        content_type: str
    ) -> FileInfo:
        """
        上传文件
        
        Args:
            file_data: 文件数据流
            filename: 文件名
            content_type: 文件MIME类型
            
        Returns:
            FileInfo: 文件信息
        """
        pass
    
    @abstractmethod
    async def download(self, file_id: str) -> Optional[bytes]:
        """
        下载文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            bytes: 文件内容，如果文件不存在返回None
        """
        pass
    
    @abstractmethod
    async def delete(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def exists(self, file_id: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 文件是否存在
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """
        获取文件信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            FileInfo: 文件信息，如果文件不存在返回None
        """
        pass 