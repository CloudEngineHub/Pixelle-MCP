# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from datetime import datetime
import os
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field
from pixelle.logger import logger
from pixelle.core import mcp
from pixelle.utils.os_util import get_data_path
from pixelle.comfyui.workflow_parser import WorkflowParser, WorkflowMetadata
from pixelle.comfyui.facade import execute_workflow

CUSTOM_WORKFLOW_DIR = get_data_path("custom_workflows")
os.makedirs(CUSTOM_WORKFLOW_DIR, exist_ok=True)

class WorkflowManager:
    """工作流管理器，支持动态加载和热更新"""
    
    def __init__(self, workflows_dir: str = CUSTOM_WORKFLOW_DIR):
        self.workflows_dir = Path(workflows_dir)
        self.loaded_workflows = {}

    
    def parse_workflow_metadata(self, workflow_path: Path, tool_name: str = None) -> Optional[WorkflowMetadata]:
        """使用新的工作流解析器解析工作流元数据"""
        parser = WorkflowParser()
        metadata = parser.parse_workflow_file(str(workflow_path), tool_name)
        return metadata
    
    def _generate_params_str(self, params: Dict[str, Any]) -> str:
        """生成函数参数字符串"""
        # 分离必需参数和可选参数，确保参数顺序正确
        required_params = []
        optional_params = []
        
        for param_name, param in params.items():
            # 直接使用用户提供的description
            description = param.description or ''
            
            # 生成 Field 参数列表
            field_args = [f"description={repr(description)}"]
            if param.default is not None:
                field_args.append(f"default={repr(param.default)}")
            
            # 生成完整的参数定义
            param_str = f"{param_name}: {param.type} = Field({', '.join(field_args)})"
            
            # 根据是否有默认值分类
            if param.default is not None:
                optional_params.append(param_str)
            else:
                required_params.append(param_str)
        
        # 必需参数在前，可选参数在后
        return ", ".join(required_params + optional_params)
    
    def _generate_workflow_function(self, title: str, params_str: str) -> tuple[str, str]:
        """Generate the workflow execution function code
        
        Returns:
            tuple: (function_code, workflow_path) - Function code and workflow path
        """
        final_workflow_path = os.path.join(CUSTOM_WORKFLOW_DIR, f"{title}.json")
        
        template = '''async def {title}({params_str}):
    try:
        # Get the passed parameters (excluding special parameters)
        params = {{k: v for k, v in locals().items() if not k.startswith('_')}}
        
        # Execute the workflow - workflow_path is retrieved from the external environment
        result = await execute_workflow(WORKFLOW_PATH, params)
        
        # Convert the result to a format friendly to LLM
        if result.status == "completed":
            return result.to_llm_result()
        else:
            return "Workflow execution failed: " + str(result.msg or result.status)
            
    except Exception as e:
        logger.error("Workflow execution failed {title_safe}: " + str(e), exc_info=True)
        return "Workflow execution exception: " + str(e)
'''

        function_code = template.format(
            title=title,
            params_str=params_str,
            title_safe=repr(title)
        )
        
        return function_code, final_workflow_path


    def _register_workflow(self, title: str, workflow_handler, metadata: WorkflowMetadata) -> None:
        """注册并记录工作流"""
        
        # 注册为MCP工具
        mcp.tool(workflow_handler)
        
        # 记录工作流信息
        self.loaded_workflows[title] = {
            "function": workflow_handler,
            "metadata": metadata.model_dump(),
            "loaded_at": datetime.now()
        }
        
        logger.info(f"成功加载工作流: {title}")
    
    def _save_workflow_if_needed(self, workflow_path: Path, title: str):
        """如果需要，保存工作流文件到工作流目录"""
        target_workflow_path = self.workflows_dir / f"{title}.json"
        try:
            # 确保工作流目录存在
            self.workflows_dir.mkdir(parents=True, exist_ok=True)

            # 如果源文件和目标文件是同一个文件，直接跳过
            if os.path.abspath(str(workflow_path)) == os.path.abspath(str(target_workflow_path)):
                logger.debug(f"工作流文件已存在且路径相同，无需复制: {target_workflow_path}")
                return

            # 复制工作流文件到工作流目录
            import shutil
            shutil.copy2(workflow_path, target_workflow_path)
            logger.info(f"工作流文件已保存到: {target_workflow_path}")
        except Exception as e:
            logger.warning(f"保存工作流文件失败: {e}")
        

    def load_workflow(self, workflow_path: Path | str, tool_name: str = None) -> Dict:
        """加载单个工作流
        
        Args:
            workflow_path: 工作流文件路径
            tool_name: 工具名称，优先级高于工作流文件名
            save_workflow_if_not_exists: 是否将工作流文件保存到工作流目录（如果目标文件不存在）
        """
        try:
            if isinstance(workflow_path, str):
                workflow_path = Path(workflow_path)
            
            # 检查文件是否存在
            if not workflow_path.exists():
                logger.error(f"工作流文件不存在: {workflow_path}")
                return {
                    "success": False,
                    "error": f"工作流文件不存在: {workflow_path}"
                }
            
            # 使用新的解析器解析工作流元数据
            metadata = self.parse_workflow_metadata(workflow_path, tool_name)
            if not metadata:
                logger.error(f"无法解析工作流元数据: {workflow_path}")
                return {
                    "success": False,
                    "error": f"无法解析工作流元数据: {workflow_path}"
                }

            title = metadata.title
            
            
            # 验证title格式
            if not re.match(r'^[a-zA-Z0-9_\.-]+$', title):
                logger.error(f"工具名称 '{title}' 格式无效。只允许使用字母、数字、下划线、点和连字符。")
                return {
                    "success": False,
                    "error": f"工具名称 '{title}' 格式无效。只允许使用字母、数字、下划线、点和连字符。"
                }
            
            # 生成参数字符串
            params_str = self._generate_params_str(metadata.params)
            
            # 创建工具处理函数
            exec_locals = {}
            
            # 生成工作流执行函数
            func_def, target_workflow_path = self._generate_workflow_function(title, params_str)
            # 执行函数定义，将工作流路径作为变量传入执行环境
            exec(func_def, {
                "metadata": metadata, 
                "logger": logger, 
                "Field": Field,
                "execute_workflow": execute_workflow,
                "WORKFLOW_PATH": target_workflow_path,
            }, exec_locals)
            
            dynamic_function = exec_locals[title]
            if metadata.description:
                dynamic_function.__doc__ = metadata.description
            
            # 注册并记录工作流
            self._register_workflow(title, dynamic_function, metadata)
            
            # 保存工作流文件到工作流目录
            self._save_workflow_if_needed(workflow_path, title)
            
            logger.debug(f"工作流 '{title}' 已成功加载为MCP工具")
            return {
                "success": True,
                "workflow": title,
                "metadata": metadata.model_dump(),
                "message": f"工作流 '{title}' 已成功加载为MCP工具"
            }
            
        except Exception as e:
            logger.error(f"加载工作流失败 {workflow_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"加载工作流失败: {str(e)}"
            }
            
    
    def unload_workflow(self, workflow_name: str) -> Dict:
        """卸载工作流"""
        if workflow_name not in self.loaded_workflows:
            return {
                "success": False,
                "error": f"工作流 '{workflow_name}' 不存在或未加载"
            }
        
        try:
            # 从MCP服务器中移除
            mcp.remove_tool(workflow_name)
            
            # 删除工作流文件
            workflow_path = os.path.join(CUSTOM_WORKFLOW_DIR, f"{workflow_name}.json")
            if os.path.exists(workflow_path):
                os.remove(workflow_path)
            
            # 从记录中删除
            del self.loaded_workflows[workflow_name]
            
            logger.info(f"成功卸载工作流: {workflow_name}")
            
            return {
                "success": True,
                "workflow": workflow_name,
                "message": f"工作流 '{workflow_name}' 已卸载"
            }
                
        except Exception as e:
            logger.error(f"卸载工作流失败 {workflow_name}: {e}")
            return {
                "success": False,
                "error": f"卸载工作流失败: {str(e)}"
            }
    
    
    def load_all_workflows(self) -> Dict:
        """加载所有工作流"""
        results = {
            "success": [],
            "failed": []
        }
        
        # 确保目录存在
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载所有JSON文件
        for json_file in self.workflows_dir.glob("*.json"):
            result = self.load_workflow(json_file)
            if result["success"]:
                results["success"].append(result["workflow"])
            else:
                results["failed"].append({
                    "file": json_file.name,
                    "error": result["error"]
                })
        
        return results
    
    def get_workflow_status(self) -> Dict:
        """获取所有工作流状态"""
        return {
            "total_loaded": len(self.loaded_workflows),
            "workflows": {
                name: {
                    "metadata": info["metadata"],
                    "loaded_at": info["loaded_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(info["loaded_at"], datetime) else str(info["loaded_at"])
                }
                for name, info in self.loaded_workflows.items()
            }
        }
    
    def reload_all_workflows(self) -> Dict:
        """手动重新加载所有工作流"""
        logger.info("开始手动重新加载所有工作流")
        
        # 清除所有已加载的工作流
        for workflow_name in list(self.loaded_workflows.keys()):
            try:
                mcp.remove_tool(workflow_name)
            except:
                pass  # 忽略移除失败的情况
        
        self.loaded_workflows.clear()
        
        # 重新加载所有工作流
        results = self.load_all_workflows()
        
        logger.info(f"手动重新加载完成: 成功 {len(results['success'])}，失败 {len(results['failed'])}")
        
        return {
            "success": True,
            "message": f"重新加载完成: 成功 {len(results['success'])}，失败 {len(results['failed'])}",
            "results": results
        }
    




# 创建工作流管理器实例
workflow_manager = WorkflowManager()

# 初始加载所有工作流
load_results = workflow_manager.load_all_workflows()
logger.info(f"初始工作流加载结果: {load_results}")

# 导出模块级别的变量和实例
__all__ = ['workflow_manager', 'WorkflowManager', 'CUSTOM_WORKFLOW_DIR'] 