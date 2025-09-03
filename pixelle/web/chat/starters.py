# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from typing import Awaitable, Optional, Callable, Any, List, Dict, Tuple
import chainlit as cl
from pydantic import BaseModel
import json
from pathlib import Path
import re
import uuid
import asyncio
import random

from pixelle.utils.os_util import get_data_path

ReplyHandler = Callable[[cl.Message], Awaitable[None]]

class StarterModel(BaseModel):
    label: str
    icon: Optional[str] = None
    image: Optional[str] = None
    reply_handler: Optional[ReplyHandler] = None
    messages: Optional[List[Dict[str, Any]]] = None
    enabled: bool = True
    order: int = 999
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def message(self) -> str:
        """从messages中获取用户消息内容"""
        if not self.messages:
            return ""
        
        # 查找第一个用户消息
        for item in self.messages:
            if (item.get("role") == "user" and 
                item.get("type") == "message"):
                return item.get("content", "")
        
        return ""
    
    def to_cl_starter(self) -> cl.Starter:
        """转换为Chainlit Starter对象"""
        return cl.Starter(
            label=self.label,
            message=self.message,
            icon=self.icon,
        )

# 打字机效果配置
TYPING_EFFECT_CONFIG = {
    "user_message": {
        "delay_per_char": 0.05,
        "max_total_duration": 1.0
    },
    "assistant_message": {
        "delay_per_char": 0.02,
        "max_total_duration": 2.0
    }
}

# 文件操作相关函数
SYSTEM_STARTERS_DIR = Path("./starters")
CUSTOM_STARTERS_DIR = Path(get_data_path("custom_starters"))

def ensure_starters_dirs():
    """确保系统和用户 starters 目录都存在"""
    SYSTEM_STARTERS_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_STARTERS_DIR.mkdir(parents=True, exist_ok=True)

def get_system_starters_dir() -> Path:
    """获取系统预置starter目录"""
    return SYSTEM_STARTERS_DIR

def get_custom_starters_dir() -> Path:
    """获取用户自定义starter目录"""
    return CUSTOM_STARTERS_DIR

def parse_filename(filename: str) -> Tuple[bool, int, str]:
    """
    解析文件名格式：[_]xxx_label.json
    返回：(enabled, order, label)
    """
    # 移除.json后缀
    name = filename.replace('.json', '')
    
    # 检查是否以_开头（禁用标记）
    enabled = True
    if name.startswith('_'):
        enabled = False
        name = name[1:]  # 移除前面的_
    
    # 匹配格式：xxx_label
    match = re.match(r'^(\d+)_(.+)$', name)
    if match:
        order = int(match.group(1))
        label = match.group(2)
        return enabled, order, label
    else:
        # 如果不匹配格式，返回默认值
        return enabled, 999, name

def get_next_order_number() -> int:
    """获取用户目录下一个排序号"""
    ensure_starters_dirs()
    max_order = 0
    
    # 只考虑用户自定义目录的排序号
    for starter_file in CUSTOM_STARTERS_DIR.glob("*.json"):
        _, order, _ = parse_filename(starter_file.name)
        if order != 999:  # 忽略默认值
            max_order = max(max_order, order)
    
    return max_order + 1

def load_custom_starter(starter_file: Path) -> Optional[StarterModel]:
    """从文件加载单个自定义 starter"""
    try:
        # 解析文件名
        enabled, order, expected_label = parse_filename(starter_file.name)
        
        with open(starter_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return StarterModel(
            label=expected_label,
            icon=data.get("icon", "/public/tool.svg"),
            image=data.get("image", None),
            messages=data.get("messages", []),
            enabled=enabled,
            order=order,
        )
    except Exception as e:
        print(f"Error loading starter from {starter_file}: {e}")
        return None

def load_system_starters() -> List[StarterModel]:
    """加载系统预置 starters"""
    ensure_starters_dirs()
    system_starters = []
    
    for starter_file in SYSTEM_STARTERS_DIR.glob("*.json"):
        starter = load_custom_starter(starter_file)
        if starter and starter.enabled:  # 只加载启用的starters
            system_starters.append(starter)
    
    # 按order字段排序
    system_starters.sort(key=lambda x: x.order)
    
    return system_starters

def load_custom_starters() -> List[StarterModel]:
    """加载用户自定义 starters"""
    ensure_starters_dirs()
    custom_starters = []
    
    for starter_file in CUSTOM_STARTERS_DIR.glob("*.json"):
        starter = load_custom_starter(starter_file)
        if starter and starter.enabled:  # 只加载启用的starters
            custom_starters.append(starter)
    
    # 按order字段排序
    custom_starters.sort(key=lambda x: x.order)
    
    return custom_starters

def get_all_starters() -> List[StarterModel]:
    """获取所有启用的 starters，系统预置在前，用户自定义在后"""
    system_starters = load_system_starters()
    custom_starters = load_custom_starters()
    
    # 系统预置在前，用户自定义在后
    return system_starters + custom_starters

def convert_message_to_dict(message: cl.Message) -> Dict[str, Any]:
    """将 cl.Message 转换为字典格式"""
    message_dict = {
        "created_at": message.created_at,
        "role": "user" if message.type == "user_message" else "ai",
        "type": "message",
        "content": message.content,
    }
    
    # 处理元素
    if message.elements:
        elements = []
        for element in message.elements:
            if isinstance(element, cl.Image):
                elements.append({
                    "type": "image",
                    "url": element.url,
                    "size": getattr(element, 'size', 'small')
                })
            elif isinstance(element, cl.Video):
                elements.append({
                    "type": "video",
                    "url": element.url,
                    "size": getattr(element, 'size', 'small')
                })
            elif isinstance(element, cl.Audio):
                elements.append({
                    "type": "audio",
                    "url": element.url,
                    "size": getattr(element, 'size', 'small')
                })
        
        if elements:
            message_dict["elements"] = elements
    
    return message_dict

def convert_step_to_dict(step: cl.Step) -> Dict[str, Any]:
    """将 cl.Step 转换为字典格式"""
    return {
        "created_at": step.created_at,
        "role": "ai",
        "type": "step",
        "name": step.name,
        "input": step.input if step.input else {},
        "output": step.output if step.output else ""
    }

async def save_conversation_as_starter(label: str, user_message: str) -> bool:
    """保存当前对话为 starter"""
    try:
        ensure_starters_dirs()
        
        # 获取对话历史
        chat_context = cl.chat_context.get()
        # 构建消息数组
        pure_messages = []
        for item in chat_context:
            if not item.content and not item.elements:
                continue
            if item.type == "system_message":
                continue
            else:
                pure_messages.append(convert_message_to_dict(item))
        
        
        
        # 从 user_session 获取 steps
        current_steps = cl.user_session.get("current_steps", [])
        step_messages = []
        for step in current_steps:
            step_messages.append(convert_step_to_dict(step))
            
        all_messages = pure_messages + step_messages
        all_messages.sort(key=lambda x: x.get("created_at", ""))
        
        # 为首条用户消息添加\u200B前缀以标识starter
        if all_messages:
            first_user_msg = None
            for msg in all_messages:
                if msg.get("role") == "user" and msg.get("type") == "message":
                    first_user_msg = msg
                    break
            if first_user_msg and first_user_msg.get("content"):
                # 添加零宽度空格前缀标识这是starter消息
                starter_prefix = "\u200B"
                msg_content = first_user_msg["content"]
                if not msg_content.startswith(starter_prefix):
                    first_user_msg["content"] = starter_prefix + msg_content
        
        # 创建 starter 数据
        starter_data = {
            "icon": "/public/tool.svg",
            "messages": all_messages
        }
        
        # 生成文件名
        order = get_next_order_number()
        filename = f"{order:03d}_{label}.json"
        filepath = CUSTOM_STARTERS_DIR / filename
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(starter_data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error saving starter: {e}")
        return False

def build_save_action():
    return cl.Action(
        name="save_as_starter", 
        payload={"value": "save_starter"}, 
        icon="save"
    )

async def show_prompt_dialog(title: str, message: str, placeholder: str = ""):
    """显示自定义prompt对话框，返回(dialog_id, cancel_callback)"""
    dialog_id = str(uuid.uuid4())
    
    # 创建自定义元素
    prompt_element = cl.CustomElement(
        name="PromptDialog",
        props={
            "open": True,
            "title": title,
            "message": message,
            "placeholder": placeholder,
            "dialogId": dialog_id
        }
    )
    
    # 发送对话框
    prompt_msg = cl.Message(content="", elements=[prompt_element])
    await prompt_msg.send()
    
    # 将对话框信息存储到用户会话中
    cl.user_session.set(f"prompt_dialog_{dialog_id}", {
        "message": prompt_msg,
        "resolved": False,
        "result": None
    })
    
    # 定义取消回调函数
    async def cancel_callback():
        """清理prompt对话框相关资源"""
        try:
            await prompt_msg.remove()
            # cl.chat_context.remove(prompt_msg)
            cl.user_session.set(f"prompt_dialog_{dialog_id}", None)
        except Exception:
            pass  # 清理失败时忽略
    
    return dialog_id, cancel_callback

async def show_alert(alert_type: str, title: str, message: str):
    """显示alert对话框"""
    alert_element = cl.CustomElement(
        name="AlertDialog",
        props={
            "open": True,
            "type": alert_type,
            "title": title,
            "message": message
        }
    )
    
    # 发送alert
    alert_msg = cl.Message(content="", elements=[alert_element])
    await alert_msg.send()

@cl.action_callback("prompt_confirmed")
async def on_prompt_confirmed(action):
    """处理用户确认输入"""
    dialog_id = action.payload.get("dialogId")
    value = action.payload.get("value", "").strip()
    
    if dialog_id:
        dialog_info = cl.user_session.get(f"prompt_dialog_{dialog_id}")
        if dialog_info:
            dialog_info["resolved"] = True
            dialog_info["result"] = value
            cl.user_session.set(f"prompt_dialog_{dialog_id}", dialog_info)

@cl.action_callback("save_as_starter")
async def on_save_starter(action):
    """处理保存为Starter的action"""
    try:
        # 获取对话历史
        chat_context = cl.chat_context.get()
        if not chat_context or len(chat_context) < 2:
            await show_alert("error", "无法保存", "需要有对话内容才能保存为 Starter")
            return
        
        # 获取第一条用户消息的内容作为显示用
        first_user_message = None
        for msg in chat_context:
            if isinstance(msg, cl.Message) and msg.type == "user_message":
                first_user_message = msg.content
                break
        
        if not first_user_message:
            await show_alert("error", "无法保存", "无法找到用户消息")
            return
        
        # 显示自定义prompt对话框
        dialog_id, cancel_callback = await show_prompt_dialog(
            title="保存为 Starter",
            message="请输入Starter的标签名（用于显示在首页）",
            placeholder="如：图片编辑教程"
        )
        
        # 等待用户输入（一直等待，无超时）
        import asyncio
        while True:
            await asyncio.sleep(0.1)
            dialog_info = cl.user_session.get(f"prompt_dialog_{dialog_id}")
            if dialog_info and dialog_info.get("resolved"):
                label = dialog_info.get("result")
                break
        
        if not label:
            # 用户取消，清理prompt消息
            await cancel_callback()
            return
        
        # 验证标签名
        import re
        if not re.match(r'^[\w\u4e00-\u9fff\-_\s]+$', label):
            # 输入无效，清理prompt消息
            await cancel_callback()
            await show_alert("warning", "输入无效", "标签名只能包含中英文、数字、下划线、横线和空格")
            return
        
        # 保存完成后清理prompt消息
        await cancel_callback()
        
        # 保存 starter（传入label即可，user_message参数已不再使用）
        success = await save_conversation_as_starter(label, first_user_message)
        
        
        if success:
            await show_alert("success", "保存成功", f"已成功保存为 Starter：{label}")
            # 移除action按钮
            await action.remove()
        else:
            await show_alert("error", "保存失败", "请检查文件权限或联系管理员")
            
    except Exception as e:
        # 异常时也要清理状态
        if 'cancel_callback' in locals():
            await cancel_callback()
        await show_alert("error", "操作失败", str(e))

async def handle_messages(messages: List[Dict[str, Any]]) -> None:
    """处理预置回答数组"""
    if not messages:
        return
    
    for item in messages:
        role = item.get("role", "ai")
        item_type = item.get("type", "message")
        
        if item_type == "step":
            await handle_step_item(item)
        elif item_type == "message":
            await handle_message_item(item, role)

async def handle_step_item(item: Dict[str, Any]) -> None:
    """处理步骤项"""
    step_name = item.get("name", "处理中...")
    step_input = item.get("input", {})
    step_output = item.get("output", "")
    
    async with cl.Step(name=step_name) as step:
        step.input = step_input
        
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)
        
        step.output = step_output

async def stream_content_with_typing_effect(content: str, delay_per_char: float = 0.02, message_type: str = "assistant_message", max_total_duration: float = 3.0) -> cl.Message:
    """使用打字机效果流式输出内容
    
    Args:
        content: 要输出的内容
        delay_per_char: 每个字符的延迟时间（秒）
        message_type: 消息类型
        max_total_duration: 最大总时长（秒），超过此时间会加速输出
    """
    if not content:
        message = cl.Message(content="", type=message_type)
        await message.send()
        return message
    
    # 创建空消息，指定消息类型
    message = cl.Message(content="", type=message_type)
    
    # 计算理论总时长
    theoretical_duration = len(content) * delay_per_char
    
    # 如果理论时长超过最大时长，调整延迟
    if theoretical_duration > max_total_duration:
        adjusted_delay = max_total_duration / len(content)
    else:
        adjusted_delay = delay_per_char
    
    # 逐字符流式输出
    for char in content:
        await message.stream_token(char)
        await asyncio.sleep(adjusted_delay)
    
    # 完成流式输出
    await message.send()
    return message

async def handle_message_item(item: Dict[str, Any], role: str) -> None:
    """处理消息项"""
    content = item.get("content", "")
    elements_data = item.get("elements", [])
    
    # 构建元素列表
    elements = []
    for elem_data in elements_data:
        elem_type = elem_data.get("type", "")
        elem_url = elem_data.get("url", "")
        elem_size = elem_data.get("size", "small")
        
        if elem_type == "image" and elem_url:
            elements.append(cl.Image(url=elem_url, size=elem_size))
        elif elem_type == "video" and elem_url:
            elements.append(cl.Video(url=elem_url, size=elem_size))
        elif elem_type == "audio" and elem_url:
            elements.append(cl.Audio(url=elem_url, size=elem_size))
    
    # user 和 ai 消息都使用打字机效果
    if role == "user":
        # 用户消息 - 使用打字机效果
        config = TYPING_EFFECT_CONFIG["user_message"]
        message = await stream_content_with_typing_effect(
            content, 
            delay_per_char=config["delay_per_char"], 
            message_type="user_message", 
            max_total_duration=config["max_total_duration"]
        )
    else:
        # AI助手消息 - 使用打字机效果
        config = TYPING_EFFECT_CONFIG["assistant_message"]
        message = await stream_content_with_typing_effect(
            content, 
            delay_per_char=config["delay_per_char"], 
            message_type="assistant_message", 
            max_total_duration=config["max_total_duration"]
        )
    
    # content 输出完成后，一次性添加 elements
    if elements:
        message.elements = elements
        await message.update()

@cl.set_starters
async def set_starters():
    return [starter.to_cl_starter() for starter in get_all_starters()]

async def hook_by_starters(message: cl.Message):
    """Hook函数：根据starter消息内容进行处理"""
    
    # 检查是否为首条用户消息
    cl_messages = cl.chat_context.get()
    user_messages = [msg for msg in cl_messages if msg.type == "user_message"]
    is_first_message = len(user_messages) == 1
    if not is_first_message:
        return False
    
    # 严格匹配消息内容
    for starter in get_all_starters():
        # 从messages中获取第一个用户消息进行匹配
        if not starter.messages:
            continue
            
        first_user_item = None
        for item in starter.messages:
            if (item.get("role") == "user" and 
                item.get("type") == "message"):
                first_user_item = item
                break
        
        if not first_user_item:
            continue
            
        starter_message = first_user_item.get("content", "")
        if message.content != starter_message:
            continue
            
        # 检查并处理starter中的图片元素
        starter_elements = first_user_item.get("elements", [])
        if starter_elements and not message.elements:
            message.elements = []
            for elem_data in starter_elements:
                elem_type = elem_data.get("type", "")
                elem_url = elem_data.get("url", "")
                elem_size = elem_data.get("size", "small")
                
                if elem_type == "image" and elem_url:
                    message.elements.append(cl.Image(url=elem_url, size=elem_size))
                elif elem_type == "video" and elem_url:
                    message.elements.append(cl.Video(url=elem_url, size=elem_size))
                elif elem_type == "audio" and elem_url:
                    message.elements.append(cl.Audio(url=elem_url, size=elem_size))
            await message.update()
        
        # 处理消息，跳过第一个用户消息（已经发送过了）
        if starter.messages and len(starter.messages) > 1:
            await handle_messages(starter.messages[1:])
            return True
        # 其次使用传统的 reply_handler（向后兼容）
        elif starter.reply_handler:
            await starter.reply_handler(starter)
            return True
    
    return False