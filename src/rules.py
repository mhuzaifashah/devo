import os

RULE_FILENAMES = [".aiagentrules", ".aiagent_rules.md", "AGENTS.md"]


def rule_read(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read().strip()
    except Exception:
        return None
    if content:
        return content
    return None


def load_rules(project_root: str, workspace_manager: object) -> str:
    sections: list[str] = []
    checked: set[str] = set()

    for filename in RULE_FILENAMES:
        path = os.path.join(project_root, filename)
        if not os.path.isfile(path):
            continue
        content = rule_read(path)
        if not content:
            continue
        sections.append(f"[Rules: {filename} @ project]\n{content}")
        checked.add(path)

    for name, root in workspace_manager.list():
        for filename in RULE_FILENAMES:
            path = os.path.join(root, filename)
            if path in checked or not os.path.isfile(path):
                continue
            content = rule_read(path)
            if not content:
                continue
            sections.append(f"[Rules: {filename} @ {name}]\n{content}")
            checked.add(path)

    return "\n\n".join(sections)
