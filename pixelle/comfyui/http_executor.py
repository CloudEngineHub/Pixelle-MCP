# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import os
import json
import time
import uuid
import asyncio
from typing import Optional, Dict, Any

from pixelle.comfyui.base_executor import ComfyUIExecutor, COMFYUI_API_KEY, logger
from pixelle.comfyui.models import ExecuteResult


class HttpExecutor(ComfyUIExecutor):
    """HTTP 方式的 ComfyUI 执行器"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url)

    async def _queue_prompt(self, workflow: Dict[str, Any], client_id: str, prompt_ext_params: Optional[Dict[str, Any]] = None) -> str:
        """将工作流提交到队列"""
        prompt_data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        # 更新prompt_data与prompt_ext_params的所有参数
        if prompt_ext_params:
            prompt_data.update(prompt_ext_params)
        
        json_data = json.dumps(prompt_data)
        
        # 使用aiohttp发送请求
        prompt_url = f"{self.base_url}/prompt"
        async with self.get_comfyui_session() as session:
            async with session.post(
                    prompt_url, 
                    data=json_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    raise Exception(f"提交工作流失败: [{response.status}] {response_text}")
                
                result = await response.json()
                prompt_id = result.get("prompt_id")
                if not prompt_id:
                    raise Exception(f"获取prompt_id失败: {result}")
                logger.info(f"任务已提交: {prompt_id}")
                return prompt_id

    async def _wait_for_results(self, prompt_id: str, client_id: str, timeout: Optional[int] = None, output_id_2_var: Optional[Dict[str, str]] = None) -> ExecuteResult:
        """等待工作流执行结果（HTTP方式）"""
        start_time = time.time()
        logger.info(f"HTTP方式等待执行结果，prompt_id: {prompt_id}, client_id: {client_id}")
        result = ExecuteResult(
            status="processing",
            prompt_id=prompt_id
        )

        # 获取基础URL
        base_url = self.base_url

        while True:
            # 检查超时
            if timeout is not None and timeout > 0:
                duration = time.time() - start_time
                if duration > timeout:
                    logger.warning(f"超时: {duration} 秒")
                    result.status = "timeout"
                    result.duration = duration
                    return result

            # 使用HTTP API获取历史记录
            history_url = f"{self.base_url}/history/{prompt_id}"
            async with self.get_comfyui_session() as session:
                async with session.get(history_url) as response:
                    if response.status != 200:
                        await asyncio.sleep(1.0)
                        continue
                    history_data = await response.json()
                    if prompt_id not in history_data:
                        await asyncio.sleep(1.0)
                        continue
                    
                    prompt_history = history_data[prompt_id]
                    status = prompt_history.get("status")
                    if status and status.get("status_str") == "error":
                        result.status = "error"
                        messages = status.get("messages")
                        if messages:
                            errors = [
                                body.get("exception_message")
                                for type, body in messages
                                if type == "execution_error"
                            ]
                            error_message = "\n".join(errors)
                        else:
                            error_message = "未知错误"
                        result.msg = error_message
                        result.duration = time.time() - start_time
                        return result
                    
                    if "outputs" in prompt_history:
                        result.outputs = prompt_history["outputs"]
                        result.status = "completed"

                        # 按文件扩展名收集所有图片、视频、音频和文本输出
                        output_id_2_images = {}
                        output_id_2_videos = {}
                        output_id_2_audios = {}
                        output_id_2_texts = {}
                        
                        for node_id, node_output in prompt_history["outputs"].items():
                            images, videos, audios = self._split_media_by_suffix(node_output, base_url)
                            if images:
                                output_id_2_images[node_id] = images
                            if videos:
                                output_id_2_videos[node_id] = videos
                            if audios:
                                output_id_2_audios[node_id] = audios
                            
                            # 收集文本输出
                            if "text" in node_output:
                                texts = node_output["text"]
                                if isinstance(texts, str):
                                    texts = [texts]
                                elif not isinstance(texts, list):
                                    texts = [str(texts)]
                                output_id_2_texts[node_id] = texts

                        # 如果有映射则按变量名映射
                        if output_id_2_images:
                            result.images_by_var = self._map_outputs_by_var(output_id_2_var or {}, output_id_2_images)
                            result.images = self._extend_flat_list_from_dict(result.images_by_var)

                        if output_id_2_videos:
                            result.videos_by_var = self._map_outputs_by_var(output_id_2_var or {}, output_id_2_videos)
                            result.videos = self._extend_flat_list_from_dict(result.videos_by_var)

                        if output_id_2_audios:
                            result.audios_by_var = self._map_outputs_by_var(output_id_2_var or {}, output_id_2_audios)
                            result.audios = self._extend_flat_list_from_dict(result.audios_by_var)

                        # 处理texts/texts_by_var
                        if output_id_2_texts:
                            result.texts_by_var = self._map_outputs_by_var(output_id_2_var or {}, output_id_2_texts)
                            result.texts = self._extend_flat_list_from_dict(result.texts_by_var)

                        # 设置执行耗时
                        result.duration = time.time() - start_time
                        return result
            await asyncio.sleep(1.0)

    async def execute_workflow(self, workflow_file: str, params: Dict[str, Any] = None) -> ExecuteResult:
        """执行工作流（HTTP方式）"""
        try:
            if not os.path.exists(workflow_file):
                logger.error(f"工作流文件不存在: {workflow_file}")
                return ExecuteResult(status="error", msg=f"工作流文件不存在: {workflow_file}")
            
            # 获取工作流元数据
            metadata = self.get_workflow_metadata(workflow_file)
            if not metadata:
                return ExecuteResult(status="error", msg="无法解析工作流元数据")
            
            # 加载工作流JSON
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            if not workflow_data:
                return ExecuteResult(status="error", msg="工作流数据缺失")
            
            # 使用新的参数映射逻辑
            if params:
                workflow_data = await self._apply_params_to_workflow(workflow_data, metadata, params)
            else:
                # 即使没有传入参数，也需要应用默认值
                workflow_data = await self._apply_params_to_workflow(workflow_data, metadata, {})
            
            # 从元数据提取输出节点信息
            output_id_2_var = self._extract_output_nodes(metadata)
            
            # 生成客户端ID
            client_id = str(uuid.uuid4())
            
            # 准备额外参数
            prompt_ext_params = {}
            if COMFYUI_API_KEY:
                prompt_ext_params = {
                    "extra_data": {
                        "api_key_comfy_org": COMFYUI_API_KEY
                    }
                }
            else:
                logger.warning("COMFYUI_API_KEY 未设置")
            
            # 提交工作流到ComfyUI队列
            try:
                prompt_id = await self._queue_prompt(workflow_data, client_id, prompt_ext_params)
            except Exception as e:
                error_message = f"提交工作流失败: [{type(e)}] {str(e)}"
                logger.error(error_message)
                return ExecuteResult(status="error", msg=error_message)
            
            # 等待结果
            result = await self._wait_for_results(prompt_id, client_id, None, output_id_2_var)
            
            # 转存结果文件
            result = await self.transfer_result_files(result)
            return result
            
        except Exception as e:
            logger.error(f"执行工作流出错: {str(e)}", exc_info=True)
            return ExecuteResult(status="error", msg=str(e)) 