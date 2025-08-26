# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
from typing import Optional
from pydantic_settings import BaseSettings

from pixelle.yml_env_loader import load_yml_and_set_env

# 优先加载config.yml并注入环境变量
load_yml_and_set_env("base")
load_yml_and_set_env("server")
load_yml_and_set_env("client")


class Settings(BaseSettings):
    # 服务基础配置
    server_host: str = "localhost"
    server_port: int = 9004
    public_read_url: Optional[str] = None  # 公开访问的URL，用于文件访问
    local_storage_path: str = "files"
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    def get_read_url(self) -> str:
        """获取基础URL，优先使用PUBLIC_READ_URL，否则根据host:port构建"""
        if self.public_read_url:
            return self.public_read_url
        return f"http://{self.server_host}:{self.server_port}"

    class ConfigDict:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局配置实例
settings = Settings()
