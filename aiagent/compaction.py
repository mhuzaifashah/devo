from langchain_core.messages import HumanMessage, SystemMessage


SUMMARY_SYSTEM_PROMPT = """Summarize the conversation for future context.

Focus on:
- Goals
- Decisions
- Files changed
- Tests run
- TODOs / next steps

Be concise and avoid repetition.
"""


def estimate_tokens(text):
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def estimate_messages_tokens(messages, summary_text=""):
    total = estimate_tokens(summary_text)
    for msg in messages:
        content = msg.get("content") or ""
        total += estimate_tokens(content)
    return total


def prune_tool_outputs(messages, keep=5):
    if keep is None:
        return messages
    tool_indices = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
    if len(tool_indices) <= keep:
        return messages
    to_remove = set(tool_indices[: len(tool_indices) - keep])
    return [m for i, m in enumerate(messages) if i not in to_remove]


def _build_transcript(summary_text, messages):
    lines = []
    if summary_text:
        lines.append("[Prior summary]")
        lines.append(summary_text.strip())
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()


def compact_history(llm, summary_text, messages, settings):
    transcript = _build_transcript(summary_text, messages)
    if not transcript:
        return summary_text or "", messages
    try:
        response = llm.invoke(
            [
                SystemMessage(SUMMARY_SYSTEM_PROMPT),
                HumanMessage(transcript),
            ]
        )
        new_summary = getattr(response, "content", "").strip()
    except Exception:
        new_summary = summary_text or ""

    max_history = settings.get("memory_max_history_messages", 20)
    trimmed = messages[-max_history:] if max_history else messages
    return new_summary, trimmed
