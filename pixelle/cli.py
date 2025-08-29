# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path
from typing import Dict, List, Optional

from pixelle.settings import settings
from pixelle.utils.network_util import (
    check_mcp_streamable,
    test_comfyui_connection,
    test_ollama_connection,
    get_openai_models,
    get_ollama_models,
    check_url_status,
)
from pixelle.utils.process_util import (
    check_port_in_use,
    get_process_using_port,
    kill_process_on_port,
)
from pixelle.utils.config_util import (
    build_env_lines,
)
from pixelle.utils.os_util import set_root_path


app = typer.Typer(add_completion=False, help="🎨 Pixelle MCP - A simple solution to convert ComfyUI workflow to MCP tool")
console = Console()


def main(
    root_path: Optional[str] = typer.Option(
        None, 
        "--root-path", 
        help="Root path for Pixelle MCP (default: ~/.pixelle)"
    )
):
    """🎨 Pixelle MCP - A simple tool to convert ComfyUI workflow to MCP tool"""
    
    # Set root path if provided
    if root_path and isinstance(root_path, str):
        set_root_path(root_path)
    
    # Always show current root path for debugging
    from pixelle.utils.os_util import get_pixelle_root_path
    current_root_path = get_pixelle_root_path()
    console.print(f"🗂️  [bold blue]Root Path:[/bold blue] {current_root_path}")
    
    # Show welcome message
    show_welcome()
    
    # Detect config status
    config_status = detect_config_status()
    
    if config_status == "first_time":
        # First time use: full setup wizard + start
        console.print("\n🎯 [bold blue]Detect this is your first time using Pixelle MCP![/bold blue]")
        console.print("We will guide you through a simple configuration process...\n")
        
        if questionary.confirm("Start configuration wizard?", default=True, instruction="(Y/n)").ask():
            run_full_setup_wizard()
        else:
            console.print("❌ Configuration cancelled. You can always run [bold]pixelle[/bold] to configure.")
            return
            
    elif config_status == "incomplete":
        # Config is incomplete: guide user to handle
        console.print("\n⚠️  [bold yellow]Detect config file exists but is incomplete[/bold yellow]")
        console.print("💡 Suggest to re-run configuration or manually edit config file")
        show_main_menu()
        
    else:
        # Config is complete: show main menu
        show_main_menu()


def show_welcome():
    """Show welcome message"""
    welcome_text = """
🎨 [bold blue]Pixelle MCP 2.0[/bold blue]
A simple solution to convert ComfyUI workflow to MCP tool

✨ 30 seconds from zero to AI assistant
🔧 Zero code to convert workflow to MCP tool  
🌐 Support Cursor, Claude Desktop, etc. MCP clients
🤖 Support multiple mainstream LLMs (OpenAI, Ollama, Gemini, etc.)
"""
    
    console.print(Panel(
        welcome_text,
        title="Welcome to Pixelle MCP",
        border_style="blue",
        padding=(1, 2)
    ))


def detect_config_status() -> str:
    """Detect current config status"""
    from pixelle.utils.os_util import get_pixelle_root_path
    pixelle_root = get_pixelle_root_path()
    env_file = Path(pixelle_root) / ".env"
    
    if not env_file.exists():
        return "first_time"
    
    # Check required configs
    required_configs = [
        "COMFYUI_BASE_URL",
        # At least one LLM config is required
        ("OPENAI_API_KEY", "OLLAMA_BASE_URL", "GEMINI_API_KEY", "DEEPSEEK_API_KEY", "CLAUDE_API_KEY", "QWEN_API_KEY")
    ]
    
    env_vars = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"\'')
    
    # Check ComfyUI config
    if "COMFYUI_BASE_URL" not in env_vars or not env_vars["COMFYUI_BASE_URL"]:
        return "incomplete"
    
    # Check if at least one LLM config is present
    llm_configs = required_configs[1]
    has_llm = any(key in env_vars and env_vars[key] for key in llm_configs)
    if not has_llm:
        return "incomplete"
    
    return "complete"


def run_full_setup_wizard():
    """Run full setup wizard"""
    console.print("\n🚀 [bold]Start Pixelle MCP configuration wizard[/bold]\n")
    
    try:
        # Step 1: ComfyUI config
        comfyui_config = setup_comfyui()
        if not comfyui_config:
            console.print("⚠️  ComfyUI config skipped, using default config")
            comfyui_config = {"url": "http://localhost:8188"}  # Use default value
        
        # Step 2: LLM config (can be configured multiple)
        llm_configs = setup_multiple_llm_providers()
        if not llm_configs:
            console.print("❌ At least one LLM provider is required")
            return
        
        # Step 3: Select default model (based on selected providers and models)
        all_models = collect_all_selected_models(llm_configs)
        selected_default_model = select_default_model_interactively(all_models)

        # Step 4: Service config
        service_config = setup_service_config()
        if not service_config:
            console.print("⚠️  Service config skipped, using default config")
            service_config = {"port": "9004", "enable_web": True}  # Use default value
        
        # Step 5: Save config
        save_unified_config(comfyui_config, llm_configs, service_config, selected_default_model)
        
        # Step 6: Ask to start immediately
        console.print("\n✅ [bold green]Configuration completed![/bold green]")
        if questionary.confirm("Start Pixelle MCP immediately?", default=True, instruction="(Y/n)").ask():
            start_pixelle_server()
            
    except KeyboardInterrupt:
        console.print("\n\n❌ Configuration cancelled (Ctrl+C pressed)")
        console.print("💡 You can always run [bold]pixelle[/bold] to configure")
    except Exception as e:
        console.print(f"\n❌ Error during configuration: {e}")
        console.print("💡 You can always run [bold]pixelle[/bold] to try again")


def setup_comfyui(default_url: str = None):
    """Setup ComfyUI - Step 1"""
    console.print(Panel(
        "🧩 [bold]ComfyUI configuration[/bold]\n\n"
        "Pixelle MCP needs to connect to your ComfyUI service to execute workflows.\n"
        "ComfyUI is a powerful AI workflow editor, if you haven't installed it yet,\n"
        "please visit: https://github.com/comfyanonymous/ComfyUI",
        title="Step 1/4: ComfyUI configuration",
        border_style="blue"
    ))
    
    # Manual config
    console.print("\n📝 Please configure ComfyUI service address")
    console.print("💡 If you choose 'n', you can input custom address")
    
    # Use default value or code default value
    final_default_url = default_url or "http://localhost:8188"
    use_default = questionary.confirm(
        f"Use default address {final_default_url}?",
        default=True,
        instruction="(Y/n)"
    ).ask()
    
    if use_default:
        url = final_default_url
        console.print(f"✅ Using default address: {url}")
    else:
        url = questionary.text(
            "Please input custom ComfyUI address:",
            instruction="(e.g. http://192.168.1.100:8188)"
        ).ask()
    
    if not url:
        return None
    
    # Test connection
    console.print(f"🔌 Testing connection to {url}...")
    if test_comfyui_connection(url):
        console.print("✅ [bold green]ComfyUI connection successful![/bold green]")
        return {"url": url}
    else:
        console.print("❌ [bold red]Cannot connect to ComfyUI[/bold red]")
        console.print("Please check:")
        console.print("1. Whether ComfyUI is running")
        console.print("2. Whether the address is correct")
        console.print("3. Whether the network is available")
        
        # Ask if skip test
        skip_test = questionary.confirm(
            "Skip connection test?",
            default=True,
            instruction="(Y/n, skip will directly use the address you entered)"
        ).ask()
        
        if skip_test:
            console.print(f"⏭️  Skipped connection test, using address: {url}")
            return {"url": url}
        else:
            # Re-test, but keep the user's input address
            return setup_comfyui(url)


def setup_multiple_llm_providers():
    """Setup multiple LLM providers - Step 2"""
    console.print(Panel(
        "🤖 [bold]LLM provider configuration[/bold]\n\n"
        "Pixelle MCP supports multiple LLM providers, you can configure one or more.\n"
        "The benefits of configuring multiple providers:\n"
        "• Can use different models in different scenarios\n"
        "• Provide backup solutions, improve service availability\n"
        "• Some models perform better on specific tasks",
        title="Step 2/4: LLM provider configuration",
        border_style="green"
    ))
    
    configured_providers = []
    
    while True:
        # Show available providers
        available_providers = [
            questionary.Choice("🔥 OpenAI (recommended) - GPT-4, GPT-3.5, etc.", "openai"),
            questionary.Choice("🏠 Ollama (local) - Free local model", "ollama"),
            questionary.Choice("💎 Google Gemini - Google latest model", "gemini"),
            questionary.Choice("🚀 DeepSeek - High-performance code model", "deepseek"),
            questionary.Choice("🤖 Claude - Anthropic's powerful model", "claude"),
            questionary.Choice("🌟 Qwen - Alibaba Tongyi Qwen", "qwen"),
        ]
        
        # Filter configured providers
        remaining_providers = [p for p in available_providers 
                             if p.value not in [cp["provider"] for cp in configured_providers]]
        
        if not remaining_providers:
            console.print("✅ All available LLM providers are configured, automatically enter next step")
            break
        
        # Show currently configured providers
        if configured_providers:
            console.print("\n📋 [bold]Configured providers:[/bold]")
            for provider in configured_providers:
                console.print(f"  ✅ {provider['provider'].title()}")
        
        # Select provider to configure
        if configured_providers:
            remaining_providers.append(questionary.Choice("🏁 Complete configuration", "done"))
        
        # Always add exit option
        remaining_providers.append(questionary.Choice("❌ Cancel configuration", "cancel"))
        
        provider = questionary.select(
            "Select LLM provider to configure:" if not configured_providers else "Select LLM provider to continue configuration:",
            choices=remaining_providers
        ).ask()
        
        if provider == "cancel":
            if questionary.confirm("Are you sure you want to cancel configuration?", default=False, instruction="(y/N)").ask():
                console.print("❌ Configuration cancelled")
                return None
            else:
                continue  # Continue configuration loop
        
        if provider == "done":
            break
        
        # Configure specific provider
        provider_config = configure_specific_llm(provider)
        if provider_config:
            configured_providers.append(provider_config)
            
            # Show selected models
            models = provider_config.get('models', '')
            if models:
                model_list = [m.strip() for m in models.split(',')]
                model_display = '、'.join(model_list)
                console.print(f"✅ [bold green]{provider.title()} configuration successful![/bold green]")
                console.print(f"📋 You selected {model_display} model\n")
            else:
                console.print(f"✅ [bold green]{provider.title()} configuration successful![/bold green]\n")
        
        if not configured_providers:
            console.print("⚠️  At least one LLM provider is required to continue")
        else:
            # Check if there are any remaining providers to configure
            # remaining_providers has already filtered out configured providers, and will add "done" and "cancel" options
            actual_remaining = len([p for p in remaining_providers if p.value not in ["done", "cancel"]])
            if actual_remaining > 0:
                if not questionary.confirm("Continue configuring other LLM providers?", default=False, instruction="(y/N)").ask():
                    break
            else:
                # All providers are configured, automatically enter next step
                break
    
    return configured_providers


def configure_specific_llm(provider: str) -> Optional[Dict]:
    """Configure specific LLM provider"""
    
    if provider == "openai":
        return configure_openai()
    elif provider == "ollama":
        return configure_ollama()
    elif provider == "gemini":
        return configure_gemini()
    elif provider == "deepseek":
        return configure_deepseek()
    elif provider == "claude":
        return configure_claude()
    elif provider == "qwen":
        return configure_qwen()
    
    return None


def configure_openai() -> Optional[Dict]:
    """Configure OpenAI"""
    console.print("\n🔥 [bold]Configure OpenAI compatible interface[/bold]")
    console.print("Support OpenAI official and all compatible OpenAI SDK providers")
    console.print("Including but not limited to: OpenAI, Azure OpenAI, various third-party proxy services, etc.")
    console.print("Get OpenAI official API Key: https://platform.openai.com/api-keys\n")
    
    api_key = questionary.password("Please input your OpenAI API Key:").ask()
    if not api_key:
        return None
    
    console.print("💡 If you use proxy or third-party service, select 'n' to input custom address")
    default_base_url = "https://api.openai.com/v1"
    use_default_url = questionary.confirm(
        f"Use default API address {default_base_url}?",
        default=True,
        instruction="(Y/n)"
    ).ask()
    
    if use_default_url:
        base_url = default_base_url
        console.print(f"✅ Using default address: {base_url}")
    else:
        base_url = questionary.text(
            "Please input custom API address:",
            instruction="(e.g. https://your-proxy.com/v1)"
        ).ask()
    
    # Try to get model list
    console.print("🔍 Getting available model list...")
    available_models = get_openai_models(api_key, base_url)
    
    if available_models:
        console.print(f"📋 Found {len(available_models)} available models")
        
        # Pre-select recommended models
        recommended_models = []
        for model in ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]:
            if model in available_models:
                recommended_models.append(model)
        
        if recommended_models:
            console.print(f"💡 Pre-selected recommended models: {', '.join(recommended_models)}")
        
        # Directly provide multi-select interface
        # Create choices list, and mark recommended models as default selected
        choices = []
        for model in available_models:
            if model in recommended_models:
                choices.append(questionary.Choice(f"{model} (recommended)", model, checked=True))
            else:
                choices.append(questionary.Choice(model, model, checked=False))
        
        selected_models = questionary.checkbox(
            "Please select the model to use (space to select/cancel, enter to confirm):",
            choices=choices,
            instruction="Use arrow keys to navigate, space to select/cancel, enter to confirm"
        ).ask()
        
        if selected_models:
            models = ",".join(selected_models)
            console.print(f"✅ Selected models: {models}")
        else:
            console.print("⚠️  No models selected, using manual input")
            models = questionary.text(
                "Please input custom models:",
                instruction="(Separate multiple models with commas)"
            ).ask()
    else:
        console.print("⚠️  Cannot get model list, using default config")
        default_models = "gpt-4o-mini,gpt-4o"
        use_default_models = questionary.confirm(
            f"Use default recommended models {default_models}?",
            default=True,
            instruction="(Y/n)"
        ).ask()
        
        if use_default_models:
            models = default_models
            console.print(f"✅ Using default models: {models}")
        else:
            models = questionary.text(
                "Please input custom models:",
                instruction="(multiple models separated by commas, e.g. gpt-4,gpt-3.5-turbo)"
            ).ask()
    
    return {
        "provider": "openai",
        "api_key": api_key,
        "base_url": base_url,
        "models": models
    }


def configure_ollama() -> Optional[Dict]:
    """Configure Ollama"""
    console.print("\n🏠 [bold]Configure Ollama (local model)[/bold]")
    console.print("Ollama can run open-source models locally, completely free and data does not leave the machine")
    console.print("Install Ollama: https://ollama.ai\n")
    
    console.print("💡 If Ollama is running on other address, select 'n' to input custom address")
    default_base_url = "http://localhost:11434/v1"
    use_default_url = questionary.confirm(
        f"Use default Ollama address {default_base_url}?",
        default=True,
        instruction="(Y/n)"
    ).ask()
    
    if use_default_url:
        base_url = default_base_url
        console.print(f"✅ Using default address: {base_url}")
    else:
        base_url = questionary.text(
            "Please input custom Ollama address:",
            instruction="(e.g. http://192.168.1.100:11434/v1)"
        ).ask()
    
    # Test connection
    console.print("🔌 Testing Ollama connection...")
    if test_ollama_connection(base_url):
        console.print("✅ Ollama connection successful")
        
        # Get available models
        models = get_ollama_models(base_url)
        if models:
            console.print(f"📋 Found {len(models)} available models")
            selected_models = questionary.checkbox(
                "Please select the model to use:",
                choices=[questionary.Choice(model, model) for model in models]
            ).ask()
            
            if selected_models:
                return {
                    "provider": "ollama", 
                    "base_url": base_url,
                    "models": ",".join(selected_models)
                }
        else:
            console.print("⚠️  No available models found, you may need to download models first")
            console.print("e.g. ollama pull llama2")
            
            models = questionary.text(
                "Please manually specify models:",
                instruction="(multiple models separated by commas)"
            ).ask()
            
            if models:
                return {
                    "provider": "ollama",
                    "base_url": base_url, 
                    "models": models
                }
    else:
        console.print("❌ Cannot connect to Ollama")
        console.print("Please ensure Ollama is running")
        
    return None


def configure_gemini() -> Optional[Dict]:
    """Configure Gemini"""
    console.print("\n💎 [bold]Configure Google Gemini[/bold]")
    console.print("Google Gemini is the latest large language model from Google")
    console.print("Get API Key: https://makersuite.google.com/app/apikey\n")
    
    api_key = questionary.password("Please input your Gemini API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "Available models (optional):",
        default="gemini-pro,gemini-pro-vision",
        instruction="(multiple models separated by commas)"
    ).ask()
    
    return {
        "provider": "gemini",
        "api_key": api_key,
        "models": models
    }


def configure_deepseek() -> Optional[Dict]:
    """Configure DeepSeek"""
    console.print("\n🚀 [bold]Configure DeepSeek[/bold]")
    console.print("DeepSeek is a highly cost-effective code-specific model")
    console.print("Get API Key: https://platform.deepseek.com/api_keys\n")
    
    api_key = questionary.password("Please input your DeepSeek API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "Available models (optional):",
        default="deepseek-chat,deepseek-coder",
        instruction="(multiple models separated by commas)"
    ).ask()
    
    return {
        "provider": "deepseek",
        "api_key": api_key,
        "models": models
    }


def configure_claude() -> Optional[Dict]:
    """Configure Claude"""
    console.print("\n🤖 [bold]Configure Claude[/bold]")
    console.print("Claude is a powerful AI assistant developed by Anthropic")
    console.print("Get API Key: https://console.anthropic.com/\n")
    
    api_key = questionary.password("Please input your Claude API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "Available models (optional):",
        default="claude-3-sonnet-20240229,claude-3-haiku-20240307",
        instruction="(multiple models separated by commas)"
    ).ask()
    
    return {
        "provider": "claude",
        "api_key": api_key,
        "models": models
    }


def configure_qwen() -> Optional[Dict]:
    """Configure Qwen"""
    console.print("\n🌟 [bold]Configure Alibaba Tongyi Qwen[/bold]")
    console.print("Tongyi Qwen is a large language model developed by Alibaba")
    console.print("Get API Key: https://dashscope.console.aliyun.com/\n")
    
    api_key = questionary.password("Please input your Qwen API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "Available models (optional):",
        default="qwen-plus,qwen-turbo",
        instruction="(multiple models separated by commas)"
    ).ask()
    
    return {
        "provider": "qwen",
        "api_key": api_key, 
        "models": models
    }


def setup_service_config():
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
        default=default_host,
        instruction="(localhost=only accessible from this machine, 0.0.0.0=allows external access)"
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


def save_unified_config(comfyui_config: Dict, llm_configs: List[Dict], service_config: Dict, default_model: Optional[str] = None):
    """Save unified configuration to .env file"""
    console.print(Panel(
        "💾 [bold]Save configuration[/bold]\n\n"
        "Saving configuration to .env file...",
        title="Step 4/4: Save configuration",
        border_style="magenta"
    ))
    
    env_lines = build_env_lines(comfyui_config, llm_configs, service_config, default_model)
    
    # Save to root path
    from pixelle.utils.os_util import get_pixelle_root_path
    pixelle_root = get_pixelle_root_path()
    env_path = Path(pixelle_root) / '.env'
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(env_lines))
    
    console.print("✅ [bold green]Configuration saved to .env file[/bold green]")
    
    # Reload config immediately
    reload_config()


def reload_config():
    """Reload environment variables and settings configuration"""
    import os
    from dotenv import load_dotenv
    
    # Force reload .env file from root path
    from pixelle.utils.os_util import get_pixelle_root_path
    pixelle_root = get_pixelle_root_path()
    env_path = Path(pixelle_root) / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
    # Set Chainlit environment variables
    from pixelle.utils.os_util import get_src_path
    import os
    os.environ["CHAINLIT_APP_ROOT"] = get_src_path()
    
    # Update global settings instance values
    from pixelle import settings as settings_module
    
    # Create new Settings instance to get latest configuration
    from pixelle.settings import Settings
    new_settings = Settings()
    
    # Update global settings object attributes
    for field_name in new_settings.model_fields:
        setattr(settings_module.settings, field_name, getattr(new_settings, field_name))
    
    console.print("🔄 [bold blue]Configuration reloaded[/bold blue]")


def collect_all_selected_models(llm_configs: List[Dict]) -> List[str]:
    """Collect all models from all configured providers, remove duplicates and maintain order."""
    seen = set()
    ordered_models: List[str] = []
    for conf in llm_configs or []:
        models_str = (conf.get("models") or "").strip()
        if not models_str:
            continue
        for m in models_str.split(","):
            model = m.strip()
            if model and model not in seen:
                seen.add(model)
                ordered_models.append(model)
    return ordered_models


def select_default_model_interactively(all_models: List[str]) -> Optional[str]:
    """Provide interactive selection of default model using arrow keys; return None if no models or user cancels."""
    if not all_models:
        return None

    # Default value: first item, but allow user to change
    default_choice_value = all_models[0]
    choices = [
        questionary.Choice(
            title=(m if m != default_choice_value else f"{m} (default)"),
            value=m,
            shortcut_key=None,
        )
        for m in all_models
    ]

    console.print("\n⭐ Please select the default model for the session (can be modified in .env)")
    selected = questionary.select(
        "Default model:",
        choices=choices,
        default=default_choice_value,
        instruction="Use arrow keys to navigate, press Enter to confirm",
    ).ask()

    return selected or default_choice_value


def show_main_menu():
    """Show main menu"""
    console.print("\n📋 [bold]Current configuration status[/bold]")
    show_current_config()
    
    action = questionary.select(
        "Please select the action to perform:",
        choices=[
            questionary.Choice("🚀 Start Pixelle MCP", "start"),
            questionary.Choice("🔄 Reconfigure Pixelle MCP", "reconfig"),
            questionary.Choice("📝 Manual edit configuration", "manual"),
            questionary.Choice("📋 Check status", "status"),
            questionary.Choice("❓ Help", "help"),
            questionary.Choice("❌ Exit", "exit")
        ]
    ).ask()
    
    if action == "start":
        start_pixelle_server()
    elif action == "reconfig":
        run_fresh_setup_wizard()
    elif action == "manual":
        guide_manual_edit()
    elif action == "status":
        check_service_status()
    elif action == "help":
        show_help()
    elif action == "exit":
        console.print("👋 Goodbye!")
    else:
        console.print(f"Feature {action} is under development...")


def show_current_config():
    """Show current configuration"""
    from pixelle.settings import settings
    
    # Create configuration table
    table = Table(title="Current configuration", show_header=True, header_style="bold magenta")
    table.add_column("Configuration item", style="cyan", width=20)
    table.add_column("Current value", style="green")
    
    # Service configuration
    table.add_row("Service address", f"http://{settings.host}:{settings.port}")
    table.add_row("ComfyUI address", settings.comfyui_base_url)
    
    # LLM configuration
    providers = settings.get_configured_llm_providers()
    if providers:
        table.add_row("LLM providers", ", ".join(providers))
        models = settings.get_all_available_models()
        if models:
            table.add_row("Available models", f"{len(models)} models")
            table.add_row("Default model", settings.chainlit_chat_default_model)
    else:
        table.add_row("LLM providers", "[red]Not configured[/red]")
    
    # Web interface
    web_status = "Enabled" if settings.chainlit_auth_enabled else "Disabled"
    table.add_row("Web interface", web_status)
    
    console.print(table)


def run_fresh_setup_wizard():
    """Reconfigure Pixelle MCP (same process as initial setup)"""
    console.print(Panel(
        "🔄 [bold]Reconfigure Pixelle MCP[/bold]\n\n"
        "This will start a fresh configuration process, which is the same as the initial setup.\n"
        "Existing configuration will be replaced.",
        title="Reconfigure Pixelle MCP",
        border_style="yellow"
    ))
    
    if not questionary.confirm("Are you sure you want to reconfigure Pixelle MCP?", default=True, instruction="(Y/n)").ask():
        console.print("❌ Reconfigure cancelled")
        return
    
    console.print("\n🚀 [bold]Start reconfiguration wizard[/bold]\n")
    
    try:
        # Step 1: ComfyUI configuration
        comfyui_config = setup_comfyui()
        if not comfyui_config:
            console.print("⚠️  ComfyUI configuration skipped, using default configuration")
            comfyui_config = {"url": "http://localhost:8188"}  # Use default value
        
        # Step 2: LLM configuration (multiple providers can be configured)
        llm_configs = setup_multiple_llm_providers()
        if not llm_configs:
            console.print("❌ At least one LLM provider is required")
            return
        
        # Step 3: Select default model (based on selected providers and models)
        all_models = collect_all_selected_models(llm_configs)
        selected_default_model = select_default_model_interactively(all_models)

        # Step 4: Service configuration
        service_config = setup_service_config()
        if not service_config:
            console.print("⚠️  Service configuration skipped, using default configuration")
            service_config = {"port": "9004", "host": "localhost"}  # Use default value
        
        # Step 5: Save configuration
        save_unified_config(comfyui_config, llm_configs, service_config, selected_default_model)
        
        # Step 6: Ask if immediately start
        console.print("\n✅ [bold green]Reconfiguration completed![/bold green]")
        if questionary.confirm("Start Pixelle MCP immediately?", default=True, instruction="(Y/n)").ask():
            start_pixelle_server()
            
    except KeyboardInterrupt:
        console.print("\n\n❌ Reconfiguration cancelled (Ctrl+C pressed)")
        console.print("💡 You can always rerun [bold]pixelle[/bold] to configure")
    except Exception as e:
        console.print(f"\n❌ Error occurred during configuration: {e}")
        console.print("💡 You can rerun [bold]pixelle[/bold] to try again")


def guide_manual_edit():
    """Guide user to manually edit configuration"""
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
        console.print("💡 Or exit and rerun [bold]pixelle[/bold] for initial configuration")
        return
    
    # Provide some common editors suggestions
    console.print("\n💡 Recommended editors:")
    console.print("• VS Code: code .env")
    console.print("• Nano: nano .env") 
    console.print("• Vim: vim .env")
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
    
    console.print("\n📋 After configuration, rerun [bold]pixelle[/bold] to apply the configuration")
    console.print("🗑️  If you need to completely reconfigure, delete the .env file and rerun [bold]pixelle[/bold]")


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
    
    from pixelle.settings import settings
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
    if settings.chainlit_auth_enabled:
        web_status = check_url_status(pixelle_url)
        status_table.add_row(
            "Web interface",
            pixelle_url,
            "🟢 Available" if web_status else "🔴 Unavailable",
            "Chat interface" if web_status else "Please start the service first"
        )
    else:
        web_status = True  # If disabled, consider it as normal status
        status_table.add_row(
            "Web interface",
            "Disabled",
            "⚪ Disabled",
            "Disabled in configuration"
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


    


def show_help():
    """Show help information"""
    console.print(Panel(
        "❓ [bold]Get help[/bold]\n\n"
        "Opening Pixelle MCP GitHub page...",
        title="Help",
        border_style="blue"
    ))
    
    console.print("• 📚 Documentation: https://github.com/AIDC-AI/Pixelle-MCP")
    console.print("• 🐛 Issue feedback: https://github.com/AIDC-AI/Pixelle-MCP/issues")
    console.print("• 💬 Community discussion: https://github.com/AIDC-AI/Pixelle-MCP#-community")
    console.print("• 📦 Installation guide: https://github.com/AIDC-AI/Pixelle-MCP/blob/main/INSTALL.md")


if __name__ == "__main__":
    main()
