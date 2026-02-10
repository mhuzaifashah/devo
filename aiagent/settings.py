import os
import tomllib

from dotenv import load_dotenv


def _load_toml_config(config_path):
    if not os.path.isfile(config_path):
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _split_model_string(model_str):
    if not model_str:
        return None, None
    if ":" not in model_str:
        return None, model_str.strip()
    provider, model = model_str.split(":", 1)
    return provider.strip().lower(), model.strip()


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _default_safe_commands():
    if os.name == "nt":
        return ["dir", "ls", "type", "cat", "rg", "git", "py", "python", "pytest", "where"]
    return ["ls", "dir", "cat", "type", "rg", "git", "python", "python3", "pytest", "which"]


def load_settings():
    load_dotenv()

    project_root = os.getcwd()
    config_path = os.path.join(project_root, "aiagent.toml")
    config = _load_toml_config(config_path)
    agent_cfg = config.get("agent", {})
    workspaces_cfg = config.get("workspaces", {})
    safety_cfg = config.get("safety", {})
    hooks_cfg = config.get("hooks", {})
    openrouter_cfg = config.get("openrouter", {})
    azure_cfg = config.get("azure_openai", {})
    memory_cfg = config.get("memory", {})
    compaction_cfg = config.get("compaction", {})

    cfg_provider = agent_cfg.get("provider")
    cfg_model = agent_cfg.get("model")
    cfg_workdir = agent_cfg.get("workdir")
    cfg_workspace = agent_cfg.get("workspace")
    cfg_max_iters = agent_cfg.get("max_iters")
    cfg_temperature = agent_cfg.get("temperature")
    cfg_safety_mode = agent_cfg.get("safety_mode")

    env_provider = os.environ.get("AIAGENT_PROVIDER")
    env_model = os.environ.get("AIAGENT_MODEL")
    env_workdir = os.environ.get("AIAGENT_WORKDIR")
    env_max_iters = os.environ.get("AIAGENT_MAX_ITERS")
    env_temperature = os.environ.get("AIAGENT_TEMPERATURE")
    env_safety_mode = os.environ.get("AIAGENT_SAFETY_MODE")
    env_allow_unsafe_shell = os.environ.get("AIAGENT_ALLOW_UNSAFE_SHELL")
    env_auto_rollback = os.environ.get("AIAGENT_AUTO_ROLLBACK")
    env_workspace = os.environ.get("AIAGENT_WORKSPACE")

    provider = (cfg_provider or env_provider or "").strip() or None
    model = (cfg_model or env_model or "").strip() or None

    model_provider_from_str, model_from_str = _split_model_string(model)
    if model_provider_from_str:
        if provider and provider.lower() != model_provider_from_str:
            raise ValueError(
                "Conflicting provider in model string. "
                f"Got provider '{provider}' and model '{model}'."
            )
        provider = model_provider_from_str
        model = model_from_str
    elif model_from_str:
        model = model_from_str

    if provider is not None:
        provider = provider.strip().lower()

    primary_workspace = workspaces_cfg.get("primary") or cfg_workdir or env_workdir
    extra_workspaces = workspaces_cfg.get("additional") or []
    if isinstance(extra_workspaces, str):
        extra_workspaces = [extra_workspaces]
    use_git_worktrees = bool(workspaces_cfg.get("use_git_worktrees"))

    max_iters = int(cfg_max_iters or env_max_iters or "20")
    temperature = float(cfg_temperature or env_temperature or "0.2")

    safety_mode = (
        cfg_safety_mode
        or env_safety_mode
        or safety_cfg.get("mode")
        or "guarded"
    ).strip().lower()
    allow_unsafe_shell = _parse_bool(
        env_allow_unsafe_shell if env_allow_unsafe_shell is not None else safety_cfg.get("allow_unsafe_shell")
    )
    auto_rollback = _parse_bool(
        env_auto_rollback if env_auto_rollback is not None else safety_cfg.get("auto_rollback")
    )
    safe_commands = safety_cfg.get("safe_commands", _default_safe_commands())
    if isinstance(safe_commands, str):
        safe_commands = [safe_commands]

    if safety_mode == "overdrive":
        allow_unsafe_shell = True

    memory_enabled = _parse_bool(memory_cfg.get("enabled", True))
    session_dir = memory_cfg.get("session_dir") or ".aiagent/sessions"
    max_history_messages = int(memory_cfg.get("max_history_messages") or 20)
    context_budget = int(memory_cfg.get("context_budget") or 150000)

    compaction_enabled = _parse_bool(compaction_cfg.get("enabled", True))
    trigger_ratio = float(compaction_cfg.get("trigger_ratio") or 0.8)
    prune_outputs = _parse_bool(compaction_cfg.get("prune_tool_outputs", True))
    tool_output_keep = int(compaction_cfg.get("tool_output_keep") or 5)

    return {
        "project_root": project_root,
        "provider": provider,
        "model": model,
        "primary_workspace": primary_workspace,
        "extra_workspaces": extra_workspaces,
        "default_workspace": cfg_workspace or env_workspace,
        "use_git_worktrees": use_git_worktrees,
        "max_iters": max_iters,
        "temperature": temperature,
        "safety_mode": safety_mode,
        "allow_unsafe_shell": allow_unsafe_shell,
        "safe_commands": safe_commands,
        "auto_rollback": auto_rollback,
        "hook_pre": _ensure_list(hooks_cfg.get("pre") or []),
        "hook_post": _ensure_list(hooks_cfg.get("post") or []),
        "openrouter": openrouter_cfg,
        "azure_openai": azure_cfg,
        "memory_enabled": memory_enabled,
        "memory_session_dir": session_dir,
        "memory_max_history_messages": max_history_messages,
        "memory_context_budget": context_budget,
        "compaction_enabled": compaction_enabled,
        "compaction_trigger_ratio": trigger_ratio,
        "compaction_prune_tool_outputs": prune_outputs,
        "compaction_tool_output_keep": tool_output_keep,
    }


def _ensure_list(value):
    if isinstance(value, str):
        return [value]
    return list(value) if isinstance(value, (list, tuple)) else []
