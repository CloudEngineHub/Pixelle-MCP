# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Welcome and initial setup detection for interactive mode."""

from rich.console import Console

from pixelle.cli.utils.display import show_welcome
from pixelle.cli.utils.command_utils import detect_config_status

console = Console()


def run_interactive_mode():
    """Run interactive mode with welcome message and menu"""
    # Show welcome message
    show_welcome()
    
    # Detect config status
    config_status = detect_config_status()
    
    if config_status == "first_time":
        # First time use: full setup wizard + start
        console.print("\n🎯 [bold blue]Detect this is your first time using Pixelle MCP![/bold blue]")
        console.print("We will guide you through a simple configuration process...\n")
        
        import questionary
        if questionary.confirm("Start configuration wizard?", default=True, instruction="(Y/n)").ask():
            from pixelle.cli.interactive.wizard import run_full_setup_wizard
            run_full_setup_wizard()
        else:
            console.print("❌ Configuration cancelled. You can always run [bold]pixelle[/bold] to configure.")
            return
            
    elif config_status == "incomplete":
        # Config is incomplete: guide user to handle
        console.print("\n⚠️  [bold yellow]Detect config file exists but is incomplete[/bold yellow]")
        console.print("💡 Suggest to re-run configuration or manually edit config file")
        from pixelle.cli.interactive.menu import show_main_menu
        show_main_menu()
        
    else:
        # Config is complete: show main menu
        from pixelle.cli.interactive.menu import show_main_menu
        show_main_menu()
