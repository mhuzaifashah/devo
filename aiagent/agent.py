import os
import platform
from datetime import datetime

from langchain.agents.factory import create_agent
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain_core.messages import AIMessage, HumanMessage

from aiagent.compaction import compact_history, estimate_messages_tokens, prune_tool_outputs
from aiagent.providers import get_llm
from aiagent.rules import load_rules
from aiagent.tools import build_tools




def _render_system_prompt(content):
    now = datetime.now().astimezone()
    replacements = {
        "{{OS}}": f"{platform.system()} {platform.release()}".strip(),
        "{{DATE}}": now.date().isoformat(),
        "{{TIME}}": now.time().replace(microsecond=0).isoformat(),
    }
    rendered = content
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def _load_system_prompt(project_root):
    system_path = os.path.join(project_root, "system.md")
    try:
        with open(system_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except Exception as e:
        raise ValueError(f"Failed to load system prompt: {e}")
    if not content:
        raise ValueError("System prompt is empty. Populate system.md.")
    return _render_system_prompt(content)


def _extract_output(result):
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return getattr(last, "content", "") or ""


def _build_system_prompt(base_prompt, rules_text, workspaces, safety_mode, summary_text=None):
    workspace_lines = "\n".join([f"- {name}: {path}" for name, path in workspaces])
    safety_note = (
        "Safety mode: overdrive. Unsafe shell commands are enabled."
        if safety_mode == "overdrive"
        else "Safety mode: guarded. Prefer safe tools and avoid destructive commands."
    )
    prompt_parts = [
        base_prompt,
        "Available workspaces:",
        workspace_lines or "- none",
        "When calling tools, pass the 'workspace' argument if you need a non-default root.",
        "Never use destructive shell commands (rm/del/Remove-Item).",
        safety_note,
    ]
    if rules_text:
        prompt_parts.append("Rules:")
        prompt_parts.append(rules_text)
    if summary_text:
        prompt_parts.append("Session summary:")
        prompt_parts.append(summary_text.strip())
    return "\n".join(prompt_parts)


def _to_lc_messages(history):
    messages = []
    for msg in history or []:
        role = msg.get("role")
        content = msg.get("content") or ""
        if role == "user":
            messages.append(HumanMessage(content))
        elif role == "assistant":
            messages.append(AIMessage(content))
        elif role == "tool":
            try:
                from langchain_core.messages import ToolMessage

                messages.append(ToolMessage(content=content, name=msg.get("name")))
            except Exception:
                messages.append(AIMessage(content))
    return messages


def _serialize_message(message):
    msg_type = getattr(message, "type", "")
    content = getattr(message, "content", "") or ""
    name = getattr(message, "name", None)
    if msg_type == "human":
        role = "user"
    elif msg_type == "ai":
        role = "assistant"
    elif msg_type == "tool":
        role = "tool"
    elif msg_type == "system":
        role = "system"
    else:
        role = "assistant"
    return {"role": role, "content": content, "name": name}


def run_agent(prompt, provider, model, workspace_manager, settings, history=None, summary_text=None, verbose=False):
    provider_key = provider
    if provider in {"open_router", "openrouter"}:
        provider_key = "openrouter"
    elif provider in {"azure_openai", "azure-openai"}:
        provider_key = "azure_openai"

    llm = get_llm(
        provider,
        model,
        temperature=settings["temperature"],
        settings=settings.get(provider_key) or {},
    )
    tools = build_tools(
        workspace_manager=workspace_manager,
        settings=settings,
    )
    rules_text = load_rules(settings["project_root"], workspace_manager)

    history = history or []
    summary_text = summary_text or ""
    if not settings.get("memory_enabled"):
        history = []
        summary_text = ""
    if settings.get("memory_enabled") and settings.get("compaction_enabled"):
        budget = settings.get("memory_context_budget", 150000)
        ratio = settings.get("compaction_trigger_ratio", 0.8)
        tool_keep = settings.get("compaction_tool_output_keep", 5)
        pruned = history
        if settings.get("compaction_prune_tool_outputs"):
            pruned = prune_tool_outputs(history, keep=tool_keep)
        token_est = estimate_messages_tokens(pruned, summary_text) + int(len(prompt) / 4)
        if budget and token_est > int(budget * ratio):
            summary_text, pruned = compact_history(llm, summary_text, pruned, settings)
            history = pruned
        else:
            history = pruned

    base_prompt = _load_system_prompt(settings["project_root"])
    system_prompt = _build_system_prompt(
        base_prompt, rules_text, workspace_manager.list(), settings["safety_mode"], summary_text
    )

    middleware = [
        ToolCallLimitMiddleware(run_limit=settings["max_iters"], exit_behavior="end")
    ]
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        debug=verbose,
    )
    input_messages = _to_lc_messages(history) + [HumanMessage(prompt)]
    result = agent.invoke({"messages": input_messages})
    output = _extract_output(result)

    result_messages = result.get("messages", [])
    new_messages = []
    if len(result_messages) > len(input_messages):
        for msg in result_messages[len(input_messages) :]:
            serialized = _serialize_message(msg)
            if serialized["role"] != "system":
                new_messages.append(serialized)
    else:
        new_messages.append({"role": "assistant", "content": output})

    return output, new_messages, summary_text, history
