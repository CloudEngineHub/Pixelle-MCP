# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

def format_duration(duration_seconds: float) -> str:
    """
    将秒数格式化为人类友好的时间字符串
    
    Args:
        duration_seconds: 时长（秒）
        
    Returns:
        格式化后的时间字符串，如：1h23m45s, 2m30s, 1.5s, 500ms
    """
    if duration_seconds < 0:
        return "0ms"
    
    # 转换为毫秒
    total_ms = int(duration_seconds * 1000)
    
    # 如果小于1秒，显示毫秒
    if total_ms < 1000:
        return f"{total_ms}ms"
    
    # 转换为各个时间单位
    hours = int(duration_seconds // 3600)
    minutes = int((duration_seconds % 3600) // 60)
    seconds = duration_seconds % 60
    
    # 构建时间字符串
    time_parts = []
    
    if hours > 0:
        time_parts.append(f"{hours}h")
    
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    
    # 对于秒，如果有小数部分且总时长小于10秒，保留1位小数
    if seconds > 0:
        if duration_seconds < 10 and seconds != int(seconds):
            time_parts.append(f"{seconds:.1f}s")
        else:
            time_parts.append(f"{int(seconds)}s")
    
    # 如果没有任何时间部分（理论上不应该发生），返回0ms
    if not time_parts:
        return "0ms"
    
    return "".join(time_parts) 