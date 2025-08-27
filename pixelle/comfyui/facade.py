# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from typing import Dict, Any

from pixelle.comfyui.models import ExecuteResult
from pixelle.comfyui.websocket_executor import WebSocketExecutor
from pixelle.comfyui.http_executor import HttpExecutor
from pixelle.settings import settings

# 配置变量
COMFYUI_EXECUTOR_TYPE = settings.comfyui_executor_type


class ComfyUIClient:
    """ComfyUI 客户端 Facade 类，提供统一的对外接口"""
    
    def __init__(self, base_url: str = None, executor_type: str = None):
        """
        初始化 ComfyUI 客户端
        
        Args:
            base_url: ComfyUI 服务的基础URL
            executor_type: 执行器类型，'websocket' 或 'http'
        """
        self.base_url = base_url
        self.executor_type = executor_type or COMFYUI_EXECUTOR_TYPE
        self._executor = None
        
    def _get_executor(self):
        """获取对应的执行器实例"""
        if self._executor is None:
            if self.executor_type == 'websocket':
                self._executor = WebSocketExecutor(self.base_url)
            elif self.executor_type == 'http':
                self._executor = HttpExecutor(self.base_url)
            else:
                raise ValueError(f"Unsupported executor type: {self.executor_type}")
        return self._executor
    
    async def execute_workflow(self, workflow_file: str, params: Dict[str, Any] = None) -> ExecuteResult:
        """
        执行工作流
        
        Args:
            workflow_file: 工作流文件路径
            params: 工作流参数
            
        Returns:
            执行结果
        """
        executor = self._get_executor()
        return await executor.execute_workflow(workflow_file, params)
    
    def get_workflow_metadata(self, workflow_file: str):
        """
        获取工作流元数据
        
        Args:
            workflow_file: 工作流文件路径
            
        Returns:
            工作流元数据
        """
        executor = self._get_executor()
        return executor.get_workflow_metadata(workflow_file)


# 创建默认客户端实例
default_client = ComfyUIClient()


# 提供便捷的函数接口
async def execute_workflow(workflow_file: str, params: Dict[str, Any] = None) -> ExecuteResult:
    """
    执行工作流的便捷函数
    
    Args:
        workflow_file: 工作流文件路径
        params: 工作流参数
        
    Returns:
        执行结果
    """
    return await default_client.execute_workflow(workflow_file, params)


def get_workflow_metadata(workflow_file: str):
    """
    获取工作流元数据的便捷函数
    
    Args:
        workflow_file: 工作流文件路径
        
    Returns:
        工作流元数据
    """
    return default_client.get_workflow_metadata(workflow_file) 