import argparse
import os

from aiagent.agent import run_agent
from aiagent.session_store import SessionStore
from aiagent.settings import load_settings
from aiagent.ui import ConsoleUI
from aiagent.workspaces import build_workspace_manager


class _HelpAll(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print(parser.format_help())
        subparsers = getattr(parser, "_subparsers_list", [])
        for sub in subparsers:
            print("\n" + sub.format_help())
        parser.exit()


def _add_shared_args(parser):
    parser.add_argument(
        "--provider",
        help="Model provider (openai, anthropic, gemini, groq, ollama, mistral, openrouter, azure_openai)",
    )
    parser.add_argument("--model", help="Model name or provider:model")
    parser.add_argument("--workdir", help="Primary workspace path override")
    parser.add_argument("--workspace", help="Default workspace name")
    parser.add_argument("--verbose", action="store_true", help="Verbose agent output")
    parser.add_argument("--plain", action="store_true", help="Plain output (no rich UI)")


def _resolve_provider_model(parser, settings, provider, model):
    provider = provider or settings["provider"]
    model = model or settings["model"]
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
    return provider, model


def main():
    parser = argparse.ArgumentParser(description="AI coding agent", add_help=False)
    parser.add_argument(
        "-h",
        "--help",
        action=_HelpAll,
        nargs=0,
        help="Show this help message and exit (includes subcommands).",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    devo = subparsers.add_parser("devo", help="Start or resume a session")
    devo.add_argument("prompt", nargs="?", help="Initial prompt to run")
    devo.add_argument("--once", action="store_true", help="Run once and exit")
    devo.add_argument("--session", help="Resume a session by id")
    devo.add_argument("--list-session", action="store_true", help="List sessions")
    _add_shared_args(devo)

    parser._subparsers_list = [devo]
    args = parser.parse_args()
    if not args.command:
        parser.error("A command is required. Use --help to see available commands.")

    settings = load_settings()
    if args.workdir:
        settings["primary_workspace"] = args.workdir
    if args.workspace:
        settings["default_workspace"] = args.workspace

    session_dir = settings["memory_session_dir"]
    if not os.path.isabs(session_dir):
        session_dir = os.path.join(settings["project_root"], session_dir)
    store = SessionStore(session_dir)

    if args.list_session:
        ui = ConsoleUI(enabled=not args.plain)
        sessions = store.list_sessions()
        if not sessions:
            ui.print_info("No sessions found.")
            return
        for idx, meta in enumerate(sessions, start=1):
            ui.print_info(
                f"{idx}. {meta.get('session_id')}  {meta.get('last_used_at')}"
            )
        return

    provider, model = _resolve_provider_model(parser, settings, args.provider, args.model)

    ui = ConsoleUI(enabled=not args.plain)
    workspace_manager = build_workspace_manager(settings)
    ui.banner(provider, model, workspace_manager, settings["safety_mode"])

    if args.once:
        if not args.prompt:
            parser.error("--once requires a prompt.")
        try:
            output, _, _, _ = run_agent(
                prompt=args.prompt,
                provider=provider,
                model=model,
                workspace_manager=workspace_manager,
                settings=settings,
                verbose=args.verbose,
            )
        except Exception as e:
            ui.print_error(f"Error: {e}")
            return
        ui.print_output(output)
        return

    if args.session:
        session_value = args.session.strip()
        if session_value.isdigit():
            sessions = store.list_sessions()
            index = int(session_value)
            if index < 1 or index > len(sessions):
                ui.print_error(f"Session index '{session_value}' not found.")
                return
            session_id = sessions[index - 1].get("session_id")
        else:
            if not store.session_exists(session_value):
                ui.print_error(f"Session '{session_value}' not found.")
                return
            session_id = session_value
    else:
        session_id = store.create_session(provider, model, workspace_manager.list())
        ui.print_info(f"Session started: {session_id}")

    summary_text, history = store.load_session(session_id)

    def _run_turn(user_prompt):
        nonlocal summary_text, history
        output, new_messages, summary_text, history = run_agent(
            prompt=user_prompt,
            provider=provider,
            model=model,
            workspace_manager=workspace_manager,
            settings=settings,
            history=history,
            summary_text=summary_text,
            verbose=args.verbose,
        )
        turn_messages = [{"role": "user", "content": user_prompt}] + new_messages
        history = history + turn_messages
        store.append_messages(session_id, turn_messages)
        store.write_summary(session_id, summary_text)
        ui.print_output(output)

    if args.prompt:
        try:
            _run_turn(args.prompt)
        except Exception as e:
            ui.print_error(f"Error: {e}")
            return

    try:
        while True:
            user_prompt = ui.prompt().strip()
            if not user_prompt:
                continue
            _run_turn(user_prompt)
    except KeyboardInterrupt:
        ui.print_info("\nSession ended.")


if __name__ == "__main__":
    main()
