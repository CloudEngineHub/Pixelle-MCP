# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import chainlit as cl
from chainlit.mcp import McpConnection
from mcp import ClientSession
import utils.llm_util as llm_util
from converters.message_converter import messages_from_chaintlit_to_openai
import chat.starters as starters
import auth.auth as auth

from core.core import logger
from core.prompt import DEFAULT_SYSTEM_PROMPT
from converters.tool_converter import tools_from_chaintlit_to_openai
from chat.chat_handler import handle_mcp_connect, handle_mcp_disconnect
from chat.chat_settings import setup_chat_settings, setup_settings_update
import chat.chat_handler as tool_handler
from utils.file_uploader import upload


# @cl.set_chat_profiles
async def chat_profile(user: cl.User | None) -> list[cl.ChatProfile]:
    models = llm_util.get_all_models()
    default_model = llm_util.get_default_model()
    default_model_name = default_model.name if default_model else None
    return [
        cl.ChatProfile(
            name=model.name,
            markdown_description=f"Use **{model.name}** to talk with you.",
            default=default_model_name == model.name,
        )
        for model in models
    ]

@cl.on_chat_start
async def start():
    """初始化聊天会话"""
    # await setup_chat_settings()
    
    # 从settings中获取系统提示词，如果没有则使用默认值
    settings = cl.user_session.get("settings", {})
    system_prompt = settings.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    
    sys_message = cl.Message(
        type="system_message",
        content=system_prompt
    )
    cl.chat_context.add(sys_message)
    
@cl.on_settings_update
async def on_settings_update(settings):
    await setup_settings_update(settings)


@cl.on_message
async def on_message(message: cl.Message):
    """处理用户消息"""
    # 检查是否为starter消息，如果已处理则直接返回
    is_handled = await starters.hook_by_starters(message)
    if not is_handled:
        await cl.Message(
            content="The current scene does not support dialogue.",
        ).send()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
