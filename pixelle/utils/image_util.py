# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from enum import Enum
from typing import Tuple, Literal
from PIL import Image
from utils.file_util import download_files


class AspectRatio(Enum):
    """图片宽高比枚举"""
    SQUARE = "1:1"           # 1:1 正方形
    LANDSCAPE_16_9 = "16:9"  # 16:9 横向
    PORTRAIT_9_16 = "9:16"   # 9:16 纵向
    LANDSCAPE_4_3 = "4:3"    # 4:3 横向
    PORTRAIT_3_4 = "3:4"     # 3:4 纵向
    
    @property
    def ratio_value(self) -> float:
        """获取宽高比的数值"""
        if self == AspectRatio.SQUARE:
            return 1.0
        elif self == AspectRatio.LANDSCAPE_16_9:
            return 16/9
        elif self == AspectRatio.PORTRAIT_9_16:
            return 9/16
        elif self == AspectRatio.LANDSCAPE_4_3:
            return 4/3
        elif self == AspectRatio.PORTRAIT_3_4:
            return 3/4
        return 1.0
    
    def get_dimensions(self, quality: Literal["low", "high"] = "low") -> Tuple[int, int]:
        """
        根据宽高比和质量获取具体的宽高尺寸
        
        Args:
            quality: "low" 或 "high"
            
        Returns:
            Tuple[int, int]: (width, height)
        """
        if quality == "high":
            long_side = 1024
        else:  # low quality
            long_side = 512
            
        if self in [AspectRatio.LANDSCAPE_16_9, AspectRatio.LANDSCAPE_4_3]:
            # 横向，宽度为长边
            width = long_side
            height = int(long_side / self.ratio_value)
        elif self in [AspectRatio.PORTRAIT_9_16, AspectRatio.PORTRAIT_3_4]:
            # 纵向，高度为长边
            height = long_side
            width = int(long_side * self.ratio_value)
        else:  # 正方形
            width = height = long_side
            
        return width, height


async def detect_image_aspect_ratio_enum(image_url: str) -> AspectRatio:
    """
    从图片URL检测图片的宽高比
    
    Args:
        image_url: 图片的URL
        
    Returns:
        AspectRatio: 宽高比枚举
    """
    try:
        async with download_files(image_url) as temp_file_path:
            with Image.open(temp_file_path) as img:
                width, height = img.size
                
                # 计算宽高比
                ratio = width / height
                
                # 根据比例返回对应的宽高比枚举
                if abs(ratio - 1.0) < 0.1:  # 接近正方形
                    return AspectRatio.SQUARE
                elif abs(ratio - 16/9) < 0.1:  # 接近16:9
                    return AspectRatio.LANDSCAPE_16_9
                elif abs(ratio - 9/16) < 0.1:  # 接近9:16
                    return AspectRatio.PORTRAIT_9_16
                elif abs(ratio - 4/3) < 0.1:  # 接近4:3
                    return AspectRatio.LANDSCAPE_4_3
                elif abs(ratio - 3/4) < 0.1:  # 接近3:4
                    return AspectRatio.PORTRAIT_3_4
                else:
                    # 根据宽高比判断是横向还是纵向
                    if ratio > 1:
                        return AspectRatio.LANDSCAPE_16_9  # 默认横向宽高比
                    else:
                        return AspectRatio.PORTRAIT_9_16  # 默认纵向宽高比
                        
    except Exception as e:
        # 如果检测失败，返回默认值
        return AspectRatio.SQUARE


async def detect_image_aspect_ratio(image_url: str) -> str:
    """
    从图片URL检测图片的宽高比（向后兼容函数）
    
    Args:
        image_url: 图片的URL
        
    Returns:
        str: 宽高比字符串，如 "1:1", "16:9", "9:16", "4:3", "3:4"
    """
    aspect_ratio_enum = await detect_image_aspect_ratio_enum(image_url)
    return aspect_ratio_enum.value 