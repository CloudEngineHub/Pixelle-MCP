# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Service configuration setup."""

from typing import Dict, Optional
import questionary
from rich.console import Console
from rich.panel import Panel



console = Console()


def setup_service_config() -> Optional[Dict]:
    """Configure service options - Step 3"""
    console.print(Panel(
        "⚙️ [bold]Service configuration[/bold]\n\n"
        "Configure Pixelle MCP service options, including port, host address, etc.",
        title="Step 3/4: Service configuration",
        border_style="yellow"
    ))
    
    default_port = "9004"
    port = questionary.text(
        "Service port:",
        default=default_port,
        instruction="(press Enter to use default port 9004, or input other port)"
    ).ask()
    
    if not port:
        port = default_port
    
    console.print(f"✅ Service will start on port {port}")
    
    # Configure host address
    console.print("\n📡 [bold yellow]Host address configuration[/bold yellow]")
    console.print("🔍 [dim]Host address determines the network interface the service listens on:[/dim]")
    console.print("   • [green]localhost[/green] - Only accessible from this machine (recommended for local development)")
    console.print("   • [yellow]0.0.0.0[/yellow] - Allows external access (used for server deployment or LAN sharing)")
    console.print("\n⚠️  [bold red]Security tips:[/bold red]")
    console.print("   When using 0.0.0.0, please ensure:")
    console.print("   1. Firewall rules are configured")
    console.print("   2. Running in a trusted network environment")
    
    default_host = "localhost"
    host = questionary.text(
        "Host address:",
        default=default_host
    ).ask()
    
    if not host:
        host = default_host
    
    if host == "0.0.0.0":
        console.print("⚠️  [bold yellow]External access is enabled, please ensure network security![/bold yellow]")
    else:
        console.print(f"✅ Service will listen on {host}")
    
    return {
        "port": port,
        "host": host,
    }
