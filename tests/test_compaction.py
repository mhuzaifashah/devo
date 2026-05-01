from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage

from src import agent as agent_module
from src.compaction import compact_history, estimate_messages_tokens, prune_tool_outputs


class SummaryModel:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages: list[object]) -> object:
        self.calls += 1
        del messages
        return type("Resp", (), {"content": "TRACE: compaction triggered"})()


class EchoAgent:
    def invoke(self, payload: dict[str, object]) -> dict[str, object]:
        messages = list(payload.get("messages", []))
        messages.append(AIMessage(content="ok"))
        return {"messages": messages}


class CaptureAgent:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def invoke(self, payload: dict[str, object]) -> dict[str, object]:
        self.messages = list(payload.get("messages", []))
        return {"messages": self.messages + [AIMessage(content="ok")]}


class WorkspaceStub:
    def __init__(self, root: Path) -> None:
        self.default_name = "primary"
        self.root = str(root)

    def get(self, name: str) -> str:
        del name
        return self.root

    def list(self) -> list[tuple[str, str]]:
        return [("primary", self.root)]


def test_prune_tool_outputs_keeps_user_assistant_and_last_10_tools() -> None:
    messages = [{"role": "user", "content": "u1"}, {"role": "assistant", "content": "a1"}]
    for index in range(15):
        messages.append({"role": "tool", "content": f"t{index}"})
    pruned = prune_tool_outputs(messages, keep=10)
    roles = [item["role"] for item in pruned]
    assert roles.count("user") == 1
    assert roles.count("assistant") == 1
    assert roles.count("tool") == 10
    tool_values = [item["content"] for item in pruned if item["role"] == "tool"]
    assert tool_values == [f"t{index}" for index in range(5, 15)]


def test_compaction_summary_and_trim() -> None:
    llm = SummaryModel()
    messages = [
        {"role": "user", "content": "A" * 1500},
        {"role": "assistant", "content": "B" * 1500},
        {"role": "tool", "content": "C" * 1500},
        {"role": "assistant", "content": "D" * 1500},
        {"role": "user", "content": "E" * 1500},
    ]
    settings: dict[str, object] = {"memory_max_history_messages": 3, "memory_context_budget": 1000}
    summary, tail = compact_history(llm, "", messages, settings)
    assert llm.calls == 1
    assert summary == "TRACE: compaction triggered"
    assert 1 <= len(tail) <= 3


def test_run_agent_compaction_trace(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "system.md").write_text("system {{OS}} {{DATE}} {{TIME}}", encoding="utf-8")

    model = SummaryModel()
    manager = WorkspaceStub(tmp_path)
    history = [{"role": "user", "content": "X" * 3000}] * 10
    settings: dict[str, object] = {
        "project_root": str(project_root),
        "temperature": 0.0,
        "max_iters": 3,
        "safety_mode": "guarded",
        "allow_unsafe_shell": False,
        "unsafe_commands": ["rm", "rmdir", "del", "erase", "remove-item", "format", "mkfs", "shutdown"],
        "auto_rollback": False,
        "hook_pre": [],
        "hook_post": [],
        "memory_enabled": True,
        "memory_max_history_messages": 4,
        "memory_context_budget": 500,
        "compaction_enabled": True,
        "compaction_trigger_ratio": 0.6,
        "compaction_prune_tool_outputs": True,
        "compaction_tool_output_keep": 2,
        "openrouter": {},
        "azure_openai": {},
    }

    monkeypatch.setattr(agent_module, "get_llm", lambda *args, **kwargs: model)
    monkeypatch.setattr(agent_module, "build_tools", lambda **kwargs: [])
    monkeypatch.setattr(agent_module, "load_rules", lambda *args, **kwargs: "")
    monkeypatch.setattr(agent_module, "create_agent", lambda **kwargs: EchoAgent())

    output, fresh, summary, pruned = agent_module.run_agent(
        prompt="compact this",
        provider="stub",
        model="stub",
        workspace_manager=manager,
        settings=settings,
        history=history,
        summary_text="",
        verbose=False,
    )
    assert output == "ok"
    assert model.calls == 1, "TRACE: compaction was not triggered in run_agent."
    assert summary == "TRACE: compaction triggered"
    assert len(pruned) <= 4
    assert estimate_messages_tokens(pruned, summary) < estimate_messages_tokens(history, "")
    assert fresh


def test_run_agent_keeps_user_assistant_history_under_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "system.md").write_text("system {{OS}} {{DATE}} {{TIME}}", encoding="utf-8")

    model = SummaryModel()
    capture = CaptureAgent()
    manager = WorkspaceStub(tmp_path)
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply1"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "reply2"},
    ]
    settings: dict[str, object] = {
        "project_root": str(project_root),
        "temperature": 0.0,
        "max_iters": 3,
        "safety_mode": "guarded",
        "allow_unsafe_shell": False,
        "unsafe_commands": ["rm", "rmdir", "del", "erase", "remove-item", "format", "mkfs", "shutdown"],
        "auto_rollback": False,
        "hook_pre": [],
        "hook_post": [],
        "memory_enabled": True,
        "memory_max_history_messages": 20,
        "memory_context_budget": 150000,
        "compaction_enabled": True,
        "compaction_trigger_ratio": 0.8,
        "compaction_prune_tool_outputs": True,
        "compaction_tool_output_keep": 10,
        "openrouter": {},
        "azure_openai": {},
    }

    monkeypatch.setattr(agent_module, "get_llm", lambda *args, **kwargs: model)
    monkeypatch.setattr(agent_module, "build_tools", lambda **kwargs: [])
    monkeypatch.setattr(agent_module, "load_rules", lambda *args, **kwargs: "")
    monkeypatch.setattr(agent_module, "create_agent", lambda **kwargs: capture)

    output, _, _, _ = agent_module.run_agent(
        prompt="third",
        provider="stub",
        model="stub",
        workspace_manager=manager,
        settings=settings,
        history=history,
        summary_text="",
        verbose=False,
    )
    assert output == "ok"
    sent = [str(getattr(item, "content", "")) for item in capture.messages]
    assert sent == ["first", "reply1", "second", "reply2", "third"]
