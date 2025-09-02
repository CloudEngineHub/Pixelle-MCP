# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Main menu for interactive mode."""

import questionary
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from pixelle.cli.utils.display import show_current_config, show_help
from pixelle.cli.utils.server_utils import start_pixelle_server, check_service_status
from pixelle.cli.interactive.wizard import run_fresh_setup_wizard

console = Console()


def show_main_menu():
    """Show main menu"""
    console.print("\n📋 [bold]Current configuration status[/bold]")
    show_current_config()
    
    action = questionary.select(
        "Please select the action to perform:",
        choices=[
            questionary.Choice("🚀 [start] Start Pixelle MCP", "start"),
            questionary.Choice("🔄 [init] Initialize/reconfigure Pixelle MCP", "init"),
            questionary.Choice("📝 [edit] Edit configuration", "edit"),
            questionary.Choice("🔧 [workflow] View workflow information", "workflow"),
            questionary.Choice("🐛 [dev] Development & system status", "dev"),
            questionary.Choice("❓ [help] Help", "help"),
            questionary.Choice("❌ Exit", "exit")
        ]
    ).ask()
    
    if action == "start":
        start_pixelle_server()
    elif action == "init":
        run_fresh_setup_wizard()
    elif action == "edit":
        guide_edit_config()
    elif action == "workflow":
        from pixelle.cli.commands.workflow import workflow_command
        workflow_command()
    elif action == "dev":
        from pixelle.cli.commands.dev import dev_command
        dev_command()
    elif action == "help":
        show_help()
    elif action == "exit":
        console.print("👋 Goodbye!")
    else:
        console.print(f"Feature {action} is under development...")


def guide_edit_config():
    """Guide user to edit configuration"""
    console.print(Panel(
        "✏️ [bold]Manual edit configuration[/bold]\n\n"
        "Configuration file contains detailed comments, you can directly edit to customize the configuration.\n"
        "Configuration file location: .env\n\n"
        "💡 If you need to completely reconfigure, delete the .env file and rerun 'pixelle'\n"
        "💡 After editing, rerun 'pixelle' to apply the configuration",
        title="Manual configuration guide",
        border_style="green"
    ))
    
    # Show current configuration file path
    from pixelle.utils.os_util import get_pixelle_root_path
    pixelle_root = get_pixelle_root_path()
    env_path = Path(pixelle_root) / ".env"
    console.print(f"📁 Configuration file path: {env_path.absolute()}")
    
    if not env_path.exists():
        console.print("\n⚠️  Configuration file does not exist!")
        console.print("💡 Please run the interactive guide first: select '🔄 Reconfigure Pixelle MCP' from the menu")
        console.print("💡 Or exit and rerun [bold cyan]pixelle[/bold cyan] for initial configuration")
        return
    
    # Provide some common editors suggestions
    console.print("\n💡 Recommended editors:")
    console.print("• VS Code: [bold cyan]code .env[/bold cyan]")
    console.print("• Nano: [bold cyan]nano .env[/bold cyan]") 
    console.print("• Vim: [bold cyan]vim .env[/bold cyan]")
    console.print("• Or any text editor")
    
    console.print("\n📝 Common configuration modifications:")
    console.print("• Change port: modify PORT=9004")
    console.print("• Add new LLM: configure the corresponding API_KEY")
    console.print("• Disable LLM: delete or clear the corresponding API_KEY")
    console.print("• Change ComfyUI: modify COMFYUI_BASE_URL")
    
    # Ask if open file
    if questionary.confirm("Open configuration file in default editor?", default=True, instruction="(Y/n)").ask():
        try:
            import subprocess
            import platform
            
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(env_path)])
            elif platform.system() == "Windows":
                subprocess.run(["notepad", str(env_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(env_path)])
                
            console.print("✅ Configuration file opened in default editor")
        except Exception as e:
            console.print(f"❌ Cannot open automatically: {e}")
            console.print("💡 Please manually edit the file")
    
    console.print("\n📋 After configuration, rerun [bold cyan]pixelle[/bold cyan] to apply the configuration")
    console.print("🗑️  If you need to completely reconfigure, delete the .env file and rerun [bold cyan]pixelle[/bold cyan]")
