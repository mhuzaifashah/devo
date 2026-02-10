import os
import subprocess


class WorkspaceManager:
    def __init__(self, project_root, workspaces, default_name):
        self.project_root = project_root
        self._workspaces = workspaces
        self._default_name = (
            default_name if default_name in workspaces else next(iter(workspaces))
        )

    @property
    def default_name(self):
        return self._default_name

    def list(self):
        return [(name, path) for name, path in self._workspaces.items()]

    def get(self, name=None):
        if name is None:
            name = self._default_name
        if name not in self._workspaces:
            raise KeyError(f"Unknown workspace '{name}'. Available: {list(self._workspaces)}")
        return self._workspaces[name]


def _resolve_path(project_root, path):
    if path is None:
        return None
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(project_root, path))


def _load_git_worktrees(project_root):
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

    worktrees = {}
    current = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current.get("path"):
                name = current.get("name") or os.path.basename(current["path"])
                worktrees[name] = current["path"]
            current = {"path": line.split(" ", 1)[1].strip()}
        elif line.startswith("branch "):
            branch = line.split(" ", 1)[1].strip()
            name = branch.rsplit("/", 1)[-1]
            current["name"] = f"wt_{name}"
        elif line.startswith("detached"):
            current["name"] = "wt_detached"

    if current.get("path"):
        name = current.get("name") or os.path.basename(current["path"])
        worktrees[name] = current["path"]

    return worktrees


def build_workspace_manager(settings):
    project_root = settings["project_root"]

    workspaces = {}
    primary = settings.get("primary_workspace")
    if primary:
        workspaces["primary"] = _resolve_path(project_root, primary)

    for idx, extra in enumerate(settings.get("extra_workspaces", []), start=1):
        name = f"ws_{idx}"
        workspaces[name] = _resolve_path(project_root, extra)

    if settings.get("use_git_worktrees"):
        worktrees = _load_git_worktrees(project_root)
        for name, path in worktrees.items():
            if path not in workspaces.values():
                workspaces[name] = os.path.abspath(path)

    if not workspaces:
        workspaces["primary"] = project_root

    default_name = settings.get("default_workspace") or "primary"

    return WorkspaceManager(project_root, workspaces, default_name)
