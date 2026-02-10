import os

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI


ALLOWED_PROVIDERS = {
    "openai",
    "anthropic",
    "gemini",
    "groq",
    "ollama",
    "openrouter",
    "open_router",
    "azure_openai",
    "azure-openai",
}


def _openrouter_headers(settings):
    headers = {}
    site_url = os.environ.get("OPENROUTER_SITE_URL") or settings.get("site_url")
    app_name = os.environ.get("OPENROUTER_APP_NAME") or settings.get("app_name")
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name
    return headers or None


def get_llm(provider, model, temperature=0.2, settings=None):
    if not provider or not model:
        raise ValueError("Provider and model are required.")
    provider = provider.lower().strip()
    settings = settings or {}

    if provider == "openai":
        return ChatOpenAI(model=model, temperature=temperature)
    if provider == "anthropic":
        return ChatAnthropic(model=model, temperature=temperature)
    if provider == "gemini":
        return ChatGoogleGenerativeAI(model=model, temperature=temperature)
    if provider == "groq":
        return ChatGroq(model=model, temperature=temperature)
    if provider == "ollama":
        return ChatOllama(model=model, temperature=temperature)
    if provider == "mistral":
        raise ValueError(
            "Mistral is temporarily disabled due to dependency conflicts with "
            "langchain==1.2.7. Use OpenRouter with a Mistral model instead."
        )
    if provider in {"openrouter", "open_router"}:
        base_url = settings.get("base_url") or "https://openrouter.ai/api/v1"
        api_key = os.environ.get("OPENROUTER_API_KEY")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
            default_headers=_openrouter_headers(settings),
        )
    if provider in {"azure_openai", "azure-openai"}:
        azure_endpoint = settings.get("endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_version = settings.get("api_version") or os.environ.get("OPENAI_API_VERSION")
        azure_deployment = settings.get("deployment") or model
        azure_model = settings.get("model_name")
        return AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            azure_deployment=azure_deployment,
            model=azure_model or model,
            temperature=temperature,
        )

    raise ValueError(
        f"Unknown provider '{provider}'. Expected one of: {', '.join(sorted(ALLOWED_PROVIDERS))}."
    )
