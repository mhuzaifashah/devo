import os

from langchain_core.tools import tool

from aiagent.checkpoints import CheckpointManager
from aiagent.hooks import HookManager
from functions.edit_file import edit_file, insert_file, append_file
from functions.get_files_info import get_files_info
from functions.get_file_content import get_file_content
from functions.write_file import write_file
from functions.run_shell_command import run_shell_command


def build_tools(workspace_manager, settings):
    checkpoint_root = os.path.join(settings["project_root"], ".aiagent", "checkpoints")
    checkpoints = CheckpointManager(
        checkpoint_root,
        enabled=True,
        auto_rollback=settings.get("auto_rollback", False),
    )
    hook_paths = list(dict.fromkeys(settings.get("hook_pre", []) + settings.get("hook_post", [])))
    hooks = HookManager(hook_paths, settings["project_root"])

    def _resolve_workspace(name):
        return name or workspace_manager.default_name

    def _run_with_hooks(tool_name, args, workspace_name, workdir, func, snapshot_path=None):
        checkpoint_id = checkpoints.start(tool_name, args, workspace_name, workdir)
        if snapshot_path:
            abs_workdir = os.path.abspath(workdir)
            abs_path = os.path.abspath(os.path.join(workdir, snapshot_path))
            if abs_path.startswith(abs_workdir):
                rel_path = os.path.normpath(snapshot_path)
                checkpoints.snapshot_file(checkpoint_id, abs_path, rel_path)

        allow, reason = hooks.before_tool_call(
            {
                "tool": tool_name,
                "args": args,
                "workspace": workspace_name,
                "workdir": workdir,
                "checkpoint_id": checkpoint_id,
            }
        )
        if not allow:
            checkpoints.finish(checkpoint_id, status="blocked", error=reason)
            return f"Error: {reason}"

        try:
            result = func()
            checkpoints.finish(checkpoint_id, status="ok")
            hooks.after_tool_call(
                {
                    "tool": tool_name,
                    "args": args,
                    "workspace": workspace_name,
                    "workdir": workdir,
                    "checkpoint_id": checkpoint_id,
                    "result": result,
                }
            )
            return result
        except Exception as e:
            checkpoints.finish(checkpoint_id, status="error", error=str(e))
            if checkpoints.auto_rollback:
                checkpoints.rollback(checkpoint_id)
            return f"Error: {e}"

    @tool
    def list_workspaces(**_ignored: object) -> str:
        """List available workspaces and their root paths."""
        lines = [f"- {name}: {path}" for name, path in workspace_manager.list()]
        return "\n".join(lines) if lines else "No workspaces configured."

    @tool
    def list_files(directory: str = ".", workspace: str | None = None, **_ignored: object) -> str:
        """List files in a directory relative to the selected workspace."""
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "list_files",
            {"directory": directory, "workspace": workspace_name},
            workspace_name,
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
        **_ignored: object,
    ) -> str:
        """Read the contents of a file relative to the selected workspace.

        Supports optional start_line/end_line (1-based) and max_chars truncation.
        """
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "read_file",
            {
                "file_path": file_path,
                "workspace": workspace_name,
                "start_line": start_line,
                "end_line": end_line,
                "max_chars": max_chars,
            },
            workspace_name,
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
        **_ignored: object,
    ) -> str:
        """Write content to a file relative to the selected workspace (full overwrite)."""
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "write_file",
            {"file_path": file_path, "workspace": workspace_name},
            workspace_name,
            workdir,
            lambda: write_file(workdir, file_path=file_path, content=content),
            snapshot_path=file_path,
        )

    @tool
    def edit_file_tool(
        file_path: str,
        edits: list[dict],
        mode: str | None = None,
        workspace: str | None = None,
        **_ignored: object,
    ) -> str:
        """Apply targeted edits to a file.

        Edits can be:
        - text replacements: {"old_text": "...", "new_text": "...", "count": 1}
        - line ranges: {"start_line": 10, "end_line": 12, "new_text": "..."}
        """
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "edit_file",
            {"file_path": file_path, "workspace": workspace_name},
            workspace_name,
            workdir,
            lambda: edit_file(
                workdir,
                file_path=file_path,
                edits=edits,
                mode=mode or "strict",
            ),
            snapshot_path=file_path,
        )

    @tool
    def insert_file_tool(
        file_path: str,
        line: int,
        text: str,
        position: str | None = None,
        workspace: str | None = None,
        **_ignored: object,
    ) -> str:
        """Insert text before or after a line in a file."""
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "insert_file",
            {"file_path": file_path, "workspace": workspace_name},
            workspace_name,
            workdir,
            lambda: insert_file(
                workdir,
                file_path=file_path,
                line=line,
                text=text,
                position=position or "before",
            ),
            snapshot_path=file_path,
        )

    @tool
    def append_file_tool(
        file_path: str,
        text: str,
        workspace: str | None = None,
        **_ignored: object,
    ) -> str:
        """Append text to the end of a file."""
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "append_file",
            {"file_path": file_path, "workspace": workspace_name},
            workspace_name,
            workdir,
            lambda: append_file(
                workdir,
                file_path=file_path,
                text=text,
            ),
            snapshot_path=file_path,
        )


    @tool
    def run_shell_safe(
        command: str,
        workspace: str | None = None,
        **_ignored: object,
    ) -> str:
        """Run a safe shell command (read-only, allowlist enforced)."""
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "run_shell_safe",
            {"command": command, "workspace": workspace_name},
            workspace_name,
            workdir,
            lambda: run_shell_command(
                workdir,
                command=command,
                safe_mode=True,
                safe_prefixes=settings.get("safe_commands", []),
            ),
        )

    @tool
    def run_shell_unsafe(
        command: str,
        workspace: str | None = None,
        **_ignored: object,
    ) -> str:
        """Run an unsafe shell command (requires overdrive mode)."""
        if not settings.get("allow_unsafe_shell"):
            return (
                "Error: unsafe shell commands are disabled. "
                "Set safety_mode='overdrive' or allow_unsafe_shell=true."
            )
        workspace_name = _resolve_workspace(workspace)
        workdir = workspace_manager.get(workspace_name)
        return _run_with_hooks(
            "run_shell_unsafe",
            {"command": command, "workspace": workspace_name},
            workspace_name,
            workdir,
            lambda: run_shell_command(
                workdir,
                command=command,
                safe_mode=False,
                safe_prefixes=settings.get("safe_commands", []),
            ),
        )

    @tool
    def list_checkpoints(**_ignored: object) -> str:
        """List recent checkpoints."""
        items = checkpoints.list_checkpoints()
        if not items:
            return "No checkpoints recorded."
        lines = []
        for item in items[:10]:
            lines.append(f"- {item['id']} ({item.get('tool')}): {item.get('status')}")
        return "\n".join(lines)

    @tool
    def rollback_checkpoint(checkpoint_id: str, **_ignored: object) -> str:
        """Rollback changes captured in a checkpoint."""
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
