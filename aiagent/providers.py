from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


ALLOWED_PROVIDERS = {"openai", "anthropic", "gemini", "groq", "ollama"}


def get_llm(provider, model, temperature=0.2):
    if not provider or not model:
        raise ValueError("Provider and model are required.")
    provider = provider.lower().strip()

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

    raise ValueError(
        f"Unknown provider '{provider}'. Expected one of: openai, anthropic, gemini, groq, ollama."
    )
