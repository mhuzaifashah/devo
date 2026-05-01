from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from src.agent import run_agent
from src.session_store import SessionStore
from src.settings import unsafe_default
from src.workspaces import Workspace

PROMPTS = [
    "Call list_workspaces and report workspace names.",
    "Call list_files at workspace root and report key frontend folders.",
    "Find the landing page file and call read_file for its first 180 lines.",
    "Create .devo_test/tool_probe.md using write_file_tool with line 'probe:start'.",
    "Append 'probe:append' to .devo_test/tool_probe.md using append_file_tool.",
    "Insert 'probe:insert' before line 2 in .devo_test/tool_probe.md using insert_file_tool.",
    "Use edit_file_tool to replace 'probe:insert' with 'probe:edit' in .devo_test/tool_probe.md.",
    "Run run_shell_safe with command 'python --version' and report output.",
    "Call list_checkpoints and return the latest checkpoint id.",
    "Call rollback_checkpoint on the latest checkpoint id from list_checkpoints.",
    "Identify navbar component file and read only lines that define glass styles.",
    "Improve navbar glass look: slightly stronger blur, subtle border, maintain readability.",
    "Tune first section spacing for desktop and mobile without changing text content.",
    "Add a small accent hover transition for navbar links using existing style conventions.",
    "Refine the second section card alignment for consistent vertical rhythm.",
    "Update third section CTA button states: normal, hover, focus-visible.",
    "Run list_files and read_file to confirm all changed files compile logically.",
    (
        "Write .devo_test/summary.md with bullet list of files changed and why. "
        "Do not rely on prior chat memory; first use list_files/read_file to infer final file state."
    ),
]

REQUIRED_TOOLS = {
    "list_workspaces",
    "list_files",
    "read_file",
    "write_file_tool",
    "edit_file_tool",
    "insert_file_tool",
    "append_file_tool",
    "run_shell_safe",
    "list_checkpoints",
    "rollback_checkpoint",
}


def enabled() -> bool:
    return os.environ.get("AIAGENT_RUN_LLM_TESTS", "").strip() == "1"


def provider_model() -> tuple[str, str]:
    provider = os.environ.get("AIAGENT_TEST_PROVIDER", "").strip()
    model = os.environ.get("AIAGENT_TEST_MODEL", "").strip()
    if provider and model:
        return provider, model
    pytest.fail("Set AIAGENT_TEST_PROVIDER and AIAGENT_TEST_MODEL when AIAGENT_RUN_LLM_TESTS=1.")
    raise AssertionError("unreachable")


def frontend_source() -> Path:
    path = os.environ.get(
        "AIAGENT_TEST_FRONTEND_DIR",
        r"D:\Code\Python\AGENT CODING\frontend",
    ).strip()
    root = Path(path)
    if root.is_dir():
        return root
    pytest.fail(f"Frontend test directory not found: {root}")
    raise AssertionError("unreachable")


@pytest.mark.integration
def test_session_prompt_suite_frontend(tmp_path: Path) -> None:
    if not enabled():
        pytest.skip("Set AIAGENT_RUN_LLM_TESTS=1 to run LLM integration tests.")

    provider, model = provider_model()
    source = frontend_source()

    workspace = tmp_path / "frontend_copy"
    shutil.copytree(
        source,
        workspace,
        ignore=shutil.ignore_patterns("node_modules", ".next", "dist", "build", ".git"),
    )

    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    system_source = Path(__file__).resolve().parents[1] / "src" / "prompts" / "system.md"
    (project_root / "system.md").write_text(system_source.read_text(encoding="utf-8"), encoding="utf-8")

    manager = Workspace(
        project_root=str(project_root),
        workspaces={"primary": str(workspace)},
        default_name="primary",
    )
    settings: dict[str, object] = {
        "project_root": str(project_root),
        "temperature": 0.1,
        "max_iters": 30,
        "safety_mode": "guarded",
        "allow_unsafe_shell": False,
        "unsafe_commands": unsafe_default(),
        "auto_rollback": False,
        "hook_pre": [],
        "hook_post": [],
        "memory_enabled": True,
        "memory_max_history_messages": 20,
        "memory_context_budget": 150000,
        "compaction_enabled": True,
        "compaction_trigger_ratio": 0.8,
        "compaction_prune_tool_outputs": True,
        "compaction_tool_output_keep": 5,
        "openrouter": {},
        "azure_openai": {},
        "ollama": {},
        "mistral": {},
    }

    store = SessionStore(str(project_root / ".aiagent" / "sessions"))
    sid = store.create_session(provider, model, manager.list())
    summary, history = store.load_session(sid)

    hits: set[str] = set()
    for prompt in PROMPTS:
        output, fresh, next_summary, base_history = run_agent(
            prompt=prompt,
            provider=provider,
            model=model,
            workspace_manager=manager,
            settings=settings,
            history=history,
            summary_text=summary,
            verbose=False,
        )
        assert output.strip(), f"Empty model output for prompt: {prompt}"
        batch = [{"role": "user", "content": prompt}, *fresh]
        history = base_history + batch
        summary = next_summary
        store.append_messages(sid, batch)
        store.write_summary(sid, summary)
        for item in fresh:
            role = str(item.get("role") or "")
            name = str(item.get("name") or "")
            if role == "tool" and name:
                hits.add(name)

    summary_path = workspace / ".devo_test" / "summary.md"
    assert summary_path.is_file(), "Expected .devo_test/summary.md to be created."
    summary_content = summary_path.read_text(encoding="utf-8").strip()
    assert summary_content, "Expected .devo_test/summary.md to contain content."

    missing = REQUIRED_TOOLS - hits
    assert not missing, f"Tools not exercised by prompt suite: {sorted(missing)}"
