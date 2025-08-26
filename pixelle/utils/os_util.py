# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from pathlib import Path
import pixelle
import base64
import os

def get_root_path(*paths: str) -> str:
    root_dir = str(Path(__file__).parent.parent.parent)
    return os.path.join(root_dir, *paths)

def get_data_path(*paths: str) -> str:
    return get_root_path("data", *paths)

def get_src_path(*paths: str) -> str:
    src_dir_name = Path(pixelle.__file__).parent.name
    return get_root_path(src_dir_name, *paths)

def get_temp_path(*paths: str) -> str:
    temp_path = get_root_path("temp")
    os.makedirs(temp_path, exist_ok=True)
    if paths:
        return os.path.join(temp_path, *paths)
    return temp_path

def save_base64_to_file(base64_str, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(base64_str))
