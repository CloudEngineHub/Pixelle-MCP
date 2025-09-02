# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""Main entry point for Pixelle CLI."""

import typer

from pixelle.cli.commands.interactive import interactive_command
from pixelle.cli.commands.start import start_command
from pixelle.cli.commands.init import init_command
from pixelle.cli.commands.edit import edit_command
from pixelle.cli.commands.help import help_command
from pixelle.cli.commands.workflow import workflow_command
from pixelle.cli.commands.dev import dev_command
from pixelle.cli.interactive.welcome import run_interactive_mode

# Create typer app
app = typer.Typer(add_completion=False, help="🎨 Pixelle MCP - A simple solution to convert ComfyUI workflow to MCP tool")

# Add commands
app.command("interactive", hidden=False)(interactive_command)
app.command("start")(start_command)
app.command("init")(init_command)
app.command("edit")(edit_command)
app.command("help")(help_command)
app.command("workflow")(workflow_command)
app.command("dev")(dev_command)


def main():
    """Main entry point - detect if running interactively or with command args"""
    import sys
    
    # If no command-line arguments (except script name), run interactive mode
    if len(sys.argv) == 1:
        # Run interactive mode directly
        run_interactive_mode()
    else:
        # Let typer handle command parsing
        app()


if __name__ == "__main__":
    main()
