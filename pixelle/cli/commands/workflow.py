# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Workflow command implementation."""

import typer
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def workflow_command():
    """🔧 Display all current workflow files and tools information"""
    
    # Show current root path
    from pixelle.utils.os_util import get_pixelle_root_path, get_data_path
    current_root_path = get_pixelle_root_path()
    console.print(f"🗂️  [bold blue]Root Path:[/bold blue] {current_root_path}")
    
    # Get workflow directories
    builtin_workflows_dir = Path(current_root_path) / "workflows"
    custom_workflows_dir = Path(get_data_path("custom_workflows"))
    
    console.print(Panel(
        f"📁 [bold]Custom Workflows:[/bold] {custom_workflows_dir}",
        title="Workflow Directories",
        border_style="cyan"
    ))
    
    # Get loaded workflow manager info
    try:
        from pixelle.manager.workflow_manager import workflow_manager
        loaded_workflows = workflow_manager.loaded_workflows
        total_loaded = len(loaded_workflows)
    except Exception as e:
        console.print(f"⚠️  Cannot access workflow manager: {e}")
        loaded_workflows = {}
        total_loaded = 0
    

    
    # Loaded Tools Details Table
    if loaded_workflows:
        loaded_table = Table(title="⚡ Currently Loaded MCP Tools", show_header=True, header_style="bold blue")
        loaded_table.add_column("Tool Name", style="cyan", width=18)
        loaded_table.add_column("Parameters", style="yellow", width=22)
        loaded_table.add_column("Description", style="white", width=30)
        loaded_table.add_column("Created", style="green", width=18)
        loaded_table.add_column("Modified", style="blue", width=18)
        
        for tool_name, tool_info in loaded_workflows.items():
            metadata = tool_info.get("metadata", {})
            description = metadata.get("description", "No description")
            if not description or description == "No description":
                description = "[dim]No description[/dim]"
            else:
                # Limit description length to avoid overly tall rows
                max_length = 120  # Adjust based on column width
                if len(description) > max_length:
                    description = description[:max_length-3] + "..."
            
            # Format parameters - each parameter on a new line
            params = metadata.get("params", {})
            if params:
                param_lines = []
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "str")
                    required = param_info.get("required", False)
                    marker = "!" if required else "?"
                    param_lines.append(f"{param_name}({param_type}){marker}")
                param_display = "\n".join(param_lines)
            else:
                param_display = "No params"
            
            # Get file creation and modification timesc
            workflow_file = custom_workflows_dir / f"{tool_name}.json"
            if workflow_file.exists():
                file_stat = workflow_file.stat()
                created_time = datetime.fromtimestamp(file_stat.st_ctime).strftime("%Y-%m-%d %H:%M")
                modified_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            else:
                created_time = "Unknown"
                modified_time = "Unknown"
            
            loaded_table.add_row(tool_name, param_display, description, created_time, modified_time)
        
        console.print(loaded_table)
        
        # Simple summary
        active_tools = len(loaded_workflows)
        console.print(f"\n📊 [bold]Total Active MCP Tools:[/bold] {active_tools}")
    else:
        console.print("⚡ [yellow]No MCP tools are currently loaded[/yellow]")
    

