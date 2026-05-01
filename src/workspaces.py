import os
import subprocess


class Workspace:
    def __init__(self, project_root: str, workspaces: dict[str, str], default_name: str) -> None:
        self.project_root = project_root
        self.workspaces = workspaces
        if default_name in workspaces:
            self.default_name = default_name
        else:
            self.default_name = next(iter(workspaces))

    def list(self) -> list[tuple[str, str]]:
        return [(name, path) for name, path in self.workspaces.items()]

    def get(self, name: str | None = None) -> str:
        if name is None:
            name = self.default_name
        if name not in self.workspaces:
            raise KeyError(f"Unknown workspace '{name}'. Available: {list(self.workspaces)}")
        return self.workspaces[name]


def path_resolve(project_root: str, path: str | None) -> str | None:
    if path is None:
        return None
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(project_root, path))


def worktrees_load(project_root: str) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return {}

    if result.returncode != 0:
        return {}

    worktrees: dict[str, str] = {}
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current.get("path"):
                name = current.get("name") or os.path.basename(current["path"])
                worktrees[name] = current["path"]
            current = {"path": line.split(" ", 1)[1].strip()}
            continue

        if line.startswith("branch "):
            branch = line.split(" ", 1)[1].strip()
            name = branch.rsplit("/", 1)[-1]
            current["name"] = f"wt_{name}"
            continue

        if line.startswith("detached"):
            current["name"] = "wt_detached"

    if current.get("path"):
        name = current.get("name") or os.path.basename(current["path"])
        worktrees[name] = current["path"]

    return worktrees


def build_workspace_manager(settings: dict[str, object]) -> Workspace:
    project_root = str(settings["project_root"])

    workspaces: dict[str, str] = {}
    primary = settings.get("primary_workspace")
    if primary:
        resolved = path_resolve(project_root, str(primary))
        if resolved:
            workspaces["primary"] = resolved

    extras = settings.get("extra_workspaces", [])
    if isinstance(extras, list):
        for index, extra in enumerate(extras, start=1):
            resolved = path_resolve(project_root, str(extra))
            if resolved:
                workspaces[f"ws_{index}"] = resolved

    if settings.get("use_git_worktrees"):
        worktrees = worktrees_load(project_root)
        for name, path in worktrees.items():
            if path in workspaces.values():
                continue
            workspaces[name] = os.path.abspath(path)

    if not workspaces:
        workspaces["primary"] = project_root

    default_name = str(settings.get("default_workspace") or "primary")
    return Workspace(project_root, workspaces, default_name)


WorkspaceManager = Workspace
