from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

Message = dict[str, object]

SUMMARY_SYSTEM_PROMPT = """Summarize the conversation for future context.

Focus on:
- Goals
- Decisions
- Files changed
- Tests run
- TODOs / next steps
- Chronological list of important user requests
- Key assistant outcomes tied to those requests

Be concise and avoid repetition.
"""


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def estimate_messages_tokens(messages: list[Message], summary_text: str = "") -> int:
    total = estimate_tokens(summary_text)
    for msg in messages:
        content = str(msg.get("content") or "")
        total += estimate_tokens(content)
    return total


def prune_tool_outputs(messages: list[Message], keep: int | None = 10) -> list[Message]:
    if keep is None:
        return messages
    indices = [index for index, item in enumerate(messages) if item.get("role") == "tool"]
    if len(indices) <= keep:
        return messages
    remove = set(indices[: len(indices) - keep])
    return [item for index, item in enumerate(messages) if index not in remove]


def to_chat_messages(messages: list[Message]) -> list[object]:
    rows: list[object] = []
    for msg in messages:
        role = str(msg.get("role") or "")
        content = str(msg.get("content") or "")
        if role == "user":
            rows.append(HumanMessage(content))
            continue
        if role == "assistant":
            rows.append(AIMessage(content))
            continue
        if role == "tool":
            try:
                from langchain_core.messages import ToolMessage

                rows.append(ToolMessage(content=content, name=msg.get("name")))
                continue
            except Exception:
                rows.append(AIMessage(content))
                continue
        rows.append(AIMessage(content))
    return rows


def estimate_text_tokens(llm: object, text: str) -> int:
    if not text:
        return 0
    method = getattr(llm, "get_num_tokens", None)
    if callable(method):
        try:
            return max(1, int(method(text)))
        except Exception:
            return estimate_tokens(text)
    return estimate_tokens(text)


def estimate_history_tokens(llm: object, messages: list[Message]) -> int:
    if not messages:
        return 0
    method = getattr(llm, "get_num_tokens_from_messages", None)
    if callable(method):
        try:
            rows = to_chat_messages(messages)
            return max(1, int(method(rows)))
        except Exception:
            return estimate_messages_tokens(messages)
    return estimate_messages_tokens(messages)


def estimate_context_tokens(
    llm: object,
    messages: list[Message],
    summary_text: str,
    next_prompt: str = "",
) -> int:
    return (
        estimate_text_tokens(llm, summary_text)
        + estimate_history_tokens(llm, messages)
        + estimate_text_tokens(llm, next_prompt)
    )


def split_for_compaction(
    llm: object,
    messages: list[Message],
    summary_text: str,
    budget: int,
) -> tuple[list[Message], list[Message]]:
    if not messages:
        return [], []

    summary_tokens = estimate_text_tokens(llm, summary_text)
    target = max(1, int(budget * 0.5))
    keep_start = len(messages)
    for index in range(len(messages) - 1, -1, -1):
        tail = messages[index:]
        tail_tokens = estimate_history_tokens(llm, tail)
        if summary_tokens + tail_tokens > target:
            break
        keep_start = index
    return messages[:keep_start], messages[keep_start:]


def transcript_build(summary_text: str, messages: list[Message]) -> str:
    lines: list[str] = []
    if summary_text:
        lines.append("[Prior summary]")
        lines.append(summary_text.strip())
    for msg in messages:
        role = str(msg.get("role", "unknown")).upper()
        content = str(msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()


def compact_history(
    llm: object,
    summary_text: str,
    messages: list[Message],
    settings: dict[str, object],
) -> tuple[str, list[Message]]:
    budget = int(settings.get("memory_context_budget") or 150000)
    source, tail = split_for_compaction(llm, messages, summary_text, budget)
    if not source:
        max_history = int(settings.get("memory_max_history_messages", 20))
        if max_history and len(tail) > max_history:
            return summary_text, tail[-max_history:]
        return summary_text, tail

    transcript = transcript_build(summary_text, source)
    if not transcript:
        return summary_text, tail
    try:
        response = llm.invoke(
            [
                SystemMessage(SUMMARY_SYSTEM_PROMPT),
                HumanMessage(transcript),
            ]
        )
        new_summary = str(getattr(response, "content", "")).strip()
    except Exception:
        new_summary = summary_text or ""

    if not new_summary:
        new_summary = summary_text or ""

    max_history = int(settings.get("memory_max_history_messages", 20))
    if max_history and len(tail) > max_history:
        tail = tail[-max_history:]
    return new_summary, tail
