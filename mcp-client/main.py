# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import chainlit as cl
import chat.starters as starters


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
