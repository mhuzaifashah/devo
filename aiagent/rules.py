import os


RULE_FILENAMES = [".aiagentrules", ".aiagent_rules.md", "AGENTS.md"]


def _read_rule_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else None
    except Exception:
        return None


def load_rules(project_root, workspace_manager):
    sections = []
    checked = set()

    for filename in RULE_FILENAMES:
        path = os.path.join(project_root, filename)
        if os.path.isfile(path):
            content = _read_rule_file(path)
            if content:
                sections.append(f"[Rules: {filename} @ project]\n{content}")
                checked.add(path)

    for name, root in workspace_manager.list():
        for filename in RULE_FILENAMES:
            path = os.path.join(root, filename)
            if path in checked or not os.path.isfile(path):
                continue
            content = _read_rule_file(path)
            if content:
                sections.append(f"[Rules: {filename} @ {name}]\n{content}")
                checked.add(path)

    return "\n\n".join(sections)
