from __future__ import annotations

from pathlib import Path

from aiagent.tools import build_tools
from aiagent.workspaces import Workspace


def settings_build(project_root: Path, hook_pre: list[str] | None = None, hook_post: list[str] | None = None) -> dict[str, object]:
    return {
        "project_root": str(project_root),
        "auto_rollback": False,
        "hook_pre": hook_pre or [],
        "hook_post": hook_post or [],
        "unsafe_commands": ["rm", "rmdir", "del", "erase", "remove-item", "format", "mkfs", "shutdown"],
        "allow_unsafe_shell": False,
    }


def tool_get(tools: list[object], name: str) -> object:
    for item in tools:
        if getattr(item, "name", "") == name:
            return item
    raise AssertionError(f"Tool not found: {name}")


def test_hooks_before_after_called(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    workspace = tmp_path / "workspace"
    project_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "hook.log"
    hook_path = project_root / "hook_trace.py"
    hook_path.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "def before_tool_call(context):",
                "    path = Path(context['workdir']) / 'hook.log'",
                "    path.write_text(path.read_text(encoding='utf-8') + 'before\\n' if path.exists() else 'before\\n', encoding='utf-8')",
                "    return True",
                "def after_tool_call(context):",
                "    path = Path(context['workdir']) / 'hook.log'",
                "    path.write_text(path.read_text(encoding='utf-8') + 'after\\n', encoding='utf-8')",
            ]
        ),
        encoding="utf-8",
    )

    manager = Workspace(str(project_root), {"primary": str(workspace)}, "primary")
    tools = build_tools(manager, settings_build(project_root, [str(hook_path)], [str(hook_path)]))
    write_tool = tool_get(tools, "write_file_tool")
    result = write_tool.invoke({"file_path": "sample.txt", "content": "hello"})

    assert "Successfully wrote" in result
    assert (workspace / "sample.txt").read_text(encoding="utf-8") == "hello"
    assert log_path.read_text(encoding="utf-8").strip().splitlines() == ["before", "after"]


def test_hook_can_block_tool(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    workspace = tmp_path / "workspace"
    project_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    hook_path = project_root / "hook_block.py"
    hook_path.write_text(
        "\n".join(
            [
                "def before_tool_call(context):",
                "    if context.get('tool') == 'write_file':",
                "        return {'allow': False, 'reason': 'blocked-by-test'}",
                "    return True",
            ]
        ),
        encoding="utf-8",
    )

    manager = Workspace(str(project_root), {"primary": str(workspace)}, "primary")
    tools = build_tools(manager, settings_build(project_root, [str(hook_path)], []))
    write_tool = tool_get(tools, "write_file_tool")
    result = write_tool.invoke({"file_path": "blocked.txt", "content": "x"})

    assert "blocked-by-test" in result
    assert not (workspace / "blocked.txt").exists()


def test_checkpoint_rollback_restores_file(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    workspace = tmp_path / "workspace"
    project_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "target.txt"
    target.write_text("one\n", encoding="utf-8")

    manager = Workspace(str(project_root), {"primary": str(workspace)}, "primary")
    tools = build_tools(manager, settings_build(project_root))
    edit_tool = tool_get(tools, "edit_file_tool")
    list_tool = tool_get(tools, "list_checkpoints")
    rollback_tool = tool_get(tools, "rollback_checkpoint")

    result = edit_tool.invoke(
        {
            "file_path": "target.txt",
            "edits": [{"old_text": "one", "new_text": "two", "count": 1}],
            "mode": "strict",
        }
    )
    assert "Applied 1 edit(s)" in result
    assert target.read_text(encoding="utf-8") == "two\n"

    listing = list_tool.invoke({})
    first = listing.splitlines()[0]
    checkpoint_id = first.split(" ", 2)[1]
    rollback = rollback_tool.invoke({"checkpoint_id": checkpoint_id})

    assert "Rollback complete." in rollback
    assert target.read_text(encoding="utf-8") == "one\n"


def test_shell_safe_and_unsafe_modes(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    workspace = tmp_path / "workspace"
    project_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    manager = Workspace(str(project_root), {"primary": str(workspace)}, "primary")
    tools = build_tools(manager, settings_build(project_root))
    safe_tool = tool_get(tools, "run_shell_safe")
    unsafe_tool = tool_get(tools, "run_shell_unsafe")

    safe_result = safe_tool.invoke({"command": "python --version"})
    unsafe_result = unsafe_tool.invoke({"command": "python --version"})

    assert "Python" in safe_result
    assert "unsafe shell commands are disabled" in unsafe_result
