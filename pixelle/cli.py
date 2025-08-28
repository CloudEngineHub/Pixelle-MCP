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
    parse_env_file,
    detect_config_status_from_env,
    build_env_lines,
)


app = typer.Typer(add_completion=False, help="🎨 Pixelle MCP - 将ComfyUI工作流转换为MCP工具")
console = Console()


def main():
    """🎨 Pixelle MCP 统一入口点 - 智能判断用户意图"""
    
    # 显示欢迎界面
    show_welcome()
    
    # 检测配置状态
    config_status = detect_config_status()
    
    if config_status == "first_time":
        # 首次使用：完整配置向导 + 启动
        console.print("\n🎯 [bold blue]检测到这是您首次使用 Pixelle MCP！[/bold blue]")
        console.print("我们将引导您完成简单的配置过程...\n")
        
        if questionary.confirm("开始配置向导？", default=True, instruction="(Y/n)").ask():
            run_full_setup_wizard()
        else:
            console.print("❌ 配置已取消。您可以随时再次运行 [bold]pixelle[/bold] 来配置。")
            return
            
    elif config_status == "incomplete":
        # 配置不完整：引导用户处理
        console.print("\n⚠️  [bold yellow]检测到配置文件存在但不完整[/bold yellow]")
        console.print("💡 建议重新引导配置或手动编辑配置文件")
        show_main_menu()
        
    else:
        # 已完整配置：显示主菜单
        show_main_menu()


def show_welcome():
    """显示欢迎界面"""
    welcome_text = """
🎨 [bold blue]Pixelle MCP 2.0[/bold blue]
将ComfyUI工作流转换为MCP工具的极简解决方案

✨ 30秒从零到AI助手
🔧 零代码将工作流转为MCP工具  
🌐 支持Cursor、Claude Desktop等MCP客户端
🤖 支持多种主流LLM（OpenAI、Ollama、Gemini等）
"""
    
    console.print(Panel(
        welcome_text,
        title="Welcome to Pixelle MCP",
        border_style="blue",
        padding=(1, 2)
    ))


def detect_config_status() -> str:
    """检测当前配置状态"""
    env_file = Path(".env")
    
    if not env_file.exists():
        return "first_time"
    
    # 检查必要的配置项
    required_configs = [
        "COMFYUI_BASE_URL",
        # 至少要有一个LLM配置
        ("OPENAI_API_KEY", "OLLAMA_BASE_URL", "GEMINI_API_KEY", "DEEPSEEK_API_KEY", "CLAUDE_API_KEY", "QWEN_API_KEY")
    ]
    
    env_vars = {}
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"\'')
    
    # 检查ComfyUI配置
    if "COMFYUI_BASE_URL" not in env_vars or not env_vars["COMFYUI_BASE_URL"]:
        return "incomplete"
    
    # 检查是否至少有一个LLM配置
    llm_configs = required_configs[1]
    has_llm = any(key in env_vars and env_vars[key] for key in llm_configs)
    if not has_llm:
        return "incomplete"
    
    return "complete"


def run_full_setup_wizard():
    """运行完整的配置向导"""
    console.print("\n🚀 [bold]开始 Pixelle MCP 配置向导[/bold]\n")
    
    try:
        # Step 1: ComfyUI配置
        comfyui_config = setup_comfyui()
        if not comfyui_config:
            console.print("⚠️  ComfyUI配置跳过，将使用默认配置继续")
            comfyui_config = {"url": "http://localhost:8188"}  # 使用默认值
        
        # Step 2: LLM配置（可配置多个）
        llm_configs = setup_multiple_llm_providers()
        if not llm_configs:
            console.print("❌ 至少需要配置一个LLM提供商")
            return
        
        # Step 3: 选择默认模型（基于已选择的提供商与模型）
        all_models = collect_all_selected_models(llm_configs)
        selected_default_model = select_default_model_interactively(all_models)

        # Step 4: 服务配置
        service_config = setup_service_config()
        if not service_config:
            console.print("⚠️  服务配置跳过，将使用默认配置继续")
            service_config = {"port": "9004", "enable_web": True}  # 使用默认值
        
        # Step 5: 保存配置
        save_unified_config(comfyui_config, llm_configs, service_config, selected_default_model)
        
        # Step 6: 询问立即启动
        console.print("\n✅ [bold green]配置完成！[/bold green]")
        if questionary.confirm("立即启动 Pixelle MCP？", default=True, instruction="(Y/n)").ask():
            start_pixelle_server()
            
    except KeyboardInterrupt:
        console.print("\n\n❌ 配置已取消（按下了 Ctrl+C）")
        console.print("💡 您可以随时重新运行 [bold]pixelle[/bold] 来配置")
    except Exception as e:
        console.print(f"\n❌ 配置过程中发生错误: {e}")
        console.print("💡 您可以重新运行 [bold]pixelle[/bold] 来重试")


def setup_comfyui(default_url: str = None):
    """配置ComfyUI - 第一步"""
    console.print(Panel(
        "🧩 [bold]ComfyUI 配置[/bold]\n\n"
        "Pixelle MCP 需要连接到您的 ComfyUI 服务来执行工作流。\n"
        "ComfyUI 是一个强大的AI工作流编辑器，如果您还没有安装，\n"
        "请访问：https://github.com/comfyanonymous/ComfyUI",
        title="Step 1/4: ComfyUI 配置",
        border_style="blue"
    ))
    
    # 手动配置
    console.print("\n📝 请配置 ComfyUI 服务地址")
    console.print("💡 如果选择'n'，将允许您输入自定义地址")
    
    # 使用传入的默认值或代码默认值
    final_default_url = default_url or "http://localhost:8188"
    use_default = questionary.confirm(
        f"使用默认地址 {final_default_url}？",
        default=True,
        instruction="(Y/n)"
    ).ask()
    
    if use_default:
        url = final_default_url
        console.print(f"✅ 使用默认地址: {url}")
    else:
        url = questionary.text(
            "请输入自定义 ComfyUI 地址:",
            instruction="(例如: http://192.168.1.100:8188)"
        ).ask()
    
    if not url:
        return None
    
    # 测试连接
    console.print(f"🔌 正在测试连接 {url}...")
    if test_comfyui_connection(url):
        console.print("✅ [bold green]ComfyUI 连接成功！[/bold green]")
        return {"url": url}
    else:
        console.print("❌ [bold red]无法连接到 ComfyUI[/bold red]")
        console.print("请检查：")
        console.print("1. ComfyUI 是否正在运行")
        console.print("2. 地址是否正确")
        console.print("3. 网络是否畅通")
        
        # 询问是否跳过测试
        skip_test = questionary.confirm(
            "是否跳过连接测试？",
            default=True,
            instruction="(Y/n，跳过将直接使用您填写的地址)"
        ).ask()
        
        if skip_test:
            console.print(f"⏭️  已跳过连接测试，将使用地址: {url}")
            return {"url": url}
        else:
            # 重新测试，但保持用户填写的地址
            return setup_comfyui(url)


def setup_multiple_llm_providers():
    """配置多个LLM提供商 - 第二步"""
    console.print(Panel(
        "🤖 [bold]LLM 提供商配置[/bold]\n\n"
        "Pixelle MCP 支持多种LLM提供商，您可以配置一个或多个。\n"
        "配置多个提供商的好处：\n"
        "• 可以在不同场景下使用不同模型\n"
        "• 提供备选方案，提高服务可用性\n"
        "• 某些模型在特定任务上表现更好",
        title="Step 2/4: LLM 提供商配置",
        border_style="green"
    ))
    
    configured_providers = []
    
    while True:
        # 显示可选的提供商
        available_providers = [
            questionary.Choice("🔥 OpenAI (推荐) - GPT-4、GPT-3.5等", "openai"),
            questionary.Choice("🏠 Ollama (本地) - 免费本地模型", "ollama"),
            questionary.Choice("💎 Google Gemini - Google最新模型", "gemini"),
            questionary.Choice("🚀 DeepSeek - 性价比极高的代码模型", "deepseek"),
            questionary.Choice("🤖 Claude - Anthropic的强大模型", "claude"),
            questionary.Choice("🌟 Qwen - 阿里巴巴通义千问", "qwen"),
        ]
        
        # 过滤已配置的提供商
        remaining_providers = [p for p in available_providers 
                             if p.value not in [cp["provider"] for cp in configured_providers]]
        
        if not remaining_providers:
            console.print("✅ 已配置所有可用的LLM提供商，自动进入下一步")
            break
        
        # 显示当前已配置的提供商
        if configured_providers:
            console.print("\n📋 [bold]已配置的提供商：[/bold]")
            for provider in configured_providers:
                console.print(f"  ✅ {provider['provider'].title()}")
        
        # 选择要配置的提供商
        if configured_providers:
            remaining_providers.append(questionary.Choice("🏁 完成配置", "done"))
        
        # 总是添加退出选项
        remaining_providers.append(questionary.Choice("❌ 取消配置", "cancel"))
        
        provider = questionary.select(
            "选择要配置的LLM提供商：" if not configured_providers else "选择要继续配置的LLM提供商：",
            choices=remaining_providers
        ).ask()
        
        if provider == "cancel":
            if questionary.confirm("确定要取消配置吗？", default=False, instruction="(y/N)").ask():
                console.print("❌ 配置已取消")
                return None
            else:
                continue  # 继续配置循环
        
        if provider == "done":
            break
        
        # 配置具体的提供商
        provider_config = configure_specific_llm(provider)
        if provider_config:
            configured_providers.append(provider_config)
            
            # 显示选择的模型
            models = provider_config.get('models', '')
            if models:
                model_list = [m.strip() for m in models.split(',')]
                model_display = '、'.join(model_list)
                console.print(f"✅ [bold green]{provider.title()} 配置成功！[/bold green]")
                console.print(f"📋 您选择了 {model_display} 模型\n")
            else:
                console.print(f"✅ [bold green]{provider.title()} 配置成功！[/bold green]\n")
        
        if not configured_providers:
            console.print("⚠️  至少需要配置一个LLM提供商才能继续")
        else:
            # 检查是否还有未配置的提供商
            # remaining_providers已经过滤掉已配置的，且会添加"完成配置"和"取消配置"选项
            actual_remaining = len([p for p in remaining_providers if p.value not in ["done", "cancel"]])
            if actual_remaining > 0:
                if not questionary.confirm("是否继续配置其他LLM提供商？", default=False, instruction="(y/N)").ask():
                    break
            else:
                # 所有提供商都已配置完毕，自动进入下一步
                break
    
    return configured_providers


def configure_specific_llm(provider: str) -> Optional[Dict]:
    """配置具体的LLM提供商"""
    
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
    """配置OpenAI"""
    console.print("\n🔥 [bold]配置 OpenAI 兼容接口[/bold]")
    console.print("支持 OpenAI 官方以及所有兼容 OpenAI SDK 协议的提供商")
    console.print("包括但不限于：OpenAI、Azure OpenAI、各种第三方代理服务等")
    console.print("获取 OpenAI 官方 API Key: https://platform.openai.com/api-keys\n")
    
    api_key = questionary.password("请输入您的 OpenAI API Key:").ask()
    if not api_key:
        return None
    
    console.print("💡 如果使用代理或第三方服务，选择'n'输入自定义地址")
    default_base_url = "https://api.openai.com/v1"
    use_default_url = questionary.confirm(
        f"使用默认 API 地址 {default_base_url}？",
        default=True,
        instruction="(Y/n)"
    ).ask()
    
    if use_default_url:
        base_url = default_base_url
        console.print(f"✅ 使用默认地址: {base_url}")
    else:
        base_url = questionary.text(
            "请输入自定义 API 地址:",
            instruction="(例如: https://your-proxy.com/v1)"
        ).ask()
    
    # 尝试获取模型列表
    console.print("🔍 正在获取可用模型列表...")
    available_models = get_openai_models(api_key, base_url)
    
    if available_models:
        console.print(f"📋 发现 {len(available_models)} 个可用模型")
        
        # 预选推荐模型
        recommended_models = []
        for model in ["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]:
            if model in available_models:
                recommended_models.append(model)
        
        if recommended_models:
            console.print(f"💡 已为您预选推荐模型: {', '.join(recommended_models)}")
        
        # 直接提供多选界面
        # 创建choices列表，并标记推荐模型为默认选中
        choices = []
        for model in available_models:
            if model in recommended_models:
                choices.append(questionary.Choice(f"{model} (推荐)", model, checked=True))
            else:
                choices.append(questionary.Choice(model, model, checked=False))
        
        selected_models = questionary.checkbox(
            "请选择要使用的模型（空格选择/取消，回车确认）:",
            choices=choices,
            instruction="使用方向键导航，空格键选择/取消选择，回车键确认"
        ).ask()
        
        if selected_models:
            models = ",".join(selected_models)
            console.print(f"✅ 已选择模型: {models}")
        else:
            console.print("⚠️  未选择任何模型，将使用手动输入")
            models = questionary.text(
                "请输入自定义模型:",
                instruction="(多个模型用英文逗号分隔)"
            ).ask()
    else:
        console.print("⚠️  无法获取模型列表，使用默认配置")
        default_models = "gpt-4o-mini,gpt-4o"
        use_default_models = questionary.confirm(
            f"使用默认推荐模型 {default_models}？",
            default=True,
            instruction="(Y/n)"
        ).ask()
        
        if use_default_models:
            models = default_models
            console.print(f"✅ 使用默认模型: {models}")
        else:
            models = questionary.text(
                "请输入自定义模型:",
                instruction="(多个模型用英文逗号分隔，例如: gpt-4,gpt-3.5-turbo)"
            ).ask()
    
    return {
        "provider": "openai",
        "api_key": api_key,
        "base_url": base_url,
        "models": models
    }


def configure_ollama() -> Optional[Dict]:
    """配置Ollama"""
    console.print("\n🏠 [bold]配置 Ollama (本地模型)[/bold]")
    console.print("Ollama 可以在本地运行开源模型，完全免费且数据不出本机")
    console.print("安装 Ollama: https://ollama.ai\n")
    
    console.print("💡 如果Ollama运行在其他地址，选择'n'输入自定义地址")
    default_base_url = "http://localhost:11434/v1"
    use_default_url = questionary.confirm(
        f"使用默认 Ollama 地址 {default_base_url}？",
        default=True,
        instruction="(Y/n)"
    ).ask()
    
    if use_default_url:
        base_url = default_base_url
        console.print(f"✅ 使用默认地址: {base_url}")
    else:
        base_url = questionary.text(
            "请输入自定义 Ollama 地址:",
            instruction="(例如: http://192.168.1.100:11434/v1)"
        ).ask()
    
    # 测试连接
    console.print("🔌 正在测试 Ollama 连接...")
    if test_ollama_connection(base_url):
        console.print("✅ Ollama 连接成功")
        
        # 获取可用模型
        models = get_ollama_models(base_url)
        if models:
            console.print(f"📋 发现 {len(models)} 个可用模型")
            selected_models = questionary.checkbox(
                "选择要使用的模型:",
                choices=[questionary.Choice(model, model) for model in models]
            ).ask()
            
            if selected_models:
                return {
                    "provider": "ollama", 
                    "base_url": base_url,
                    "models": ",".join(selected_models)
                }
        else:
            console.print("⚠️  未发现可用模型，您可能需要先下载模型")
            console.print("例如：ollama pull llama2")
            
            models = questionary.text(
                "手动指定模型:",
                instruction="(多个模型用英文逗号分隔)"
            ).ask()
            
            if models:
                return {
                    "provider": "ollama",
                    "base_url": base_url, 
                    "models": models
                }
    else:
        console.print("❌ 无法连接到 Ollama")
        console.print("请确保 Ollama 正在运行")
        
    return None


def configure_gemini() -> Optional[Dict]:
    """配置Gemini"""
    console.print("\n💎 [bold]配置 Google Gemini[/bold]")
    console.print("Google Gemini 是Google最新的大语言模型")
    console.print("获取API Key: https://makersuite.google.com/app/apikey\n")
    
    api_key = questionary.password("请输入您的 Gemini API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "可用模型 (可选):",
        default="gemini-pro,gemini-pro-vision",
        instruction="(多个模型用英文逗号分隔)"
    ).ask()
    
    return {
        "provider": "gemini",
        "api_key": api_key,
        "models": models
    }


def configure_deepseek() -> Optional[Dict]:
    """配置DeepSeek"""
    console.print("\n🚀 [bold]配置 DeepSeek[/bold]")
    console.print("DeepSeek 是性价比极高的代码专用模型")
    console.print("获取API Key: https://platform.deepseek.com/api_keys\n")
    
    api_key = questionary.password("请输入您的 DeepSeek API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "可用模型 (可选):",
        default="deepseek-chat,deepseek-coder",
        instruction="(多个模型用英文逗号分隔)"
    ).ask()
    
    return {
        "provider": "deepseek",
        "api_key": api_key,
        "models": models
    }


def configure_claude() -> Optional[Dict]:
    """配置Claude"""
    console.print("\n🤖 [bold]配置 Claude[/bold]")
    console.print("Claude 是 Anthropic 开发的强大AI助手")
    console.print("获取API Key: https://console.anthropic.com/\n")
    
    api_key = questionary.password("请输入您的 Claude API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "可用模型 (可选):",
        default="claude-3-sonnet-20240229,claude-3-haiku-20240307",
        instruction="(多个模型用英文逗号分隔)"
    ).ask()
    
    return {
        "provider": "claude",
        "api_key": api_key,
        "models": models
    }


def configure_qwen() -> Optional[Dict]:
    """配置Qwen"""
    console.print("\n🌟 [bold]配置 阿里巴巴通义千问[/bold]")
    console.print("通义千问是阿里巴巴开发的大语言模型")
    console.print("获取API Key: https://dashscope.console.aliyun.com/\n")
    
    api_key = questionary.password("请输入您的 Qwen API Key:").ask()
    if not api_key:
        return None
    
    models = questionary.text(
        "可用模型 (可选):",
        default="qwen-plus,qwen-turbo",
        instruction="(多个模型用英文逗号分隔)"
    ).ask()
    
    return {
        "provider": "qwen",
        "api_key": api_key, 
        "models": models
    }


def setup_service_config():
    """配置服务选项 - 第三步"""
    console.print(Panel(
        "⚙️ [bold]服务配置[/bold]\n\n"
        "配置 Pixelle MCP 的服务选项，包括端口、主机地址等。",
        title="Step 3/4: 服务配置",
        border_style="yellow"
    ))
    
    default_port = "9004"
    port = questionary.text(
        "服务端口:",
        default=default_port,
        instruction="(直接回车使用默认端口9004，或输入其他端口号)"
    ).ask()
    
    if not port:
        port = default_port
    
    console.print(f"✅ 服务将在端口 {port} 启动")
    
    # 配置主机地址
    console.print("\n📡 [bold yellow]主机地址配置[/bold yellow]")
    console.print("🔍 [dim]主机地址决定了服务监听的网络接口：[/dim]")
    console.print("   • [green]localhost[/green] - 仅本机访问（推荐用于本地开发）")
    console.print("   • [yellow]0.0.0.0[/yellow] - 允许外部访问（用于服务器部署或局域网共享）")
    console.print("\n⚠️  [bold red]安全提示：[/bold red]")
    console.print("   选择 0.0.0.0 时，请确保：")
    console.print("   1. 已配置防火墙规则")
    console.print("   2. 已设置强密码认证")
    console.print("   3. 在可信网络环境中运行")
    
    default_host = "localhost"
    host = questionary.text(
        "主机地址:",
        default=default_host,
        instruction="(localhost=本机访问, 0.0.0.0=允许外部访问)"
    ).ask()
    
    if not host:
        host = default_host
    
    if host == "0.0.0.0":
        console.print("⚠️  [bold yellow]已设置为允许外部访问，请确保网络安全！[/bold yellow]")
    else:
        console.print(f"✅ 服务将在 {host} 上监听")
    
    return {
        "port": port,
        "host": host,
    }


def save_unified_config(comfyui_config: Dict, llm_configs: List[Dict], service_config: Dict, default_model: Optional[str] = None):
    """保存统一配置到.env文件"""
    console.print(Panel(
        "💾 [bold]保存配置[/bold]\n\n"
        "正在将配置保存到 .env 文件...",
        title="Step 4/4: 保存配置",
        border_style="magenta"
    ))
    
    env_lines = build_env_lines(comfyui_config, llm_configs, service_config, default_model)
    with open('.env', 'w', encoding='utf-8') as f:
        f.write('\n'.join(env_lines))
    
    console.print("✅ [bold green]配置已保存到 .env 文件[/bold green]")
    
    # 🔥 关键修复：立即重新加载环境变量和settings
    reload_config()


def reload_config():
    """重新加载环境变量和settings配置"""
    import os
    from dotenv import load_dotenv
    
    # 强制重新加载.env文件
    load_dotenv(override=True)
    
    # 重新设置Chainlit环境变量
    from pixelle.utils.os_util import get_root_path
    os.environ["CHAINLIT_APP_ROOT"] = get_root_path()
    
    # 更新全局settings实例的值
    from pixelle import settings as settings_module
    
    # 创建新的Settings实例来获取最新配置
    from pixelle.settings import Settings
    new_settings = Settings()
    
    # 更新全局settings对象的属性
    for field_name in new_settings.model_fields:
        setattr(settings_module.settings, field_name, getattr(new_settings, field_name))
    
    console.print("🔄 [bold blue]配置已重新加载[/bold blue]")


def collect_all_selected_models(llm_configs: List[Dict]) -> List[str]:
    """从已配置的各提供商配置中收集所有模型，去重并保持顺序。"""
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
    """提供方向键选择默认模型的交互；若无模型或用户取消则返回 None。"""
    if not all_models:
        return None

    # 默认值：第一项，但允许用户更改
    default_choice_value = all_models[0]
    choices = [
        questionary.Choice(
            title=(m if m != default_choice_value else f"{m} (默认)"),
            value=m,
            shortcut_key=None,
        )
        for m in all_models
    ]

    console.print("\n⭐ 请选择会话默认模型（可随时在 .env 中修改）")
    selected = questionary.select(
        "默认模型:",
        choices=choices,
        default=default_choice_value,
        instruction="使用方向键选择，回车确认",
    ).ask()

    return selected or default_choice_value


def show_main_menu():
    """显示主菜单"""
    console.print("\n📋 [bold]当前配置状态[/bold]")
    show_current_config()
    
    action = questionary.select(
        "请选择要执行的操作:",
        choices=[
            questionary.Choice("🚀 启动 Pixelle MCP", "start"),
            questionary.Choice("🔄 重新引导配置", "reconfig"),
            questionary.Choice("✏️ 手动编辑配置", "manual"),
            questionary.Choice("📋 查看状态", "status"),
            questionary.Choice("❓ 帮助", "help"),
            questionary.Choice("❌ 退出", "exit")
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
        console.print("👋 再见！")
    else:
        console.print(f"功能 {action} 正在开发中...")


def show_current_config():
    """显示当前配置"""
    from pixelle.settings import settings
    
    # 创建配置表格
    table = Table(title="当前配置", show_header=True, header_style="bold magenta")
    table.add_column("配置项", style="cyan", width=20)
    table.add_column("当前值", style="green")
    
    # 服务配置
    table.add_row("服务地址", f"http://{settings.host}:{settings.port}")
    table.add_row("ComfyUI地址", settings.comfyui_base_url)
    
    # LLM配置
    providers = settings.get_configured_llm_providers()
    if providers:
        table.add_row("LLM提供商", ", ".join(providers))
        models = settings.get_all_available_models()
        if models:
            table.add_row("可用模型", f"{len(models)} 个模型")
            table.add_row("默认模型", settings.chainlit_chat_default_model)
    else:
        table.add_row("LLM提供商", "[red]未配置[/red]")
    
    # Web界面
    web_status = "启用" if settings.chainlit_auth_enabled else "禁用"
    table.add_row("Web界面", web_status)
    
    console.print(table)


def run_fresh_setup_wizard():
    """重新引导配置（与首次配置完全相同的流程）"""
    console.print(Panel(
        "🔄 [bold]重新引导配置 Pixelle MCP[/bold]\n\n"
        "将从头开始进行完整配置，这与首次配置是完全相同的流程。\n"
        "现有配置将被全新配置替换。",
        title="重新引导配置",
        border_style="yellow"
    ))
    
    if not questionary.confirm("确定要重新进行完整配置吗？", default=True, instruction="(Y/n)").ask():
        console.print("❌ 重新配置已取消")
        return
    
    console.print("\n🚀 [bold]开始重新配置向导[/bold]\n")
    
    try:
        # Step 1: ComfyUI配置
        comfyui_config = setup_comfyui()
        if not comfyui_config:
            console.print("⚠️  ComfyUI配置跳过，将使用默认配置继续")
            comfyui_config = {"url": "http://localhost:8188"}  # 使用默认值
        
        # Step 2: LLM配置（可配置多个）
        llm_configs = setup_multiple_llm_providers()
        if not llm_configs:
            console.print("❌ 至少需要配置一个LLM提供商")
            return
        
        # Step 3: 选择默认模型（基于已选择的提供商与模型）
        all_models = collect_all_selected_models(llm_configs)
        selected_default_model = select_default_model_interactively(all_models)

        # Step 4: 服务配置
        service_config = setup_service_config()
        if not service_config:
            console.print("⚠️  服务配置跳过，将使用默认配置继续")
            service_config = {"port": "9004", "host": "localhost"}  # 使用默认值
        
        # Step 5: 保存配置
        save_unified_config(comfyui_config, llm_configs, service_config, selected_default_model)
        
        # Step 6: 询问立即启动
        console.print("\n✅ [bold green]重新配置完成！[/bold green]")
        if questionary.confirm("立即启动 Pixelle MCP？", default=True, instruction="(Y/n)").ask():
            start_pixelle_server()
            
    except KeyboardInterrupt:
        console.print("\n\n❌ 重新配置已取消（按下了 Ctrl+C）")
        console.print("💡 您可以随时重新运行 [bold]pixelle[/bold] 来配置")
    except Exception as e:
        console.print(f"\n❌ 配置过程中发生错误: {e}")
        console.print("💡 您可以重新运行 [bold]pixelle[/bold] 来重试")


def guide_manual_edit():
    """引导用户手动编辑配置"""
    console.print(Panel(
        "✏️ [bold]手动编辑配置[/bold]\n\n"
        "配置文件包含详细的注释说明，您可以直接编辑来自定义配置。\n"
        "配置文件位置：.env\n\n"
        "💡 如需完全重新配置，删除 .env 文件后重新运行 'pixelle'\n"
        "💡 编辑完成后，重新运行 'pixelle' 来应用配置",
        title="手动配置指南",
        border_style="green"
    ))
    
    # 显示当前配置文件路径
    env_path = Path(".env").absolute()
    console.print(f"📁 配置文件路径: {env_path}")
    
    if not env_path.exists():
        console.print("\n⚠️  配置文件不存在！")
        console.print("💡 请先运行交互引导: 选择菜单中的 '🔄 重新引导配置'")
        console.print("💡 或者退出并重新运行 [bold]pixelle[/bold] 进行首次配置")
        return
    
    # 提供一些常用编辑器的建议
    console.print("\n💡 推荐编辑器:")
    console.print("• VS Code: code .env")
    console.print("• Nano: nano .env") 
    console.print("• Vim: vim .env")
    console.print("• 或任何文本编辑器")
    
    console.print("\n📝 常见配置修改:")
    console.print("• 更换端口: 修改 PORT=9004")
    console.print("• 添加新LLM: 配置对应的 API_KEY")
    console.print("• 禁用LLM: 删除或清空对应的 API_KEY")
    console.print("• 更换ComfyUI: 修改 COMFYUI_BASE_URL")
    
    # 询问是否要打开文件
    if questionary.confirm("是否要在默认编辑器中打开配置文件？", default=True, instruction="(Y/n)").ask():
        try:
            import subprocess
            import platform
            
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(env_path)])
            elif platform.system() == "Windows":
                subprocess.run(["notepad", str(env_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(env_path)])
                
            console.print("✅ 已在默认编辑器中打开配置文件")
        except Exception as e:
            console.print(f"❌ 无法自动打开: {e}")
            console.print("💡 请手动编辑文件")
    
    console.print("\n📋 配置完成后，重新运行 [bold]pixelle[/bold] 来应用配置")
    console.print("🗑️  如需完全重新配置，删除 .env 文件后重新运行 [bold]pixelle[/bold]")


def start_pixelle_server():
    """启动Pixelle服务器"""
    console.print("\n🚀 [bold]正在启动 Pixelle MCP...[/bold]")
    
    try:
        # 重新加载环境变量
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        port = int(settings.port)
        
        # 检查端口是否被占用
        if check_port_in_use(port):
            process_info = get_process_using_port(port)
            if process_info:
                console.print(f"⚠️  [bold yellow]检测到端口 {port} 已被占用[/bold yellow]")
                console.print(f"占用进程: {process_info}")
                
                kill_service = questionary.confirm(
                    "是否终止现有服务并重新启动？",
                    default=True,
                    instruction="(Y/n)"
                ).ask()
                
                if kill_service:
                    console.print("🔄 正在终止现有服务...")
                    if kill_process_on_port(port):
                        console.print("✅ 现有服务已终止")
                        import time
                        time.sleep(1)  # 等待端口释放
                    else:
                        console.print("❌ 无法终止现有服务，启动可能失败")
                        proceed = questionary.confirm(
                            "是否仍要尝试启动？",
                            default=False,
                            instruction="(y/N)"
                        ).ask()
                        if not proceed:
                            console.print("❌ 启动已取消")
                            return
                else:
                    console.print("❌ 启动已取消")
                    return
            else:
                console.print(f"⚠️  [bold yellow]端口 {port} 被占用，但无法确定占用进程[/bold yellow]")
                console.print("启动可能失败，建议更换端口或手动处理")
        
        # 启动服务
        console.print(Panel(
            f"🌐 Web 界面: http://localhost:{settings.port}/\n"
            f"🔌 MCP 端点: http://localhost:{settings.port}/mcp\n"
            f"📁 已加载工作流目录: data/custom_workflows/",
            title="🎉 Pixelle MCP 正在运行！",
            border_style="green"
        ))
        
        console.print("\n按 [bold]Ctrl+C[/bold] 停止服务\n")
        
        # 导入并启动main
        from pixelle.main import main as start_main
        start_main()
        
    except KeyboardInterrupt:
        console.print("\n👋 Pixelle MCP 已停止")
    except Exception as e:
        console.print(f"❌ 启动失败: {e}")


def check_service_status():
    """检查服务状态"""
    console.print(Panel(
        "📋 [bold]检查服务状态[/bold]\n\n"
        "正在检查各项服务的运行状态...",
        title="服务状态检查",
        border_style="cyan"
    ))
    
    from pixelle.settings import settings
    import requests
    
    # 创建状态表格
    status_table = Table(title="服务状态", show_header=True, header_style="bold cyan")
    status_table.add_column("服务", style="cyan", width=20)
    status_table.add_column("地址", style="yellow", width=30)
    status_table.add_column("状态", width=15)
    status_table.add_column("说明", style="white")
    
    # 检查MCP端点
    pixelle_url = f"http://{settings.host}:{settings.port}"
    mcp_status = check_url_status(f"{pixelle_url}/mcp")
    status_table.add_row(
        "MCP 端点",
        f"{pixelle_url}/mcp",
        "🟢 可用" if mcp_status else "🔴 不可用",
        "MCP协议端点" if mcp_status else "请先启动服务"
    )
    
    # 检查Web界面
    if settings.chainlit_auth_enabled:
        web_status = check_url_status(pixelle_url)
        status_table.add_row(
            "Web 界面",
            pixelle_url,
            "🟢 可用" if web_status else "🔴 不可用",
            "聊天界面" if web_status else "请先启动服务"
        )
    else:
        web_status = True  # 如果禁用，算作正常状态
        status_table.add_row(
            "Web 界面",
            "已禁用",
            "⚪ 禁用",
            "已在配置中禁用"
        )
    
    # 检查ComfyUI
    comfyui_status = test_comfyui_connection(settings.comfyui_base_url)
    status_table.add_row(
        "ComfyUI",
        settings.comfyui_base_url,
        "🟢 连接正常" if comfyui_status else "🔴 连接失败",
        "工作流执行引擎" if comfyui_status else "请检查ComfyUI是否运行"
    )
    
    console.print(status_table)
    
    # 显示LLM配置状态
    providers = settings.get_configured_llm_providers()
    if providers:
        console.print(f"\n🤖 [bold]LLM 提供商：[/bold] {', '.join(providers)} ({len(providers)} 个)")
        models = settings.get_all_available_models()
        console.print(f"📋 [bold]可用模型：[/bold] {len(models)} 个")
        console.print(f"⭐ [bold]默认模型：[/bold] {settings.chainlit_chat_default_model}")
    else:
        console.print("\n⚠️  [bold yellow]警告：[/bold yellow] 未配置任何LLM提供商")
    
    # 总结
    total_services = 3  # MCP, Web, ComfyUI
    running_services = sum([mcp_status, web_status, comfyui_status])
    
    if running_services == total_services:
        console.print("\n✅ [bold green]所有服务运行正常！[/bold green]")
    else:
        console.print(f"\n⚠️  [bold yellow]{running_services}/{total_services} 服务正常运行[/bold yellow]")
        console.print("💡 如有服务未运行，请检查配置或重启服务")


    


def show_help():
    """显示帮助信息"""
    console.print(Panel(
        "❓ [bold]获取帮助[/bold]\n\n"
        "正在打开 Pixelle MCP GitHub 主页...",
        title="帮助",
        border_style="blue"
    ))
    
    import webbrowser
    github_url = "https://github.com/AIDC-AI/Pixelle-MCP"
    
    try:
        webbrowser.open(github_url)
        console.print(f"🌐 已在浏览器中打开: {github_url}")
    except Exception as e:
        console.print(f"❌ 无法自动打开浏览器: {e}")
        console.print(f"📋 请手动访问: {github_url}")
    
    console.print("\n📚 其他帮助资源:")
    console.print("• 🐛 问题反馈: https://github.com/AIDC-AI/Pixelle-MCP/issues")
    console.print("• 💬 社区讨论: https://github.com/AIDC-AI/Pixelle-MCP#-community")


if __name__ == "__main__":
    main()
