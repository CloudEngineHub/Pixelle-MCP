# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Server management utility functions."""

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pixelle.settings import settings
from pixelle.utils.process_util import (
    check_port_in_use,
    get_process_using_port,
    kill_process_on_port,
)
from pixelle.utils.network_util import (
    check_mcp_streamable,
    test_comfyui_connection,
    check_url_status,
)

console = Console()


def start_pixelle_server():
    """Start Pixelle server"""
    console.print("\n🚀 [bold]Starting Pixelle MCP...[/bold]")
    
    try:
        # Reload environment variables
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        port = int(settings.port)
        
        # Check if port is in use
        if check_port_in_use(port):
            process_info = get_process_using_port(port)
            if process_info:
                console.print(f"⚠️  [bold yellow]Port {port} is in use[/bold yellow]")
                console.print(f"Occupied process: {process_info}")
                
                kill_service = questionary.confirm(
                    "Terminate existing service and restart?",
                    default=True,
                    instruction="(Y/n)"
                ).ask()
                
                if kill_service:
                    console.print("🔄 Terminating existing service...")
                    if kill_process_on_port(port):
                        console.print("✅ Existing service terminated")
                        import time
                        time.sleep(1)  # Wait for port to be released
                    else:
                        console.print("❌ Cannot terminate existing service, launch may fail")
                        proceed = questionary.confirm(
                            "Still try to launch?",
                            default=False,
                            instruction="(y/N)"
                        ).ask()
                        if not proceed:
                            console.print("❌ Launch cancelled")
                            return
                else:
                    console.print("❌ Launch cancelled")
                    return
            else:
                console.print(f"⚠️  [bold yellow]Port {port} is in use, but cannot determine the occupied process[/bold yellow]")
                console.print("Launch may fail, suggest changing port or manually handle")
        
        # Start service
        console.print(Panel(
            f"🌐 Web interface: http://localhost:{settings.port}/\n"
            f"🔌 MCP endpoint: http://localhost:{settings.port}/pixelle/mcp\n"
            f"📁 Loaded workflow directory: data/custom_workflows/",
            title="🎉 Pixelle MCP is running!",
            border_style="green"
        ))
        
        console.print("\nPress [bold]Ctrl+C[/bold] to stop service\n")
        
        # Import and start main
        from pixelle.main import main as start_main
        start_main()
        
    except KeyboardInterrupt:
        console.print("\n👋 Pixelle MCP stopped")
    except Exception as e:
        console.print(f"❌ Launch failed: {e}")


def check_service_status():
    """Check service status"""
    console.print(Panel(
        "📋 [bold]Check service status[/bold]\n\n"
        "Checking the status of all services...",
        title="Service status check",
        border_style="cyan"
    ))
    
    import requests
    
    # Create status table
    status_table = Table(title="Service status", show_header=True, header_style="bold cyan")
    status_table.add_column("Service", style="cyan", width=20)
    status_table.add_column("Address", style="yellow", width=40)
    status_table.add_column("Status", width=15)
    status_table.add_column("Description", style="white")
    
    # Check MCP endpoint
    pixelle_url = f"http://{settings.host}:{settings.port}"
    pixelle_mcp_server_url = f"{pixelle_url}/pixelle/mcp"
    mcp_status = check_mcp_streamable(pixelle_mcp_server_url)
    status_table.add_row(
        "MCP endpoint",
        pixelle_mcp_server_url,
        "🟢 Available" if mcp_status else "🔴 Unavailable",
        "MCP protocol endpoint" if mcp_status else "Please start the service first"
    )
    
    # Check Web interface
    web_status = check_url_status(pixelle_url)
    status_table.add_row(
        "Web interface",
        pixelle_url,
        "🟢 Available" if web_status else "🔴 Unavailable",
        "Chat interface" if web_status else "Please start the service first"
    )
    
    # Check ComfyUI
    comfyui_status = test_comfyui_connection(settings.comfyui_base_url)
    status_table.add_row(
        "ComfyUI",
        settings.comfyui_base_url,
        "🟢 Connected" if comfyui_status else "🔴 Connection failed",
        "Workflow execution engine" if comfyui_status else "Please check if ComfyUI is running"
    )
    
    console.print(status_table)
    
    # Show LLM configuration status
    providers = settings.get_configured_llm_providers()
    if providers:
        console.print(f"\n🤖 [bold]LLM providers:[/bold] {', '.join(providers)} ({len(providers)} providers)")
        models = settings.get_all_available_models()
        console.print(f"📋 [bold]Available models:[/bold] {len(models)} models")
        console.print(f"⭐ [bold]Default model:[/bold] {settings.chainlit_chat_default_model}")
    else:
        console.print("\n⚠️  [bold yellow]Warning:[/bold yellow] No LLM providers configured")
    
    # Summary
    total_services = 3  # MCP, Web, ComfyUI
    running_services = sum([mcp_status, web_status, comfyui_status])
    
    if running_services == total_services:
        console.print("\n✅ [bold green]All services are running normally![/bold green]")
    else:
        console.print(f"\n⚠️  [bold yellow]{running_services}/{total_services} services are running normally[/bold yellow]")
        console.print("💡 If any service is not running, please check the configuration or restart the service")
