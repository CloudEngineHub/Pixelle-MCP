# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from pathlib import Path
import base64
import os

def get_root_path(*paths: str) -> str:
    root_dir = str(Path(__file__).parent.parent.parent)
    return os.path.join(root_dir, *paths)

def get_data_path(*paths: str) -> str:
    return get_root_path("data", *paths)

def save_base64_to_file(base64_str, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(base64_str))
