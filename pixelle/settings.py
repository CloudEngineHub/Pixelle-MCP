# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
from typing import Optional
from pydantic_settings import BaseSettings
import os

from pixelle.utils.os_util import get_root_path
from pixelle.yml_env_loader import load_yml_and_set_env

os.environ["CHAINLIT_APP_ROOT"] = get_root_path()

# Load config.yml and inject env vars
load_yml_and_set_env("base")
load_yml_and_set_env("server")
load_yml_and_set_env("client")


class Settings(BaseSettings):
    server_host: str = "localhost"
    server_port: int = 9004
    public_read_url: Optional[str] = None
    local_storage_path: str = "files"
    # 100MB
    max_file_size: int = 100 * 1024 * 1024

    def get_read_url(self) -> str:
        if self.public_read_url:
            return self.public_read_url
        return f"http://{self.server_host}:{self.server_port}"

    class ConfigDict:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局配置实例
settings = Settings()
