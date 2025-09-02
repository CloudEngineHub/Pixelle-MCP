# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Status command implementation."""

import typer
from rich.console import Console

from pixelle.cli.utils.command_utils import detect_config_status, get_command_prefix
from pixelle.cli.utils.server_utils import check_service_status
from pixelle.cli.setup.config_saver import reload_config

console = Console()


def status_command():
    """📋 Check service status (non-interactive)"""
    
    # Show current root path
    from pixelle.utils.os_util import get_pixelle_root_path
    current_root_path = get_pixelle_root_path()
    console.print(f"🗂️  [bold blue]Root Path:[/bold blue] {current_root_path}")
    
    # Check configuration first
    config_status = detect_config_status()
    
    # Get command prefix for error messages
    cmd_prefix = get_command_prefix()
    
    if config_status == "first_time":
        console.print("❌ [bold red]No configuration found![/bold red]")
        console.print(f"💡 Please run [bold]{cmd_prefix} reconfig[/bold] to configure first")
        raise typer.Exit(1)
    elif config_status == "incomplete":
        console.print("❌ [bold red]Configuration is incomplete![/bold red]")
        console.print(f"💡 Please run [bold]{cmd_prefix} reconfig[/bold] to fix configuration")
        raise typer.Exit(1)
    
    # Reload config to ensure we have latest settings
    reload_config()
    
    # Check service status
    check_service_status()
