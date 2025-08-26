# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import os
import json
import time
import uuid
import asyncio
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse
import websockets

from pixelle.comfyui.base_executor import ComfyUIExecutor, COMFYUI_API_KEY, logger
from pixelle.comfyui.models import ExecuteResult


class WebSocketExecutor(ComfyUIExecutor):
    """WebSocket 方式的 ComfyUI 执行器"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url)
        self._parse_ws_url()
        
        logger.info(f"HTTP Base URL: {self.http_base_url}")
        logger.info(f"WebSocket Base URL: {self.ws_base_url}")
    
    def _parse_ws_url(self):
        """解析API URL并构建WebSocket URL"""
        # 使用标准URL解析器解析base_url
        parsed = urlparse(self.base_url)
        
        # 根据原始scheme确定WebSocket scheme
        ws_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        http_scheme = 'https' if parsed.scheme == 'https' else 'http'
        
        # 原始路径
        base_path = parsed.path.rstrip('/')

        # 构建WebSocket URL，添加 /ws 路径
        ws_netloc = parsed.netloc
        ws_path = f"{base_path}/ws"
        self.ws_base_url = urlunparse((ws_scheme, ws_netloc, ws_path, '', '', ''))
        
        # 构建HTTP URL，保持原有结构
        self.http_base_url = urlunparse((http_scheme, ws_netloc, base_path, '', '', ''))

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

    def _parse_ws_message(self, message: dict, prompt_id: str) -> tuple[bool, dict]:
        """
        解析websocket消息
        
        Args:
            message: websocket消息
            prompt_id: 要监听的prompt_id
            
        Returns:
            (是否执行完成, 消息内容)
        """
        invoke_completed = False
        if message.get('type') == 'executing':
            data = message.get('data', {})
            if data.get('node') is None and data.get('prompt_id') == prompt_id:
                invoke_completed = True
        return invoke_completed, message

    def _build_result_from_collected_outputs(self, collected_outputs: Dict[str, Any], prompt_id: str, output_id_2_var: Optional[Dict[str, str]] = None) -> ExecuteResult:
        """
        从收集的WebSocket输出中构建执行结果
        """
        try:
            logger.info(f"从收集的输出中构建执行结果 (prompt_id: {prompt_id})")
            
            # 按文件扩展名收集所有图片、视频、音频输出
            output_id_2_images = {}
            output_id_2_videos = {}
            output_id_2_audios = {}
            output_id_2_texts = {}
            
            for node_id, output in collected_outputs.items():
                images, videos, audios = self._split_media_by_suffix(output, self.http_base_url)
                if images:
                    output_id_2_images[node_id] = images
                if videos:
                    output_id_2_videos[node_id] = videos
                if audios:
                    output_id_2_audios[node_id] = audios
                
                # 收集文本输出
                if "text" in output:
                    texts = output["text"]
                    if isinstance(texts, str):
                        texts = [texts]
                    elif not isinstance(texts, list):
                        texts = [str(texts)]
                    output_id_2_texts[node_id] = texts
            
            result = ExecuteResult(
                status="completed",
                prompt_id=prompt_id,
                outputs=collected_outputs
            )
            
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
            
            if not (result.images or result.videos or result.audios or result.texts):
                logger.warning("没有找到任何输出")
                result.status = "error"
                result.msg = "没有找到任何输出"
            
            logger.info(f"构建结果成功，输出数量: 图片={len(result.images)}, 视频={len(result.videos)}, 音频={len(result.audios)}, 文本={len(result.texts)}")
            
            return result
        except Exception as e:
            logger.error(f"从收集的输出中构建执行结果异常: {str(e)}")
            return ExecuteResult(
                status="error",
                prompt_id=prompt_id,
                msg=f"从收集的输出中构建执行结果异常: {str(e)}"
            )

    async def execute_workflow(self, workflow_file: str, params: Dict[str, Any] = None) -> ExecuteResult:
        """执行工作流（WebSocket方式）"""
        try:
            start_time = time.time()
            
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
            
            # 首先建立WebSocket连接，然后提交任务
            timeout = 30 * 60  # 默认30分钟超时
            
            # 构建WebSocket URL
            ws_url = f"{self.ws_base_url}?clientId={client_id}"
            logger.info(f"WebSocket URL: {ws_url}")
            logger.info(f"准备连接websocket服务")
            
            # 用于收集包含输出的节点
            collected_outputs = {}
            prompt_id = None
            
            try:
                # 准备WebSocket连接的额外头部，包含cookies
                additional_headers = {}
                cookies = await self._parse_comfyui_cookies()
                if cookies:
                    try:
                        if isinstance(cookies, dict):
                            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                        else:
                            cookie_string = str(cookies)
                        
                        additional_headers["Cookie"] = cookie_string
                        logger.debug(f"WebSocket连接将使用cookies: {cookie_string[:50]}...")
                    except Exception as e:
                        logger.warning(f"解析WebSocket cookies失败: {e}")
                
                # 建立WebSocket连接
                async with websockets.connect(ws_url, additional_headers=additional_headers) as websocket:
                    logger.info('WebSocket连接成功，现在提交工作流')
                    
                    # 连接成功后立即提交工作流
                    try:
                        prompt_id = await self._queue_prompt(workflow_data, client_id, prompt_ext_params)
                    except Exception as e:
                        error_message = f"提交工作流失败: [{type(e)}] {str(e)}"
                        logger.error(error_message)
                        return ExecuteResult(status="error", msg=error_message)
                    
                    logger.info(f"工作流已提交，prompt_id: {prompt_id}，开始等待结果")
                    
                    while True:
                        # 检查超时
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            logger.warning(f"WebSocket等待超时 ({timeout}秒)")
                            result = ExecuteResult(
                                status="timeout",
                                prompt_id=prompt_id,
                                msg=f"WebSocket等待超时（{timeout}秒）",
                                duration=elapsed
                            )
                            return result
                        
                        try:
                            # 等待消息，设置较短的超时以便检查总超时
                            message_str = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            
                            if not isinstance(message_str, str):
                                continue
                                
                            message = json.loads(message_str)
                            
                            # 打印目标prompt_id的完整消息用于调试
                            if message.get('data', {}).get('prompt_id') == prompt_id:
                                logger.debug(f'收到目标WebSocket消息 (prompt_id: {prompt_id}): {json.dumps(message, ensure_ascii=False)}')
                                
                                # 处理不同类型的消息
                                msg_type = message.get('type')
                                data = message.get('data', {})
                                
                                if msg_type == 'execution_cached':
                                    # 处理缓存执行消息
                                    cached_nodes = data.get('nodes', [])
                                    logger.debug(f"检测到缓存执行，跳过节点: {cached_nodes}")
                                    
                                elif msg_type == 'executed':
                                    # 收集包含输出的节点
                                    node_id = data.get('node')
                                    output = data.get('output')
                                    if output and node_id:
                                        # 检查是否有我们感兴趣的输出
                                        has_media = output.get('images') \
                                            or output.get('gifs') \
                                            or output.get('audio') \
                                            or output.get('text')
                                        if has_media:
                                            logger.info(f"收集到节点 {node_id} 的输出")
                                            collected_outputs[node_id] = output
                                            
                                elif msg_type == 'execution_error':
                                    # 处理执行错误
                                    error_message = data.get('exception_message', '未知错误')
                                    logger.error(f"执行出错: {error_message}")
                                    return ExecuteResult(
                                        status="error",
                                        prompt_id=prompt_id,
                                        msg=error_message,
                                        duration=time.time() - start_time
                                    )
                            else:
                                # 对于status消息，记录队列状态
                                if message.get('type') == 'status':
                                    queue_remaining = message.get('data', {}).get('status', {}).get('exec_info', {}).get('queue_remaining', 'unknown')
                                    logger.debug(f'队列状态更新: 剩余任务 {queue_remaining} 个')
                                else:
                                    logger.debug(f'收到其他WebSocket消息: {message}')
                            
                            # 解析消息
                            invoke_completed, parsed_message = self._parse_ws_message(message, prompt_id)
                            
                            if invoke_completed:
                                logger.info('WebSocket检测到执行完成')
                                
                                # 设置执行耗时
                                duration = time.time() - start_time
                                
                                # 如果有收集到的输出，使用它们构建结果
                                if collected_outputs:
                                    result = self._build_result_from_collected_outputs(collected_outputs, prompt_id, output_id_2_var)
                                    result.duration = duration
                                    # 转存结果文件
                                    result = await self.transfer_result_files(result)
                                    return result
                                else:
                                    # WebSocket方式没有收集到输出，返回错误
                                    logger.warning("WebSocket没有收集到任何输出")
                                    result = ExecuteResult(
                                        status="error",
                                        prompt_id=prompt_id,
                                        msg="WebSocket没有收集到任何输出",
                                        duration=duration
                                    )
                                    return result
                                
                        except asyncio.TimeoutError:
                            # 等待消息超时，继续循环检查总超时
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("WebSocket连接已关闭")
                            result = ExecuteResult(
                                status="error",
                                prompt_id=prompt_id,
                                msg="WebSocket连接已关闭",
                                duration=time.time() - start_time
                            )
                            return result
                            
            except Exception as e:
                logger.error(f"WebSocket连接或执行异常: {str(e)}")
                result = ExecuteResult(
                    status="error",
                    prompt_id=prompt_id,
                    msg=f"WebSocket连接或执行异常: {str(e)}",
                    duration=time.time() - start_time
                )
                return result
                
        except Exception as e:
            logger.error(f"执行工作流出错: {str(e)}", exc_info=True)
            return ExecuteResult(status="error", msg=str(e)) 