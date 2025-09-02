# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Command-line utility functions."""

from pathlib import Path
from rich.console import Console

console = Console()


def get_command_prefix():
    """Get the correct command prefix based on how the script was invoked"""
    import sys
    script_name = sys.argv[0]
    
    if "uvx" in script_name or "pixelle-mcp" in script_name:
        return "uvx pixelle-mcp@latest"
    elif script_name.endswith("cli.py"):
        return f"python {script_name}"
    elif "__main__.py" in script_name or "-m" in sys.argv:
        return "python -m pixelle.cli"
    else:
        return "pixelle"


def detect_config_status() -> str:
    """Detect current config status"""
    from pixelle.utils.os_util import get_pixelle_root_path
    pixelle_root = get_pixelle_root_path()
    env_file = Path(pixelle_root) / ".env"
    
    if not env_file.exists():
        return "first_time"
    
    # Check required configs
    required_configs = [
        "COMFYUI_BASE_URL",
        # At least one LLM config is required
        ("OPENAI_API_KEY", "OLLAMA_BASE_URL", "GEMINI_API_KEY", "DEEPSEEK_API_KEY", "CLAUDE_API_KEY", "QWEN_API_KEY")
    ]
    
    env_vars = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"\'')
    
    # Check ComfyUI config
    if "COMFYUI_BASE_URL" not in env_vars or not env_vars["COMFYUI_BASE_URL"]:
        return "incomplete"
    
    # Check if at least one LLM config is present
    llm_configs = required_configs[1]
    has_llm = any(key in env_vars and env_vars[key] for key in llm_configs)
    if not has_llm:
        return "incomplete"
    
    return "complete"
