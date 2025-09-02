# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Start command implementation."""

import typer
from rich.console import Console

from pixelle.cli.utils.command_utils import detect_config_status, get_command_prefix
from pixelle.cli.utils.server_utils import start_pixelle_server

console = Console()


def start_command():
    """🚀 Start Pixelle MCP server directly (non-interactive)"""
    
    # Show current root path
    from pixelle.utils.os_util import get_pixelle_root_path
    current_root_path = get_pixelle_root_path()
    console.print(f"🗂️  [bold blue]Root Path:[/bold blue] {current_root_path}")
    
    # Check if configuration exists
    config_status = detect_config_status()
    
    # Get command prefix for error messages
    cmd_prefix = get_command_prefix()
    
    if config_status == "first_time":
        console.print("❌ [bold red]No configuration found![/bold red]")
        console.print(f"💡 Please run [bold]{cmd_prefix} reconfig[/bold] to configure first")
        console.print(f"💡 Or run [bold]{cmd_prefix}[/bold] for interactive setup")
        raise typer.Exit(1)
    elif config_status == "incomplete":
        console.print("❌ [bold red]Configuration is incomplete![/bold red]")
        console.print(f"💡 Please run [bold]{cmd_prefix} reconfig[/bold] to fix configuration")
        console.print(f"💡 Or run [bold]{cmd_prefix} manual[/bold] to edit manually")
        raise typer.Exit(1)
    
    # Start server directly
    start_pixelle_server()
