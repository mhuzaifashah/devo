import argparse

from aiagent.agent import run_agent
from aiagent.settings import load_settings


def main():
    parser = argparse.ArgumentParser(description="AI coding agent")
    parser.add_argument("prompt", help="Prompt to send to the agent")
    parser.add_argument("--provider", help="Model provider (openai, anthropic, gemini, groq, ollama)")
    parser.add_argument("--model", help="Model name or provider:model")
    parser.add_argument("--workdir", help="Working directory for tools")
    parser.add_argument("--verbose", action="store_true", help="Verbose agent output")
    args = parser.parse_args()

    settings = load_settings()
    provider = args.provider or settings["provider"]
    model = args.model or settings["model"]
    workdir = args.workdir or settings["workdir"]
    max_iters = settings["max_iters"]
    temperature = settings["temperature"]

    if model and ":" in model:
        model_provider, model_name = model.split(":", 1)
        model_provider = model_provider.strip().lower()
        model_name = model_name.strip()
        if provider and provider.lower() != model_provider:
            parser.error(
                f"Conflicting provider: '{provider}' vs model '{model}'. Use one."
            )
        provider = model_provider
        model = model_name

    if not provider or not model:
        parser.error(
            "Provider and model are required. Set them in aiagent.toml, "
            "AIAGENT_PROVIDER/AIAGENT_MODEL, or pass --provider/--model."
        )

    output = run_agent(
        prompt=args.prompt,
        provider=provider,
        model=model,
        workdir=workdir,
        max_iters=max_iters,
        temperature=temperature,
        verbose=args.verbose,
    )
    print(output)


if __name__ == "__main__":
    main()
