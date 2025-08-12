# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from datetime import timedelta
import json
import os
import time
import chainlit as cl
from typing import Any, Dict, List
from mcp import ClientSession
import re
from utils.llm_util import ModelInfo, ModelType

from litellm import acompletion
import litellm

from chat.starters import build_save_action
from utils.time_util import format_duration
from core.core import logger

save_starter_enabled = os.getenv("CHAINLIT_SAVE_STARTER_ENABLED", "false").lower() == "true"


def format_llm_error_message(model_name: str, error_str: str) -> str:
    """统一的 LLM 错误消息格式化函数"""
    # 处理常见的错误类型，提供友好的英文错误信息
    if "RateLimitError" in error_str or "429" in error_str:
        if "quota" in error_str.lower() or "exceed" in error_str.lower():
            return f"⚠️ {model_name} API quota exceeded. Please check your plan and billing details."
        else:
            return f"⚠️ {model_name} API rate limit hit. Please try again later."
    elif "401" in error_str or "authentication" in error_str.lower():
        return f"🔑 {model_name} API key is invalid. Please check your configuration."
    elif "403" in error_str or "permission" in error_str.lower():
        return f"🚫 {model_name} API access denied. Please check permissions."
    elif "timeout" in error_str.lower():
        return f"⏰ {model_name} API call timed out. Please retry."
    else:
        return f"❌ {model_name} model call failed: {error_str}"


def get_all_tools() -> List[Dict[str, Any]]:
    """获取所有可用的 MCP 工具"""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    all_tools = []
    for connection_tools in mcp_tools.values():
        all_tools.extend(connection_tools)
    return all_tools


def find_tool_connection(tool_name: str) -> str:
    """查找工具所属的 MCP 连接"""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    for connection_name, tools in mcp_tools.items():
        if any(tool["function"]["name"] == tool_name for tool in tools):
            return connection_name
    return None


def _extract_content(content_list):
    """从 CallToolResult 的 content 列表中提取文本内容"""
    if not content_list:
        return ""
    
    text_parts = []
    for content_item in content_list:
        # 处理不同类型的内容
        if hasattr(content_item, 'text'):
            # TextContent
            text_parts.append(content_item.text)
        elif hasattr(content_item, 'data'):
            # ImageContent 或其他二进制内容
            text_parts.append(f"[Binary content: {getattr(content_item, 'mimeType', 'unknown')}]")
        elif hasattr(content_item, 'uri'):
            # EmbeddedResource
            text_parts.append(f"[Resource: {content_item.uri}]")
        else:
            # 其他未知类型，尝试转换为字符串
            text_parts.append(str(content_item))
    
    return text_parts[0] if len(text_parts) == 1 else text_parts


@cl.step(type="tool")
async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """执行 MCP 工具调用"""
    # 记录开始时间
    start_time = time.time()
    
    def _format_result_with_duration(content: str) -> str:
        """统一格式化带耗时的结果"""
        duration = time.time() - start_time
        return f"[Took {format_duration(duration)}] {content}"
    
    current_step = cl.context.current_step
    current_step.input = tool_input
    current_step.name = tool_name
    await current_step.update()
    
    def record_step():
        # 获取现有的消息历史
        current_steps = cl.user_session.get("current_steps", [])
        current_steps.append(current_step)
        # 更新消息历史
        cl.user_session.set("current_steps", current_steps)
    
    # 查找工具所属的连接
    mcp_name = find_tool_connection(tool_name)
    if not mcp_name:
        error_msg = json.dumps({"error": f"Tool {tool_name} not found in any MCP connection"})
        result_with_duration = _format_result_with_duration(error_msg)
        current_step.output = result_with_duration
        record_step()
        return result_with_duration
    
    # 获取 MCP 会话
    mcp_session, _ = cl.context.session.mcp_sessions.get(mcp_name)
    if not mcp_session:
        error_msg = json.dumps({"error": f"MCP {mcp_name} not found in any MCP connection"})
        result_with_duration = _format_result_with_duration(error_msg)
        current_step.output = result_with_duration
        record_step()
        return result_with_duration
    
    try:
        # 调用 MCP 工具，返回 CallToolResult 对象
        logger.info(f"Calling MCP tool: {tool_name} with input: {tool_input}")
        result = await mcp_session.call_tool(tool_name, tool_input, read_timeout_seconds=timedelta(hours=1))
        
        # 检查是否有错误
        if result.isError:
            error_content = _extract_content(result.content)
            logger.error(f"Tool execution failed: {error_content}")
            error_msg = json.dumps({"error": f"Tool execution failed: {error_content}"})
            result_with_duration = _format_result_with_duration(error_msg)
            current_step.output = result_with_duration
            return result_with_duration
        
        # 提取内容文本
        content = _extract_content(result.content)
        logger.info(f"Tool execution succeeded: {content}")
        result_with_duration = _format_result_with_duration(str(content))
        current_step.output = result_with_duration
        record_step()
        return result_with_duration
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        error_msg = json.dumps({"error": str(e)})
        result_with_duration = _format_result_with_duration(error_msg)
        current_step.output = result_with_duration
        record_step()
        return result_with_duration


def _extract_and_clean_media_markers(text: str) -> tuple[Dict[str, List[str]], str]:
    """提取媒体标记并清理文本
    
    Returns:
        tuple: (媒体文件字典, 清理后的文本)
               媒体文件字典格式: {"images": [...], "audios": [...], "videos": [...]}
    """
    # 匹配不同类型的媒体标记
    patterns = {
        "images": r'\[SHOW_IMAGE:([^\]]+)\]',
        "audios": r'\[SHOW_AUDIO:([^\]]+)\]',
        "videos": r'\[SHOW_VIDEO:([^\]]+)\]'
    }
    
    media_files = {"images": [], "audios": [], "videos": []}
    cleaned_text = text
    
    # 提取各类型媒体文件并清理文本
    for media_type, pattern in patterns.items():
        media_files[media_type] = re.findall(pattern, cleaned_text)
        cleaned_text = re.sub(pattern, '', cleaned_text)
    
    # 移除多余的空白字符
    cleaned_text = cleaned_text.rstrip()
    
    return media_files, cleaned_text


def _is_url(source: str) -> bool:
    """判断媒体源是否为URL"""
    return source.startswith(('http://', 'https://'))


async def _process_media_markers(msg: cl.Message):
    """处理消息中的媒体标记"""
    if not msg.content:
        return
        
    # 提取媒体标记并清理文本
    media_files, cleaned_content = _extract_and_clean_media_markers(msg.content)
    
    # 更新消息内容（移除标记）
    msg.content = cleaned_content
    
    # 处理图片
    for i, img_source in enumerate(media_files["images"]):
        img_source = img_source.strip()
        
        img_params = {
            "name": f"Generated_Image_{i+1}",
            "display": "inline",
            "size": "small",
        }
        
        if _is_url(img_source):
            img_params["url"] = img_source
        else:
            img_params["path"] = img_source
        
        img_element = cl.Image(**img_params)
        msg.elements.append(img_element)
        logger.info(f"Added image element: {img_source}")
    
    # 处理音频
    for i, audio_source in enumerate(media_files["audios"]):
        audio_source = audio_source.strip()
        
        audio_params = {
            "name": f"Generated_Audio_{i+1}",
            "display": "inline",
            "size": "small",
        }
        
        if _is_url(audio_source):
            audio_params["url"] = audio_source
        else:
            audio_params["path"] = audio_source
        
        audio_element = cl.Audio(**audio_params)
        msg.elements.append(audio_element)
        logger.info(f"Added audio element: {audio_source}")
    
    # 处理视频
    for i, video_source in enumerate(media_files["videos"]):
        video_source = video_source.strip()
        
        video_params = {
            "name": f"Generated_Video_{i+1}",
            "display": "inline",
            "size": "small",
        }
        
        if _is_url(video_source):
            video_params["url"] = video_source
        else:
            video_params["path"] = video_source
        
        video_element = cl.Video(**video_params)
        msg.elements.append(video_element)
        logger.info(f"Added video element: {video_source}")


async def _process_tool_call_delta(
    tool_calls_delta: List[Any], 
    current_tool_calls: Dict[int, Dict], 
    current_args: Dict[int, str]
):
    """处理工具调用的增量数据"""
    for tool_call_delta in tool_calls_delta:
        index = tool_call_delta.index
        
        # 初始化工具调用数据结构
        if index not in current_tool_calls:
            current_tool_calls[index] = {
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""}
            }
            current_args[index] = ""
        
        # 累积工具调用信息
        if tool_call_delta.id:
            current_tool_calls[index]["id"] = tool_call_delta.id
        if tool_call_delta.function and tool_call_delta.function.name:
            current_tool_calls[index]["function"]["name"] = tool_call_delta.function.name
        if tool_call_delta.function and tool_call_delta.function.arguments:
            current_args[index] += tool_call_delta.function.arguments
            current_tool_calls[index]["function"]["arguments"] = current_args[index]


async def _execute_tool_calls(
    current_tool_calls: Dict[int, Dict], 
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """执行所有工具调用并更新消息历史"""
    # 构建包含工具调用的助手消息
    tool_calls_list = list(current_tool_calls.values())
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls_list
    })
    
    # 执行所有工具调用
    for tool_call in tool_calls_list:
        tool_name = tool_call["function"]["name"]
        tool_args_str = tool_call["function"]["arguments"]
        
        try:
            # 解析工具参数
            tool_args = json.loads(tool_args_str)
            
            # 执行工具调用
            tool_response = await execute_tool(tool_name, tool_args)
            
            # 添加工具响应到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_response
            })
            
        except Exception as e:
            error_message = f"工具调用错误: {str(e)}"
            logger.error(error_message)
            # 添加错误响应到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": error_message
            })
    
    return messages


async def _handle_stream_chunk(chunk, msg, current_tool_calls, current_args):
    """处理流式响应的单个chunk"""
    choice = chunk.choices[0]
    delta = choice.delta
    has_tool_call = False
    
    # 处理工具调用
    if delta.tool_calls:
        has_tool_call = True
        await _process_tool_call_delta(
            delta.tool_calls, 
            current_tool_calls, 
            current_args
        )
    
    # 处理普通文本响应
    elif delta.content:
        await msg.stream_token(delta.content)
    
    return has_tool_call, choice.finish_reason


async def _handle_response(model_info, api_params, enhanced_messages, messages):
    """处理流式响应"""
    # 为这一轮响应创建独立的消息对象
    msg = cl.Message(content="")
    
    current_tool_calls = {}
    current_args = {}
    has_tool_call = False
    
    try:
        # 准备 LiteLLM 参数 - 直接传递所有必要参数
        litellm_params = {
            "model": f"{model_info.provider}/{model_info.model}",
            "stream": True,
            "num_retries": 0,
            "timeout": 30,
            "api_key": model_info.api_key,
            "base_url": model_info.base_url or None,
            **api_params,
        }
        
        logger.info(f"Call LLM: {model_info.provider}/{model_info.model}")
        response = await acompletion(**litellm_params)
        
        try:
            async for chunk in response:
                chunk_has_tool_call, finish_reason = await _handle_stream_chunk(
                    chunk, msg, current_tool_calls, current_args
                )
                
                if chunk_has_tool_call:
                    has_tool_call = True
                
                # 检查完成状态
                if finish_reason == 'tool_calls':
                    try:
                        # 先发送当前轮次的消息（如果有内容的话）
                        if msg.content and msg.content.strip():
                            await msg.send()
                        
                        # 执行工具调用
                        enhanced_messages = await _execute_tool_calls(
                            current_tool_calls, 
                            enhanced_messages
                        )
                        return enhanced_messages, True  # 继续下一轮
                        
                    except Exception as e:
                        error_message = f"Error when processing tool calls: {str(e)}"
                        logger.error(error_message)
                        await msg.stream_token(f"\n{error_message}\n")
                        await msg.send()
                        return messages, False  # 结束处理
                
                elif finish_reason:
                    # 其他完成原因，结束流式处理
                    break
            
            # 处理媒体标记并发送消息
            if not has_tool_call:
                await _process_media_markers(msg)
                if msg.content and msg.content.strip():
                    if save_starter_enabled:
                        # 在AI回复消息上添加保存Action
                        msg.actions = [
                            build_save_action()
                        ]
                    await msg.send()
                
                # 添加助手消息到历史记录
                if msg.content and msg.content.strip():
                    enhanced_messages.append({
                        "role": "assistant", 
                        "content": msg.content
                    })
            else:
                # 如果有工具调用，直接发送消息（工具调用相关的消息已经在别处处理）
                await msg.send()
            
            return enhanced_messages, False  # 结束处理
            
        except Exception as e:
            error_str = str(e)
            error_message = format_llm_error_message(model_info.name, error_str)
            logger.error(f"Stream processing error: {error_str}")
            await msg.stream_token(f"\n{error_message}\n")
            # 即使出错也要处理媒体标记
            await _process_media_markers(msg)
            await msg.send()
            return messages, False
            
    except Exception as e:
        error_str = str(e)
        error_message = format_llm_error_message(model_info.name, error_str)
        logger.error(f"LiteLLM call failed: {error_str}")
        await msg.stream_token(f"\n{error_message}\n")
        # 即使出错也要处理媒体标记
        await _process_media_markers(msg)
        await msg.send()
        return messages, False


async def process_streaming_response(
    messages: List[Dict[str, Any]], 
    model_info: ModelInfo,
) -> List[Dict[str, Any]]:
    """
    处理流式响应和工具调用
    
    Args:
        messages: 消息历史
        model_info: 使用的模型信息
        
    Returns:
        更新后的消息历史
    """
    
    # 清理steps，针对用户重新编辑已发送消息的场景做处理
    chat_messages = cl.chat_context.get()
    if len(chat_messages) >= 2:  # 至少有2条消息才需要处理
        # 获取倒数第二条消息的时间戳
        second_last_msg = chat_messages[-2]
        second_last_time = second_last_msg.created_at
        
        if second_last_time:
            # 获取当前steps
            current_steps = cl.user_session.get("current_steps", [])
            # 只保留时间戳在倒数第二条消息之前的steps
            filtered_steps = [
                step for step in current_steps 
                if str(step.created_at) <= second_last_time
            ]
            # 更新steps
            cl.user_session.set("current_steps", filtered_steps)
    
    tools = get_all_tools()
    
    # 注入媒体显示系统指令
    enhanced_messages = messages.copy()
    
    while True:  # 循环处理工具调用
        # 准备 API 参数
        api_params = {
            "messages": enhanced_messages,
        }
        
        # 如果有工具，添加工具参数
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = "auto"
        
        
        # 所有参数都通过 LiteLLM 函数参数传递，不使用环境变量
        try:
            enhanced_messages, should_continue = await _handle_response(
                model_info, api_params, enhanced_messages, messages
            )
            
            if not should_continue:
                return enhanced_messages
                
        except Exception as e:
            error_str = str(e)
            error_message = format_llm_error_message(model_info.name, error_str)
            logger.error(f"LiteLLM main loop error: {error_str}")
            # 发送错误消息给用户
            error_msg = cl.Message(content=error_message)
            await error_msg.send()
            return enhanced_messages  # 直接返回，不要继续循环


# MCP 连接管理的便捷函数
async def handle_mcp_connect(connection, session: ClientSession, tools_converter_func):
    """处理 MCP 连接的通用逻辑"""
    tools_result = await session.list_tools()
    openai_tools = tools_converter_func(tools_result.tools)
    
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = openai_tools
    cl.user_session.set("mcp_tools", mcp_tools)

async def handle_mcp_disconnect(name: str):
    """处理 MCP 断开连接的通用逻辑"""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    if name in mcp_tools:
        del mcp_tools[name]
    cl.user_session.set("mcp_tools", mcp_tools) 

 