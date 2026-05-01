from __future__ import annotations

import argparse
import os

from src.agent import run_agent
from src.session_store import SessionStore
from src.settings import load_settings
from src.ui import ConsoleUI
from src.workspaces import WorkspaceManager, build_workspace_manager

Settings = dict[str, object]
Message = dict[str, object]
History = list[Message]


def text(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def shared(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        help="Model provider (openai, anthropic, gemini, groq, ollama, mistral, openrouter, azure_openai)",
    )
    parser.add_argument("--model", help="Model name or provider:model")
    parser.add_argument("--workdir", help="Primary workspace path override")
    parser.add_argument("--workspace", help="Default workspace name")
    parser.add_argument("--verbose", action="store_true", help="Verbose agent output")
    parser.add_argument("--plain", action="store_true", help="Plain output (no rich UI)")


def parser_build() -> tuple[argparse.ArgumentParser, list[argparse.ArgumentParser]]:
    parser = argparse.ArgumentParser(description="AI coding agent", add_help=False)
    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Show this help message and exit (includes subcommands).",
    )
    subs = parser.add_subparsers(dest="command", required=False)
    devo = subs.add_parser("devo", help="Start or resume a session")
    devo.add_argument("prompt", nargs="?", help="Initial prompt to run")
    devo.add_argument("--once", action="store_true", help="Run once and exit")
    devo.add_argument("--session", help="Resume a session by id")
    devo.add_argument("--list-session", action="store_true", help="List sessions")
    shared(devo)
    return parser, [devo]


def help_show(parser: argparse.ArgumentParser, items: list[argparse.ArgumentParser]) -> None:
    print(parser.format_help())
    for item in items:
        print("\n" + item.format_help())


def args_get(
    parser: argparse.ArgumentParser,
    items: list[argparse.ArgumentParser],
) -> argparse.Namespace:
    args = parser.parse_args()
    if args.help:
        help_show(parser, items)
        raise SystemExit(0)
    if args.command:
        return args
    parser.error("A command is required. Use --help to see available commands.")
    raise SystemExit(2)


def settings_get(args: argparse.Namespace) -> Settings:
    settings = load_settings()
    if args.workdir:
        settings["primary_workspace"] = args.workdir
    if args.workspace:
        settings["default_workspace"] = args.workspace
    return settings


def store_get(settings: Settings) -> SessionStore:
    base = text(settings.get("memory_session_dir"))
    root = text(settings.get("project_root"))
    if os.path.isabs(base):
        return SessionStore(base)
    return SessionStore(os.path.join(root, base))


def sessions_show(store: SessionStore, ui: ConsoleUI) -> None:
    rows = store.list_sessions()
    if not rows:
        ui.print_info("No sessions found.")
        return
    for index, meta in enumerate(rows, start=1):
        sid = text(meta.get("session_id"))
        stamp = text(meta.get("last_used_at"))
        ui.print_info(f"{index}. {sid}  {stamp}")


def model_get(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    settings: Settings,
) -> tuple[str, str]:
    provider = text(args.provider) or text(settings.get("provider"))
    model = text(args.model) or text(settings.get("model"))

    if model and ":" in model:
        parts = model.split(":", 1)
        model_provider = parts[0].strip().lower()
        model_name = parts[1].strip()
        if provider and provider.lower() != model_provider:
            parser.error(f"Conflicting provider: '{provider}' vs model '{model}'. Use one.")
        provider = model_provider
        model = model_name

    if provider and model:
        return provider, model
    parser.error(
        "Provider and model are required. Set them in aiagent.toml, "
        "AIAGENT_PROVIDER/AIAGENT_MODEL, or pass --provider/--model."
    )
    raise SystemExit(2)


def once_run(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    provider: str,
    model: str,
    manager: WorkspaceManager,
    settings: Settings,
    ui: ConsoleUI,
) -> bool:
    if not args.once:
        return False
    if not args.prompt:
        parser.error("--once requires a prompt.")
    try:
        output, _, _, _ = run_agent(
            prompt=args.prompt,
            provider=provider,
            model=model,
            workspace_manager=manager,
            settings=settings,
            verbose=bool(args.verbose),
        )
    except Exception as error:
        ui.print_error(f"Error: {error}")
        return True
    ui.print_output(output)
    return True


def session_get(
    args: argparse.Namespace,
    provider: str,
    model: str,
    manager: WorkspaceManager,
    store: SessionStore,
    ui: ConsoleUI,
) -> str:
    if not args.session:
        sid = store.create_session(provider, model, manager.list())
        ui.print_info(f"Session started: {sid}")
        return sid

    value = args.session.strip()
    if value.isdigit():
        rows = store.list_sessions()
        index = int(value)
        if index < 1 or index > len(rows):
            ui.print_error(f"Session index '{value}' not found.")
            return ""
        return text(rows[index - 1].get("session_id"))

    if store.session_exists(value):
        return value
    ui.print_error(f"Session '{value}' not found.")
    return ""


def turn_run(
    prompt: str,
    provider: str,
    model: str,
    manager: WorkspaceManager,
    settings: Settings,
    store: SessionStore,
    sid: str,
    ui: ConsoleUI,
    verbose: bool,
    summary: str,
    history: History,
) -> tuple[str, History]:
    output, fresh, next_summary, next_history = run_agent(
        prompt=prompt,
        provider=provider,
        model=model,
        workspace_manager=manager,
        settings=settings,
        history=history,
        summary_text=summary,
        verbose=verbose,
    )
    batch: History = [{"role": "user", "content": prompt}]
    batch.extend(fresh)
    final_history = next_history + batch
    store.append_messages(sid, batch)
    store.write_summary(sid, next_summary)
    ui.print_output(output)
    return next_summary, final_history


def loop_run(
    args: argparse.Namespace,
    provider: str,
    model: str,
    manager: WorkspaceManager,
    settings: Settings,
    store: SessionStore,
    sid: str,
    ui: ConsoleUI,
) -> None:
    summary, history = store.load_session(sid)

    if args.prompt:
        try:
            summary, history = turn_run(
                prompt=args.prompt,
                provider=provider,
                model=model,
                manager=manager,
                settings=settings,
                store=store,
                sid=sid,
                ui=ui,
                verbose=bool(args.verbose),
                summary=summary,
                history=history,
            )
        except Exception as error:
            ui.print_error(f"Error: {error}")
            return

    try:
        while True:
            prompt = ui.prompt().strip()
            if not prompt:
                continue
            summary, history = turn_run(
                prompt=prompt,
                provider=provider,
                model=model,
                manager=manager,
                settings=settings,
                store=store,
                sid=sid,
                ui=ui,
                verbose=bool(args.verbose),
                summary=summary,
                history=history,
            )
    except KeyboardInterrupt:
        ui.print_info("\nSession ended.")


def main() -> None:
    parser, items = parser_build()
    args = args_get(parser, items)
    settings = settings_get(args)
    store = store_get(settings)
    ui = ConsoleUI(enabled=not args.plain)

    if args.list_session:
        sessions_show(store, ui)
        return

    provider, model = model_get(parser, args, settings)
    manager = build_workspace_manager(settings)
    ui.banner(provider, model, manager, text(settings.get("safety_mode")))

    if once_run(parser, args, provider, model, manager, settings, ui):
        return

    sid = session_get(args, provider, model, manager, store, ui)
    if not sid:
        return
    loop_run(args, provider, model, manager, settings, store, sid, ui)


if __name__ == "__main__":
    main()
