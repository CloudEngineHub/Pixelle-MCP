# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).
from typing import Optional
from pydantic_settings import BaseSettings
import os

from pixelle.utils.os_util import get_root_path
from pixelle.yml_env_loader import load_yml_and_set_env


# Load config.yml and inject env vars
load_yml_and_set_env("base")
load_yml_and_set_env("server")
load_yml_and_set_env("client")


class Settings(BaseSettings):
    host: str = "localhost"
    port: int = 9004
    public_read_url: Optional[str] = None
    local_storage_path: str = "files"

    def get_read_url(self) -> str:
        if self.public_read_url:
            return self.public_read_url
        return f"http://{self.host}:{self.server_port}"

    class ConfigDict:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()

# Extra env vars
os.environ["CHAINLIT_APP_ROOT"] = get_root_path()
os.environ["CHAINLIT_HOST"] = str(settings.host)
os.environ["CHAINLIT_PORT"] = str(settings.port)
