# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Interactive command implementation."""

from rich.console import Console

from pixelle.cli.interactive.welcome import run_interactive_mode

console = Console()


def interactive_command():
    """🎨 Run in interactive mode (default when no command specified)"""
    
    # Always show current root path for debugging
    from pixelle.utils.os_util import get_pixelle_root_path
    current_root_path = get_pixelle_root_path()
    console.print(f"🗂️  [bold blue]Root Path:[/bold blue] {current_root_path}")
    
    # Run interactive mode
    run_interactive_mode()
