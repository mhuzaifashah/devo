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


def load_settings():
    load_dotenv()

    config_path = os.path.join(os.getcwd(), "aiagent.toml")
    config = _load_toml_config(config_path)
    agent_cfg = config.get("agent", {})

    cfg_provider = agent_cfg.get("provider")
    cfg_model = agent_cfg.get("model")
    cfg_workdir = agent_cfg.get("workdir")
    cfg_max_iters = agent_cfg.get("max_iters")
    cfg_temperature = agent_cfg.get("temperature")

    env_provider = os.environ.get("AIAGENT_PROVIDER")
    env_model = os.environ.get("AIAGENT_MODEL")
    env_workdir = os.environ.get("AIAGENT_WORKDIR")
    env_max_iters = os.environ.get("AIAGENT_MAX_ITERS")
    env_temperature = os.environ.get("AIAGENT_TEMPERATURE")

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

    workdir = cfg_workdir or env_workdir or os.getcwd()
    max_iters = int(cfg_max_iters or env_max_iters or "20")
    temperature = float(cfg_temperature or env_temperature or "0.2")

    return {
        "provider": provider,
        "model": model,
        "workdir": workdir,
        "max_iters": max_iters,
        "temperature": temperature,
    }
