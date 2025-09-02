# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Manual command implementation."""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from pixelle.cli.utils.command_utils import get_command_prefix

console = Console()


def manual_command():
    """📝 Show manual configuration guide (non-interactive)"""
    
    # Show current root path
    from pixelle.utils.os_util import get_pixelle_root_path
    current_root_path = get_pixelle_root_path()
    console.print(f"🗂️  [bold blue]Root Path:[/bold blue] {current_root_path}")
    
    # Show configuration file path and instructions
    pixelle_root = get_pixelle_root_path()
    env_path = Path(pixelle_root) / ".env"
    
    # Get command prefix for messages
    cmd_prefix = get_command_prefix()
    
    console.print(Panel(
        "✏️ [bold]Manual edit configuration[/bold]\n\n"
        "Configuration file contains detailed comments, you can directly edit to customize the configuration.\n"
        f"Configuration file location: {env_path.absolute()}\n\n"
        f"💡 If you need to completely reconfigure, delete the .env file and run '{cmd_prefix} reconfig'\n"
        f"💡 After editing, run '{cmd_prefix} status' to check configuration",
        title="Manual configuration guide",
        border_style="green"
    ))
    
    if not env_path.exists():
        console.print("\n⚠️  [bold yellow]Configuration file does not exist![/bold yellow]")
        console.print(f"💡 Please run [bold]{cmd_prefix} reconfig[/bold] first to create the configuration")
        raise typer.Exit(1)
    
    console.print("\n📝 Common configuration modifications:")
    console.print("• Change port: modify PORT=9004")
    console.print("• Add new LLM: configure the corresponding API_KEY")
    console.print("• Disable LLM: delete or clear the corresponding API_KEY")
    console.print("• Change ComfyUI: modify COMFYUI_BASE_URL")
    
    console.print(f"\n📁 [bold]Configuration file path:[/bold] {env_path.absolute()}")
