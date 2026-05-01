import os
from collections.abc import Callable
from typing import Protocol

from langchain_core.tools import BaseTool, tool

from aiagent.checkpoints import CheckpointManager
from aiagent.hooks import HookManager
from aiagent.tools.common import is_within_directory
from aiagent.tools.files import (
    append_file,
    edit_file,
    get_file_content,
    get_files_info,
    insert_file,
    write_file,
)
from aiagent.tools.shell import run_shell_command


class Workspace(Protocol):
    default_name: str

    def get(self, name: str) -> str:
        ...

    def list(self) -> list[tuple[str, str]]:
        ...


def to_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def build_tools(workspace_manager: Workspace, settings: dict[str, object]) -> list[BaseTool]:
    project_root = str(settings["project_root"])
    checkpoint_root = os.path.join(project_root, ".aiagent", "checkpoints")
    checkpoints = CheckpointManager(
        checkpoint_root,
        enabled=True,
        auto_rollback=bool(settings.get("auto_rollback", False)),
    )
    hook_paths = to_list(settings.get("hook_pre")) + to_list(settings.get("hook_post"))
    unique_hook_paths = list(dict.fromkeys(hook_paths))
    hooks = HookManager(unique_hook_paths, project_root)
    unsafe_commands = to_list(settings.get("unsafe_commands"))
    allow_unsafe_shell = bool(settings.get("allow_unsafe_shell"))

    def workspace_name(name: str | None) -> str:
        if name:
            return name
        return workspace_manager.default_name

    def run_tool(
        tool_name: str,
        args: dict[str, object],
        active_workspace: str,
        workdir: str,
        call: Callable[[], str],
        snapshot: str | None = None,
    ) -> str:
        checkpoint_id = checkpoints.start(tool_name, args, active_workspace, workdir)
        if snapshot:
            abs_path = os.path.abspath(os.path.join(workdir, snapshot))
            if is_within_directory(workdir, abs_path):
                checkpoints.snapshot_file(checkpoint_id, abs_path, os.path.normpath(snapshot))

        allow, reason = hooks.before_tool_call(
            {
                "tool": tool_name,
                "args": args,
                "workspace": active_workspace,
                "workdir": workdir,
                "checkpoint_id": checkpoint_id,
            }
        )
        if not allow:
            checkpoints.finish(checkpoint_id, status="blocked", error=reason)
            return f"Error: {reason}"

        try:
            result = call()
        except Exception as error:
            checkpoints.finish(checkpoint_id, status="error", error=str(error))
            if checkpoints.auto_rollback and checkpoint_id:
                checkpoints.rollback(checkpoint_id)
            return f"Error: {error}"

        checkpoints.finish(checkpoint_id, status="ok")
        hooks.after_tool_call(
            {
                "tool": tool_name,
                "args": args,
                "workspace": active_workspace,
                "workdir": workdir,
                "checkpoint_id": checkpoint_id,
                "result": result,
            }
        )
        return result

    @tool
    def list_workspaces(**extra: object) -> str:
        """List available workspaces and their root paths."""
        del extra
        items = [f"- {name}: {path}" for name, path in workspace_manager.list()]
        if not items:
            return "No workspaces configured."
        return "\n".join(items)

    @tool
    def list_files(directory: str = ".", workspace: str | None = None, **extra: object) -> str:
        """List files in a directory relative to the selected workspace."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "list_files",
            {"directory": directory, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: get_files_info(workdir, directory=directory),
        )

    @tool
    def read_file(
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_chars: int | None = None,
        workspace: str | None = None,
        **extra: object,
    ) -> str:
        """Read the contents of a file relative to the selected workspace."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "read_file",
            {
                "file_path": file_path,
                "workspace": active_workspace,
                "start_line": start_line,
                "end_line": end_line,
                "max_chars": max_chars,
            },
            active_workspace,
            workdir,
            lambda: get_file_content(
                workdir,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                max_chars=max_chars,
            ),
        )

    @tool
    def write_file_tool(
        file_path: str,
        content: str,
        workspace: str | None = None,
        **extra: object,
    ) -> str:
        """Write content to a file relative to the selected workspace (full overwrite)."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "write_file",
            {"file_path": file_path, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: write_file(workdir, file_path=file_path, content=content),
            snapshot=file_path,
        )

    @tool
    def edit_file_tool(
        file_path: str,
        edits: list[dict[str, object]],
        mode: str | None = None,
        workspace: str | None = None,
        **extra: object,
    ) -> str:
        """Apply targeted edits to a file."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "edit_file",
            {"file_path": file_path, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: edit_file(
                workdir,
                file_path=file_path,
                edits=edits,
                mode=mode or "strict",
            ),
            snapshot=file_path,
        )

    @tool
    def insert_file_tool(
        file_path: str,
        line: int,
        text: str,
        position: str | None = None,
        workspace: str | None = None,
        **extra: object,
    ) -> str:
        """Insert text before or after a line in a file."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "insert_file",
            {"file_path": file_path, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: insert_file(
                workdir,
                file_path=file_path,
                line=line,
                text=text,
                position=position or "before",
            ),
            snapshot=file_path,
        )

    @tool
    def append_file_tool(
        file_path: str,
        text: str,
        workspace: str | None = None,
        **extra: object,
    ) -> str:
        """Append text to the end of a file."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "append_file",
            {"file_path": file_path, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: append_file(workdir, file_path=file_path, text=text),
            snapshot=file_path,
        )

    @tool
    def run_shell_safe(command: str, workspace: str | None = None, **extra: object) -> str:
        """Run a shell command with unsafe-command denylist enforcement."""
        del extra
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "run_shell_safe",
            {"command": command, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: run_shell_command(
                workdir,
                command=command,
                safe_mode=True,
                unsafe_commands=unsafe_commands,
            ),
        )

    @tool
    def run_shell_unsafe(command: str, workspace: str | None = None, **extra: object) -> str:
        """Run an unsafe shell command (requires overdrive mode)."""
        del extra
        if not allow_unsafe_shell:
            return (
                "Error: unsafe shell commands are disabled. "
                "Set safety_mode='overdrive' or allow_unsafe_shell=true."
            )
        active_workspace = workspace_name(workspace)
        workdir = workspace_manager.get(active_workspace)
        return run_tool(
            "run_shell_unsafe",
            {"command": command, "workspace": active_workspace},
            active_workspace,
            workdir,
            lambda: run_shell_command(
                workdir,
                command=command,
                safe_mode=False,
                unsafe_commands=unsafe_commands,
            ),
        )

    @tool
    def list_checkpoints(**extra: object) -> str:
        """List recent checkpoints."""
        del extra
        items = checkpoints.list_checkpoints()
        if not items:
            return "No checkpoints recorded."
        lines = [f"- {item['id']} ({item.get('tool')}): {item.get('status')}" for item in items[:10]]
        return "\n".join(lines)

    @tool
    def rollback_checkpoint(checkpoint_id: str, **extra: object) -> str:
        """Rollback changes captured in a checkpoint."""
        del extra
        return checkpoints.rollback(checkpoint_id)

    return [
        list_workspaces,
        list_files,
        read_file,
        write_file_tool,
        edit_file_tool,
        insert_file_tool,
        append_file_tool,
        run_shell_safe,
        run_shell_unsafe,
        list_checkpoints,
        rollback_checkpoint,
    ]
