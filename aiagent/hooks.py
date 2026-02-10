import importlib.util
import os


class HookManager:
    def __init__(self, hook_paths, project_root):
        self._hooks = []
        for path in hook_paths:
            full_path = path
            if not os.path.isabs(path):
                full_path = os.path.join(project_root, path)
            if os.path.isfile(full_path):
                module = _load_module_from_path(full_path)
                if module:
                    self._hooks.append(module)

    def before_tool_call(self, context):
        for hook in self._hooks:
            func = getattr(hook, "before_tool_call", None)
            if not func:
                continue
            result = func(context)
            if result is False:
                return False, "Blocked by hook."
            if isinstance(result, dict) and result.get("allow") is False:
                return False, result.get("reason", "Blocked by hook.")
        return True, None

    def after_tool_call(self, context):
        for hook in self._hooks:
            func = getattr(hook, "after_tool_call", None)
            if func:
                func(context)


def _load_module_from_path(path):
    module_name = f"aiagent_hook_{os.path.splitext(os.path.basename(path))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
