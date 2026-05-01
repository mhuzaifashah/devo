import importlib.util
import os
from types import ModuleType


class Hook:
    def __init__(self, hook_paths: list[str], project_root: str) -> None:
        self.hooks: list[ModuleType] = []
        for path in hook_paths:
            full_path = path
            if not os.path.isabs(path):
                full_path = os.path.join(project_root, path)
            if not os.path.isfile(full_path):
                continue
            module = module_load(full_path)
            if module:
                self.hooks.append(module)

    def before_tool_call(self, context: dict[str, object]) -> tuple[bool, str | None]:
        for hook in self.hooks:
            func = getattr(hook, "before_tool_call", None)
            if not func:
                continue
            result = func(context)
            if result is False:
                return False, "Blocked by hook."
            if isinstance(result, dict) and result.get("allow") is False:
                return False, str(result.get("reason", "Blocked by hook."))
        return True, None

    def after_tool_call(self, context: dict[str, object]) -> None:
        for hook in self.hooks:
            func = getattr(hook, "after_tool_call", None)
            if not func:
                continue
            func(context)


def module_load(path: str) -> ModuleType | None:
    module_name = f"aiagent_hook_{os.path.splitext(os.path.basename(path))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HookManager = Hook
